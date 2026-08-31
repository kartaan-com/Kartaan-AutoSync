/* A small stand-in for a browser, so the parts of the product that draw on a
 * screen can be checked without one.
 *
 * ONE of these, shared by every check that needs it. A second copy is how the
 * two drift apart, and this project's own register records three separate
 * occasions where a defect hid behind a stand-in that behaved better than the
 * real thing (cycles 6, 7, 8 and 9 in audit/out/solved_problems.md).
 *
 * IT IS DELIBERATELY AWKWARD. Every place a real browser is unhelpful, this
 * is unhelpful in the same way, because being generous here is what hid those
 * defects:
 *
 *   - a dropdown accepts only values that are on its list, and always hands
 *     back text, never the type that was put in;
 *   - a number box holds only what a number box can hold, and goes blank for
 *     anything else -- "0x10" and " 5 " both convert to numbers and neither
 *     can ever appear in the box;
 *   - a switched-off control cannot be clicked and cannot take the keyboard;
 *   - anything taken off the page loses the keyboard, the way a browser drops
 *     it to nowhere;
 *   - only what is genuinely attached to the page can be focused at all.
 *
 * WHERE IT IS HARSHER than a real browser, written down so the next person
 * is not surprised.
 *
 * **NO COUNT IS GIVEN, on purpose (cycle 46, R5#8).** What stood here said
 * two, then three, then five, and the list under it ran to six -- one of
 * which was not a harshness at all but a KINDNESS, filed under the opposite
 * heading. A number typed into a comment is wrong from the next edit.
 *
 * Being harsh is not automatically safe, and the tempting sentence that it
 * "can only make a check fail, never pass" is wrong: a check asserting
 * something is ABSENT passes for the wrong reason when this cannot find what
 * a real browser would. The version-stamp checks assert "Version not stated",
 * so if the product ever moved that tag into the body, this would answer
 * nothing, the check would stay green, and a real browser would find it.
 * Harsh in the wrong place hides a fault exactly the way generous does.
 *
 * They are:
 *
 *   - querySelector understands exactly one shape, `meta[name="x"]` with
 *     double quotes, and throws at anything else. A real browser accepts
 *     single quotes, no quotes and spare whitespace. The throw is deliberate
 *     and matches matchMedia: a question this does not understand, answered
 *     with a silent "nothing found", looks exactly like the thing genuinely
 *     being absent;
 *   - it searches only the meta tags a check supplied, so a meta tag placed
 *     anywhere in the page body is invisible to it. A real browser searches
 *     the whole document;
 *   - a click submits a form only when the button ITSELF is clicked. A real
 *     browser also submits when something inside the button is clicked;
 *   - a form is submitted by a CLICK on its submit button and by nothing else.
 *     A real browser also submits it from the keyboard -- Enter in a single-
 *     line box -- which is the whole reason the product wraps its fields in a
 *     form element at all. So the one behaviour that element exists for cannot
 *     be checked here, and has to be looked at in a real browser;
 *   - removeAttribute works on attributes only, and does NOT reflect the
 *     `hidden`, `disabled` or `title` properties the product sets directly.
 *     Ask the property, not the attribute;
 *
 * AND WHERE IT IS KINDER, which is the more dangerous direction: a stand-in
 * that lets something through is how a defect reaches a real browser.
 *
 *   - **a value put into a box is kept exactly as it was given.** A real
 *     browser NORMALISES: a one-line box strips carriage returns and line
 *     feeds out of whatever is assigned to it, and a notes box folds CRLF to
 *     LF. This keeps both. That matters because the form refuses a starting
 *     value the box did not hand back unchanged -- so a record whose name or
 *     notes arrived carrying a line break would be refused by a real browser
 *     and accepted here, and no check in this repo can see the difference;
 *   - **`children` is an ordinary array**, so it carries .find, .filter and
 *     .map. A real browser hands back a list with none of them. That one is
 *     caught elsewhere: `tools/check_product.py` refuses product code that
 *     reaches for a list method a real browser does not give you, and the
 *     note further down this file says the same thing at the code.
 *
 * It lives outside src/ on purpose: it is not part of the product and must
 * never be served with it.
 */

/* Exactly what a number box accepts: an optional minus, digits, an optional
 * decimal part, an optional exponent. */
const NUMBER_BOX = /^-?\d+(\.\d+)?([eE][-+]?\d+)?$/;

