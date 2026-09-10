"""Driving a page, step by step. The other half of phase 4.

**IT ANSWERS EXACTLY WHAT THE AMAZON DOOR ANSWERS**, so the runner cannot tell
them apart -- same states, same `say`, same `their_id`. That is the whole of D100:
one report list, one log, one board, and the door is a detail underneath. A report
moving from this door to an API door is one word in the report list, and nothing
above here changes at all.

**WHAT `browser` HAS TO BE**, written down because somebody else implements it --
the seller's own Chrome, driven by an extension:

    browser.go(address, patience)            -> None, or raises
    browser.find(how, what, exact, patience, near) -> how many things match
    browser.click(how, what, exact, near)    -> None, or raises

**`near` IS A LIST OF WAYS THE SAME ROW COULD BE NAMED, AND A ROW MATCHES IF IT
CARRIES ANY ONE OF THEM.** Not one string. Both portals have been met writing a
day more than one way, and the working reference builds five spellings on
Flipkart and six on Meesho rather than choosing between them. Every candidate in
the list names the SAME day, so a longer list can never match a different day's
row -- only a right row that would otherwise have been missed over a leading
nought.

    browser.pick_range(start, end, patience, also_by_the_cursor)
                                             -> None, or raises. The last one
                                                says whether THIS calendar
                                                switches a day off in the
                                                cursor as well
    browser.take_file(patience)              -> bytes, or None if nothing came
    browser.wait(seconds)                    -> None, when there is nothing to
                                                look at and only time to pass
    browser.click_away()                     -> None; shuts whatever the page
                                                has open, by clicking where
                                                nothing is
    browser.overlays()                       -> [{width, height, text, blocks}, ...]
    browser.page_text()                      -> what is on the page now
    browser.needs_signing_in()               -> True when the portal is asking

**EVERYTHING THAT CAN WAIT IS TOLD HOW LONG TO WAIT, and that was missing.** The
step has said how patient to be since it was written -- 300 seconds while Meesho
builds a file, 45 while a page draws -- and not one of those numbers ever reached
the browser. So every "wait for this to appear" step asked once and gave up,
which is exactly the failure the number exists to prevent: `find` would have
reported the platform as having renamed a button that was half a second away.
**Only `click` is not told, and that is deliberate: what it clicks has just been
found, so waiting there would be waiting for something already in front of it.**

**IT HOLDS NO KNOWLEDGE.** Every decision -- which step, what to look for, what a
failure is called, whether to retry -- is in `browser.py`, where it is checked
without a browser existing. The extension carries out instructions and reports
what it saw. That is deliberate: the reference put all of it in 3,800 lines of
JavaScript that nothing could check, and every failure for three months was a
button that had moved.

**NOTHING HERE IS ASKED FOR TWICE EITHER**, but for a different reason than
Amazon. There is no rationed request -- a page is just a page. What must not
happen is a file being downloaded twice into two differently-named copies, which
is how the reference put three wrongly-dated duplicates into Drive.
"""

from dataclasses import dataclass, replace
from datetime import date, timedelta
from typing import Callable, List, Optional, Sequence

import browser as pages
import recipes as book
from landing import file_name_for
from reports import report as kartaan_report

# The same four words the Amazon door answers with. **Not similar -- the same.**
LANDED = "landed"
NOTHING_TO_FETCH = "nothing-to-fetch"
STILL_WAITING = "still-waiting"
FAILED = "failed"


@dataclass(frozen=True)
class Fetched:
    """What one attempt came to. The same shape the Amazon door gives back."""

    state: str
    report_id: str
    data_date: date
    file_name: Optional[str] = None
    size: int = 0
    say: str = ""
    their_id: Optional[str] = None
    # What the page looked like when something could not be found. **Captured
    # automatically, first time** -- rule 4.
    page_was: str = ""


class NeedsSigningIn(RuntimeError):
    """The portal wants somebody to sign in.

    **ITS OWN KIND, because it is not a fault in the report.** Every report after
    it in the run will hit the same wall, and calling each of them broken buries
    the one thing that actually needs doing. The reference reported it as a
    per-report failure and its queue died on the spot.
    """


