# Moving sellers to a new version: the three groups (A88, D392 / D424 / D426)

A seller's nightly file does not name a version. It names a **group**: `group-1`,
`group-2` or `group-3`. Each group is a label that points at one released version.
After a release, Kartaan moves the labels, and every seller's next night runs the
new version by itself. Nobody edits a seller's file again.

| Group | Who | Moved |
|---|---|---|
| group-1 | Rumee (his own pipeline) | right after a release |
| group-2 | the next sellers | after group-1 has had one quiet night |
| group-3 | everyone else | after group-2 has had one quiet night |

The tool refuses to move a group to anything that is not a published release, to
move group-2 or group-3 past the one before it, or to move a group backwards
(unless told it is a rollback, and a rollback only ever goes to an older version).

## After every release (Kartaan Control, with the owner's login)

Run these in any copy of this repository, signed in to GitHub with `gh auth login`
as the owner. The printed command names the exact commit GitHub holds for the
version, so nothing in your own copy needs to be up to date.

1. Ask the tool; it reads GitHub and prints one command. It changes nothing:

       python tools/move_group.py group-1 v0.1.21

2. Run the command it printed. Then check:

       python tools/move_group.py --check

3. One quiet night later: the same two steps for `group-2`. One more: `group-3`.
4. **Rollback** (a bad version): `python tools/move_group.py group-2 v0.1.20 --rollback`
   prints a command that moves only that group back. Do it for every group already on the bad version (order does not matter for a rollback).

## group-1 moves by itself on a release (AJ9 piece 5)

When a release is **published**, `.github/workflows/move-group-1.yml` points `group-1` at it, using the same
refusals as the tool above (published release only, never `v0.1.0`, never backwards). It runs on that event
only, only in kartaan-com, with the repository's own token (no stored key). If it refuses, or GitHub refuses
the push, the job turns red and `group-1` stays where it was. It never touches group-2 or group-3.

**Steps for the owner, once** (without them the job turns red and nothing else happens). The bypass is for the whole
GitHub Actions app, not for this one workflow, so it is given ONLY to `group-1`; group-2 and group-3 stay admin-only:
github.com/kartaan-com/Kartaan-AutoSync > Settings > Rules > Rulesets >
1. Open `groups`, change its target pattern from `group-*` to two patterns: `group-2` and `group-3`. Save.
2. New branch ruleset named `group-1`. Target: Include by pattern > `group-1`. Tick: Restrict creations, Restrict
   updates, Restrict deletions, Block force pushes. Enforcement Active. Bypass list: Add bypass > "Repository admin"
   (Always allow) and Add bypass > **GitHub Actions** (Always allow). Save.
(The `versions` tag ruleset is not changed.)

## group-2 and group-3: the design (NOT built; built in the Server round when a group-2 seller exists)

- **Who counts the quiet nights:** the Server, because it sees every pipeline's `/finished` call; this repository
  cannot read other sellers' nights.
- **Rule:** two clean nights of every pipeline in the group before, then the next group moves. A bad night
  stops the move and the Server tells him (`/tell`, kind `problem`).
- **Who moves it:** a small GitHub Actions job started by the Server that proves who is calling with
  GitHub's OIDC id-token (no stored key), then runs the same refusals as `move_group.py`.
- Until then group-2 and group-3 are moved by hand as in the section above.

## One-time, by the owner on GitHub: only the owner may move a group or a version

This repository is public. Without this, anyone with write access could move a
group, or re-cut a released version, onto code that was never released.

github.com/kartaan-com/Kartaan-AutoSync > Settings > Rules > Rulesets > New ruleset.
Make two. In both: Enforcement = Active; Bypass list = Add bypass > role
"Repository admin", mode "Always allow" (nobody else).

1. **New branch ruleset** named `groups`. Target: Add target > Include by pattern > `group-*`.
   Tick all of: Restrict creations, Restrict updates, Restrict deletions, Block force pushes.
2. **New tag ruleset** named `versions`. Targets: Include by pattern > `v*` and
   Include by pattern > `group-*`. Tick: Restrict creations, Restrict updates,
   Restrict deletions, Block force pushes.
   (A released version never moves, and no tag may be named like a group.)

The owner moves groups with the bypass, which is intended. (Once group-1 follows releases by itself, `groups` covers
only `group-2` and `group-3`, and a separate `group-1` ruleset also lets the GitHub Actions app in: see above.)

## First time only: create the three groups

Before any pipeline is moved to a group, the groups must exist. Pick the release
the sellers should be on (v0.1.20 or later), then run the tool for `group-1`, then
`group-2`, then `group-3`, in that order, each with that tag (the tool refuses a
group that would run ahead of the one before it). Then `--check`.

## Moving a pipeline onto a group, once

Every pipeline has one line that says which code to run:
`uses: kartaan-com/Kartaan-AutoSync/.github/workflows/autosync.yml@v0.1.20`.
The only change is the last word, once, for ever.

- **His own (Rumeein/kartaan-pipeline)**, only after `--check` shows group-1 exists (run these in Git Bash, not PowerShell):

      gh repo clone Rumeein/kartaan-pipeline
      cd kartaan-pipeline
      sed -i 's#autosync.yml@v[0-9.]*#autosync.yml@group-1#' .github/workflows/autosync.yml
      grep -n "autosync.yml@" .github/workflows/autosync.yml    # must now end @group-1
      git commit -am "Follow group-1" && git push

  Then in Actions > Auto-sync > Run workflow once, to see it start.
- **A seller already set up:** in their `kartaan-pipeline`, open
  `.github/workflows/autosync.yml`, change the last word on the `uses:` line
  (`v0.1.20` or whichever version) to the group Kartaan gave them (`group-2` or
  `group-3`), click Commit changes. They never touch it again.
- **A new seller:** the template already says `group-1`; Kartaan changes it to
  their group when setting them up.
