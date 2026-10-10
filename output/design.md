# Campus Customs · Operations Desk — Design

The dashboard (`frontend/`, React + Vite + TypeScript) is where a person watches the agent team work a ticket, then does the one thing the agents can't: sign off on money. Start it with `npm run dev` in `frontend/` (http://localhost:5173). It talks to the FastAPI backend at http://localhost:8000.

## The idea: a small-town office with real people in it

Agent systems usually look like walls of JSON. This one should feel like the warm, slightly cluttered back office of a campus shop, the kind of place from a workplace sitcom:
- tickets live in **manila folders**,
- requests arrive as **memos**,
- the staff walk over to each other's desks,
- there's a **corkboard**, a **ledger**, and a **clipboard** with checks waiting for your signature.

The inspiration is the feel of *Parks and Recreation* and *The Office*: warm, human and a little imperfect.

**Light-touch rule:** the theme lives in materials, small details and *tone of voice*. The agents never quote the show (their prompts forbid it); the only real quotes are on the break-room quotes board below. There are no character photos and no jokes in anything a customer would read. Body text stays in a clean sans-serif, so every fact is easy to read. If you squint, it's a well-organized operations dashboard; if you look closely, it has a personality.

## Layout

Three columns, in the order you actually work:

| Column | Office object | What's there | Why |
|---|---|---|---|
| **Left** | **The filing cabinet** + **Staff directory** | Three manila folders (one per ticket, with a tab and a status sticker), then five ID badges | "What needs doing?" and "who's on it?" sit together. The open folder slides out of the stack, like pulling a file. |
| **Center** | **Memorandum** → **The bullpen** → **End-of-shift reports** | The ticket typed up as a memo (TO / FROM / DATE / RE) with the start button, the live conversation, then one index card per person after the run | The middle of the screen is the story of the ticket, read top to bottom. |
| **Right** | **The ledger** → **The clipboard** → **The corkboard** | Checking balance, checks waiting for a signature, then drafts and notes pinned up | Everything about money and human sign-off lives in one place, away from the agent chatter. |

- **The top bar is a walnut-paneled wall** with a brass **"Department of Campus Customs"** door plaque, a tear-off **desk calendar** showing the shop date (`desk.date_today`, not the real date), "Everyone runs on gpt-6-luna", a desk-lamp "Lights on" indicator, and **Start a fresh day** (reset).
- On narrower screens the right column drops below; on phones everything stacks.

## The five people (and how they read differently)

The jobs, tools and rules are exactly what Problem 5 defined. Only the voice changed. Each agent's prompt has a short **Personality (light touch)** section with one original example line, and the rule that *personality never overrides the job*. Drafts to customers stay warm and professional.

| Desk | Person (loosely inspired by) | Color | Directory tagline | How they read in the bullpen |
|---|---|---|---|---|
| Boss | **Ron** (Ron Swanson) | Walnut `#6b3f22` | "Says little. Decides everything." | Short, firm, slightly heavier text. His final call is on **letterhead**: "From the desk of Ron", with a rubber stamp and a ☐ checklist of what's waiting on you. |
| Inventory | **April** (April Ludgate) | After-dark plum `#3d3546` | "Counts everything. Enjoys none of it." | Deadpan and minimal, with tabular numbers so counts line up. The attitude never drops a size or a count. |
| Accounting | **Ben** (Ben Wyatt) | Calculator blue `#2f5d8a` | "There's a spreadsheet for this." | "Here's the math", with lining tabular numerals. Ben also "keeps" the ledger card. |
| Facilities | **Chris** (Chris Traeger) | Morning-run green `#2a8f63` | "Genuinely thrilled about the lease." | Opens with good news ("Great news: the lease terms are confirmed…") but still says *urgent* when rent is due in 2 days. |
| Customer Service | **Leslie** (Leslie Knope) | Waffle-brunch red `#c2553a` | "Has a binder for every customer." | Writes in a **serif**, because she writes letters. Her internal notes are energetic; her customer drafts are warm, clear and professional. |