/* KNOWN PLACE THIS IS MORE GENEROUS THAN A REAL BROWSER, written down rather
 * than left to be discovered: `children` here is an ordinary array, so it
 * carries .find, .filter and .map. A real browser hands back a list that has
 * none of those -- only .length and being able to loop over it. Product code
 * must therefore use Array.from(...) before reaching for any of them, or it
 * will pass every check here and fail in front of a seller. That very mistake
 * was made and caught while wiring up scrolling. */
export class FakeNode {
  constructor(tag) {
    this.tagName = tag;
    this.type = '';
    this.id = '';
    this.children = [];
    this.parentNode = null;
    this.dataset = {};
    this.disabled = false;
    this.checked = false;
    this.title = '';
    this.colSpan = 1;
    this.scope = '';
    this.placeholder = '';
    this.hidden = false;
    /* Anything not set reads as empty text, the way a real one does, rather
     * than as nothing at all. Code that saves a style and puts it back would
     * otherwise put back "undefined". */
    this.style = new Proxy(
      {},
      {
        get: (held, name) => (name in held ? held[name] : ''),
        set: (held, name, value) => {
          held[name] = value;
          return true;
        },
      }
    );
    this._classes = new Set();
    this._text = '';
    this._value = '';
    this._listeners = new Map();
    this._attributes = {};
  }

  get className() {
    return [...this._classes].join(' ');
  }
  set className(value) {
    this._classes = new Set(String(value).split(/\s+/).filter(Boolean));
  }

  get classList() {
    const classes = this._classes;
    return {
      add: (c) => classes.add(c),
      remove: (c) => classes.delete(c),
      contains: (c) => classes.has(c),
      toggle: (c, on) => (on ? classes.add(c) : classes.delete(c)),
    };
  }

  get textContent() {
    return this._text + this.children.map((c) => c.textContent).join('');
  }
  set textContent(value) {
    this.children = [];
    this._text = String(value);
  }

  /* AN OPTION NOBODY GAVE A VALUE TO IS WORTH ITS OWN TEXT.
   *
   * A real browser answers with the text between the tags. This answered with
   * an empty string, so an options list built without values looked like a list
   * of blanks -- and "nothing is chosen" could never be told apart from
   * "chosen, and it happens to be empty". */
  _optionValue() {
    return this._valueSet ? this._value : this.textContent;
  }

  get value() {
    if (this.tagName === 'option') return this._optionValue();
    return this._value;
  }
  set value(v) {
    const wanted = String(v);
    this._valueSet = true;
    if (this.tagName === 'select') {
      const known = this.children.some((c) => c.tagName === 'option' && c._optionValue() === wanted);
      this._value = known ? wanted : '';
      return;
    }
    if (this.tagName === 'input' && this.type === 'number') {
      this._value = wanted === '' || NUMBER_BOX.test(wanted) ? wanted : '';
      return;
    }
    this._value = wanted;
  }

  append(...nodes) {
    for (const node of nodes) {
      if (node.parentNode) {
        /* Moved, not taken off the page. A browser keeps the keyboard on
         * something that is only being shifted about while it stays on the
         * page, so unhooking it plainly rather than through remove() -- which
         * drops the keyboard -- matters. Being HARSHER than a real browser is
         * as bad as being kinder: it would report focus lost where a real one
         * keeps it, and send someone chasing a fault that is not there. */
        const from = node.parentNode;
        from.children = from.children.filter((c) => c !== node);
        node.parentNode = null;
      }
      node.parentNode = this;
      this.children.push(node);
      /* A DROPDOWN SELECTS ITS FIRST OPTION THE MOMENT ONE IS ADDED.
       *
       * A real browser does. This did not -- a select started empty and stayed
       * empty until something assigned to it -- which made the product's
       * "nothing is chosen to begin with" behaviour true here whatever the
       * product did. Move the empty-valued placeholder BELOW the options loop,
       * or delete it, and in a real browser the box opens on the first real
       * option with nothing saying so: a seller adding a bought-in part saves
       * it as a raw material. Every check stayed green.
       *
       * Fourth logging of "a stand-in kinder than a browser lets code pass
       * everything and fail in front of a seller". */
      if (this.tagName === 'select' && node.tagName === 'option'
          && this.children.filter((c) => c.tagName === 'option').length === 1) {
        this._value = node._optionValue();
      }
    }
  }

  _detach(node) {
    node.parentNode = null;
    /* A browser does not leave the keyboard on something it has taken off the
     * page -- it drops it entirely. */
    const doc = globalThis.document;
    if (doc && doc.activeElement && node.contains(doc.activeElement)) {
      doc.activeElement = null;
    }
  }