def do_the_steps(
    browser,
    report_id: str,
    data_date: date,
    panel: str,
    say: Callable[[str], None],
    asked_already: Optional[str] = None,
    *,
    run_day: date,
) -> Fetched:
    """Walk one report's recipe, and answer what came of it.

    **`run_day` IS THE DAY THIS RUN IS HAPPENING, AND IT IS NOT `data_date`.** On
    an ordinary night the data date is yesterday; on a catch-up it can be weeks
    back. **Meesho's exported-files panel names a row by the day the export was
    MADE**, which is the day of the run and nothing else, so the two have to be
    told apart -- the reference tells them apart in one function, two lines
    apart (`content/meesho.js:1055`). **It has no default**, because a default
    would be the guess this whole argument exists to remove.

    **A COVERING IS ASKED ABOUT ONLY ONCE A LOOKUP HAS ALREADY FAILED, and that
    is a correction made on 2026-08-28 with the evidence in front of it.** It used
    to be asked before every click, so that a failure could never be written down
    as "button not found" when the button was underneath a promotion -- a month of
    diagnosis went chasing exactly that. Two things read off his own panel say the
    order has to be the other way round:

      - **the panel a recipe opens ON PURPOSE sits on a full-screen backdrop
        too.** Meesho's "Bulk Stock Update" panel measures the whole window and
        contains the very Download the recipe is about to press. Asked
        beforehand, the door refuses to carry on because of a panel it opened;
      - **and a covering never actually stops anything here.** A click is sent
        straight to the thing being clicked, so a sheet laid over the page does
        not intercept it the way it intercepts a person's mouse.

    So a covering does not STOP a step -- it EXPLAINS one that stopped. Asked in
    this order the failure still says "something is covering the page", which was
    the whole point, and a panel the recipe opened costs nothing.
    """
    # **BOTH LOOKUPS INSIDE THE SAME GUARD.** The report lookup sat outside it, so
    # a report this door has no recipe for threw straight out instead of being
    # answered -- and the runner would have recorded a bare KeyError as the reason
    # a seller's data was missing. A door answers; it does not throw at its caller.
    try:
        which = kartaan_report(report_id)
        how = book.recipe(report_id)
        # **A TWO-PHASE REPORT IS NEVER ASKED FOR TWICE.** Flipkart's Reports Centre
        # allows twenty requests a day; the reference burned through them
        # re-submitting reports that had actually worked, then spent the rest of the
        # day locked out. Given what it was asked under, this collects.
        collecting = bool(asked_already) or not how.two_phase
        steps = book.steps_for(report_id, panel, collecting=collecting)
    except (KeyError, ValueError) as wrong:
        return Fetched(FAILED, report_id, data_date, say=str(wrong))

    for step in steps:
        wrong = pages.why_step_is_refused(step)
        if wrong:
            # A bad recipe is a fault in the product, not in the portal, and it
            # says so rather than reading as the platform having changed.
            return Fetched(FAILED, report_id, data_date, say=f"This recipe is wrong: {wrong}")

        # **THE DAY GOES IN AFTER THE STEP HAS BEEN JUDGED, NEVER BEFORE.** Every
        # rule about a placeholder is a rule about the RECIPE -- a row named
        # without the day, a wording nobody said whose it was -- and once the day
        # is in, all of them are gone from the text and the rules read as passing.
        step = _with_the_day_in(step, data_date, run_day)

        # **SIGNING IN IS ASKED ABOUT FIRST, AND IT IS NOT THIS REPORT'S FAULT.**
        if browser.needs_signing_in():
            raise NeedsSigningIn(
                "The Meesho panel is asking to be signed in to. Nothing can be fetched from it "
                "until somebody does, and every report after this one would fail the same way."
            )

        if step.do == pages.GO:
            browser.go(step.address, step.patience)
            continue

        if step.do == pages.WAIT:
            # **NOTHING TO LOOK AT, ONLY TIME TO PASS.** Meesho builds an orders
            # export on its own servers and the page it was asked from does not
            # change at all while it happens -- so there is nothing a `wait-for`
            # could watch. See `browser.WAIT`.
            browser.wait(step.patience)
            continue

        if step.do == pages.PICK_RANGE:
            # **A RANGE IS NOT ALWAYS ONE DAY.** Flipkart's Reports Centre needs the
            # start strictly before the end, so its smallest range is two days --
            # and it names the row it produces by the END date, which is the day
            # actually being fetched.
            # **AND HOW THIS CALENDAR SWITCHES A DAY OFF GOES WITH IT.** Flipkart
            # disables a day two different ways and one of them shows only in the
            # cursor -- its own habit, not a rule of browsers, so the recipe says
            # which calendar this is rather than the door assuming it of every
            # one. Dropped here, the second mechanism is caught by nothing.
            # **AND A CONTROL THAT TOGGLES IS PRESSED AGAIN WHILE THIS WAITS.**
            # Flipkart's calendar is drawn by a **Custom** chip that toggles, so a
            # chip press that arrived early opened nothing and this step waits its
            # whole patience out at a page that will never change. The reference
            # presses the chip again once, part-way through (`content/flipkart.js`
            # StepD), and has done every night for months.
            _the_range_goes_in(
                browser, step, say, report_id,
                data_date - timedelta(days=step.range_days - 1), data_date,
            )
            continue

        if step.do == pages.TAKE_FILE:
            got = _take_the_file(browser, step, report_id, data_date, which)
            if isinstance(got, Fetched):
                return got
            body = got
            name = file_name_for(which, data_date)
            return Fetched(LANDED, report_id, data_date, file_name=name, size=len(body),
                           say=f"Landed {name} ({len(body)} bytes).")

        # CLICK and WAIT_FOR both have to find something first.
        many = _how_many_match(browser, step, say, report_id)
        if many == 0:
            # **WHICH OF THE TWO IT WAS, decided now that the lookup has failed.**
            # "Button not found" sent a month of diagnosis at a button that was
            # there all along, underneath a promotion -- so it still has to say.
            return _gave_up(report_id, data_date, pages.WentWrong(
                kind=(pages.COVERED_UP if pages.is_covered(browser.overlays()) is not None
                      else pages.FOUND_NOTHING),
                looking_for=step.find.name(), doing=step.why,
                page_was=pages.capture(browser.page_text()),
            ))
        if many > 1:
            # **AMBIGUITY IS A FAILURE, NOT A COIN TOSS.** Nine days of payments
            # were lost to a chart legend that read like a menu item, because the
            # code took the first match.
            return _gave_up(report_id, data_date, pages.WentWrong(
                kind=pages.FOUND_SEVERAL, looking_for=step.find.name(), doing=step.why,
                page_was=pages.capture(browser.page_text()), matches=many,
            ))

        if step.do == pages.CLICK:
            browser.click(step.find.how, step.find.what, step.find.exact, step.find.near)
            say(f"{report_id}: {step.why}.")

    if not collecting:
        # **THE ASKING PHASE FINISHED, AND THAT IS A SUCCESS, NOT A FAILURE.** The
        # platform is building it now. `their_id` is the day it was asked under,
        # which is how the row is found when a later run comes back -- and holding
        # it is what stops this being asked for a second time.
        return Fetched(
            STILL_WAITING, report_id, data_date, their_id=data_date.isoformat(),
            say=(
                f"Asked for it. About {how.ready_in_minutes} minutes before it is ready; "
                "a later run will collect it rather than asking again."
            ),
        )

    # **A RECIPE THAT NEVER TOOK A FILE IS A FAULT IN THE RECIPE**, and it says so
    # rather than reporting a missing file as the platform's doing.
    return Fetched(
        FAILED, report_id, data_date,
        say="Every step ran and none of them took a file. The recipe is missing its last step.",
    )


