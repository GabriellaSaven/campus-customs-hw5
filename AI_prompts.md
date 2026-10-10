# AI Prompt Log — Homework 5 (Campus Customs Multi-Agent Operations)

A running log of the prompts I used to vibe-code this project. One section per
problem, kept updated as we go.

## Scenario setup

### Initial prompt

We are now doing homework 5. The scenario is as follows: Campus Customs Multi-Agent
Operations is an agentic team that runs the shop. Open tickets land on a board,
including customer orders, rent, unpaid bills, discount requests, whatever the shop
has to handle. We're going to build three pieces that talk to each other. 1), an MCP
server. 2) a fast API backend with a multi-agent team. And 3), a React dashboard so a
human can watch the agents at work and improve requests. The agent team has full
connectivity such that any agent may delegate tasks to another agent for help. We'll
build these agents. 1) the boss, which reads tickets, decides who should work on it
and makes final calls. 2) inventory, which checks stock by SKU and size. Spots
shortfalls and figures out which vendor can restock. 3) accounting, which watches cash
and invoices, checks margins and prepares payments or purchase orders for human
approval. 4) facilities, which handles the shop's space side, including rent, leases,
etc. 5) customer service, which drafts messages for customers. We have the following
rules for the shop. The field desk.date_today is "today" for the shop and the date is
used to determine what it overdue. Vendor lead times come from the vendor's table. A
vendor will not ship new product while they are still have an open unpaid invoice.
Human approval is required for any payments and points will be deducted if this is
not done. If the payment is made, make sure to update the relevant table. If there
isn't enough cash, the pay tool must refuse. There cannot be any negative balances.
Cash only goes out on this homework. We do not model revenue, so no money comes in.
Before full run to resolve the tickets, make sure to reset the database to the
original values. Do not email customers or call real vendors. Drafts should stay on
the board. I need to use my PORTKEY_API_KEY for AI calls and only use GPT-6 Luna
through port key for every agent. Multi-agent chats burn tokens fast and points will
be deducted if any other model shows up in my code or runs. We're going to work one
problem at a time as we always do and I'll teach, type each problem into the chat.

### Follow-up prompt

it is gpt-6-luna

**What was lacking after the initial prompt:** The scenario said "GPT-6 Luna" while
the course `AGENTS.md` and earlier homework code named an older Luna model, so the exact
model string was ambiguous. Because any other model costs points, it had to be
confirmed as `gpt-6-luna` before any code was written.

## Problem 1: Vibe coder prompts

### Initial prompt

Problem 1: vibe coder prompts. Create AI_prompts.md and keep it updated as we always
do. This should include a section for each problem with the problem number and title,
at least one prompt that I typed in my own words, and one follow up prompt if I needed
it.

### Follow-up prompt

No follow-up prompt was used.

**What was lacking after the initial prompt:** Nothing major. The prompt didn't say
where to put the file or how to format it, so I matched the Homework 4 log: the file
sits in the `Homework 5` root, each problem gets its own section, and each section
says what was missing after the first prompt.

## Problem 2: Study the Campus Customs database

### Initial prompt

Problem 2: study the campus customs database. Open data/campus_customs.db and look
through every table and its fields. Copy the priginal file to data/campus_customs.db
as later problems will update this working copy. Study the three open tickets. So you
see how they link to the other tables. Start outputs/harness.md so you see how they
link to the other tables. Start outputs-harness.md. For each table, list the fields
and one short line on why that table is important for the agents. In later problems,
we'll keep growing this harness file.

### Follow-up prompt

sorry I meant that you need to start data/campus_custims_new.db so update that please

**What was lacking after the initial prompt:** The copy step named the same path as
the source (`data/campus_customs.db`), so it didn't say which file was the working
copy. On the first pass I treated `campus_customs.db` as the working copy and saved a
backup as `campus_customs_original.db`. The follow-up fixed this:
`data/campus_customs.db` stays the untouched original and `data/campus_customs_new.db`
is the working copy. The prompt also gave the harness path
two ways (`outputs/harness.md` and `outputs-harness.md`); I first used
`outputs/harness.md`, and in Problem 3 it was corrected to `output/harness.md`. Finally, it didn't ask for the cross-ticket math, but that math
shows the shop can't afford all three spends, which the agents need to know.

## Problem 3: Build the MCP server

### Initial prompt

