/* What a seller is told, in the two lengths they ask in.
 *
 * **WRITTEN AS DATA, NOT AS A PAGE** -- the same decision the ERP made in
 * `src/shared/definitions/manual.js`, and for the same reason. A manual buried
 * inside the markup that draws it cannot be checked, cannot be searched, and
 * drifts away from the product the first time a screen changes. Held here, a
 * check can ask whether every part of the panel still has an entry, and one that
 * loses its entry goes red rather than quietly shipping a help card with a hole
 * in it.
 *
 * **IT ANSWERS THE QUESTION A SELLER ACTUALLY ARRIVES WITH.** Not "the reports
 * list shows your reports" -- they can see that. What they want to know is why
 * one of them says nothing was fetched, and whether that means something is
 * broken.
 *
 * **THREE LENGTHS, BECAUSE THREE DIFFERENT PEOPLE READ THEM. His instruction,
 * 2026-09-11:** a tooltip beside the thing, a manual for somebody who wants to be
 * shown, and a developer's document for whoever works on this next. The third is
 * `docs/HOW_IT_WORKS.md` and is not in here, because nobody reading the panel
 * wants it.
 *
 * **A TOOLTIP AND AN ENTRY MAY NOT DISAGREE, AND THE TOOLTIP WINS.** It sits next
 * to the thing it describes, so it is the one that gets noticed when it is wrong.
 */

/** The short line beside a control. **Keyed by the part's own name in
 *  `screen.js`**, so a check can pair them up and a control that grows without
 *  one goes red rather than shipping bare.
 *
 *  **SHORT MEANS ONE SENTENCE.** A tooltip nobody finishes reading is a tooltip
 *  that did not help, and the manual is where the long answer lives. */
export const TOOLTIPS = {
  connectDrive: 'Lets Kartaan put your reports into your own Google Drive. It can only ever see '
    + 'the folder it makes itself, and you do this once.',
  panelName: 'The part of your own Meesho address between "fulfillment/" and "/orders". It is '
    + 'yours, so it is not built into the extension.',
  savePanel: 'Keeps the panel name on this computer. Nothing is sent anywhere.',
  runNow: 'Fetches the ticked reports now, for yesterday. Leave the window alone while it works.',
  from: 'The first day to fetch. Leave both date boxes empty and Run now fetches yesterday, '
    + 'which is the usual thing.',
  to: 'The last day to fetch. With a day in the first box too, every day between the two is '
    + 'fetched, oldest first, up to a month at a time.',
  stop: 'Stops the run after the report it is on. What has already landed stays.',
  resume: 'Shown when a platform asked you to sign in. Sign in first, then this carries on from '
    + 'the report where the sync stopped.',
  hour: 'The hour it runs by itself, every day. Your computer has to be awake and Chrome open.',
  log: 'What the last run did, in its own words. It is written as it happens, so an '
    + 'interrupted run still says how far it got.',
};

/** One entry per part of the panel.
 *
 *  `id`    matches the part's own name in `screen.js`, so a check can pair them
 *          and a missing entry is a failure rather than a gap nobody notices.
 *  `crux`  one line. What this part is for.
 *  `steps` what a seller comes here to do, in order.
 *  `more`  why it works this way. Skippable, and worth keeping: every one of
 *          these was written after something went wrong.
 */
