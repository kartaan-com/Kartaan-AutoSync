"""The run that starts itself, with nobody present. The thing that was missing.

**EVERY PIECE OF AUTO-SYNC EXISTED AND NOTHING JOINED THEM.** `reports.py` says
what there is, `schedule.py` says what is owed, `amazon_door.py` fetches one,
`landing.py` names it, `drive_door.py` puts it away, `runlog.py` writes down what
happened, `board.py` and `alarms.py` say what is wrong. This is the file that
calls them in order, and it is the last one because it is the only one that can
only be written once all the others are right.

**IT RUNS IN THE SELLER'S OWN GITHUB ACTIONS (D36), and only the API half runs
there (D100).** Amazon has a documented way in, so nobody needs to be sitting
there. Meesho has none and Akamai in front of it, so Meesho runs in the seller's
own Chrome through the extension, and a job here that tried it would fail on
twenty-one reports every night and make the log read as though the platform were
broken. `reports.on_the_api_door()` is what decides that, not this file.

**THE SHAPE: A DECIDING HALF AND A DOING HALF, like every other pair here.**
`one_tick` is handed everything -- the clock, the record, the doors, the log --
so every rule below can be checked with no account, no token and no internet.
**The part that reads a secret and opens a real connection is not in this file
at all**: it is `start.py`, which is what the workflow runs. That split is not
tidiness -- it is what lets every line here be proved by breaking it on purpose,
which is the one thing that cannot be done to code that needs an account.

**AND IT IS A TICK, NOT A NIGHT.** The workflow wakes this up several times a
day and `clock.py` decides whether a run is actually due. That is deliberate:
GitHub's own documentation says a scheduled run "can be delayed during periods of
high loads", and a job that fired once a night would lose the whole day whenever
that happened. D108 says no day is ever lost, so the answer is more chances and
one clock -- rather than one chance and hope.

**WHEN THIS JOB FAILS, AND WHEN IT DOES NOT.** D108 splits failures in two and so
does this:

  - **Ours is a defect and the job goes red**: nothing could be read, the run's
    own memory could not be saved, the evidence could not be got out of the
    building. Those mean the next run cannot be trusted, and a green tick over
    them is exactly the silence this whole package is built against.
  - **Theirs is recorded and the job stays green**: a report Amazon would not
    give up, a day that is late, a settlement that has not been published. Those
    are on the board, in the log, and in an alarm that goes to a person. Turning
    them red as well trains everybody to ignore the red.
"""

import os
from dataclasses import dataclass
from datetime import date, datetime
from typing import Callable, List, Optional, Sequence, Tuple

import between_runs
import clock
import manifest
import reading
import runlog
import runner
from landing import Arrived
from reports import API, Report, on_the_api_door

# The folder in the seller's Drive that holds what belongs to the job itself
# rather than to any one report -- the run's memory and the copy of the log.
#
# **A NAME NO REPORT CAN HAVE.** Every report id is `<platform>_<something>`, so
# a plain word cannot collide with one, and the whole of `drive_door` can be used
# for these two files exactly as it is used for a report's.
OURS = "autosync"


@dataclass(frozen=True)
class Tick:
    """What one waking-up came to.

    `ran` is the question everything else hangs off: a tick that decided not to
    run and a tick that ran and fetched nothing look identical in a summary, and
    they are entirely different days.
    """

    ran: bool
    why_not: Optional[str] = None
    happened: Optional[runner.WhatHappened] = None
    alarms_sent: Tuple[str, ...] = ()
    # **WHAT WENT WRONG ON OUR SIDE, and only ours.** A report failing is not in
    # here; it is in `happened.failed`, on the board, and in an alarm.
    our_faults: Tuple[str, ...] = ()
    # **WHAT THE NIGHT READ, and it is always said even when it is nothing.**
    # Two runs have already "succeeded" in eleven and forty-seven seconds while
    # doing nothing, and a summary that mentioned the reading only when there
    # was some would make that night and a night that read the whole folder look
    # identical.
    what_was_read: Optional[reading.WhatTheNightRead] = None

    @property
    def is_a_defect(self) -> bool:
        return bool(self.our_faults)

    def summary(self) -> str:
        if not self.ran:
            return f"Did not run: {self.why_not}"
        said = self.happened.summary() if self.happened else "Ran."
        if self.what_was_read is not None:
            said += "  " + self.what_was_read.says()
        if self.our_faults:
            said += "  " + "  ".join(self.our_faults)
        return said


