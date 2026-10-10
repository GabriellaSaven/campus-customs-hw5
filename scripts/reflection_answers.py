"""Gabriella's reflection questions and answers for Problem 10, exactly as written
(question wording, paragraph breaks and text unchanged)."""

REFLECTION = [
    (
        "How would I evaluate the performance of the agents on each ticket and why?",
        [
            "Overall, I think the agents performed quite well, but some tickets worked more smoothly than others.",
            "For Ticket 101, the team reached the right result. Inventory correctly found that there were no size S Bulldog tees in stock and that the shop was short by one. It also identified Bulldog Print Co as the relevant vendor and found that the vendor was blocked by the overdue $840 invoice. Accounting then created a payment request rather than trying to pay the invoice itself, and Customer Service drafted a message to Tauhid explaining that the size was unavailable without promising a restock date.",
            "The Boss also correctly left the ticket as awaiting approval because a human still needed to approve the payment. I think this ticket showed that the team could work across stock, supplier, accounting and customer service issues.",
            "For Ticket 102, I think the agents performed very well because the task was simpler. Facilities confirmed that the monthly rent was $2,400, due on September 2, and therefore urgent but not overdue. Accounting then checked the available cash and filed a payment request for human approval.   The Boss left the ticket awaiting approval, and after I approved the payment, the ticket was resolved.",
            "For Ticket 103, the team did a good job of combining several different issues. Inventory found that only 8 of the 20 medium hoodies were available, so 12 more would be needed. Accounting calculated the margins at different discount levels and found that the extra 12 hoodies would cost $264 to restock. However, only $160 would remain after the earlier payment requests, so the shop could not afford the restock. The agents therefore correctly avoided creating an unaffordable payment request.",
            "The main weakness on Ticket 103 was the Customer Service draft. The first version mentioned the outstanding vendor invoice and funding, which are internal business details that should not have been included in a customer-facing message. I later changed the Customer Service rules and added a guardrail so that wording like this would be rejected. The revised test did not leak those details.",
        ],
    ),
    (
        "For each ticket, how did actual compare to the expected plan I wrote earlier?",
        [
            "Ticket 101 was fairly close to my expected plan. I expected the Boss to start with Inventory, which is what happened. I then expected Inventory to hand the problem to Accounting, but in the actual run the Boss contacted Accounting directly. The Boss also contacted Accounting twice, once to confirm the invoice situation and once to create the payment request",
            "The overall result was still what I expected. Inventory found the stock problem, Accounting dealt with the overdue invoice, Customer Service drafted the reply, Facilities was not involved, and the Boss left the ticket awaiting approval. The main difference was therefore in how the agents communicated, rather than in the final decision.",
            "Ticket 102 also mostly matched my expected plan. I expected Facilities to check the lease and Accounting to handle the financial side. Both of those things happened. However, I expected Facilities to pass the task directly to Accounting. In the actual run, the Boss separately contacted Facilities and Accounting, and Accounting also went back to Facilities to confirm the lease details.",
            "This was slightly more back-and-forth than I expected, but the agents still reached the correct outcome. No unnecessary Inventory or Customer Service agent was involved.",
            "Ticket 103 was also broadly similar to my expected plan. The Boss contacted Inventory first to understand the stock position and Accounting to work out the margins, restock cost and available cash. Accounting also asked Inventory for stock and vendor information. The Boss then asked Customer Service to draft the response.",
            "The biggest difference was the final decision. I had expected the Boss to decide on a reasonable discount once Accounting had worked out the margins. In the actual full run, the Boss chose not to offer a discount or promise the order because the shop only had $160 available after the earlier payment requests, while the restock would cost $264. I think this was a sensible change from my plan because the agents took the wider cash situation across the three tickets into account.",
        ],
    ),
    (
        "What would have been simpler as one agent with tools and why?",
        [
            "Ticket 102 would probably have been simpler with one agent that had the right tools.",
            "The task was quite straightforward. The agent needed to check the rent amount, confirm the due date, look at the available cash and prepare a payment request. Instead, the task moved between the Boss, Facilities and Accounting, and Accounting even asked Facilities to confirm information that had already been checked.",
            "One agent with access to the lease, cash and payment-request tools could probably have handled this safely and with fewer model calls.",
            "I do not think the same is as true for Ticket 103. That ticket involved inventory, suppliers, pricing, cash and customer communication. In that case, having different specialist agents was more useful because each agent had a clear area of responsibility.",
        ],
    ),
    (
        "Describe three new problems Campus Customs might face that this agent team could solve with the tools I built?",
        [
            "One possible problem is a student group asking for a large order of T-shirts in several sizes. Inventory could check each size, identify shortages and find the right supplier. Accounting could check the cost and cash position, and Customer Service could draft the response.",
            "A second problem is having several bills due at the same time when there is not enough cash to pay all of them. Accounting could check each invoice and the available cash, while the Boss could decide which payments should be prioritised. The current system already showed that it can deal with this kind of problem because the invoice and rent together left only $160 in checking.",
            "A third problem is another student organisation asking for a bulk discount on a different product. Inventory could check whether enough stock exists, Accounting could calculate the margin at different discount levels, the Boss could make the final decision, and Customer Service could draft the response.",
        ],
    ),
    (
        "Describe three new problems Campus Customs might face that this agent team could not solve with the tools I build and explain the tools and agents I would need to solve them:",
        [
            "One problem would be a maintenance issue, such as a pipe bursting or the heating breaking in the shop. The Facilities agent exists, but the current database only contains lease information. It does not contain contractors, repair history, costs or emergency contacts. To solve this, I would add tools for finding approved contractors, recording maintenance problems and requesting repair work. Facilities could continue to handle the problem.",
            "A second problem would be a customer asking for a refund or return. The current Customer Service agent can draft messages, but the team does not have tools for checking return eligibility, processing refunds or updating an order after a return. I would add tools for order history, return policies and refund requests. Customer Service and Accounting could work together, with a human still approving the actual refund.",
            "A third problem would be deciding what merchandise Campus Customs should order for the next semester based on past sales. The current tools show stock levels and prices, but there is no historical sales data or forecasting tool. I would add a sales-history database and tools for looking at past demand, seasonal patterns and best-selling products. I might also create a new Merchandising or Planning agent whose job is to use this information to recommend what the shop should order.",
        ],
    ),
]