Problem 3: build the MCP server. Write an MCP server in mcp_server/ using FastMCP.
This should talk to data/campus_customs_new.db. We don't need to connect or run it
now. We'll do this later. Every agent in the homework uses the tools in the MCP server
that we just created, and we'll add more tools to it later. But for now, write three
tools that I know I'll need for the tickets in the database. Keep the names clear,
don't invent any data, and only use information in the database. In output/harness.md
list each of these three MCP tools and for every tool include: the table that it
reads, the ticket it helps unlock (1021, 102 or 103) and a sentence on why that tool
was right for that ticket. Add a short mcp_server/README.md file to explain the
purpose of the MCP server and which database it uses and the three tools it has.

### Follow-up prompt

Is everything working perfectly so far? Do you have any questions or concerns?

Make sure you're always using GPT-6 Luna. If you haven't been, then go back and
update things. It should be output, not outputs.

**What was lacking after the initial prompt:** The prompt didn't say which three
tools to build or whether they could write to the database. I chose one read-only
tool per ticket: `check_stock` → 101, `get_lease_rent_status` → 102 and
`check_discount_margin` → 103. Two small slips: "1021" meant ticket 101, and the
harness folder was `outputs/` in Problem 2 but `output/` here. The follow-up settled
it as `output/`, so the folder was renamed. The review also found that the tools never
closed their database connections, which was fixed. The follow-up confirmed the model
is GPT-6 Luna: no AI calls had been made yet, and the course `AGENTS.md` was updated
from the older Luna model to `gpt-6-luna`. The prompt also didn't
mention that the project needed a virtual environment with FastMCP installed, so I
created `Homework 5/.venv` per the course rules.

## Problem 4: Add the MCP server to the vibe coder and test each tool

### Initial prompt

Problem 4: add the mcp server to the vibe coder and test each tool. Add my MCP server
to this project that you can call the tools. Save the connection JSON text in .mcp.json
at the project root. Or wherever else you save local MCP server lists. Now test each of
my three MCP tools. Save the evidence in output/mcp_smoke.json. or wherever else you
save local MCP server lists. Now test each of my three MCP tools. Save the evidence in
for every tool, include the prompt that I asked for, the tool name, and the tool
output. which must match the values in data/campus_customs_new.db.

### Follow-up prompt

have you done everything correctly so far?

make sure the json file is switched so that it can run on another computer. approve
the MCP server in claude code.

(Then, while approving it: "What's going on?", "how about now?", "and now?", "done".)

**What was lacking after the initial prompt:** Part of the prompt was repeated, and it
didn't give the test questions, so I wrote one question per tool using that ticket's
own data. It also didn't say how to prove the outputs "match" the database, so the
test re-reads each value with plain SQL and records a per-field match. Ticket 103
names no discount %, so 10% was used as a labeled test value. Finally, Claude Code
only loads a project `.mcp.json` server after the user approves it, so the test talks
to the server over the same stdio connection that `.mcp.json` defines. The follow-up asked for an audit:
all files, references and model strings checked out, and both databases were still
identical to the original.
The second follow-up fixed `.mcp.json`, which used full paths from one Mac. It now
uses `${CLAUDE_PROJECT_DIR:-.}` and was tested in a fresh copy of the project with a
new virtual environment. Approval was added in `.claude/settings.local.json`, but
Claude Code still requires a one-time interactive trust or approval prompt for a new
folder. Approving it took several rounds: the
first prompt was answered "Continue without using this MCP server" (which rejected it),
and a later attempt failed because `claude` wasn't on the shell PATH. The approval is
now saved in `.claude/settings.local.json`, but `claude mcp get` still reports
"Pending approval", which matches a known Claude Code issue with approvals saved there.

## Problem 5: Build the agent team and grow the MCP tools

### Initial prompt

Problem 5: build the agent team and grow the mcp tools. Build the agentic team for
campus customs using PydanticAI: boss, inventory, accounting, facilities and customer
service. Include the prompts, models and agent loops so that they delegate work to one
another with full connectivity. In backend/prompts/ put the agent prompts and make sure
it is one file per agent. Put data types in backend/models.py and the agent files under
backend/ (the layout doesnt matter as long as the roles for all five are clear). Make
sure to use my PORTKEY_API_KEY and ONLY use gpt-6-luna for each and every agent.