def _with_the_day_in(step, data_date, run_day):
    """One step with the days put into it, wherever they are named.

    **UNTIL THIS EXISTED THE PLACEHOLDERS CROSSED TO THE PAGE AS THEY WERE.**
    `find.near` went to the browser holding the literal characters `{day}` or
    `{day_in_words}`, so every lookup narrowed to a row was narrowed to a row no
    page has ever carried -- which finds nothing, every night, and reads as the
    portal having renamed something.

    **TWO DAYS GO IN, NOT ONE, AND WHICH ONE IS THE LOOKUP'S OWN ANSWER.**
    `{day}` is always the day the data is about. `{day_in_words}` is whichever
    day the lookup says names the row: Flipkart's Reports Centre names it by the
    end of the range, which is the data date; Meesho's exported-files panel names
    it by the day the export was made, which is the day of the run. Filled with
    the other one, the row is looked for under a day that is on no row at all.

    **AND `near` COMES OUT AS SEVERAL ROWS IT COULD BE, NOT ONE.** Both portals
    have been met writing a day more than one way, so the lookup carries every
    spelling that portal writes and a row matches if it carries any of them.

    **AND THIS IS THE SAME FILLING-IN `extension/walk.js` DOES, held to it by a
    check that runs both halves.** Two descriptions of one rule is the fault this
    project has already been caught by four times; here one of them would put a
    seller's report request against the wrong row.
    """
    changed = {}
    # **THE ADDRESS TOO, and no recipe names the day in one today.** The walker
    # on the other side fills it there, so leaving it out here would be the two
    # halves quietly disagreeing on the day the first recipe to want it was
    # written -- which is precisely the drift a generated crossing exists to
    # prevent. An address may only ever name the day plainly; naming it in a
    # portal's own wording is refused, because an address has no lookup on which
    # to say whose wording it meant.
    if "{day}" in step.address:
        changed["address"] = step.address.replace("{day}", data_date.isoformat())
    if step.find is not None:
        changed["find"] = replace(step.find, near=_the_rows_it_could_be(
            step.find, data_date, run_day))
    return replace(step, **changed) if changed else step