def one_tick(
    now: Callable[[], datetime],
    read_state: Callable[[], Optional[bytes]],
    save_state: Callable[[bytes], None],
    arrivals: Callable[[str], Sequence[Arrived]],
    fetch: Callable[..., object],
    sink: Callable[[Sequence[runlog.Line]], None],
    send: Callable[[Sequence[str]], None],
    reports: Optional[Sequence[Report]] = None,
    even_if_not_due: bool = False,
    not_before_hour: int = clock.NOT_BEFORE_HOUR,
    ask_the_hour: Optional[Callable[[], object]] = None,
    save_board: Optional[Callable[[Sequence], None]] = None,
    save_run: Optional[Callable[..., None]] = None,
    # **THE DOWNLOAD MANIFEST, READ AND WRITTEN AS A PAIR (specification 25).**
    # It is read before it is written because this half only ever replaces its
    # OWN lines -- the extension's twenty-three come through untouched, and a
    # night the extension never opened must not turn them into `missing`.
    read_manifest: Optional[Callable[[], Optional[bytes]]] = None,
    save_manifest: Optional[Callable[[bytes], None]] = None,
    # **THE READING HALF, HANDED IN LIKE EVERYTHING ELSE.** What is in a report's
    # folder, how to fetch one file back, and the one place a sale can land. All
    # three together or the reading says in words that it did not happen -- see
    # `reading.read_what_is_new`.
    what_is_in_the_folder: Optional[Callable[[str], Sequence]] = None,
    bring_the_file_back: Optional[Callable[[str], bytes]] = None,
    record_the_sales: Optional[Callable[[Sequence], None]] = None,
) -> Tick:
    """Wake up, decide whether a run is due, and if it is, do one.

    Everything it needs is handed in. **Nothing here reads a clock, opens a
    connection or touches a disk**, which is what lets the order of these steps --
    the part that has actually gone wrong in the reference, repeatedly -- be
    checked without any of those things.
    """
    faults: List[str] = []
    moment = now()

    # **THE HOUR THE SELLER CHOSE, ASKED OF THEIR OWN DATABASE (D114).** Before
    # this there was nowhere to ask: the setting was written on the business
    # record by the This business tab and the job read an environment variable
    # nobody set, so a seller who chose eleven at night was fetched at two in the
    # morning for ever and nothing said so.
    #
    # **IT IS ASKED FIRST, because the clock needs it to decide anything at all.**
    # And a question that cannot be answered STOPS THE RUN and is our own defect:
    # falling back to the default would be exactly the silent wrong hour this
    # replaces. A tick happens every hour, so nothing is lost by refusing one.
    if ask_the_hour is not None:
        try:
            said = ask_the_hour()
        except Exception as wrong:  # noqa: BLE001 - reported, never swallowed
            told = (
                f"The hour this seller chose could not be read, so nothing has been fetched: {wrong}"
            )
            return Tick(ran=False, why_not=told, our_faults=(told,))
        # **NOTHING CHOSEN IS NOT A FAULT.** A seller who has connected but not yet
        # finished setting the business up has no record and no choice, and
        # `the_hour_they_mean` answers the default for them. Anything that is not
        # a whole hour comes back as they wrote it, so the clock refuses it in
        # their own words rather than quietly fetching at the default hour.
        not_before_hour = clock.the_hour_they_mean(said)

    # **THE RECORD IS READ BEFORE ANYTHING ELSE, and a damaged one stops
    # everything.** Read as empty, it would throw away what Amazon is already
    # building and ask for it all again -- one rationed call a minute, and two
    # reports where there should be one.
    try:
        state = between_runs.read(read_state())
    except between_runs.Damaged as damaged:
        return Tick(ran=False, why_not=str(damaged), our_faults=(str(damaged),))
    except Exception as wrong:  # noqa: BLE001 - reported, never swallowed
        said = f"What the last run left behind could not be fetched: {wrong}"
        return Tick(ran=False, why_not=said, our_faults=(said,))

    # **HIS DAY, and the moment handed in is already his** -- `clock.his_clock` is
    # applied once, at the edge, where the machine is asked the time. Converting
    # again here would ask for the wrong day for five and a half hours out of
    # every twenty-four, and nothing would say so.
    today = moment.date()

    last = between_runs.as_the_clock_reads_it(state)
    given_up_on = clock.gave_up_on(last, moment)

    # **STARTED BY HAND, AND ONLY ONE OF THE CLOCK'S TWO REASONS CAN BE
    # OVERRIDDEN.** "The last one finished an hour ago" is somebody's judgement to
    # make -- they are standing there and they know why they pressed it. "One is
    # going right now" is not: two runs at once fetch every file twice, into two
    # differently-named copies, which is the fault that put three wrongly-dated
    # files into the reference's Drive.
    #
    # **AND IT IS ASKED OF THE RECORD, never of the clock's sentence.** Deciding
    # which reason it was by reading the words would break silently the day one
    # of them is reworded.
    if even_if_not_due:
        if last.still_going and not given_up_on:
            return Tick(
                ran=False,
                why_not=(
                    f"A run started at {last.started.isoformat()} and has not finished. "
                    "Two at once would fetch every file twice, so this one has not started "
                    "even though it was asked for by hand."
                ),
            )
    else:
        # **THE HOUR THE SELLER CHOSE IS PART OF WHETHER A RUN IS DUE**, and it
        # is a floor rather than an appointment: the first tick at or after it.
        # An appointment missed by an hour is a day lost, and GitHub's own
        # documentation says a scheduled run can be delayed.
        why_not = clock.why_not_now(last, moment, not_before_hour)
        if why_not:
            return Tick(ran=False, why_not=why_not)

    # **A RUN THAT WAS ABANDONED IS SAID, NEVER QUIETLY STEPPED OVER.** It is what
    # a killed job leaves behind -- the machine shut, the runner cancelled, the
    # job hitting its own six-hour ceiling -- and the reference had four of them
    # in twenty-six days with not one written down anywhere.
    #
    # It goes in through `refused`, which is the runner's way of putting a
    # system-level line in the log BEFORE anything is fetched. That is where this
    # belongs: whoever reads the log tomorrow needs it above the run, not after.
    say_first: List[str] = []
    if given_up_on:
        say_first.append(
            f"The run that started at {state.last_started.isoformat()} never finished and has "
            "been given up on. Whatever it was fetching was not recorded as done, so it is "
            "owed again."
        )

    # **WRITTEN DOWN BEFORE THE FETCHING.** A run killed halfway must leave behind
    # a record saying it started, or nothing can tell "one is going" from "none
    # ever has" -- and the giving-up rule above reads exactly that difference.
    # If this cannot be saved the run does not start: two runs at once fetch every
    # file twice, into two differently-named copies.
    # **THE DAYS BEFORE THIS ONE, kept before today is added to them (cycle 46,
    # R2#8).** `started()` puts today into the list, and the quiet alarm is asked
    # of that list further down -- so it always saw a run today and never said a
    # word, **including on the night a job comes back after a week of silence,
    # which is exactly when it is worth saying.**
    #
    # **WHAT THIS STILL CANNOT DO, said plainly rather than left to be found:**
    # nothing running AT ALL cannot be noticed from inside a run, because there
    # is no run to notice it. That is what D123 is for -- every run reports back
    # to Kartaan, and it is the silence that is read there.
    quiet_before = state.run_days
    state = state.started(moment)
    try:
        save_state(between_runs.write(state))
    except Exception as wrong:  # noqa: BLE001
        said = f"The run could not record that it had started, so it has not started: {wrong}"
        return Tick(ran=False, why_not=said, our_faults=(said,))

    name = moment.strftime("%Y%m%dT%H%M%S")
    which = list(reports if reports is not None else on_the_api_door())
    in_flight = between_runs.carried_in_flight(state)

    # **THE RUN IS WRITTEN DOWN BEFORE IT FETCHES ANYTHING (D114), and that is the
    # whole point of writing it down at all.** A run that started and never
    # finished is the case the reference could not report -- four days in
    # twenty-six -- and it can only be seen if something was written before the
    # thing that ended it happened.
    #
    # **AND IT IS NOT ALLOWED TO STOP THE RUN.** What must survive is what Amazon
    # is building, and that is already saved above; this is a record for a screen.
    # Refusing to fetch because a screen would be short of one row would turn a
    # database blip into a lost day, and D108 says no day is lost.
    _try(faults, save_run, "The run could not be written down as started",
         name, moment)

    happened = runner.do_a_run(
        name=name,
        reports=which,
        fetch=fetch,
        arrivals=arrivals,
        in_flight=in_flight,
        sink=sink,
        now=now,
        today=today,
        refused=tuple(say_first),
    )

    # **AND NOW WHAT IS NEW IN THE FOLDER IS READ. Until this line nothing in
    # this package called `whats_new` at all**, so the list of what had been read
    # stayed empty for ever and every night worked out what was new from nothing.
    #
    # **IT IS AFTER THE FETCHING SO THAT WHAT LANDED TONIGHT IS READ TONIGHT, and
    # it is not JOINED to it.** His rule is that reading is *"solely based on what
    # is new"* in the folder -- never on whether a fetch succeeded -- and that
    # stays true here because `read_what_is_new` is handed the folder and the
    # record and nothing else. One platform having a bad night still cannot cost
    # the day's numbers (D148).
    #
    # **WHAT IT READ GOES INTO THE RECORD BEFORE THE RECORD IS SAVED, one line
    # below.** Worked out after the save, a night's reading would be done again
    # from scratch tomorrow -- which is the very fault this whole step exists to
    # close.
    #
    # **AND IT SITS BEFORE `finished()` RATHER THAN AFTER IT, WHICH IS A TRADE
    # AND IS WRITTEN DOWN AS ONE.** Until `finished()` is saved the record still
    # says a run is going, so no second tick can start while this is downloading
    # -- and two at once reading one folder would write every sale twice. The
    # cost is that what Amazon is building waits for the reading before it is
    # saved, so a job killed mid-reading loses it. Both losses are reported by
    # name below. **Putting the reading after the finished-save would swap one
    # for the other, and the swap is worth somebody's judgement rather than a
    # session's: it would need its own save and would open exactly the
    # two-runs-at-once window the clock exists to shut.**
    try:
        what_was_read = reading.read_what_is_new(
            already_read=state.files_read,
            what_is_in_the_folder=what_is_in_the_folder,
            bring_it_back=bring_the_file_back,
            record_the_sales=record_the_sales,
        )
    except Exception as wrong:  # noqa: BLE001 - reported, never swallowed
        # **THE RECORD IS LEFT EXACTLY AS IT WAS.** Anything else here either
        # forgets a file that is still in the folder, or writes down as read a
        # file whose sales went nowhere.
        what_was_read = None
        faults.append(f"What is new in the folder could not be worked out: {wrong}")
    else:
        state = between_runs.with_files_read(state, what_was_read.files_read)
        # **A FOLDER NOBODY COULD LIST IS OUR OWN DEFECT (D108).** What is new
        # cannot be decided without it. A single file that would not read is the
        # platform's: named, counted, and left green.
        if what_was_read.is_a_defect:
            faults.append(
                "What is new could not be worked out for every folder, so nothing was "
                "let go of and some files may not have been read: "
                + "  ".join(what_was_read.could_not_list)
            )

    # **THE MEMORY IS PUT BACK FIRST, before anything is worked out or sent.**
    # What Amazon is building is the one thing that costs something to lose, and
    # every line between here and the save is another line that could throw.
    state = between_runs.with_in_flight(state, in_flight).finished(now())
    wrong_with_it = between_runs.why_it_cannot_be_saved(state)
    if wrong_with_it:
        faults.append(f"The run's own record was not saved: {wrong_with_it}")
    else:
        try:
            save_state(between_runs.write(state))
        except Exception as wrong:  # noqa: BLE001
            # **SAID LOUDLY.** Lost, the next run asks Amazon again for every
            # report it is already building. That is not a nuisance -- it is a
            # rationed call spent and two reports where there should be one.
            faults.append(
                f"The run finished and could not record what it left behind: {wrong}. "
                "The next run may ask Amazon again for reports it is already building."
            )

    # **THE BOARD AND THE ALARMS ARE WORKED OUT FROM THE RECORD, not from the run
    # that has just happened.** That is what lets "nothing is running at all" ever
    # be said -- the reference could not raise it, because every alarm it had
    # lived inside a run, and the case it was for is the case where none happens.
    sent: Tuple[str, ...] = ()
    try:
        rows, alarms = runner.look(
            reports=which,
            arrivals=arrivals,
            # **A FIRST NIGHT HAS NO DAYS BEFORE IT, so there is no gap to
            # report.** Asked of an empty list, the quiet alarm answers
            # "nothing has ever run" -- on the night something is running,
            # which is a brand-new seller being told their job is broken on
            # the day they connect. The list with today in it is what says so.
            run_days=quiet_before or state.run_days,
            today=today,
            # **WHY EACH LATE REPORT IS LATE, IN ITS OWN WORDS (cycle 46, R2#6).**
            # This was left off, so the one column on the board that exists to
            # say why said nothing on every row, on every night -- a seller was
            # told a report was five days late and nothing else. The run records
            # the reason against each report; `WhatHappened` now carries it out.
            reason_for=happened.reasons.get,
            failed_ids=happened.failed,
        )
        # **THE BOARD GOES INTO THE SELLER'S OWN DATABASE (D114).** Every row,
        # every run: each is named for its report and its day, so tonight's
        # answer about the 12th replaces last night's rather than sitting beside
        # it, and a day that has since arrived stops reading as missing without
        # anything having to go and delete a row.
        _try(faults, save_board, "The day board could not be written down", rows)
        changed = runner.tell_somebody(alarms, state.standing, send)
        sent = tuple(a.key for a in changed.raised)
        state = between_runs.with_standing(
            state, [a.key for a in changed.raised + changed.still]
        )
        # **THE SAME QUESTION IS ASKED HERE, BECAUSE THIS WRITES THE SAME
        # RECORD.** For one round the guard fifty lines above refused a record
        # that finished before it started -- and this line then wrote that very
        # record anyway. So the refusal cost a fault line and prevented nothing:
        # `read` still took the impossible finish back as fact on the next run.
        # **Neuter either of the two and the same named check goes red.**
        cannot_be_saved = between_runs.why_it_cannot_be_saved(state)
        if cannot_be_saved:
            faults.append(f"Which alarms have gone out could not be recorded: {cannot_be_saved}")
        else:
            try:
                save_state(between_runs.write(state))
            except Exception as wrong:  # noqa: BLE001
                # **NOT FATAL, AND NOT SILENT.** The worst this costs is the same
                # alarm going out again tomorrow. Losing what Amazon is building
                # would cost more, and that was already saved above.
                faults.append(f"Which alarms have gone out could not be recorded: {wrong}")
    except Exception as wrong:  # noqa: BLE001
        faults.append(f"The board and the alarms could not be worked out: {wrong}")

    # **IS THE FILE REALLY THERE? WRITTEN DOWN WHERE ANYBODY CAN READ IT
    # (specification 25).** The day board above is a screen's view of a
    # fortnight; this is a standing record in the seller's own Drive, one line
    # per report per day, so nothing downstream has to list every folder itself
    # and nothing has to trust tonight's log. **It is also the evidence Golden
    # Rule 35 needs**: without it, three quiet nights cannot be told apart from
    # three nights when nothing ran.
    #
    # **THIS HALF WRITES ONLY ITS OWN LINES, AND THAT IS THE WHOLE SAFETY.**
    # `only_mine` refuses anything else, and `merge` leaves every line it was not
    # given exactly as it was -- so a night the seller's Chrome never opened
    # cannot mark one of the extension's twenty-three reports `missing`.
    #
    # **AND IT CANNOT STOP THE RUN.** Like the board and the run record, a
    # manifest that would not write costs a reader one answer and is said out
    # loud; refusing to fetch over it would turn a Drive blip into a lost day.
    if read_manifest is not None and save_manifest is not None:
        try:
            standing = manifest.read(read_manifest())
            fresh = manifest.lines_for(which, arrivals, today, checked_on=today)
            # **ASKED OF THE DOOR, NEVER OF WHAT THIS RUN HAPPENED TO BE
            # HANDED.** Derived from the list it was given, the answer would
            # always be yes and the refusal could never fire. This job is the API
            # half; a browser report reaching it is a fault, not a line to write.
            strayed = manifest.only_mine(fresh, manifest.mine(API, which))
            if strayed:
                faults.append(f"The download manifest was not written: {strayed}")
            else:
                save_manifest(manifest.write(manifest.merge(standing, fresh)))
        except Exception as wrong:  # noqa: BLE001 - recorded, never swallowed
            faults.append(
                f"Whether the files are really in Drive could not be written down: {wrong}"
            )

    # **AND THE RUN IS WRITTEN DOWN AGAIN, FINISHED.** The same name, so this
    # replaces the record written before the fetching rather than leaving two
    # records of one run. Written last, because until here it genuinely has not.
    _try(faults, save_run, "The run could not be written down as finished",
         name, moment, now(), "")

    # **THE EVIDENCE NOT LEAVING THE BUILDING IS OUR OWN DEFECT (D108), and until
    # now nothing anywhere read it.** `runlog.Run` has recorded a failed flush
    # since it was written, and no caller ever looked -- so a run whose log
    # reached neither the seller's Drive nor their database finished green.
    if happened.could_not_flush:
        faults.append(
            f"The run log could not be got out of the building: {happened.could_not_flush}. "
            "What happened tonight is not on any screen and not in the seller's Drive."
        )

    return Tick(
        ran=True,
        happened=happened,
        alarms_sent=sent,
        our_faults=tuple(faults),
        what_was_read=what_was_read,
    )