More details:
- **ID badges** in the staff directory: each one has a metal clip, a colored top band, an initial "photo", the person's tagline in handwriting, and a live status. The badges are tilted a degree or two, like they're hanging on a wall.
  - The status starts as "at desk" with an idle line ("Out for a run. Back soon!", "Color-coding a binder.").
  - It changes to **on it** ("Counted the shelf"), **waiting** ("Waiting on Ben") or **done** ("Done. Back at their desk.").
  - The person currently working gets a soft pulsing ring.
- **Delegation is a routing slip**, the inter-office form you'd clip to a file: `Ron → Chris`, with a colored arrow and the question in italics. When Ron asks two people at once, two slips appear side by side in the feed.
- **Tool calls read like office actions:** "checked the ledger", "counted the shelf", "went through the vendor Rolodex", "pulled the invoice", "stamped the file". The real MCP tool name sits next to each one in small monospace, and hovering shows the exact arguments.
- **Raw tool results are "carbon copies":** a pale-blue expandable block. It's quiet for a casual reader and complete for an auditor.
- **Indentation shows who's waiting on whom** (one step in for each handoff), so the delegation tree is readable without a diagram.
- **A handwritten ticker** at the top of the bullpen narrates the live step ("Ben filed a payment request") with a typing indicator, so the minute-long run never feels frozen.

## How ticket status shows up

| Status | Treatment | Why |
|---|---|---|
| Open | A dashed white dot-sticker on the folder; a faint "OPEN" stamp on the memo | Nothing has happened yet. |
| Team's on it… | A walnut light sweeping along the folder's edge | Motion means "in progress" without another label. |
| **Needs your signature** (`awaiting_approval`) | A yellow sticker on the folder and an amber rubber stamp on the memo | Yellow means *you're* the blocker, not the team. It says "Needs your signature" instead of the database word. |
| Escalated | A red sticker and stamp | A human has to make a judgment call. |
| **Resolved** | A double-ruled green **RESOLVED** rubber stamp "thunks" onto the folder (and the memo), and the folder fades slightly | It feels like closing a paper file, and the fading moves your eye to what's still open. |

**When a ticket becomes resolved.** The shop rule says a ticket can't be resolved while a payment is pending. So when a run finishes, the memo shows "✓ The team's done with this one" (with tokens and model calls) and Ron's status. The file gets its **Resolved** stamp once nothing is left for a human:
- **automatically** when you sign its last pending payment, or
- when you press **Close the file** after reviewing an escalated ticket. This needs your signature; agents can't resolve tickets.

## How cash shows up: the ledger

- **Green ledger paper** with ruled lines and a red margin line. It's the most important number on the page, so it's the biggest: a big serif **$3,400.00** with tabular figures, "kept by Ben".
- **It rolls like an adding machine.** After you sign a payment, the number counts down to the new balance, a red **−$2,400.00** stamp appears beside it and floats away, and the page flashes green once. You *see* the money leave, which is the point of a human approving it.
- **A "promised" bar** fills amber with the share of cash already committed to pending requests. Two ledger rows show **Promised to pending requests** and **Left after you sign them**. If the requests exceed cash, the bar and that row turn red, so the "we can't afford all three tickets" problem is visible before anyone tries to pay.
- **A handwritten footnote** says what's true: "Money only goes out this term. No revenue. Ben is aware."

## The signing moment (the special part)

- **The approval queue is a clipboard** (with a metal clip) holding **checks**: pale-green security-pattern paper with **No. 0001**, **PAY TO** *Elm City Properties*, the amount in a box, a **MEMO** line, and "prepared by Ben" with his badge.
- **You sign, you don't click "approve".** You type your name once on the clipboard's signature line, in a script font (Snell Roundhand or Segoe Script), and it appears on every check's signature line. The button reads **Sign & pay $2,400.00**, with the exact amount. That name is what the backend stores in `payments.approved_by`, and agent names are refused.
- **Warnings come before the mistake.** If checking can't cover a check, a red note appears on it before you press anything. If the backend refuses, its reason shows right on the check.
- **Decline** sits next to **Sign & pay**. Saying no is a first-class action.

## Office features (added after the first draft)