  replaceChildren(...nodes) {
    for (const child of this.children) this._detach(child);
    this.children = [];
    this.append(...nodes);
  }

  remove() {
    if (!this.parentNode) return;
    const parent = this.parentNode;
    parent.children = parent.children.filter((c) => c !== this);
    parent._detach(this);
  }

  contains(node) {
    if (node === this) return true;
    return this.children.some((c) => c.contains(node));
  }

  setAttribute(name, value) {
    this._attributes[name] = String(value);
  }
  getAttribute(name) {
    return Object.prototype.hasOwnProperty.call(this._attributes, name) ? this._attributes[name] : null;
  }
  removeAttribute(name) {
    delete this._attributes[name];
  }

  /** On the page at all? Walks up to the body, the way a browser decides
   *  whether something can be focused. */
  isAttached() {
    let node = this;
    while (node.parentNode) node = node.parentNode;
    return node === globalThis.document.body;
  }

  /* Where this sits on the screen. A check sets it; nothing works it out,
   * because nothing here lays anything out. Defaults to somewhere plainly
   * on screen so most checks need not think about it. */
  getBoundingClientRect() {
    if (this._rect) return this._rect;
    /* Anything built after a check has started -- a redrawn row, a rebuilt
     * button -- cannot have been given a place beforehand, so a check can set
     * where everything lands by default. */
    const fallback = globalThis.document && globalThis.document.defaultRect;
    return fallback || { top: 0, bottom: 100, left: 0, right: 100, width: 100, height: 100 };
  }

  setRect(rect) {
    this._rect = rect;
  }

  scrollIntoView(options) {
    /* Recorded rather than done. What matters to a check is whether it was
     * asked for, and how. */
    globalThis.document.scrolledInto.push({ node: this, options });
  }

  focus() {
    if (this.disabled) return;
    /* A browser refuses to focus something hidden, even when asked directly.
     * Allowing it would let a check say the keyboard landed somewhere the
     * person using it could not see. */
    if (this.hidden) return;
    if (!this.isAttached()) return;
    globalThis.document.activeElement = this;
  }

  addEventListener(type, fn) {
    if (!this._listeners.has(type)) this._listeners.set(type, []);
    this._listeners.get(type).push(fn);
  }

  /* details carries what a real event would -- the key pressed, and whether
   * anything called preventDefault. A stand-in that only ever passes an empty
   * event cannot check anything that reads one.
   *
   * It also travels UP, the way a real one does: a click on something inside
   * reaches the listeners on everything around it, and `target` stays the
   * thing actually clicked the whole way. Without that, a guard like "only
   * close if the click was on the dark area itself, not on the popup inside
   * it" could not be checked at all -- which is exactly the kind of gap that
   * has let a defect through here before. */
  fire(type, details = {}) {
    if (this.disabled) return { defaultPrevented: false };
    let defaultPrevented = false;
    let stopped = false;
    const event = {
      type,
      target: this,
      ...details,
      preventDefault() {
        defaultPrevented = true;
      },
      /* Something can say "I have dealt with this, do not let it carry on
       * upward" -- which is how a button inside a row explains itself without
       * also opening the row. Without this the guard could not be checked. */
      stopPropagation() {
        stopped = true;
      },
    };

    /* AN EVENT THAT SAYS IT DOES NOT TRAVEL, DOES NOT.
     *
     * Everything the product fires is a real user action -- a click, a change,
     * a key -- and every one of those travels upward, so leaving this out was
     * right until something started dispatching events of its own. It is not
     * now: an event built with `bubbles: false` reaches only the thing it was
     * aimed at, and a stand-in that carries it upward anyway would let code
     * that never tells the page about a change pass every check here and fail
     * in front of a seller. Only an explicit false changes anything, so
     * nothing that was firing before behaves differently. */
    const travels = details.bubbles !== false;
    let node = this;
    while (node && !stopped) {
      for (const fn of [...(node._listeners.get(type) || [])]) fn(event);
      node = travels ? node.parentNode : null;
    }

    /* **AND ON TO THE DOCUMENT, which is where the chain really ends.** It used
     * to stop at `body`, so anything listening on the document heard nothing --
     * and "a press anywhere else on the page" has nowhere else to listen. Only
     * when the event travels, and only if nothing stopped it: both are true of
     * a real browser. */
    if (travels && !stopped && globalThis.document) {
      for (const fn of [...(globalThis.document._listeners?.get(type) || [])]) fn(event);
    }

    /* A real browser submits the form when a submit button inside it is
     * clicked -- the click and the submit are two separate events and product
     * code listens for the second. Without this, a form would have to listen
     * for clicks on its own button instead, which is not how a form works and
     * would then not respond to Enter either. Left out at first, and every
     * check that pressed Save read as "it did not save".
     *
     * Nothing here for preventDefault on the click: a browser skips the submit
     * in that case, and so does this. */
    /* A button with no type set at all IS a submit button in a real browser --
     * that is the HTML default. The stand-in defaulted `type` to empty text, so
     * such a button submitted nothing here and would submit in front of a
     * seller. Nothing in the product relies on it today because every button
     * sets its type; this is so the day one does not, a check catches it rather
     * than a seller. */
    const acts = this.tagName === 'button' && (this.type === 'submit' || this.type === '');
    if (type === 'click' && !defaultPrevented && acts) {
      let form = this.parentNode;
      while (form && form.tagName !== 'form') form = form.parentNode;
      if (form) form.fire('submit');
    }

    return { defaultPrevented, stopped };
  }