def _the_rows_it_could_be(find, data_date, run_day):
    """Every way the row this lookup wants could be named. **Empty when it wants
    any row at all**, which is most lookups.

    **ALWAYS A LIST, EVEN OF ONE, so that nothing downstream has to ask which
    shape it was handed.** A single string that sometimes means one row and
    sometimes means several is two things wearing one name.
    """
    if not find.near:
        return ()
    if "{day_in_words}" not in find.near:
        return (find.near.replace("{day}", data_date.isoformat()),)
    # **WHICH DAY NAMES THE ROW IS THE LOOKUP'S OWN ANSWER**, and there is no
    # default: a lookup that has not said is refused before it gets here.
    named_by = run_day if find.day_in_words_of == pages.THE_DAY_IT_WAS_MADE else data_date
    return tuple(
        find.near.replace("{day_in_words}", in_words).replace("{day}", data_date.isoformat())
        for in_words in book.the_days_in_words(find.day_in_words_is, named_by)
    )


def _how_many_match(browser, step, say, report_id):
    """How many things on the page match this step's lookup.

    **AND A CONTROL THAT TOGGLES IS PRESSED AGAIN WHILE IT WAITS, when the step
    says one does.** Flipkart's Reports Centre hides its calendar behind a date
    box and a Custom chip, both of which toggle: a press that arrived while the
    sub-page was still drawing opened nothing, and without this the next step
    waits its whole patience out at a page that will never change. The reference
    presses the date box again on every third look (`content/flipkart.js` StepD).
    """
    def look(patience):
        return browser.find(step.find.how, step.find.what, step.find.exact, patience,
                            step.find.near)

    press = step.press_again
    if press is None:
        return look(step.patience)
    spent = 0
    for _ in range(press.times):
        # **A GO THAT THREW IS A GO THAT DID NOT FIND IT, AND NOTHING MORE.** The
        # last go below is NOT caught, so a real failure still carries its own
        # words out to the seller -- what is swallowed here is only the middle of
        # the waiting, and every press in between is said out loud.
        many = _answered(look, press.after)
        if many:
            return many
        spent += press.after
        _press_it_again(browser, press, say, report_id)
    return look(max(1, step.patience - spent))


