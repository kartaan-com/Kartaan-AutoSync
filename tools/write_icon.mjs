/* The extension's own mark, drawn here rather than kept as a binary nobody can read.
 *
 * **IT EXISTS BECAUSE A NOTIFICATION MUST CARRY A PICTURE (A53, 2026-09-16).** The
 * sign-in alert was created with a one-pixel `data:` image, and when he signed out
 * of Meesho on purpose to test it, NOTHING APPEARED -- the sync paused correctly,
 * wrote it all down correctly, and told him where he was not looking. Chrome
 * refuses a notification's picture without a word any program can read, so the
 * picture is a real file in the extension.
 *
 * **WHAT IT SHOWS: KARTAAN'S OWN K.** The first drawing was a page falling into a
 * tray, and he was right about it -- *"this icon does not represent kartaan or
 * autosync"*. It was any download manager's mark. There is no Kartaan logo in any
 * of his repositories: the brand IS the word, set in brown, which is what the
 * panel's own bar shows. So the mark is that word's letter, in the panel's two
 * colours, and nothing borrowed from a platform.
 *
 * Run: node tools/write_icon.mjs
 */
import { deflateSync } from 'node:zlib';
import { writeFileSync } from 'node:fs';

/* The panel's own two colours (`from-the-erp/tokens.css`). */
const INK = [61, 26, 11];
const PAPER = [250, 246, 240];
const SIZES = [16, 32, 48, 128];
/* Four samples across and four down: enough to make an edge read as an edge
 * rather than a staircase, at sixteen pixels as well as at a hundred and
 * twenty-eight. */
const SAMPLES = 4;

const clamp = (n, low, high) => Math.min(high, Math.max(low, n));

/** Inside a rounded rectangle, in units where the icon is 1 x 1? */
function inRoundedRect(x, y, left, top, right, bottom, radius) {
  const r = Math.min(radius, (right - left) / 2, (bottom - top) / 2);
  const nearestX = clamp(x, left + r, right - r);
  const nearestY = clamp(y, top + r, bottom - r);
  if (x < left || x > right || y < top || y > bottom) return false;
  const dx = x - nearestX;
  const dy = y - nearestY;
  return dx * dx + dy * dy <= r * r;
}

/** Inside a line of a given thickness drawn from one point to another? */
function inStroke(x, y, fromX, fromY, toX, toY, thickness) {
  const alongX = toX - fromX;
  const alongY = toY - fromY;
  const length = alongX * alongX + alongY * alongY;
  const how = length === 0 ? 0
    : clamp(((x - fromX) * alongX + (y - fromY) * alongY) / length, 0, 1);
  const dx = x - (fromX + how * alongX);
  const dy = y - (fromY + how * alongY);
  return dx * dx + dy * dy <= thickness * thickness;
}

/** Inside a ring, between these two angles, with a gap left everywhere else? */
function inArc(x, y, radius, thickness, fromTurn, toTurn) {
  const dx = x - 0.5;
  const dy = y - 0.5;
  const away = Math.sqrt(dx * dx + dy * dy);
  if (Math.abs(away - radius) > thickness) return false;
  /* Turns rather than degrees: nought is due right, a quarter is straight down. */
  let turn = Math.atan2(dy, dx) / (Math.PI * 2);
  if (turn < 0) turn += 1;
  return fromTurn < toTurn
    ? (turn >= fromTurn && turn <= toTurn)
    : (turn >= fromTurn || turn <= toTurn);
}

/** Inside the triangle with these three corners? */
function inTriangle(x, y, ax, ay, bx, by, cx, cy) {
  const side = (px, py, qx, qy) => (qx - px) * (y - py) - (qy - py) * (x - px);
  const one = side(ax, ay, bx, by);
  const two = side(bx, by, cx, cy);
  const three = side(cx, cy, ax, ay);
  return (one >= 0 && two >= 0 && three >= 0) || (one <= 0 && two <= 0 && three <= 0);
}

/* Where the ring runs, and the head at the end of it: worked out once here
 * rather than inside the loop that asks about four million points.
 *
 * **THE HEAD IS A TRIANGLE ON THE END OF THE TURN, SET ACROSS IT.** Drawn as two
 * barbs swept back it came out as a loose blob at sixteen pixels, and twice at a
 * hundred and twenty-eight. Its tip runs on along the way the ring is going and
 * its base sits across the ring, which is how an arrow on a dial is drawn. */
