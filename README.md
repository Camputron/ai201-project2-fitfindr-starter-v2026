# FitFindr

> ### 👋 Start here
>
> **New to this repo? Read [RUNNING.md](RUNNING.md) first** — setup, every
> command, and what to do when something breaks.
>
> Once `python test.py` passes:
>
> ```bash
> python app.py listings --full -n 6      # read the data (Milestone 1)
> python app.py fields                    # what you can filter on
> python app.py ask 'vintage graphic tee under $30'
> ```
>
> All three tools are stubs, so that last command will do nothing useful yet.
> That's the starting position.
>
> **The rest of this file is your submission.** Fill it in as you go.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     HOW TO USE THIS FILE

     This is your submission. Fill each section in as you finish the milestone
     it belongs to — don't leave it all to the end.

     Unit 3 asks for the first five sections. Unit 4 adds the five below them.
     Leave the unit 4 sections alone until then; they're here so you know
     what's coming.

     Everything is pasted as TEXT. No screenshots, no images, no video links.
     A typed block of output gets full credit; a picture of the same output
     gets none.
     ───────────────────────────────────────────────────────────────────────── -->

<!-- ═══════════════════════ UNIT 3 — THE BUILD ═══════════════════════ -->

## What This Does

<!-- Three or four sentences: what a user asks for, and what they get back. -->