def _the_range_goes_in(browser, step, say, report_id, start, end):
    """Put the range into the page, pressing again the control that draws it.

    **THE CALENDAR IS DRAWN BY A CHIP THAT TOGGLES.** The reference presses that
    chip again once, part-way through its wait for the calendar, and has done
    every night for months (`content/flipkart.js` StepD). Dropped, the only
    symptom is a step that waits quietly and then says no calendar was showing.
    """
    def put_in(patience):
        browser.pick_range(start, end, patience, step.switched_off_days_change_the_cursor)
        return True

    press = step.press_again
    if press is None:
        put_in(step.patience)
        return
    spent = 0
    for _ in range(press.times):
        if _answered(put_in, press.after):
            return
        spent += press.after
        _press_it_again(browser, press, say, report_id)
    put_in(max(1, step.patience - spent))


def _answered(work, patience):
    """What one go answered, or nothing at all when it threw."""
    try:
        return work(patience)
    except Exception:  # noqa: BLE001
        return None


def _press_it_again(browser, press, say, report_id):
    """Press the toggling control once more. **Said, never swallowed.**

    A control that cannot be pressed again is worth knowing about -- but it is
    not this step's failure, because the step goes on waiting and reports its own
    in its own words.
    """
    try:
        browser.click(press.by.how, press.by.what, press.by.exact, ())
    except Exception as wrong:  # noqa: BLE001
        say(f"{report_id}: {press.by.name()} could not be pressed again -- {wrong}")
        return
    say(f"{report_id}: pressed {press.by.name()} again, because it is a control that toggles.")


def _take_the_file(browser, step, report_id, data_date, which):
    """The last step: whatever the page produced. Answers bytes, or a failure.

    **A STEP THAT PRESSES NOTHING HAS NO LOOKUP TO EXPLAIN**, so there is nothing
    to ask about a covering: the file either comes or it does not.
    """
    if step.find is not None:
        many = browser.find(step.find.how, step.find.what, step.find.exact, step.patience,
                            step.find.near)
        # **NOT THERE YET IS NOT THE SAME AS NOT THERE, WHEN IT LIVES IN A MENU.**
        # Meesho draws its list of finished exports as the download menu opens, so
        # an open menu shows what was ready at that moment and never changes. The
        # only way to see a newer list is to shut the menu, leave it shut, and
        # open it again. See `browser.LookAgain`.
        #
        # **THE GESTURE IS THE REFERENCE'S, NOT ONE DERIVED FROM IT**
        # (`content/meesho.js:860-878`): click where nothing is, leave it shut,
        # look the opener up AGAIN, and press it once. Pressing the opener twice
        # instead would assume it toggles -- and if it does not, both presses do
        # nothing, the list is never redrawn, and six rounds of this look exactly
        # like a night that is working.
        again = step.look_again
        tried = 0
        while many == 0 and again is not None and tried < again.times:
            tried += 1
            browser.click_away()
            browser.wait(again.after)
            # **THE OPENER IS LOOKED FOR BEFORE IT IS PRESSED, and if it has gone
            # this stops rather than throwing.** The reference does the same
            # (`if (!dlDropdown2) ... break`). Clicking at something that is not
            # there would throw past every failure this door writes, and the
            # seller would be told a control could not be found with no word of
            # what was being attempted -- the bare "button not found" that cost
            # this project a month. Stopping here falls into the failure below,
            # which carries `step.why` and the page with it.
            still_there = browser.find(again.by.how, again.by.what, again.by.exact,
                                       step.patience, again.by.near)
            if still_there == 0:
                break
            browser.click(again.by.how, again.by.what, again.by.exact, again.by.near)
            many = browser.find(step.find.how, step.find.what, step.find.exact, step.patience,
                                step.find.near)
        if many == 0:
            return _gave_up(report_id, data_date, pages.WentWrong(
                kind=(pages.COVERED_UP if pages.is_covered(browser.overlays()) is not None
                      else pages.FOUND_NOTHING),
                looking_for=step.find.name(), doing=step.why,
                page_was=pages.capture(browser.page_text()),
            ))
        if many > 1:
            return _gave_up(report_id, data_date, pages.WentWrong(
                kind=pages.FOUND_SEVERAL, looking_for=step.find.name(), doing=step.why,
                page_was=pages.capture(browser.page_text()), matches=many,
            ))
        browser.click(step.find.how, step.find.what, step.find.exact, step.find.near)

    # **THE FILE IS WAITED FOR TOO, and this is the one that would have hurt
    # most.** Asked the instant the button was pressed nothing has come back, and
    # the report then reads as the page having produced an empty file. That
    # failure looks like the platform's doing and is entirely ours.
    #
    # **THIS USED TO SAY "MEESHO TAKES UP TO FIVE MINUTES", AND THAT IS NO LONGER
    # WHAT ANY RECIPE ASKS FOR.** The five minutes were `me_orders` waiting on an
    # open download menu, which never changes while it is open; that wait is now
    # thirty seconds, spent shut, and repeated. **It is the step's own number
    # either way** -- the same one the lookup above was given -- because the
    # click that starts the download and the download itself are one moment on
    # the page, and no recipe has ever needed to tell them apart.
    body = browser.take_file(step.patience)
    if body is None:
        # **THE DOOR THAT HAS CLOSED.** Flipkart has started building files inside
        # the page and handing over a temporary handle an extension cannot fetch
        # twice. Retrying it for ever is doing nothing slowly.
        gone = _gave_up(report_id, data_date, pages.WentWrong(
            kind=pages.BUILT_IN_THE_PAGE, looking_for="the file itself", doing=step.why,
            page_was=pages.capture(browser.page_text()),
        ))
        since = book.BUILDS_IN_THE_PAGE_SINCE.get(report_id)
        if since:
            # **SAID WITH THE DAY IT STARTED**, so this reads as a known door
            # closing rather than as tonight's news. Flipkart began doing it to
            # orders and returns on 2026-08-22.
            return Fetched(
                gone.state, gone.report_id, gone.data_date,
                say=gone.say + f" This has been happening to {report_id} since {since}.",
                page_was=gone.page_was,
            )
        return gone
    if not body:
        return Fetched(
            FAILED, report_id, data_date,
            say="The page produced a file with nothing in it, so nothing has been written.",
        )
    return body