  /* BEING TOLD TO CLICK, rather than only being clicked on.
   *
   * Everything above is about RECEIVING what a person did. The auto-sync
   * driver is the first code here that has to DO it -- it is handed a page it
   * did not build and told to press one thing on it. A real element has both
   * of these; without them the driver could only be checked by inventing a
   * second stand-in, which is how two stand-ins drift apart. */
  click() {
    this.fire('click');
  }

  /** What a browser does with an event handed to it: passes it to whatever is
   *  listening, from here upwards. `fire` already does exactly that. */
  dispatchEvent(event) {
    /* `bubbles` is read by name rather than swept up with the rest. On a real
     * Event it lives on the prototype, so spreading the object gives nothing at
     * all -- and every event would then look like one that travels. */
    const { defaultPrevented } = this.fire(String(event.type), { bubbles: event.bubbles === true });
    return !defaultPrevented;
  }

  /** Find the first thing below here carrying a class. For checks only. */
  find(className) {
    if (this._classes.has(className)) return this;
    for (const child of this.children) {
      const hit = child.find(className);
      if (hit) return hit;
    }
    return null;
  }

  findAll(className, out = []) {
    if (this._classes.has(className)) out.push(this);
    for (const child of this.children) child.findAll(className, out);
    return out;
  }

  findById(id) {
    if (this.id === id) return this;
    for (const child of this.children) {
      const hit = child.findById(id);
      if (hit) return hit;
    }
    return null;
  }
}

/** Put a fresh browser in place. Call at the start of a checks file, and
 *  again whenever a check needs a clean page.
 *
 *  width sets what the page thinks it is, so a rule that only applies to a
 *  phone can be checked. */