def how_the_night_ends(
    tick: Tick, could_not_write_sales: Optional[str],
) -> Tuple[Tuple[str, ...], int]:
    """What the job says last, and the number it exits with.

    **IT LIVES HERE BECAUSE `start.py` CANNOT BE DRIVEN.** That file needs a real
    Amazon account, a real Google account and a real network, so a rule written
    there is a rule nobody ever watches fail. This one was exactly that for a
    round: it sat in `start.main`, read by no check anywhere -- the same blind
    spot that left the whole sales ledger finished at both ends and called by
    nothing.

    **A NIGHT THAT COULD NOT WRITE THE SALES LEDGER NEVER REPORTS SUCCESS.** Two
    runs of this job have already "succeeded" in eleven seconds while doing
    nothing, and that is the failure this whole repository is written against.

    **AND IT IS SAID IN FULL, LINE BY LINE, WHERE A PERSON WILL SEE IT.** What
    comes back from the writing half is D184's five steps in the seller's own
    words -- restore it first, the offer to write the history again, what that
    cannot put back, and that no second sheet is made in its place. A one-line
    "the ledger failed" would send somebody looking in the wrong place.

    **RED ONLY FOR OUR OWN DEFECTS OTHERWISE (D108).** A report Amazon would not
    give up is recorded, alarmed and on the board, and the job did its work --
    turning that red as well is how a red tick stops meaning anything.
    """
    if could_not_write_sales:
        return tuple(
            f"ALARM  {one}" for one in could_not_write_sales.splitlines()
        ), 1
    return (), 1 if tick.is_a_defect else 0