def _gave_up(report_id: str, data_date: date, wrong: pages.WentWrong) -> Fetched:
    """One failure, with the page it happened on kept.

    **THE EVIDENCE TRAVELS WITH THE FAILURE.** It is not written somewhere else to
    be correlated later -- correlating later is what nobody ever does.
    """
    return Fetched(
        state=FAILED,
        report_id=report_id,
        data_date=data_date,
        say=wrong.say(),
        page_was=wrong.page_was,
    )


def a_door(browser, panel: str, say: Callable[[str], None],
           run_day: date) -> Callable[..., Fetched]:
    """The browser door, in the shape the runner expects.

    Answers a `fetch(report_id, data_date, asked_already=None)` exactly like the
    Amazon one -- and **it means the same thing here as it does there**: a report
    the platform is still building, collected rather than asked for again. On
    Flipkart that is not politeness. Its Reports Centre allows twenty requests a
    day, and the reference burned through them re-submitting requests that had
    actually worked, then spent the rest of the day locked out.

    **`run_day` IS THE DAY THIS RUN IS HAPPENING, AND IT IS ON THE DOOR RATHER
    THAN ON `fetch`.** `fetch` answers the same three arguments the Amazon door
    does and that is what lets the runner tell them apart from nothing, so
    nothing new goes on it. **The door is built once per run**, and a run starts
    at four in the afternoon (`clock.NOT_BEFORE_HOUR`), so every export it makes
    is made on the same day.
    """

    def fetch(report_id: str, data_date: date, asked_already: Optional[str] = None) -> Fetched:
        return do_the_steps(browser, report_id, data_date, panel, say, asked_already,
                            run_day=run_day)

    return fetch