export const MANUAL = [
  {
    id: 'setup',
    label: 'Set up, once',
    crux: 'Two things only you can do, and nothing runs until both are done.',
    steps: [
      'Press Connect Google Drive and choose your own account. Kartaan makes one folder called '
        + '"Kartaan" and can never see anything else in your Drive.',
      'Paste your Meesho panel name and press Save. Open your own supplier panel and look at the '
        + 'address: it is the short word between "fulfillment/" and "/orders".',
    ],
    more: [
      'The Drive is asked for once, while you are sitting there. A run at two in the morning '
        + 'asks quietly, and if permission has never been given it stops and says so rather than '
        + 'putting a window in front of nobody and waiting for ever.',
      'Your panel name is not in the extension because the extension is the same for every '
        + 'seller. Nothing about you is written into it.',
    ],
  },
  {
    id: 'reports',
    label: 'The reports',
    crux: 'Everything Kartaan can fetch from your platforms, whether it can fetch it yet, and '
      + 'what happened to it last time.',
    steps: [
      'Every report starts ticked. Untick the ones you do not want and press Run now. With '
        + 'both websites ticked it runs Flipkart first, then Meesho.',
      'A greyed-out row is one this cannot fetch at all. The reason is written underneath the '
        + 'list, in words, rather than left as a report that silently never arrives.',
      'Two of the ad reports have no tick of their own. They show ticked when the ads report '
        + 'is, because they arrive with it out of the same request, and the row says so.',
    ],
    more: [
      'A run fetches YESTERDAY. Platforms finish a day before they publish it, so today is not '
        + 'a day anybody can ask for yet.',
      'Meesho and Flipkart are never run side by side. They are two different sites, so with both '
        + 'ticked Flipkart runs first and Meesho starts when it ends.',
    ],
  },
  {
    id: 'words',
    label: 'What the words mean',
    crux: 'Six answers. Only "Failed" means something is wrong, and only "Needs you" is yours to do.',
    steps: [
      'Landed: the file is in your Drive. The number beside it is how big it is.',
      'Still waiting: the platform is building it. It is collected on a later run.',
      'Nothing to fetch: there was genuinely nothing. No ad campaign was running, or the '
        + 'platform publishes that report on its own cycle and today is not one of its days.',
      'Failed: something went wrong, and the line says what. This is the only one worth acting '
        + 'on.',
      'Not available yet: the platform has not published that day yet, so nothing was asked for '
        + 'and none of your Flipkart requests were used. It is tried again on your next runs.',
      'Needs you: the platform still had not published that day after three days of trying. '
        + 'Kartaan stops trying and names the day at the top of this page, so you can fetch it by '
        + 'hand.',
    ],
    more: [
      '"Nothing to fetch" is written out in full on purpose. A report that quietly writes no '
        + 'file and reports a good sync is how a seller ends up with an empty folder and no '
        + 'idea anything was missing.',
      'A failure keeps the first few hundred characters of what was really on the page. It is '
        + 'the difference between "a button is missing" and "you had been signed out".',
    ],
  },
  {
    id: 'allowance',
    label: 'Flipkart lets you ask twenty times a day',
    crux: 'Three Flipkart reports spend one of those each. The panel shows how many are left.',
    steps: [
      'Watch the number before running Flipkart twice in a morning.',
      'A report is counted the moment it is asked for, not when it comes back.',
    ],
    more: [
      'Counted before rather than after on purpose. A computer that shuts down mid-request must '
        + 'leave the count too high rather than too low: too high costs you one report, too low '
        + 'costs you the rest of the day.',
    ],
  },
  {
    id: 'hour',
    label: 'The scheduled sync time',
    crux: 'It runs by itself once a day, at the hour you choose.',
    steps: [
      'Pick an hour you are not using the computer. Chrome has to be open and the machine awake.',
      'If it was asleep, the run happens the next time Chrome starts.',
      'It fetches every report on its own list, shown under the time. The ticks for Run now '
        + 'do not change it.',
    ],
    more: [
      'It moves like a person on purpose -- a few seconds looking at a page that has just drawn, '
        + 'about a second between one action and the next. A platform that reads the run as a '
        + 'machine can block your account, and the pause is never the same length twice.',
    ],
  },
  {
    id: 'log',
    label: 'What the last run did',
    crux: 'Every report it reached, what became of each, and what it did not get to.',
    steps: [
      'Read it the morning after. It says what was never reached as well as what was.',
    ],
    more: [
      'It is written as the run happens, not at the end. A run that is interrupted half way '
        + 'still says how far it got, which is the whole difference between this and a summary '
        + 'that is lost with the run that was writing it.',
    ],
  },
];

/** The manual entry for one part, or nothing. */
export function theEntryFor(id) {
  return MANUAL.find((one) => one.id === id) || null;
}
