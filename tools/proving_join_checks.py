"""Checks for tools/proving_join.py -- adding up the parts of one proving run (PV1)."""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import proving_join as pj  # noqa: E402

ran = 0
failures = []


def check(name, passed):
    global ran
    ran += 1
    print(f"{'PASS' if passed else 'FAIL'}  {name}")
    if not passed:
        failures.append(name)


def log(tried, run, caught, crashed, unparsed, hung, survived, accepted=0, extra="", word=pj.LAST_WORD):
    return (f"prove_checks: {tried} deliberate changes across 3 file(s), 1 at a time. This takes a while.\n\n"
            f"  changes tried      {tried}\n  actually run       {run} (the rest would not parse)\n  caught by a check  {caught}\n"
            f"  ended in a crash   {crashed} (noticed, but by the file failing to load)\n"
            f"  would not parse    {unparsed} (discarded, not counted as caught)\n  hung and stopped   {hung} (counted as caught)\n"
            f"  survived           {survived}\n  survived, accepted {accepted}\n\n{extra}{word}\n")


a, b = log(100, 70, 68, 1, 30, 1, 0), log(204, 143, 141, 3, 61, 0, 0)
totals, findings, problems = pj.join([a, b])
check("the counts of the parts are added, label by label, the way one whole run would have printed them",
      totals["changes tried"] == 304 and totals["actually run"] == 213 and totals["caught by a check"] == 209
      and totals["ended in a crash"] == 4 and totals["would not parse"] == 91 and totals["hung and stopped"] == 1
      and totals["survived"] == 0 and not findings and not problems)
check("'survived' is not read from the 'survived, accepted' line, nor the other way round",
      pj.read_part(log(5, 5, 4, 0, 0, 0, 1, 7))[0]["survived"] == 1 and pj.read_part(log(5, 5, 4, 0, 0, 0, 1, 7))[0]["survived, accepted"] == 7)

lost = pj.join([a, None])[2]
check("A PART WITH NO LOG IS A PART THAT DID NOT RUN, and a sum over fewer parts is never passed off as the whole run",
      len(lost) == 1 and "part 2" in lost[0])
check("a part with no counts and no reason to have none did not finish", "did not finish" in pj.join([a, "Traceback ..."])[2][0])
check("a part with counts but not the prover's last word, and nothing found, did not finish properly",
      "last word" in pj.join([a, log(3, 3, 3, 0, 0, 0, 0, word="")])[2][0])

bad = log(10, 10, 9, 0, 0, 0, 1, extra="NOT PROVEN  autosync/x.py:5  (flip)\n            line\n", word="\n1 change(s) no check noticed")
t2, f2, p2 = pj.join([a, bad])
check("a change no check noticed in ANY part is a finding of the whole run, named by its part",
      len(f2) == 1 and f2[0].startswith("part 2: NOT PROVEN") and t2["survived"] == 1 and not p2)

empty = log(0, 0, 0, 0, 0, 0, 0, extra="COVERAGE    there are 2 file(s) in scope and not one deliberate change to try on them.\n",
            word="\n0 change(s) no check noticed, 0 that stopped, 0 stale entr(ies), 1 coverage problem(s).")
t3, f3, p3 = pj.join([a, empty])
check("a share that holds no changed line is empty, not a failure, when other parts tried changes",
      t3["changes tried"] == 100 and not f3 and not p3)
check("but if no part tried anything the run measured nothing and says so", "not one change" in pj.join([empty, empty])[2][-1])

only = log(0, 0, 0, 0, 0, 0, 0, word="prove_checks: nothing was broken on purpose, because this change adds no source lines. See above.")
check("a change to checks files only, split over parts, is a pass that says nothing was broken, as one whole run is; one such part among parts that tried changes is too",
      pj.join([only, only])[2] == [] and pj.join([a, only])[2] == [] and "not one change" in pj.join([only, empty])[2][-1])
same = log(5, 5, 5, 0, 0, 0, 0, extra="STALE       autosync/x.py  (flip)\n", word="\n1 stale entr(ies).")
check("a finding the prover makes about a whole file, printed by every part, is told once", len(pj.join([same, same, same])[1]) == 1)

with tempfile.TemporaryDirectory() as folder:
    for number, text in ((1, a), (2, b)):
        (Path(folder) / f"part-{number}.log").write_text(text, encoding="utf-8")
    check("main reads part-1.log .. part-N.log and passes when all answered", pj.main([folder, "2"]) == 0)
    check("main fails when N says there should be a third log and there is none", pj.main([folder, "3"]) == 1)
check("main refuses arguments it does not understand", pj.main([]) == 2 and pj.main(["x", "0"]) == 2)

EXPECTED = 13
if ran != EXPECTED:
    print(f"FAIL  checks went missing -- {ran} ran, {EXPECTED} expected")
    failures.append("count")

print(f"\n{len(failures)} FAILED ({ran} checks)" if failures else f"\nall {ran} checks passed")
sys.exit(1 if failures else 0)