def _try(faults: List[str], doing, called: str, *what) -> None:
    """Do one thing that writes a record for a screen, and never let it stop the run.

    **THESE ARE ALL THE SAME SHAPE AND THE SAME DECISION**, so they are written
    once: what must survive a run is what Amazon is building, and that is saved
    on its own path above. A board row or a run record failing to write costs a
    screen one line and is said out loud; refusing to fetch over it would turn a
    database blip into a lost day, and D108 says no day is ever lost.

    **NOT HANDED IN AT ALL IS NOT A FAILURE.** A tick can be driven with no
    database at all -- which is how every rule in this file is checked.
    """
    if doing is None:
        return
    try:
        doing(*what)
    except Exception as wrong:  # noqa: BLE001 - recorded, never swallowed
        faults.append(f"{called}: {wrong}")


# ------------------------------------------------------- the doing half


def _drive_folder(transport, inside: str, which: str) -> str:
    from drive_door import folder_for  # noqa: PLC0415 - kept beside its uses

    return folder_for(transport, which, inside)


def _arrivals_from_drive(transport, inside: str) -> Callable[[str], Sequence[Arrived]]:
    """What has really arrived, asked of the seller's own folder.

    **ASKED OF THE FILES, NEVER OF THE RUN'S OPINION OF ITSELF (D100).** A job can
    report success and still leave nothing usable behind, and the only thing that
    settles it is looking.
    """
    from drive_door import what_has_arrived  # noqa: PLC0415

    def arrivals(report_id: str) -> Sequence[Arrived]:
        folder_id = _drive_folder(transport, inside, report_id)
        return [
            Arrived(name=str(one.get("name") or ""), size=int(one.get("size") or 0))
            for one in what_has_arrived(transport, folder_id)
        ]

    return arrivals