export function installFakeBrowser({ width = 1280, height = 800, reducedMotion = false, meta = {} } = {}) {
  const body = new FakeNode('body');
  let viewport = width;

  /* Whatever the page states about itself -- today only the version stamp.
   *
   * A tag whose content was never set does NOT get one. Putting anything that
   * is not text through setAttribute turns it into text, so an unset content
   * would come back as the nine-character word "undefined" -- a
   * plausible-looking wrong answer where a real browser hands back null, and
   * a shell built against it would print that word in the top bar. That is
   * the fault already fixed once in this very file, thirty lines above, for
   * an unset style. Pass `{ 'kartaan-version': undefined }` to get a tag that
   * genuinely has a name and no content.
   *
   * ONLY `undefined` means that. Everything else is stored, a number
   * included, because turning a number into text is exactly what a real
   * setAttribute does -- it is only wrong for the value that was never given.
   * Refusing anything that is not already text would quietly make it
   * impossible to check what happens when a page states something odd, which
   * is its own way of being kinder than a browser. */
  const metaTags = Object.entries(meta).map(([name, content]) => {
    const tag = new FakeNode('meta');
    tag.setAttribute('name', name);
    if (content !== undefined) tag.setAttribute('content', content);
    return tag;
  });

  /* **THE DOCUMENT CAN BE LISTENED TO, because a real one can.**
   *
   * It could not be, and events stopped at `body` -- so the one way to hear "a
   * press anywhere else on the page", which is what closes any menu, could not
   * be checked here at all. A stand-in that cannot show a defect is this
   * register's most expensive recurring fault, and this was one: the column
   * chooser's close-on-outside-press was written, and nothing in the harness
   * could tell whether it worked or whether it leaked a listener per table. */
  const documentListeners = new Map();

  const document = {
    body,
    activeElement: null,
    _listeners: documentListeners,
    addEventListener(type, fn) {
      if (!documentListeners.has(type)) documentListeners.set(type, []);
      documentListeners.get(type).push(fn);
    },
    /* **REMOVAL REALLY REMOVES**, and it is asked by the same function object a
     * real one is. A removal that quietly did nothing would let a listener leak
     * per table -- hundreds in a morning, since this product tears a screen
     * down and rebuilds it on every tab change -- and every check would pass. */
    removeEventListener(type, fn) {
      const held = documentListeners.get(type);
      if (!held) return;
      const at = held.indexOf(fn);
      if (at !== -1) held.splice(at, 1);
    },
    /** How many are listening for this right now. Nothing in the product may
     *  ask -- it is here so a check can see a listener that was never taken
     *  off, which is invisible from any behaviour. */
    listenerCount: (type) => (documentListeners.get(type) || []).length,
    createElement: (tag) => new FakeNode(tag),
    getElementById: (id) => body.findById(id),
    /* Only the one shape the product actually asks for. Anything else throws
     * rather than quietly answering "nothing found" -- for the same reason
     * matchMedia does: a question this does not understand, answered with a
     * silent no, looks exactly like the thing genuinely being absent. */
    querySelector(selector) {
      const asked = String(selector).trim();

      const wanted = /^meta\[name="([^"]+)"\]$/.exec(asked);
      if (wanted) {
        for (const tag of metaTags) {
          if (tag.getAttribute('name') === wanted[1]) return tag;
        }
        return null;
      }

      /* **A PLAIN CLASS, because a real browser answers that and the product
       * asks it.** The table's panels have to know where the top bar ends so
       * they never open across it, and the bar belongs to the shell -- there is
       * nothing to hand it in through.
       *
       * ADDED RATHER THAN WRAPPED IN A TRY: the product asking a question this
       * cannot answer used to throw, and the tempting fix is to catch it at the
       * call site. That would mean the stand-in's ignorance silently becoming
       * "there is no top bar", which is a different answer -- and it is the
       * answer that would let a panel open over the bar in a real browser with
       * every check still green. */
      const byClass = /^\.([A-Za-z0-9_-]+)$/.exec(asked);
      if (byClass) return body.find(byClass[1]);

      throw new Error(`The stand-in browser was asked for "${selector}", which it does not understand.`);
    },
    /* Everything that was asked to be scrolled to, in order. */
    scrolledInto: [],
  };

  globalThis.document = document;

  /* WHAT THE BROWSER WORKED OUT A THING SHOULD LOOK LIKE.
   *
   * Needed because on Meesho's supplier panel the ONLY thing marking a sidebar
   * item as something a person can press is the mouse cursor -- there is no
   * button, no link and no role attribute anywhere on that page.
   *
   * TWO PLACES THIS IS HARSHER THAN A REAL BROWSER, written down rather than
   * left to be discovered:
   *
   *   - it hands back only what was set ON THAT THING. A real browser works out
   *     the answer from the stylesheets as well;
   *   - and it does NOT inherit. `cursor` really does pass down to everything
   *     inside, so a real page has far more pressable things than this does --
   *     which the innermost rule then reduces to one either way. A check has to
   *     mark the thing it means, and it cannot check what inheriting does. */
  globalThis.getComputedStyle = (node) => {
    if (!node || !node.style) {
      throw new Error('The stand-in browser was asked how something with no style looks.');
    }
    return node.style;
  };

  globalThis.window = {
    innerWidth: width,
    innerHeight: height,
    /* Only the shapes the product actually asks about. Anything else throws
     * rather than quietly answering "no", because a stand-in that shrugs is
     * how a rule goes unchecked -- an unrecognised question answered with a
     * silent no looks exactly like the rule being off. */
    matchMedia(query) {
      const text = String(query).trim();

      const wide = /^\(min-width:\s*(\d+(?:\.\d+)?)px\)$/.exec(text);
      if (wide) return { matches: viewport >= Number(wide[1]) };

      if (text === '(prefers-reduced-motion: reduce)') return { matches: reducedMotion };

      throw new Error(`The stand-in browser was asked about "${query}", which it does not understand.`);
    },
    addEventListener() {},
    removeEventListener() {},
  };

  return {
    document,
    body,
    /** A container already on the page, which is what a real one always is. */
    container() {
      const node = new FakeNode('div');
      body.append(node);
      return node;
    },
    /** Change how wide the page is, for checking phone behaviour.
     *  Both records of the width move together -- two records of one fact
     *  that can disagree is a rule this project has already been caught by. */
    setWidth(next) {
      viewport = next;
      globalThis.window.innerWidth = next;
    },
  };
}
