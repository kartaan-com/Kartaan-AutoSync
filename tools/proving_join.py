"""Adds up the answers of the parts of one proving run (PV1): each part is `tools/proving.py --part i/N`, run on its own machine.

The ERP's prover prints a block of counts and then any NOT PROVEN / STALE / CRASHED / COVERAGE lines. A whole run on one machine prints one
such block; N parts print N, each over its own share of the changed lines. This file reads the N logs and prints the one block the whole
run would have printed, so the comparison with a run on the Dell is a comparison of the same lines.

    python tools/proving_join.py <folder holding part-1.log ... part-N.log> <N>

**IT SAYS NO UNLESS EVERY PART ANSWERED.** A missing log, a log with no counts, or a part that ended with something other than the prover's
own last word is a part that did not run, and a sum over fewer parts than were asked for would read as a smaller, passing run.
"""
import re
import sys
from pathlib import Path

# The counts, in the order the prover prints them (the labels are the prover's own).
COUNTS = ("changes tried", "actually run", "caught by a check", "ended in a crash", "would not parse", "hung and stopped",
          "survived", "survived, accepted")
# The lines the prover prints for each thing it found; any of them in any part is a finding of the whole run.
FINDINGS = ("NOT PROVEN", "STALE", "CRASHED", "COVERAGE")
# A share can be empty: with few changed lines, some line numbers (mod N) hold none.
EMPTY_SHARE = "not one deliberate change"
CHECKS_ONLY = "nothing was broken on purpose, because this change adds no"
LAST_WORD ="every deliberate change was either caught or recorded with a reason"


def checks_only(text: str) -> bool:
    """The prover's last word for a change that touches checks files and no source: nothing to break, said in its own words."""
    return CHECKS_ONLY in text


def read_part(text: str):
    """(counts, findings, said_the_last_word) for one part's log; counts is None when the log holds no count block."""
    counts = {}
    for label in COUNTS:
        # "  survived           0" must not be read as the start of "  survived, accepted   0"
        hit = re.search(rf"^  {re.escape(label)}\s+(\d+)\b", text, re.M)
        if hit:
            counts[label] = int(hit.group(1))
    findings = [line.strip() for line in text.splitlines() if line.startswith(FINDINGS)]
    return (counts if len(counts) == len(COUNTS) else None), findings, LAST_WORD in text


def join(logs):
    """(totals, findings, problems) over the parts' logs, in part order. problems is empty only when every part answered."""
    totals = dict.fromkeys(COUNTS, 0)
    findings, problems, seen, only_checks = [], [], set(), 0
    for number, text in enumerate(logs, 1):
        if text is None:
            problems.append(f"part {number} left no log, so it did not run")
            continue
        counts, found, finished = read_part(text)
        if counts is None:
            problems.append(f"part {number} printed no counts, so it did not finish")
            continue
        for label in COUNTS:
            totals[label] += counts[label]
        # An empty share prints its own COVERAGE line (the prover wants a change to try); the other parts decide whether the run tried any.
        # The checks the prover makes on the whole file (stale entries, missing checks) print in every part: told once.
        for line in found:
            if not (line.startswith("COVERAGE") and EMPTY_SHARE in line) and line not in seen:
                seen.add(line)
                findings.append(f"part {number}: {line}")
        if not finished and not found and not checks_only(text):
            problems.append(f"part {number} printed its counts but not the prover's last word")
        elif checks_only(text):
            only_checks += 1
    if totals["changes tried"] == 0 and only_checks != len(logs):
        problems.append("not one change was tried in any part")
    return totals, findings, problems


def main(argv):
    if len(argv) != 2 or not argv[1].isdigit() or int(argv[1]) < 1:
        print("usage: proving_join.py <folder with part-1.log ... part-N.log> <N>", file=sys.stderr)
        return 2
    folder, many = Path(argv[0]), int(argv[1])
    logs = []
    for number in range(1, many + 1):
        path = folder / f"part-{number}.log"
        logs.append(path.read_text(encoding="utf-8", errors="replace") if path.is_file() else None)
    totals, findings, problems = join(logs)
    print(f"proving_join: {many} part(s) added up")
    print()
    for label in COUNTS:
        print(f"  {label:<18} {totals[label]}")
    print()
    for line in findings + [f"PART PROBLEM  {one}" for one in problems]:
        print(line)
    if findings or problems:
        print(f"\n{len(findings)} finding(s), {len(problems)} part problem(s).")
        return 1
    print(LAST_WORD)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