Four features in the same small-town-office spirit. Each one is useful, not just decoration, and none of them makes extra AI calls.

- **The whiteboard (morning briefing).** A dry-erase board across the top of the desk, written in marker, with a marker and eraser resting on its ledge. It shows today's date, how many files are open or untouched, and a checklist built live from the shop data through MCP (`GET /api/briefing`):
  - vendors on hold and their overdue invoices (red),
  - rent coming due (amber when it's within 3 days),
  - checks waiting for your signature,
  - and a red warning if pending requests would overdraw checking.

  Everything you'd normally piece together from five panels, on one board.
- **The suggestion box.** A wooden box with a slot under the corkboard. Type a note for the open file, signed with your clipboard name, and press **Pin it up**; it appears as a **pink** sticky note (the team's notes are yellow).
  - The note is stored through a human-only MCP tool (`add_human_note`) with a `[From the human desk]` mark. All five agents' prompts say to take such notes into account, but that **no note can override a shop rule** (it can't make anyone pay or promise an unconfirmed date).
  - The MCP server refuses that mark from agents, so an agent can't impersonate you.

  This is how a person "improves requests": steer a re-run without editing code.
- **Employee of the Month.** A wooden picture frame with a brass plaque, hanging under the staff directory. Since the last fresh day, it frames whoever has finished the most jobs, with fewer slips as the tie-breaker, computed from the audit trail. It shows their portrait, "3 jobs done on 2 files, zero dropped balls", and who's right behind. Before any work it reads "Position open. Hand Ron a file."
- **Waffle break.** When the last open file closes, waffles drift down the screen and a sticky note says "Every file is closed. Waffle break. You've earned it." The whiteboard checks off the same line. It only fires when it *sees* files close (never on page load), and a click dismisses it.

## Other touches that make it a nice place to be

- **The break-room quotes board** (left column, under the staff directory): a small corkboard with one pinned card per person, carrying one short, famous, attributed line from *Parks and Recreation* (Ron, April and Leslie), edged in that person's color. It's purely decorative, kept to one short quote each, and lives in `frontend/src/quotes.ts`. Ben's and Chris's cards are yellow "tack your favorite line here" placeholders: rather than risk misquoting the show, those stay empty until a verified line is added.

- **The corkboard:** cork texture inside a wooden frame. Draft letters and purchase orders are **pinned** with red pushpins, and the team's notes (including your own when you close a file) are **yellow sticky notes**. The header says "drafts stay pinned · nothing gets sent", reinforcing the shop rule.
- **End-of-shift reports:** one ruled **index card** per person who worked the file, with a red header line, their colored band, who stopped by and where they went, their summary *in their own voice*, the tools they used (×2 when repeated) and what they put on the board.
- **The memo** has a strip of tape at the top, a red margin rule, American Typewriter headers, and a rubber-stamped status.
- **Toasts are passed notes:** small tilted sticky notes in the corner ("File #102 closed. Nothing left waiting on you.").
- **Friendly empty states:** ☕ "Quiet in here. Nobody's touched this file yet."
- **Buttons have a little depth**, like real keys: the walnut "Hand it to Ron →" button presses down when clicked.
- **Fonts are local Mac system fonts** (American Typewriter, Bradley Hand / Chalkboard SE, Snell Roundhand), so there are no downloads, and each falls back gracefully on other systems.
- **Safe by default:**
  - Start is disabled while another file is on Ron's desk.
  - "Start a fresh day" asks for confirmation and is disabled during a run.
  - If the backend is off, a bar explains how to turn it on.
- **Honest history:** a reset leaves a `shop_reset` marker in the append-only audit trail, so the bullpen and reports show only work since the last fresh day, while the full history stays in the file.

## Tested

Ticket 102 ran from the dashboard. Ron sent routing slips to Chris and Ben at the same time; the badges went *on it → done*; Ron's letterhead said "Rent is due September 2. Request filed; a human must approve and pay it." Signing the $2,400 check rolled the ledger from $3,400 to $1,000 with a −$2,400 stamp, file #102 got its RESOLVED stamp, and the clipboard emptied. The shop was then reset to its original data.