I want to focus specifically on writing the five agent prompt files well, because the
assignment says that more detailed prompts that cover the full scope of each agent's
work score higher than short generic prompts. Please write one detailed system prompt
for each of these five Campus Customs agents: Boss, Inventory, Accounting, Facilities,
Customer Service. Put them in separate files under `backend/prompts/`. I want each
prompt to sound clear and practical, like instructions you would give a real employee.
Do not make them overly technical or full of generic AI language. For each agent,
explain: (1) what their role is and what kinds of problems they are responsible for,
(2) what information they should check before acting, (3) what shop rules apply
specifically to them, (4) what they are allowed to do, (5) what they are not allowed to
do, (6) when they should delegate to another agent, (7) when they should escalate to
the Boss or a human, (8) how they should behave if information is missing or unclear.

Make sure the following shop rules are included where relevant: use the shop's
`desk.date_today` tool when deciding whether something is overdue, do not assume the
real-world date; never ship an order if there is an unpaid invoice; any actual payment
or movement of money must be handled by a human — an agent can identify what needs to
be paid or prepare information, but it cannot complete the payment itself; all facts
about the shop must come from the MCP tools — do not invent order status, stock levels,
invoice information, customer information, facilities information, or any other
business facts; if an agent does not have enough information to make a safe decision,
it should ask for more information, delegate, or escalate rather than guessing.

Please make each role distinct. I do not want five prompts that say basically the same
thing. [Then a focus list for each agent: Boss — understand the ticket, pick the
specialist, coordinate, check rules, resolve conflicts, escalate, don't do specialist
work. Inventory — stock levels, low/missing stock, enough to fulfil, hand invoices to
Accounting and customer comms to Customer Service, never claim stock without MCP data.
Accounting — invoices, amounts due, overdue via desk.date_today, invoice paid before
shipping, flag unpaid/overdue, never pay, escalate payments to a human. Facilities —
physical shop, equipment, maintenance, utilities, repairs; check existing info; urgent
vs. normal; escalate safety/major damage/approval; don't invent repair costs or
contractor details. Customer Service — questions, order updates, complaints; answer
only from shop data; check with Inventory and Accounting; never say an order can ship
with an unpaid invoice; polite, no unconfirmed promises; escalate sensitive issues.]

Also include a short shared rule in all five prompts that agents should keep their work
focused and avoid unnecessary back-and-forth or repeated tool calls. Before saving the
prompts, show me the five drafts in plain English so I can review whether they sound
sensible and sufficiently different from one another.

All tools that the agents need should be added to the MCP server so that they can work
on all the open tickets. Shop facts come from MCP server over data/campus_customs_new.db
and remember not to invent a second shop-tools later that bypasses MCP. Wire our agents
to append to output/audit_trail.json as they run: for each loop step, record enough so
that we can later audit them. Make sure to append to this file and don't wipe it each
run. In output/harness.md, list each agent and each MCP tool (including the ones in this
problem) with which table the tool uses. Add a short safety section please including the
guardrails that a real-world business would want if agents touch real custimers and real
money, plus any limits that keep the token use in check because i don't want this to be
expensive. Update mcp_server/README.md so that the tool list matches what we now have.
Does this make sense? Do you have questions?

### Follow-up prompt

(Answers to my three clarifying questions: shipping rule = "Vendor rule only";
payments = "Request, then human pays"; audit file = "JSON array".)

These drafts look good and are distinct enough. Please save them as the five separate
agent prompt files. Before doing so, verify that every tool named in the prompts
actually exists in the MCP server. If a required tool does not exist, add it through the
MCP server rather than bypassing MCP. Do not remove the detailed role boundaries, shop
rules, handoff rules, escalation rules, or shared efficiency footer. Keep the wording
simple and practical.

**What was lacking after the initial prompt:** Three decisions were open. (1) "Never ship
an order if there is an unpaid invoice" conflicted with the scenario's rule that a
*vendor* won't ship us stock while it has an open invoice; I chose the vendor rule only.
(2) "A human must pay" had to fit with the scenario's pay tool that refuses when cash is
short; agents now file requests, and a human-only MCP tool pays. (3) "Append to a JSON
file" could mean a JSON array or JSON Lines; I chose a JSON array. The prompt also didn't
say where drafts and payment requests live, so three board tables were added to the
working copy. It didn't say how to reset either, so a human-only `reset_shop_database`
MCP tool was added to keep everything going through MCP. During the build, gpt-6-luna
refused tool calls with reasoning on the Chat Completions endpoint, so the team uses
OpenAI's Responses API instead (same model, low reasoning effort).

