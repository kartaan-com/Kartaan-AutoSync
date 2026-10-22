"""Point a group branch (group-1/2/3) at a released version tag -- prints, never pushes (A88, D426).

A seller's pipeline names a GROUP, never a version. A group only ever points at a
released `vX.Y.Z` tag, and this tool is how it is moved after a release. It READS
GitHub (tags, releases, where each group points) and PRINTS the exact push command.
Kartaan Control or the owner runs that command; this file writes nothing anywhere.

    python tools/move_group.py group-1 v0.1.21        refuse, or print the command
    python tools/move_group.py group-1 v0.1.19 --rollback
    python tools/move_group.py --check                where each group points now
"""
import json
import re
import subprocess
import sys
from dataclasses import dataclass

REPO = "kartaan-com/Kartaan-AutoSync"
GROUPS = ("group-1", "group-2", "group-3")
BURNT = ("v0.1.0",)  # A41: fetches the wrong repository on every night.
TAG = re.compile(r"v([0-9]+)\.([0-9]+)\.([0-9]+)", re.ASCII)


@dataclass
class Facts:
    tags: dict      # tag name -> commit it points at
    releases: dict  # tag name -> "published" | "draft" | "prerelease"
    groups: dict    # group name -> tag it points at now, or None
    branches: dict  # branch name -> commit (names that exist as branches)


def _version(tag):
    return tuple(int(x) for x in TAG.fullmatch(tag).groups())


def refusals(group, tag, facts, rollback=False):
    """Every reason this move must not happen; empty means it may."""
    if group not in GROUPS:
        return [f"{group!r} is not a group; the groups are {', '.join(GROUPS)}"]
    if not TAG.fullmatch(tag):
        return [f"{tag!r} is not a whole version tag like v0.1.20"]
    if tag in BURNT:
        return [f"{tag} is burnt and must never be handed to a seller (A41)"]
    if tag not in facts.tags:
        why = "exists only as a branch, not a tag" if tag in facts.branches else "is not a tag in the repository"
        return [f"{tag} {why}"]
    state = facts.releases.get(tag)
    if state != "published":
        return [f"{tag} has no published release ({state or 'none found'}); a group only follows released versions"]
    now = facts.groups.get(group)
    if now == tag:
        return [f"{group} already points at {tag}; nothing to do"]
    going_back = bool(now) and _version(tag) < _version(now)
    if going_back and not rollback:
        return [f"{group} is at {now}; moving it back to {tag} needs --rollback"]
    if rollback and not going_back:
        return ["--rollback only moves a group to an OLDER version; this one is not older"]
    if group != GROUPS[0] and not rollback:
        ahead = facts.groups.get(GROUPS[GROUPS.index(group) - 1])
        if not ahead or _version(tag) > _version(ahead):
            return [f"{group} may not run ahead of {GROUPS[GROUPS.index(group) - 1]} (at {ahead}); move that one first"]
    return []


def commands(group, tag, facts, rollback=False):
    """The one command that makes the move. Printed, not run.

    It names the commit GitHub itself reported for the tag, so a stale or missing
    local copy of the tag cannot change what is pushed, and nothing local is needed.
    A group not yet created is created; one that exists is moved (forced, because a
    rollback or a fix tag on a side line is not a plain step forward).
    """
    sha = facts.tags[tag]
    if group in facts.branches:
        return [f"gh api -X PATCH repos/{REPO}/git/refs/heads/{group} -f sha={sha} -F force=true"]
    return [f"gh api -X POST repos/{REPO}/git/refs -f ref=refs/heads/{group} -f sha={sha}"]


def farewell():
    return "I ran nothing on GitHub. Run the command above yourself, then run --check."


def _read(*args):
    done = subprocess.run(args, capture_output=True, text=True, check=False)
    if done.returncode:
        sys.exit(f"could not read from GitHub: {' '.join(args)}\n{done.stderr.strip()}")
    return done.stdout


def gather():
    url = f"https://github.com/{REPO}.git"
    refs = {}
    for line in _read("git", "ls-remote", "--tags", "--heads", url).splitlines():
        sha, ref = line.split("\t")
        refs[ref] = sha
    tags = {}
    for ref, sha in refs.items():
        if ref.startswith("refs/tags/"):
            name = ref[len("refs/tags/"):]
            if name.endswith("^{}"):
                tags[name[:-3]] = sha  # the commit an annotated tag points at
            else:
                tags.setdefault(name, sha)
    branches = {r[len("refs/heads/"):]: s for r, s in refs.items() if r.startswith("refs/heads/")}
    releases = {}
    for item in json.loads(_read("gh", "release", "list", "--repo", REPO, "--limit", "200",
                                 "--json", "tagName,isDraft,isPrerelease")):
        releases[item["tagName"]] = ("draft" if item["isDraft"] else
                                     "prerelease" if item["isPrerelease"] else "published")
    groups = {}
    for g in GROUPS:
        sha = branches.get(g)
        groups[g] = max((t for t, s in tags.items() if s == sha and TAG.fullmatch(t)), key=_version, default=None) if sha else None
    return Facts(tags, releases, groups, branches)


def main(argv):
    if argv == ["--check"]:
        facts = gather()
        for g in GROUPS:
            print(f"{g}: {facts.groups[g] or ('NOT AT A RELEASED TAG' if g in facts.branches else 'does not exist yet')}")
        return 0
    rollback = "--rollback" in argv
    rest = [a for a in argv if a != "--rollback"]
    if len(rest) != 2:
        print(__doc__)
        return 2
    group, tag = rest
    facts = gather()
    wrong = refusals(group, tag, facts, rollback)
    if wrong:
        print("REFUSED:\n  " + "\n  ".join(wrong))
        return 1
    print(f"OK. To point {group} at {tag}, run:\n")
    print("\n".join(commands(group, tag, facts, rollback)))
    print("\n" + farewell())
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