def _the_folder_itself(transport, inside: str) -> Callable[[str], Sequence]:
    """What is really sitting in one report's folder, for the reading half.

    **THE SAME LISTING `arrivals` USES, ASKED A DIFFERENT QUESTION.** That one
    asks whether a day arrived and needs a name and a size. This one asks which
    files have not been read, and identity there is **Drive's own id, never the
    name** -- a day fetched again lands under the same name (D110), and keyed by
    name the correction would never be read.

    **THE SIZE IS CARRIED THROUGH because a nought-byte file is the third
    thing:** not new data and not already done. `whats_new` reports it and
    refuses to write it down as read, so tomorrow's real file for that day is
    still new.

    **IT DOES NOT CATCH ANYTHING.** A folder that will not list is `reading`'s to
    report as our own defect, and swallowing it here would leave it looking like
    a folder somebody emptied.
    """
    from drive_door import what_has_arrived  # noqa: PLC0415
    from whats_new import InTheFolder  # noqa: PLC0415

    def in_the_folder(report_id: str) -> Sequence:
        folder_id = _drive_folder(transport, inside, report_id)
        return [
            InTheFolder(
                which=str(one.get("id") or ""),
                name=str(one.get("name") or ""),
                size=int(one.get("size") or 0),
            )
            for one in what_has_arrived(transport, folder_id)
        ]

    return in_the_folder