## Problem 6: Plan the three tickets

### Initial prompt

Problem 6: Plan the three tickets. Before we write the backend, help me write what we
would expect the agent team to do on each of the three open tickets. Build
output/desk_tickets.html a page that I can double-click and open in my browser. It
should have one tab for each ticket: 101, 102, and 103. Also add separate Cash and
Reflection tabs for later problems; for now these can be blank or say "Coming later."
For each ticket tab, create two clearly labelled sections: Expected and Actual. For now,
fill only the Expected section and leave the Actual section empty for later.

[Then my expectations per ticket. 101: Boss calls Inventory first because there are 0
size S tees, so it's a restocking issue; delegations Boss→Inventory, Inventory→
Accounting, Accounting→Boss, Boss→Customer Service; no Facilities; tools get_ticket,
get_today, check_stock, list_inventory, list_vendors, check_vendor_status, get_invoice,
get_cash_position, request_payment, draft_purchase_order, draft_customer_message,
add_board_note, set_ticket_status. 102: Boss calls Facilities first to confirm rent
amount and due date before any payment; Boss→Facilities, Facilities→Accounting,
Accounting→Boss; no Inventory or Customer Service; tools get_ticket, get_today,
get_lease_rent_status, get_cash_position, request_payment, add_board_note,
set_ticket_status. 103: Boss calls Inventory first "because before deciding what
discount to offer"; Boss→Inventory, Inventory→Accounting, Boss→Accounting,
Accounting→Boss, Boss→Customer Service; no Facilities; tools as 101 plus
check_discount_margin, with request_payment if the unpaid supplier invoice needs to be
dealt with and draft_purchase_order if more hoodies need to be ordered.]

I want the Expected section to show the likely workflow in order, so that later I can
compare it directly with what the agents actually did. Please keep the plans realistic
and efficient. The Boss should only delegate when another agent has information or
authority that is actually needed. Avoid unnecessary back-and-forth. Use the agent
roles, shop rules, MCP tools, and open-ticket data already in my project. Do not invent
shop facts. If the ticket or available tools do not support a particular step, point
that out rather than assuming. Before building the HTML, show me your proposed plan for
Tickets 101, 102, and 103 in plain English so I can check whether I agree with the
expected workflow. Once I approve it, create `output/desk_tickets.html`.

### Follow-up prompt

what do you think?

go

**What was lacking after the initial prompt:** The ticket 103 reason was cut off mid-
sentence, and a stray repeated tool line followed it. "Accounting → Boss" was listed as
a delegation, but in our code it's a reply that flows back up the chain (asking back up
the chain is blocked to prevent loops). The plan also didn't account for run order: the
cash picture for 103 depends on 101 and 102 running first ($160 left after both pending
requests, so the $264 hoodie restock is $104 short). Nor did it account for two data
gaps: no discount policy, and invoice 501 being for a "Rush reprint CC-TEE-WHITE S",
which may already cover ticket 101's tee. After "what do you think?", we agreed to keep
Inventory → Accounting on 101, drop it on 103, make the 101 purchase order optional, and
treat repeated routine lookups as expected.

## Problem 7: Backend routes

### Initial prompt

Problem 7: backend routes. My react frontend dashboard which we will do in the next
question needs a backend that it can call. So in backend/main.py use FastAPI and add
routes that are able to 1) return three tickets and whether each is open or resolved,
2) take ticket id and run agent team on the ticket, 3) return recent agent events (what
the agents said and which tools they used) so that the board can refresh, 4) approve a
payment or purchase after a human approves because agents only prepare the pay; this
route is what actually changes cash), 5) return the current checking balance from
cash_accounts and 6) reset the database to the original values when i want to try a
fresh run. From the backend/ folder, start the server with: uvicorn main:app --reload
--port 8000 and in output/harness.md, list each route in one line (ie what url was used
and what it does).

### Follow-up prompt

(The first attempt was cut off after "So in backend"; I re-pasted the full prompt.)