const RING = 0.385;
const ENDS_AT = 0.86;
const HEAD = (() => {
  const turn = Math.PI * 2 * ENDS_AT;
  const outX = Math.cos(turn);
  const outY = Math.sin(turn);
  const goingX = -outY;
  const goingY = outX;
  const atX = 0.5 + RING * outX;
  const atY = 0.5 + RING * outY;
  return {
    tipX: atX + goingX * 0.125,
    tipY: atY + goingY * 0.125,
    leftX: atX + outX * 0.082,
    leftY: atY + outY * 0.082,
    rightX: atX - outX * 0.082,
    rightY: atY - outY * 0.082,
  };
})();

/**
 * What colour this point is: the mark drawn in units of 0..1.
 *
 * **KARTAAN AND AUTO-SYNC, BOTH (his ruling, 2026-09-16).** The K is Kartaan --
 * there is no logo in any of his repositories, so the brand is the word and this
 * is its letter. The ring turning round it, with an arrow head where the turn
 * ends, is the fetching: the one mark every person already reads as "this goes
 * round again by itself". Another Kartaan tool carries the same K and no ring.
 */
function colourAt(x, y) {
  if (!inRoundedRect(x, y, 0.02, 0.02, 0.98, 0.98, 0.22)) return null;
  /* The K, held in the middle so the ring can turn round it. */
  const stem = inStroke(x, y, 0.385, 0.320, 0.385, 0.680, 0.050);
  const upperArm = inStroke(x, y, 0.412, 0.515, 0.618, 0.320, 0.048);
  const lowerArm = inStroke(x, y, 0.412, 0.515, 0.628, 0.680, 0.048);
  /* The ring: most of the way round, open where the head is. */
  const ring = inArc(x, y, RING, 0.034, 0.10, ENDS_AT);
  const head = inTriangle(x, y, HEAD.tipX, HEAD.tipY, HEAD.leftX, HEAD.leftY,
    HEAD.rightX, HEAD.rightY);
  return (stem || upperArm || lowerArm || ring || head) ? PAPER : INK;
}

function crc32(bytes) {
  let c = ~0;
  for (const byte of bytes) {
    c ^= byte;
    for (let bit = 0; bit < 8; bit += 1) c = (c >>> 1) ^ (0xEDB88320 & -(c & 1));
  }
  return ~c >>> 0;
}

function chunk(name, body) {
  const head = Buffer.alloc(8);
  head.writeUInt32BE(body.length, 0);
  head.write(name, 4, 'ascii');
  const end = Buffer.alloc(4);
  end.writeUInt32BE(crc32(Buffer.concat([Buffer.from(name, 'ascii'), body])), 0);
  return Buffer.concat([head, body, end]);
}

/** One icon, at this many pixels a side, as PNG bytes with transparency. */
function anIcon(side) {
  const rows = [];
  for (let y = 0; y < side; y += 1) {
    /* Nought at the start of every row: PNG's "this row is stored plainly". */
    const row = [0];
    for (let x = 0; x < side; x += 1) {
      let red = 0;
      let green = 0;
      let blue = 0;
      let covered = 0;
      for (let dy = 0; dy < SAMPLES; dy += 1) {
        for (let dx = 0; dx < SAMPLES; dx += 1) {
          const at = colourAt(
            (x + (dx + 0.5) / SAMPLES) / side,
            (y + (dy + 0.5) / SAMPLES) / side,
          );
          if (!at) continue;
          red += at[0];
          green += at[1];
          blue += at[2];
          covered += 1;
        }
      }
      if (!covered) {
        row.push(0, 0, 0, 0);
      } else {
        row.push(Math.round(red / covered), Math.round(green / covered), Math.round(blue / covered),
          Math.round((covered / (SAMPLES * SAMPLES)) * 255));
      }
    }
    rows.push(Buffer.from(row));
  }
  const head = Buffer.alloc(13);
  head.writeUInt32BE(side, 0);
  head.writeUInt32BE(side, 4);
  head[8] = 8;
  /* Six: red, green, blue and how solid each pixel is. */
  head[9] = 6;
  return Buffer.concat([
    Buffer.from([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A]),
    chunk('IHDR', head),
    chunk('IDAT', deflateSync(Buffer.concat(rows), { level: 9 })),
    chunk('IEND', Buffer.alloc(0)),
  ]);
}

for (const side of SIZES) {
  const where = new URL(`../extension/icon${side}.png`, import.meta.url);
  writeFileSync(where, anIcon(side));
  console.log(`extension/icon${side}.png written`);
}