def _one_file_back(transport) -> Callable[[str], bytes]:
    """One file's bytes, by Drive's own id. **The id, never the name.**"""
    from drive_door import bring_the_file_back  # noqa: PLC0415

    def bring_it_back(file_id: str) -> bytes:
        return bring_the_file_back(transport, file_id)

    return bring_it_back


def _state_in_drive(transport, inside: str) -> Tuple[Callable[[], Optional[bytes]], Callable[[bytes], None]]:
    """Reading and writing the run's own memory, in the seller's Drive (D100).

    **A FILE THAT IS NOT THERE ANSWERS None, and that is the first night.** A file
    that is there and will not read is `between_runs`' problem, not this one --
    the difference is the whole reason that file exists.
    """
    from drive import Landing, kind_of  # noqa: PLC0415
    from drive_door import (  # noqa: PLC0415
        bring_the_file_back,
        put_the_file,
        what_is_already_there,
        FILES,
        _answered,
    )

    def read_it() -> Optional[bytes]:
        folder_id = _drive_folder(transport, inside, OURS)
        there = [
            one for one in what_is_already_there(transport, folder_id)
            if one.get("name") == between_runs.FILE_NAME
        ]
        if not there:
            return None
        if len(there) > 1:
            raise RuntimeError(
                f"There are {len(there)} copies of {between_runs.FILE_NAME} in the seller's "
                "Drive. Which one the last run wrote cannot be known, so nothing has started."
            )
        return bring_the_file_back(transport, there[0]["id"])

    def save_it(body: bytes) -> None:
        folder_id = _drive_folder(transport, inside, OURS)
        older = [
            one["id"] for one in what_is_already_there(transport, folder_id)
            if one.get("name") == between_runs.FILE_NAME
        ]
        # **THE NEW ONE GOES UP FIRST, AND THE OLD ONE COMES AWAY AFTER (cycle
        # 46, R2#3).** Written the other way round, anything that threw between
        # the two -- a dropped connection, a full Drive, a quota -- left the
        # seller with NOTHING. This file is the whole memory of what Amazon is
        # building, so losing it makes the next run ask for every one of those
        # reports again: a rationed call spent, and two reports where there
        # should be one.
        #
        # **TWO COPIES FOR A MOMENT IS RECOVERABLE. NONE IS NOT.** If the tidying
        # below fails, the next run finds two and refuses out loud, by name --
        # which is a morning's confusion rather than a silent wrong answer.
        put_the_file(
            transport,
            Landing(
                folder_id=folder_id,
                file_name=between_runs.FILE_NAME,
                kind=kind_of(between_runs.FILE_NAME),
                size=len(body),
            ),
            body,
        )
        # **REPLACED, NEVER PUT BESIDE.** Two records of what the last run left is
        # two answers to what Amazon is building, and nothing could say which was
        # the real one -- which is why `read_it` above refuses when it sees two.
        for one in older:
            _answered(
                transport.delete(f"{FILES}/{one}"),
                f"taking away the older {between_runs.FILE_NAME}",
            )

    return read_it, save_it