**What was lacking after the initial prompt:** The first send was cut off, so the full
prompt had to be pasted again. The prompt also didn't say how the dashboard learns which
payment to approve (it needs request ids), so an approval-queue route and a
`list_payment_requests` MCP tool were added. Listing all tickets including resolved ones
needed a new `list_tickets` tool, because `list_open_tickets` hides resolved tickets.
Agent runs take a minute or more, so the run route returns a `run_id` right away
(`?wait=true` blocks) and only one run is allowed at a time. Running `uvicorn main:app`
from inside `backend/` needed a path fix so `backend.*` imports work.

## Problem 8: Agent dashboard

### Initial prompt

Problem 8: agent dashboard. Build the front end now in frontend/ with Reach + Vite +
Typescript. I want the page to call the routes that we built together in problem 7 and
at least: list all three tickets, et me pick one ticket and start the team on it, show
each agent and what theyre saying/doing while the ticket runs, mark a ticket as resolved
when the run finishes, show a shorty summary of what each agent did on the ticket, let a
human approcve a pay or purchase when asked, show the checking balance which should
frop after an approved pay.

When you have created a draft we will make sure that it looks good.

Make sure that the front end talks to the backend at http://localhost:8000. On the
backend, allow the vite page origin (which is apparently usually http://localhost5173)
so that the browser can call those routes. Start the board with: npm run dev. Write
output.design.md with al the things i choose for the dashboard look including layout,
how agents read differently, how resolved tickets and cash show up and why, including
the creative choices that make it feel special and something that humans would actually
enjoy using.

Have a quotes board with famous quotes from each of them from the show

can you add a few more cool features that are in line with the parks and recreation vibe?

### Follow-up prompt

Build the dashboard with a warm sitcom-office vibe, inspired by the feel of Parks and
Recreation and The Office. I want it to feel like a real operations desk run by people
with distinct personalities, not a generic boring dashboard. Use a warm, human, slightly
imperfect office aesthetic with file-folder ticket tabs, memo-style content sections,
subtle paper or corkboard energy, and character-inspired agent identities. The five
agents should each have a distinct personality based loosely on these characters: Ron
Swanson as Boss, Ben Wyatt as Accounting, Leslie Knope as Customer Service, April Ludgate
as Inventory, and Chris Traeger as Facilities. They should all be able to do their jobs
and tools and tasks perfectly, but have the personalities of the characters. Do this
with a light touch so it feels clever and well-designed rather than gimmicky. Keep the
interface readable and functional, but make it feel like a place someone would actually
enjoy using.

**What was lacking after the initial prompt:** "Mark a ticket as resolved when the run
finishes" conflicts with the shop rule that a ticket can't be resolved while a payment
is pending, so the dashboard shows "Team finished" right away and stamps the ticket
Resolved once nothing is left for a human (auto on its final approval, or a human "Mark
resolved"). That needed a human-only `resolve_ticket` MCP tool and route. The prompt
didn't say how to build the per-agent summary, so a summary route builds it from the
audit trail. The Vite origin was written as "localhost5173" (it's
`http://localhost:5173`), and "output.design.md" was taken to mean `output/design.md`.
Testing also showed that, after a reset, the append-only audit trail made old runs look
current, so resets now leave a `shop_reset` marker and the dashboard only shows runs
after it.

**What was lacking after the first draft:** The first dashboard was clean but generic,
and the agents had no personality. After the follow-up, the UI became an office
(manila folders, memo, bullpen, ID badges, ledger, a clipboard of checks, corkboard),
and each prompt got a "Personality (light touch)" section with an original example line,
the rule that personality never overrides the job, and "no TV quotes". A first test run
showed the voices were *too* faint (Chris read like a spreadsheet), so each prompt got a
"How you sound" example and the output fields ask for the agent's own voice. A second
run showed clear voices with every fact still exact. Testing also exposed a reset race
(a poll could hit the database between the copy and the board-table rebuild), fixed by
building the fresh copy on the side and swapping it in atomically. The quotes-board follow-up added a
break-room corkboard with one short, attributed quote each for Ron, April and Leslie.
Ben's and Chris's cards were left as placeholders in `frontend/src/quotes.ts`, because
their exact famous lines couldn't be quoted word for word with confidence, and
misattributed quotes would be worse than none. The "more features" follow-up didn't
say which features, so I chose four that are useful as well as fun and make no extra AI
calls: a whiteboard briefing (new `/api/briefing` route), a suggestion box for human notes
the agents read on re-runs (new human-only `add_human_note` MCP tool, protected so agents
can't fake human notes), an Employee of the Month frame computed from the audit trail,
and a waffle-break celebration when every file closes. Testing caught two bugs, both
fixed: the open memo didn't refresh when its status changed elsewhere, and the waffle
break could fire on page reload.

## Problem 9: Resolve the tickets

### Initial prompt

Problem 9: resolve the tickets. Before we test the agents on a full run over the three
tickets, reset the working database data/custom_campus_new.db again so that i have a
clean start. Show me and note the starting checking balance and then run the three
tickets on the board until each is resolved. Then I want you to open
output/desk_tickets from problem 6 and on each ticket tab put the details into the
Actual section from the run ie which agents worked, what they delegated, and which tools
each one of them used. Make sure to keep the expected section so that I can compare
them. On the Cash tab that we created, in output/desk_tickets.html, itemize the money as
follows: starting checking balance (after you do the reset), for each ticket show how
cash changed when the ticket resolved and why (which pay/purchase, and the dollar
amount), the ending checking balance (which must match cash_amounts in the working
database). NOTE: wrong math will lose points even if the board shows every ticket as
resolved. I also want you to save: output/resolved_tickets.json for each ticket
including id, final status, short outcome, what each agent contributed and any human
approvals AND output/resolved_board.html which should be a page that I can double click
with a screenshot of the react board for each of the tickets (101, 102 and 103). Append
real runs to output/audit_trail.json and finish output/harness.md so that it covers the
tables, mcp tools, all the agents, the API routes, the dashboard and the safety rules.

### Follow-up prompt

(Answers to the approval questions: approve both payments, invoice #501 $840 and rent
$2,400; close ticket 103 as held after review; sign as "Gabriella Saven".)

**What was lacking after the initial prompt:** "Run until each is resolved" needed real
human approvals, so the run paused for my decisions on which payments to approve (both)
and how to close 103 (as held). The file names had small slips
(`custom_campus_new.db` → `data/campus_customs_new.db`; `cash_amounts` →
`cash_accounts`). The first full attempt showed the prompts weren't efficient enough:
#103 hit the 40-tool-call guardrail because Customer Service re-asked for facts and the
Boss asked for a letter before deciding. I tightened the Boss and Customer Service
prompts, raised the limits to 40 model calls / 50 tool calls, and redid the whole run
from a fresh reset. Final cash: $3,400.00 − $840.00 − $2,400.00 = $160.00, which matches
`cash_accounts`.

### Follow-up prompt (after the Problem 9 review)

Is everything working perfectly?

Yes do that

**What was lacking:** The health check passed, but the run had a real miss: Leslie's
customer draft leaked internal vendor-debt and funding details. "Yes do that" approved
tightening her prompt and re-running ticket 103. I added explicit privacy rules (with a
before/after example) plus a guardrail in the `draft_customer_message` tool, and re-ran
#103 against a scratch copy so the graded Problem 9 database, audit trail and reports
stayed untouched. The leak is fixed (0 internal terms; the old wording is refused). One
borderline line remains: a hedged earliest-arrival date.

## Problem 10: Reflection

### Initial prompt

Problem 10: reflection. I now need to open output/desk_tickets.html and fill in the
reflections tab. Here are the questions and my answers: [My written answers to five
questions: (1) how I'd evaluate the agents on each ticket and why; (2) how Actual
compared to my Expected plan for each ticket; (3) what would have been simpler as one
agent with tools (ticket 102); (4) three new problems the team could solve with the
current tools (a multi-size T-shirt order, several bills due with too little cash,
another bulk-discount request); (5) three problems it couldn't solve and the tools and
agents I'd add (a maintenance emergency, refunds and returns, merchandise planning from
sales history).]

### Follow-up prompt

I want the answers to be written exactly as I wrote them - do not paraphrase them

**What was lacking after the initial prompt:** The prompt didn't say the answers must be
verbatim, so the first version restructured parts of them: it added rating labels and a
contents bar, rewrote questions 4 and 5 as bold-headed lists and a table, added commas
to two question titles, and dropped the stray word "harness". After the follow-up, the
tab shows only my exact question wording and my paragraphs in my order (kept in
`scripts/reflection_answers.py`). A script check confirms all 5 questions and 22
paragraphs match character for character.