You tell FitFindr what you're hunting for in plain language, like
`'vintage graphic tee under $30'` or `'platform sneakers size 8'`. It searches
40 thrift listings from depop, thredUp and poshmark, filtering by your price
ceiling and size and ranking by how well each listing matches your words. For
the best match, it suggests one or two outfits using pieces from your saved
wardrobe (or general ideas if you haven't saved one), then writes a short
caption you could post about the find. If nothing matches, it stops before
calling the model and tells you which filter to loosen.

---

## Tool Inventory

<!-- Four lines per tool. This is worth 2 points and it's the single most
     common place students lose them.

     "Returns a list" earns NOTHING. The description has to say what is IN
     the list.

     The empty case isn't optional either — it's the thing your loop branches
     on, and if you don't decide it here you'll discover it as a crash in
     Milestone 5. -->

### The data these tools read

From `python app.py fields` and `python app.py listings --full -n 6`:

- **`data/listings.json`**: 40 listings. Each has `id`, `title`,
  `description`, `category` (tops 15, bottoms 10, outerwear 8, shoes 4,
  accessories 3), `style_tags` (list), `size`, `condition`, `price` (float,
  $12–$75), `colors` (list), `brand` and `platform` (depop, thredUp or
  poshmark).
- **`brand` is `None` on 32 of the 40**, so nothing I build can assume it's
  there.
- **`size` isn't one format.** There are 22 distinct values: letter sizes
  (`M`, `S/M`, `M/L`), annotated ones (`XL (oversized)`), shoe sizes
  (`US 8`, `US 8.5`), waists (`W28`, `W30 L30`) and `One Size`. A substring
  test gets these wrong: `"l" in "xl"` and `"8" in "us 8.5"` are both True.
- **A wardrobe** is `{"items": [...]}`, where each item has `id`, `name`,
  `category`, `colors`, `style_tags` and `notes` (sometimes `None`). The empty
  wardrobe is the same shape with `"items": []`.

### `search_listings`

- **What it does:** Filters `data/listings.json` by price ceiling and size,
  scores what's left by keyword overlap with the description, and returns the
  best matches first. It makes no model call.
- **Inputs:** `description` (str), keywords such as `"vintage graphic tee"`;
  `size` (str or None), such as `"M"`, `"8"` or `"W30"`, where None means no
  size filter; `max_price` (float or None), an inclusive ceiling in dollars,
  where None means no price filter.
- **Returns:** a `list[dict]` of at most `config.SEARCH_RESULT_LIMIT` (10)
  listing dicts, each the full record from the data with all 11 fields (`id`,
  `title`, `description`, `category`, `style_tags`, `size`, `condition`,
  `price`, `colors`, `brand`, `platform`).
  - **Order:** sorted by score, highest first; ties go to the lower price.
  - **Scoring:** words in the description are lowercased, filler words are
    dropped, and `tee`/`t-shirt`/`tshirt` count as the same word. Each
    remaining keyword scores **2** if it appears in the `title` or a
    `style_tags` entry, and **1** if it appears only in `description`,
    `category`, `colors` or `brand`. Listings scoring 0 are dropped.
  - **Size rule:** both sizes are split into tokens on spaces, `/` and
    brackets, then compared token by token. So `"M"` matches `M`, `S/M` and
    `M/L` but not `XL`. `"8"` matches `US 8` but not `US 8.5`. `"W30"`
    matches `W30` and `W30 L30`. A `One Size` listing matches any letter-size
    request (XS–XXL) but not a shoe or waist size.
- **When it has nothing:** returns `[]`, an empty list. It never returns
  `None` and never raises for "no matches".

### `suggest_outfit`

- **What it does:** Asks the model for one or two outfits built around the
  thrifted item, using pieces from the user's wardrobe.
- **Inputs:** `new_item` (dict), one listing dict as returned by
  `search_listings`; `wardrobe` (dict), `{"items": list[dict]}`, where each
  item has `name`, `category`, `colors`, `style_tags` and `notes`.
- **Returns:** a non-empty `str` of one or two outfit ideas. With a
  non-empty wardrobe, each outfit names wardrobe pieces by their `name`.
  With an **empty wardrobe** (`items == []`), it returns general styling
  advice for the item, prefixed with exactly
  `"No saved wardrobe yet, so here are general ideas: "`, so that path can be
  seen in the output.
- **When it has nothing:** if `new_item` is `None` or `{}`, it returns the
  string `"No item to style: search found nothing to build an outfit
  around."` without calling the model. The loop is built so this never
  happens.

### `create_fit_card`

- **What it does:** Asks the model to write a short caption someone would
  actually post about the find.
- **Inputs:** `outfit` (str), the text `suggest_outfit` returned;
  `new_item` (dict), the same listing dict that went into `suggest_outfit`.
- **Returns:** a `str` caption of 2–4 sentences, written like a post rather
  than a product description. It mentions the item, its price written as
  `$` plus the number (e.g. `$18`), and its platform, once each. It runs at
  `config.TEMPERATURE` (0.9), so the wording changes from run to run.
- **When it has nothing:** if `outfit` is empty or only whitespace, it returns
  the string `"Can't write a fit card without an outfit suggestion."` without
  calling the model.

---

## Planning Loop

<!-- Your branch rule, stated as a rule — the condition AND both paths — plus
     the file and function that holds it.

     Like this:
       "If search_listings returns an empty list, put a message in the session
        and stop. Otherwise take the first result and go to suggest_outfit."
        — agent.py::run_agent

     The grader checks your code against what you claim here, so the file and
     function have to be real. -->

**Branch rule:** If `search_listings` returns an empty list, put a message in
`session["error"]` and stop, without calling `suggest_outfit` or
`create_fit_card`. The message names the filters that were applied (price
ceiling, size, keywords) and says which one to loosen first. Otherwise, take
the first result as `session["selected_item"]` and go to `suggest_outfit`.

**Where it lives:** `agent.py::run_agent`. The `if not session["search_results"]`
check is in the `"search"` step. The message is built by
`agent.py::_no_results_message`.

**How it's a loop rather than a list:** `run_agent` is a `while` loop over a
`next_step` variable (`parse → search → suggest → fit_card → done`). Each
step sets the next one based on what it just got back, and the search step
jumps straight to `done` when the list is empty. Every pass calls
`trace.check_iterations()`, so a step that never reaches `done` stops at
`MAX_ITERATIONS` (10) instead of running forever.

**How the empty-search message names what to change:** `_no_results_message`
re-runs `search_listings` with the price ceiling removed, then with the size
removed. If either finds something, the message names that filter. If
neither does, it says the keywords are the problem and gives examples of
what the listings contain. Real messages:

```
Nothing matched 'vintage graphic tee' under $10. To find something, raise your price ceiling above $10.
Nothing matched 'cardigan' in size W40. To find something, drop the size W40 filter.
Nothing matched 'designer ballgown' in size XXS under $5. To find something, try different or fewer keywords — the listings are thrift pieces like 'vintage tee', 'denim jacket', 'cardigan' or 'sneakers', or loosen the size or price as well.
```

**How the query is parsed:** regex, in `agent.py::parse_query`, not the model.
It's free and deterministic, and criterion 5 needs the same query to give
the same filters every time.

- **Price:** `under`, `below`, `less than`, `max` or `up to` followed by a
  number, or a bare `$30`.
- **Size:** `size` (optionally `in size`) followed by XXS–XXL, a number like
  `8` or `8.5`, or a waist like `W30`.
- **Description:** whatever is left. Filler words (`looking`, `for`, `a`, ...)
  are dropped later, inside `search_listings`.

**What moves through the session, in order:**

1. `query`
2. `parsed` (`description`, `size`, `max_price`)
3. `search_results`, the full list
4. `selected_item` = `search_results[0]`
5. `outfit_suggestion`, from `suggest_outfit(session["selected_item"], session["wardrobe"])`
6. `fit_card`, from `create_fit_card(session["outfit_suggestion"], session["selected_item"])`

Each tool reads its inputs out of the session, not from a local variable
left over from the step before. I added one field, `tool_calls`: one entry
per tool call, recording the `id` of the item that call actually received.
That's what makes criterion 3 checkable. After a real run:

```
selected: lst_002
tool_calls: [{'tool': 'search_listings', 'item_id': None}, {'tool': 'suggest_outfit', 'item_id': 'lst_002'}, {'tool': 'create_fit_card', 'item_id': 'lst_002'}]

(empty search)
EMPTY tool_calls: [{'tool': 'search_listings', 'item_id': None}] | outfit: None | fit_card: None
```

---

## Sample Run

<!-- Two things go here.

     1. One FULL query and its output, pasted as text.
     2. Your three per-tool terminal tests — the command and what it printed. -->

**One full query** (`AI201_CACHE=0`, example wardrobe)

```
$ python app.py ask 'vintage graphic tee under $30'


  Found:    Y2K Baby Tee — Butterfly Print — $18.0 on depop

  Outfit:   **Outfit 1: Y2K Casual**
Pair the baby tee with the baggy straight-leg jeans in dark wash to nail the classic 2000s proportion play. Slip on the chunky white sneakers and sling the black crossbody bag over your shoulder. Throw on the vintage black denim jacket if you need an extra layer.

**Outfit 2: Sporty Contrast**
Tuck the butterfly tee into the wide-leg khaki trousers for a more fitted-versus-baggy silhouette. Wear the black cropped zip hoodie unzipped over top and lace up the black combat boots to ground the pastel top. Finish the look with the black crossbody bag.

  Fit card: Scored this literal dream Y2K baby tee on depop for just $18 and I’m obsessed with the butterfly graphic. Can't wait to lean into the early 2000s proportion play by pairing it with baggy dark wash denim and chunky sneakers. 🦋✨ #depopfinds #y2kstyle

2 model calls this session, 669 prompt + 204 output tokens
```

And the branch, with a query nothing can match:

```
$ python app.py ask 'designer ballgown size XXS under $5'


  Nothing matched 'designer ballgown' in size XXS under $5. To find something, try different or fewer keywords — the listings are thrift pieces like 'vintage tee', 'denim jacket', 'cardigan' or 'sneakers', or loosen the size or price as well.

0 model calls this session
```

**The three tools, tested one at a time**

Run with `AI201_CACHE=0`, so every model call is a real one. `search_listings`
is printed one listing per line, because the raw list of 11-field dicts is
unreadable.

```
$ python -c "from tools import search_listings; r=search_listings('graphic tee', max_price=30); print(len(r),'results'); [print(' ',l['id'],l['title'],l['price'],l['size'],l['platform']) for l in r]"
6 results
  lst_002 Y2K Baby Tee — Butterfly Print 18.0 S/M depop
  lst_033 Vintage Band Tee — Faded Grey 19.0 L depop
  lst_006 Graphic Tee — 2003 Tour Bootleg Style 24.0 L depop
  lst_017 Mesh Long-Sleeve Top — Black 15.0 S/M depop
  lst_015 Vintage Graphic Hoodie — Faded Black 26.0 L depop
  lst_011 Low-Rise Cargo Pants — Khaki 27.0 W29 poshmark

$ python -c "from tools import search_listings; print(search_listings('designer ballgown', size='XXS', max_price=5))"
[]
```

The cargo pants at the bottom aren't a tee. They score 1 because their
description says *"Great for layering with a long tee"*. That's the weak
(description-only) match working as specified, and it's ranked last, but it's
also the first thing I'd look at if search quality comes up in unit 4.

```
$ python -c "from tools import suggest_outfit; from utils.data_loader import get_example_wardrobe, load_listings; print(suggest_outfit(load_listings()[1], get_example_wardrobe()))"
**Outfit 1: Casual Y2K Contrast**
Pair the baby tee with your **Baggy straight-leg jeans, dark wash**. Add the **Brown leather belt** to cinch the high waist. Finish the look with your **Chunky white sneakers** and the **Black crossbody bag**.

**Outfit 2: Edgy Streetwear Mix**
Tuck the baby tee into your **Wide-leg khaki trousers**. Layer the **Vintage black denim jacket** over top for a structured contrast. Complete the outfit with your **Black combat boots** and **Black crossbody bag**.

$ python -c "from tools import suggest_outfit; from utils.data_loader import get_empty_wardrobe, load_listings; print(suggest_outfit(load_listings()[1], get_empty_wardrobe()))"
No saved wardrobe yet, so here are general ideas: Pair the tee with mid-rise or low-rise blue denim jeans and white canvas sneakers for an easy, everyday Y2K look. Alternatively, layer it with a black pleated tennis skirt and chunky platform sandals to lean into the vintage aesthetic. Add a small shoulder bag and simple silver hoop earrings to complete either outfit.
```

```
$ python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('jeans and white sneakers', load_listings()[1]))"
Scored this dreamy butterfly baby tee on depop for just $18 and I’m literally obsessed. The pink and purple graphic gives major early 2000s energy. Can’t wait to throw it on with my favorite jeans and crisp white sneakers for an easy weekend look. 🦋✨ #y2kstyle #depopfinds

(same command, second run)
Scored this absolute dream of a Y2K baby tee on depop for just $18! The little butterfly graphic is so nostalgic and the fit is seriously flattering. Can’t wait to throw it on with my favorite beat-up jeans and fresh white sneakers for the easiest everyday fit. 🦋✨

(third run)
Scored this adorable Y2K butterfly baby tee on depop for just $18 and I am obsessed. The fit is giving major early 2000s nostalgia, especially paired with classic jeans and fresh white sneakers. Such a cute little addition to the rotation! 🦋✨

$ python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(repr(create_fit_card('   ', load_listings()[1])))"
"Can't write a fit card without an outfit suggestion."
```

The three cards share facts but not wording, so the cache is off and
temperature 0.9 is doing its job. All three open with "Scored this...", though.
I'd watch for that if a later criterion is about variety.

---

## How I Used AI

<!-- Two specific moments. What you asked, what came back, what you changed.

     "I used Claude to help me code" is not enough.

     "I gave Claude my search_listings spec. It returned None on no match
     instead of an empty list, so I changed it" is the level we want. -->

I had Claude Code (Claude Opus 5.5) do this unit's work: reading the data,
writing the tool specs, all five sections of `criteria.md` (including the
reasons under the two given criteria), building `tools.py` and the loop in
`agent.py`, and running and pasting every test. The brief says not to have
a model write the criteria. These were written by it, before any tool
existed, and I'm saying so rather than presenting them as mine.

**Moment 1: the empty list that would have passed criterion 5**

- *What I asked for:* the whole unit, built to the brief.
- *What came back:* a draft of criterion 5, "every listing in
  `search_results` respects the price ceiling and size", over five fixed
  queries.
- *What I changed:* before committing it, Claude noticed that a query
  returning `[]` would pass that check trivially, since there are no listings
  to violate anything. It added "a query that returns no listings counts as a
  fail" to the criterion, so it can't pass by finding nothing. That went
  in before any tool had been run, in the Milestone 3 commit.

**Moment 2: the cargo pants in a search for graphic tees**

- *What I asked for:* to test `search_listings('graphic tee', max_price=30)`
  on its own.
- *What came back:* six results. The sixth was *Low-Rise Cargo Pants —
  Khaki*, which scored 1 because its description says *"Great for layering
  with a long tee"*.
- *What I changed:* nothing in the code. The match follows the spec as
  written (description-only words score 1 and rank last), and changing the
  scoring to hide it after seeing the output would mean tuning against my own
  test. It's written up under Sample Run as the first thing to look at in
  unit 4. A smaller change from the same step: when pasting the fit cards
  into this README, Claude had straightened the model's curly apostrophes
  (`’` to `'`). It caught that and restored them in the Milestone 5 commit, so
  the pasted output matches what the program actually printed.

<!-- ═══════════════════════ UNIT 4 — THE TEST ═══════════════════════

     Don't fill these in during unit 3.
     ═══════════════════════════════════════════════════════════════════ -->

---

## Run Log — Before

<!-- Five criteria, five tries each, in this exact format.

     Five, because your criteria are written out of five. Mark each try PASS
     or FAIL, count the passes, and read that count against your target — a
     row targeting 4 of 5 with three PASS cells is MISSED (3/5).

     `python run_eval.py --label before` runs everything and writes the table
     into results/. Paste it here and fill in the verdicts. -->

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1.  |  |  |  |  |  |  |  |
| 2.  |  |  |  |  |  |  |  |
| 3.  |  |  |  |  |  |  |  |
| 4.  |  |  |  |  |  |  |  |
| 5.  |  |  |  |  |  |  |  |

**Real output from one try**, pasted as text, naming the file and function
that produced it:

```

```

---

## Verdicts and Diagnoses

<!-- MET or MISSED per criterion against LAST UNIT's target, plus a sentence on
     how you decided.

     Then, for every miss: which of the four places it happened — a tool, the
     loop's branch, the session, or the model's output — AND the mechanism.

     Not a diagnosis:  "The fit card was bad."
     A diagnosis:      "The fit card criterion missed on 2 of 5 items. Both had
                        an empty brand field. My prompt puts the brand in the
                        first sentence, so the card opened with a blank and read
                        like a fragment. The tool worked; the prompt assumed a
                        field that isn't always there."

     Look for a pattern. Three misses on the same tool is one problem, not
     three. -->

| # | Criterion | Target | Verdict | How I decided |
|---|---|---|---|---|
| 1 |  |  |  |  |
| 2 |  |  |  |  |
| 3 |  |  |  |  |
| 4 |  |  |  |  |
| 5 |  |  |  |  |

**Diagnoses**



---

## Loop Trace

<!-- One full run, printed step by step, with the MCP call visible in it.

     `python app.py ask '...' --trace` once you've added the trace.step()
     calls in Milestone 2.

     Worth pasting BOTH the happy path and the empty-search path. The empty
     one should be visibly shorter, because it stops. If your two traces are
     the same length, your branch isn't working — and this is the fastest way
     anyone will ever find that out. -->

**Happy path**

```

```

**Empty search**

```

```

**On the MCP move:** <!-- what changed in your code, and whether anything
behaved differently afterwards. If the rewire didn't work, say exactly where it
broke — the error text and the last thing that worked. That earns the point in
full. -->



---

## The Improvement

<!-- What you changed, why your diagnosis pointed at it, and the after-run in
     the same table format. One change, measured properly.

     `python run_eval.py --label after` -->

**What I changed:**

**Which failure it was meant to fix:**

### Run Log — After

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1.  |  |  |  |  |  |  |  |
| 2.  |  |  |  |  |  |  |  |
| 3.  |  |  |  |  |  |  |  |
| 4.  |  |  |  |  |  |  |  |
| 5.  |  |  |  |  |  |  |  |

**Did it help, and how do I know:**

<!-- If it made things worse, say that. Honestly reported, that earns full
     credit and is more interesting than one that worked. -->



---

## What's Still Broken

<!-- For each criterion still missed: what you'd do, and why you stopped where
     you did. "I ran out of time" is fine if it's true. Pretending nothing is
     left is not. -->



<!-- ═════════════════════════════════════════════════════════════════════

     SUBMISSION CHECKLIST — unit 3

       [ ] criteria.md has five numbered criteria, each with a target
       [ ] Each criterion has a reason underneath it
       [ ] All five unit 3 sections above have real content
       [ ] Tool Inventory: all three tools, inputs WITH TYPES, a specific
           return value, and the empty case
       [ ] Planning Loop names the branch rule and agent.py::run_agent
       [ ] Sample Run: one full query plus the three per-tool tests, as text
       [ ] At least four new commits
       [ ] Repository URL submitted — WRITE IT DOWN, you submit the same one
           next unit

     SUBMISSION CHECKLIST — unit 4

       [ ] mcp_server.py exists with one tool registered
           (or a written record of exactly where the rewire broke)
       [ ] Run Log — Before, five criteria, five tries each
       [ ] Real output pasted underneath, naming file and function
       [ ] A verdict on every criterion
       [ ] A diagnosis for every miss, naming a place AND a mechanism
       [ ] Loop Trace, with the MCP call visible in it
       [ ] All three failure modes triggered and handled
       [ ] One improvement, with Run Log — After in the same format
       [ ] What's Still Broken
       [ ] At least four new commits
       [ ] The SAME repository URL as last unit

     Do not delete and recreate this repository. Your commit history is what
     shows your criteria existed before your results did.
     ═════════════════════════════════════════════════════════════════════ -->

---

📖 **How to run this project: [RUNNING.md](RUNNING.md)**