def _manifest_in_drive(transport, inside: str) -> Tuple[Callable[[], Optional[bytes]], Callable[[bytes], None]]:
    """Reading and writing the download manifest, in the seller's Drive.

    **BESIDE THE RUN'S OWN MEMORY AND THE COPY OF THE LOG**, in the same
    `autosync` folder, through the same door -- so it needs no permission this
    job does not already hold, and a seller can open it themselves.

    **WRITTEN IN THE SAME ORDER AS THE OTHER TWO, FOR THE SAME REASON (cycle 46,
    R2#3): the new one goes up first and the old one comes away after.** Done the
    other way round, anything that threw between the two would leave the seller
    with no manifest at all -- and a manifest that is not there reads as "nobody
    has ever checked anything", which is the loudest wrong answer this record can
    give. Two copies for a moment is recoverable; none is not.

    **AND IT IS ITS OWN FUNCTION RATHER THAN THE STATE FILE'S WITH A NAME PASSED
    IN.** The two say different things when they find two copies of themselves --
    two of the state file means a run must not start, two of this means a reader
    cannot be answered -- and one message covering both is the thing this package
    keeps being caught by. `_log_to_drive` below already stands as its own for the
    same reason.
    """
    from drive import Landing, kind_of  # noqa: PLC0415
    from drive_door import (  # noqa: PLC0415
        bring_the_file_back,
        put_the_file,
        what_is_already_there,
        FILES,
        _answered,
    )

    def read_it() -> Optional[bytes]:
        folder_id = _drive_folder(transport, inside, OURS)
        there = [
            one for one in what_is_already_there(transport, folder_id)
            if one.get("name") == manifest.FILE_NAME
        ]
        if not there:
            # **NOT THERE IS AN ORDINARY FIRST NIGHT**, and `manifest.read`
            # answers an empty record for it. There and unreadable is that file's
            # own refusal, not this one's.
            return None
        if len(there) > 1:
            # **AND THIS IS WHERE IT STAYS UNTIL SOMEBODY TAKES ONE AWAY, WHICH IS
            # A DECISION RATHER THAN AN OVERSIGHT.** `save_it` below puts the new
            # copy up before taking the old one down, so a delete that fails, or a
            # job that dies between the two, leaves two. From then on this refuses
            # every night, `save_it` is never reached because `one_tick` reads
            # before it saves, and **nothing in the product ever clears it.**
            #
            # **THE RUN COULD CLEAR IT ONLY BY CHOOSING BETWEEN THE TWO, AND IT IS
            # NOT ENTITLED TO.** They are two standing records of the same thing
            # written at different moments; choosing the newer is reading a clock,
            # which is the one thing this whole record is written against, and
            # merging them is choosing an answer for every day they disagree on.
            # `merge` already refuses exactly this -- *"picking one is picking at
            # random"* -- and `drive.what_to_do_about` already settles the same
            # question the same way for a report's own folder: *"deleting the rest
            # is a decision nothing here is entitled to make."* A third answer to
            # one question is what this package keeps paying for.
            #
            # **SO IT REFUSES, AND WHAT MAKES THAT SAFE IS THAT IT IS NOT QUIET.**
            # The refusal is recorded as one of the run's own faults, `Tick.
            # is_a_defect` is true of any of those, and `how_the_night_ends`
            # returns 1 for a defect -- so the job goes red, and goes red again
            # every night, until somebody looks. **It still never stops the
            # fetching**, because refusing to fetch over a Drive blip would turn it
            # into a lost day. `nightly_checks.py` drives the whole sequence: the
            # tidy-up failing, two copies standing, and the night after it ending
            # red rather than looking ordinary.
            raise RuntimeError(
                f"There are {len(there)} copies of {manifest.FILE_NAME} in the seller's Drive. "
                "Which one holds the real answers cannot be known, so nothing has been read "
                "and nothing has been written over. Until all but one of them is taken away, "
                "whether the files are really in Drive stops being written down, and every "
                "night from now on ends red saying this."
            )
        return bring_the_file_back(transport, there[0]["id"])

    def save_it(body: bytes) -> None:
        folder_id = _drive_folder(transport, inside, OURS)
        older = [
            one["id"] for one in what_is_already_there(transport, folder_id)
            if one.get("name") == manifest.FILE_NAME
        ]
        put_the_file(
            transport,
            Landing(
                folder_id=folder_id,
                file_name=manifest.FILE_NAME,
                kind=kind_of(manifest.FILE_NAME),
                size=len(body),
            ),
            body,
        )
        # **REPLACED, NEVER PUT BESIDE.** Two manifests is two answers to "is the
        # file there", and nothing could say which was the real one -- which is
        # why `read_it` above refuses when it sees two.
        for one in older:
            _answered(
                transport.delete(f"{FILES}/{one}"),
                f"taking away the older {manifest.FILE_NAME}",
            )

    return read_it, save_it


