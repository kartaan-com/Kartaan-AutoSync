"""Checks that the panel still looks like the product it belongs to.

Run: python tools/the_look_checks.py

**HIS INSTRUCTION, said separately from the rest of the panel work and meant:**
*"You should follow the colour and theme, all those things, from what the ERP
does."*

**SO THE ERP'S OWN TWO FILES ARE COPIED INTO `extension/from-the-erp/`, BYTE FOR
BYTE, AND THIS IS WHAT STOPS THE COPY DRIFTING.** A Chrome extension is loaded
from one folder and can read nothing outside it, so there is no importing a file
that lives in another repository: a copy is the only shape available. **A copy
that silently drifts is worth knowing about now rather than in six months** --
which is exactly what this file is for.

**WHAT HAPPENS THE DAY THE ERP RETUNES A COLOUR:** this goes red, by name, saying
which file and what to run. The panel does not quietly go on wearing last
season's brown while every ERP screen has moved.

**IT READS WHAT THE ERP HAS COMMITTED, never what is on its disk** -- see
`autosync/the_other_half.py`, which is the same door `firestore_checks.py` and
`sales_checks.py` already use. A check that goes green against work nobody has
committed is green about nothing.

**AND IT REFUSES RATHER THAN SKIPPING** when the ERP cannot be found. A check
that quietly stops checking is worse than no check, because it is still counted.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "autosync"))

from the_other_half import readFromKartaan  # noqa: E402

ran = 0
failures = []


def check(name, passed):
    global ran
    ran += 1
    print(f"{'PASS' if passed else 'FAIL'}  {name}")
    if not passed:
        failures.append(name)


# ---------------------------------------------------------------- the two copies
#
# **THE ERP'S PATH AND OURS, WRITTEN ONCE.** The message a failure prints names
# both, so somebody reading it knows what to copy where without opening this file.
THE_SAME_FILE = (
    ("src/shared/tokens/tokens.css", "extension/from-the-erp/tokens.css"),
    ("src/shared/components/button.css", "extension/from-the-erp/button.css"),
)


def _asLines(text):
    """The file as lines, so a Windows checkout and a Unix one agree.

    **THIS IS NOT LOOSENING THE CHECK.** The ERP normalises what it STORES with
    a `.gitattributes` and hands back Unix endings; this repository has no such
    file, so what is stored here is whatever bytes were written. Comparing raw
    bytes would therefore go red on a line ending nobody chose and that changes
    no colour -- which is a check that cries wolf, and a check that cries wolf
    gets ignored the day it is right.
    """
    return text.replace("\r\n", "\n").split("\n")


for theirs, ours in THE_SAME_FILE:
    what_they_have = readFromKartaan(*theirs.split("/"))
    here = ROOT / ours
    check(f"{ours} exists at all", here.is_file())
    if not here.is_file():
        continue
    with open(here, "r", encoding="utf-8", newline="") as handle:
        what_we_have = handle.read()
    same = _asLines(what_they_have) == _asLines(what_we_have)
    check(f"{ours} is still exactly what the ERP has committed at {theirs}", same)
    if not same:
        theirs_lines = _asLines(what_they_have)
        ours_lines = _asLines(what_we_have)
        print(f"      the ERP has {len(theirs_lines)} lines, this copy has {len(ours_lines)}.")
        for number, (a, b) in enumerate(zip(theirs_lines, ours_lines), 1):
            if a != b:
                print(f"      first difference at line {number}:")
                print(f"        the ERP: {a}")
                print(f"        here   : {b}")
                break
        print(f"      Copy it across again:  git -C <ERP> show HEAD:{theirs} > {ours}")


# --------------------------------------------------- the tokens the panel leans on
#
# **NAMED ONE BY ONE, because a file that is merely PRESENT proves nothing.** The
# panel writes `var(--on-brand)` on the brand colour and `var(--on-danger)` on the
# Stop button, and the ERP's own file says why each of those is its own token
# rather than a borrowed one: the surface colour only happens to be right in the
# light theme, and two colours that happen to work together are not a rule.
#
# **SO A TOKEN THE PANEL USES AND THE ERP STOPS DEFINING IS A COLOUR THAT SILENTLY
# BECOMES NOTHING** -- a browser drops the whole declaration and the text turns
# whatever it was going to be underneath. The ERP's own file records that exact
# fault: 91 style declarations silently dropped for names that were used and never
# defined.
TOKENS = (ROOT / "extension" / "from-the-erp" / "tokens.css").read_text(encoding="utf-8")
PANEL_CSS = (ROOT / "extension" / "panel.css").read_text(encoding="utf-8")
BUTTONS = (ROOT / "extension" / "from-the-erp" / "button.css").read_text(encoding="utf-8")

DEFINED = set(re.findall(r"^\s*(--[a-z0-9-]+)\s*:", TOKENS, re.MULTILINE))
USED = set(re.findall(r"var\((--[a-z0-9-]+)\)", PANEL_CSS))

check("the panel uses tokens at all", len(USED) > 10)
for one in sorted(USED):
    check(f"{one} is a token the ERP actually defines", one in DEFINED)

# The two that exist ONLY because borrowing the surface colour is wrong in the
# dark theme. Named here so that removing either from the ERP is loud.
check("--on-brand is defined, which is what the top bar is written in",
      "--on-brand" in DEFINED)
check("--on-danger is defined, which is what the Stop button is written in",
      "--on-danger" in DEFINED)
check("the panel writes on the brand colour with --on-brand and not with --surface",
      "var(--on-brand)" in PANEL_CSS)

# ------------------------------------------------------- and the dark theme works
#
# **EVERY TOKEN THE PANEL USES HAS TO CHANGE IN THE DARK, or something on this page
# is a light-theme colour on a nearly-black ground.** The ERP's own file says the
# first draft of it did exactly that -- carried over only the backgrounds, and left
# dark text on a dark page.
DARK = TOKENS.split("body.dark")[-1]
CHANGED_IN_THE_DARK = set(re.findall(r"^\s*(--[a-z0-9-]+)\s*:", DARK, re.MULTILINE))
# `--radius`, `--control-height`, `--font` and `--font-mono` are shapes and faces,
# not colours, and are deliberately the same in both themes.
NOT_A_COLOUR = {"--radius", "--control-height", "--font", "--font-mono"}
for one in sorted(USED - NOT_A_COLOUR):
    check(f"{one} is retuned for the dark theme, so nothing on this page stays light",
          one in CHANGED_IN_THE_DARK)

check("the ERP's dark theme really is switched by a class on the body, which is "
      "what panel.js adds", "body.dark" in TOKENS)

# ------------------------------------------------------ hidden really means hidden
#
# **THE ONE RULE IN THE ERP'S TOKEN FILE THAT IS NOT A COLOUR, and the panel leans
# on it directly.** The setup section and the message under the buttons are both
# taken off the page by setting `hidden`, and a browser hides `[hidden]` through
# its OWN stylesheet -- which ANY author `display` rule beats, whatever the
# specificity. `panel.css` sets `display: flex` on the card the setup section is.
# Without this rule, that section would sit on the page for ever after it was
# finished with, and every check would still be green because the stand-in browser
# stores `hidden` as a property and has no stylesheet at all.
check("the copied tokens still carry the rule that makes `hidden` mean hidden",
      "[hidden]" in TOKENS and "display: none !important" in TOKENS)

# ------------------------------------------------------------- the same controls
#
# The panel does not re-derive a button. It uses the ERP's, which is the whole
# point of copying `button.css` as well: measuring by eye and typing the numbers
# in again is how the seven button heights that file exists to end came about.
SCREEN = (ROOT / "extension" / "screen.js").read_text(encoding="utf-8")
for one in ("k-button", "k-button--main", "k-button--danger", "k-button--ordinary",
            "k-control"):
    check(f"the panel uses the ERP's own {one}", one in SCREEN and f".{one}" in BUTTONS)

check("and panel.css does not redefine any of them",
      not re.search(r"^\s*\.k-", PANEL_CSS, re.MULTILINE))

# **NO COLOUR IS WRITTEN INTO THE PANEL'S OWN STYLESHEET.** The ERP's D25: a
# colour written directly into a screen is a bug. Checked here as well as in
# `extension/screen.test.js` on purpose -- this file is the one somebody opens
# when they are thinking about the look, and a rule stated only somewhere else is
# a rule that gets broken here.
WITHOUT_COMMENTS = re.sub(r"/\*.*?\*/", "", PANEL_CSS, flags=re.S)
check("no colour is written straight into panel.css",
      not re.search(r"#[0-9a-fA-F]{3,8}\b", WITHOUT_COMMENTS)
      and not re.search(r"\brgba?\(", WITHOUT_COMMENTS))

print(f"\n{ran} checks, {len(failures)} failed.")
if failures:
    for one in failures:
        print(f"  FAILED: {one}")
sys.exit(1 if failures else 0)
