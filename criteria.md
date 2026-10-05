# Acceptance criteria — FitFindr

Five criteria that say what "working" means for this agent, written in unit 3
**before** any results existed.

An acceptance criterion names a target: a number, a count, a rate, or something
a person could plainly observe. *"The agent handles errors"* is an opinion.
*"When search returns nothing, the agent stops before calling the second tool,
in 5 of 5 tries"* is a criterion.

Under each one, write a sentence or two on **why that target** and not a
stricter one. A reason that says something about your tools, your loop, or the
data earns credit; *"80% seemed reasonable"* does not.

> Missing your own targets next unit costs you nothing. Setting a target so
> easy you can't miss it does.

**Two are written for you. You write three.**

---

## 1. A matching query completes all three tools

Given a query that matches at least one listing, the agent completes all three
tool calls and returns a fit card — in at least 4 of 5 tries.

**Why this target:** 4 and not 5, because this path makes two model calls per
run on a free tier capped at 15 requests a minute, and `generate.py` gives up
after 5 retries. A run that exhausts its retries during a busy eval doesn't
return a fit card, even though nothing in my code is wrong. The search can
also fail, because it's a plain keyword match. A query phrased with words that
don't appear in a listing's title, tags or description ("tshirt" is
handled, "top with a print on it" isn't) finds nothing, even if a human
would call the listing a match. I'd rather the target allow for one of those
than claim the model and my keyword list are perfect.

---

## 2. An impossible query stops before the second tool

Given a query that matches no listings, the agent stops before calling
`suggest_outfit` and returns a message naming what to change — 5 of 5 tries.

**Why this target:** 5 of 5, because nothing on this path is random.
`search_listings` makes no model call. It's a filter and a keyword count over
a fixed file, so the same query returns `[]` every time, and the branch in
`agent.py::run_agent` is a plain `if not results`. The error message is built
by my code from the parsed filters, not by the model, so "names what to change"
can't vary either. If this misses even once, it's a bug, not bad luck.

---

## 3. The item search found is the item every later tool received

On a query that matches, `session["selected_item"]["id"]` equals
`session["search_results"][0]["id"]`, and the `item_id` recorded in
`session["tool_calls"]` for both the `suggest_outfit` call and the
`create_fit_card` call is that same id. That has to hold in 5 of 5 runs of
`vintage graphic tee under $30`.

**Why this target:** 5 of 5, because handing one dict along is deterministic
code. There's no model in between that could pick a different item. The risk
I'm guarding against is a state bug that *looks* like a tool problem: the
loop reading a stale variable, re-running the search, or passing
`search_results` where it should pass `selected_item`. Any of those would still
produce a plausible outfit and a plausible caption, so the only way to see
it is to compare ids. That's why `run_agent` records the id of the item it
actually passed into each tool, rather than me trusting that it did.

---

## 4. The fit card is a postable caption that gets the facts right

For 5 runs of `vintage graphic tee under $30`, the fit card in
`session["fit_card"]`:

- is 2 to 4 sentences, counting a sentence as text ending in `.`, `!` or `?`,
  with hashtags and emoji not counted on their own;
- contains the selected item's price as `$` plus the number (`$18` or
  `$18.00`), matching `session["selected_item"]["price"]`;
- names `session["selected_item"]["platform"]` (case-insensitive).

All three have to hold in at least 4 of 5 runs.

**Why this target:** These three are what would make me not post a caption. A
wrong price is worse than no caption, and one that's eight sentences long isn't
a caption. The wording is meant to change from run to run (temperature 0.9),
so I'm not checking the words, only facts I can count. I set it at 4 of 5 and
not 5, because the price and platform only appear because my prompt asks for
them, and at 0.9 the model sometimes ignores a formatting instruction or adds
an extra sentence. A cap of 4 sentences is tight enough that I expect one run
to go over occasionally.

---

## 5. Search respects the price ceiling and the size the user asked for

For each of these 5 queries, **every** listing in `session["search_results"]`
(not just the first) has `price` ≤ the stated ceiling and passes the size
rule written in the README's Tool Inventory:

1. `vintage graphic tee under $30`
2. `denim jacket under $50`
3. `platform sneakers size 8`
4. `90s track jacket in size M`
5. `oversized flannel size L under $25`

A query that returns no listings counts as a fail, because an empty list
passes any filter without checking anything.

Target: 5 of 5 queries.

**Why this target:** This checks two of my own pieces at once: the regex that
pulls `max_price` and `size` out of the query, and the filter in
`search_listings`. Both are deterministic, so 5 of 5. The sizes in this data
are where it's easy to be wrong without noticing. `"l" in "xl"` and
`"8" in "us 8.5"` are both True, so a lazy filter would show size 8.5 shoes
to someone who asked for 8, or an XL flannel to someone who asked for L. The
results would still look like reasonable search results, which is exactly why
I check every listing and not just the top one.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     UNIT 4 — read this before you change anything above.

     If a criterion turns out to be BROKEN rather than merely unmet, you can
     revise it, and that earns credit. But never delete or edit the original
     line. Add the revision underneath it, like this:

         ## 4. Something about the fit card

         The fit card is different every time.

         **Why this target:** ...

         > **Revised in unit 4:** For 5 different items, the 5 fit cards share
         > no opening sentence.
         >
         > **Why revised:** "different" wasn't checkable — two cards that
         > differed by one word still counted. The new version is something I
         > can actually score.

     That's a revision because the criterion couldn't be MEASURED.

     Lowering a target because you missed it is not a revision, and it costs
     you the point:

         ✗ "I said the empty search stops it 5 of 5 times, but I got 3 of 5,
            so 3 of 5 is more realistic."

     A number you missed stays where it is, gets diagnosed, and gets a fix
     attempted. That's where the points are.
     ───────────────────────────────────────────────────────────────────────── -->