def _log_to_drive(transport, inside: str, today: date) -> Callable[[Sequence[runlog.Line]], None]:
    """The copy of the run log that lives in the seller's own Drive (D100).

    **HIS INSTRUCTION, VERBATIM:** *"I would not want to store that on my storage,
    let it be in seller's drive."* The Kartaan screen is the everyday view; this
    copy is what survives when the app itself is the broken thing.

    One file a day. Drive cannot add to the end of a file, so what is there is
    read, the new lines go under it, and the whole thing replaces it -- which is
    also why this is called once, on the way out of the run, rather than per line.
    """
    from drive import Landing, kind_of  # noqa: PLC0415
    from drive_door import (  # noqa: PLC0415
        bring_the_file_back,
        put_the_file,
        what_is_already_there,
        FILES,
        _answered,
    )

    called = f"autosync-log-{today.isoformat()}.txt"

    def sink(lines: Sequence[runlog.Line]) -> None:
        folder_id = _drive_folder(transport, inside, OURS)
        there = [one for one in what_is_already_there(transport, folder_id) if one.get("name") == called]
        already = b""
        if len(there) == 1:
            already = bring_the_file_back(transport, there[0]["id"]) or b""
        elif len(there) > 1:
            raise RuntimeError(
                f"There are {len(there)} files called {called} in the seller's Drive, so the "
                "run log cannot be added to without losing one of them."
            )
        adding = "".join("\t".join(line.as_row()) + "\n" for line in lines)
        body = already + adding.encode("utf-8")
        # **UP FIRST, AWAY AFTER (cycle 46, R2#3).** This is the whole of today's
        # log, not just the new lines -- Drive cannot add to the end of a file --
        # so deleting before uploading and then failing loses every line already
        # written. **That is the exact failure this package exists against**: on
        # 25 August the reference fetched ten real files and left no trace of any
        # of them.
        put_the_file(
            transport,
            Landing(folder_id=folder_id, file_name=called, kind=kind_of(called), size=len(body)),
            body,
        )
        for one in there:
            _answered(transport.delete(f"{FILES}/{one['id']}"), f"taking away the older {called}")

    return sink


def _needed(name: str) -> str:
    """One secret, or a refusal naming which one is missing.

    **NAMED, because the alternative is a whole evening.** A door built without a
    credential fails on its first call with an authorization error that says
    nothing about which of six values was left out.

    **The value itself never appears anywhere** -- not in this message, not in the
    log, not in the run's record. Golden Rule 8.
    """
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(
            f"{name} is not set. It is a GitHub Actions secret on the seller's own repository, "
            "and nothing runs without it."
        )
    return value
