"""
The FitFindr planning loop.

This is the file that makes FitFindr an agent rather than a script. It decides
which tool to run next based on what the last one returned.

If your loop calls all three tools no matter what comes back, you have a list
of function calls. A loop looks at the last result before it picks the next
step. **That branch is the graded part of this unit.**

Build and test your three tools in `tools.py` first. Then come here.

    python agent.py          runs both example paths below
"""

import re

import config
import trace
from tools import search_listings, suggest_outfit, create_fit_card
from generate import ModelUnavailable


# ── session state ─────────────────────────────────────────────────────────────

def new_session(query: str, wardrobe: dict) -> dict:
    """
    A fresh session for one user interaction.

    The session is the single source of truth for a run. Every tool result goes
    in here, and the next tool reads it back out.

    You could pass values straight from one call to the next. It would work,
    and you would not be able to test it — you can't print a variable you have
    already overwritten. Going through the session is what makes the state
    visible, and unit 4 has you write a criterion about exactly that.

    Add fields if you need them.
    """
    return {
        "query": query,              # what the user typed
        "parsed": {},                # description / size / max_price you pulled out of it
        "search_results": [],        # everything search_listings returned
        "selected_item": None,       # the one you chose — goes into suggest_outfit
        "wardrobe": wardrobe,        # the user's wardrobe
        "outfit_suggestion": None,   # what suggest_outfit returned
        "fit_card": None,            # what create_fit_card returned
        "error": None,               # set when the run ended early
        "tool_calls": [],            # one entry per tool call: name + the item id it received
    }


# ── query parsing ─────────────────────────────────────────────────────────────

# "under $30", "below 30", "less than $30.50", "max $30", or a bare "$30".
_PRICE = re.compile(
    r"(?:\b(?:under|below|less than|max|up to)\s*\$?\s*|\$)(\d+(?:\.\d+)?)",
    re.IGNORECASE,
)
# "size M", "in size 8", "size W30", "size 8.5".
_SIZE = re.compile(
    r"\b(?:in\s+)?size\s+(xxs|xs|s|m|l|xl|xxl|w?\d+(?:\.\d+)?)\b",
    re.IGNORECASE,
)


def parse_query(query: str) -> dict:
    """
    Pull a description, a size and a max_price out of plain language. Regex,
    not the model: it's free, it's the same every time, and criterion 5 needs
    the same query to produce the same filters.

    Whatever isn't a price or a size phrase is the description.
    """
    price_match = _PRICE.search(query)
    size_match = _SIZE.search(query)

    description = query
    for match in (price_match, size_match):
        if match:
            description = description.replace(match.group(0), " ")
    description = re.sub(r"[,\s]+", " ", description).strip(" ,")

    return {
        "description": description,
        "size": size_match.group(1).upper() if size_match else None,
        "max_price": float(price_match.group(1)) if price_match else None,
    }


def _no_results_message(parsed: dict) -> str:
    """
    Say what was searched and what to change. "No results" leaves the user
    guessing; this names each filter and, by re-running the search without
    it, which one is actually in the way.
    """
    desc, size, price = parsed["description"], parsed["size"], parsed["max_price"]

    searched = f"'{desc}'"
    if size:
        searched += f" in size {size}"
    if price is not None:
        searched += f" under ${price:g}"

    tips = []
    if price is not None and search_listings(desc, size, None):
        tips.append(f"raise your price ceiling above ${price:g}")
    if size and search_listings(desc, None, price):
        tips.append(f"drop the size {size} filter")
    if not tips:
        tips.append(
            "try different or fewer keywords — the listings are thrift pieces "
            "like 'vintage tee', 'denim jacket', 'cardigan' or 'sneakers'"
        )
        if price is not None or size:
            tips.append("loosen the size or price as well")

    return f"Nothing matched {searched}. To find something, " + ", or ".join(tips) + "."


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Run the loop once and return the finished session.

    Args:
        query:    what the user asked for, in plain language
                  (e.g. "vintage graphic tee under $30, size M").
        wardrobe: a wardrobe dict — get_example_wardrobe() or
                  get_empty_wardrobe() from utils/data_loader.py.

    Returns:
        The session dict. **Check session["error"] first** — if it isn't None,
        the run ended early and the later fields will still be None.

    ─────────────────────────────────────────────────────────────────────────
    TODO — build this, following the branch rule you wrote in Milestone 2.

      1. Start a session with new_session().

      2. Count the times round the loop, and call trace.check_iterations(count)
         on each one before you go again. It raises when the count passes
         MAX_ITERATIONS in config.py — see trace.py.

      3. Parse the query into a description, a size, and a max_price. Regex,
         string splitting, or asking the model are all fine — say which you
         chose in your README. Put the result in session["parsed"].

      4. Call search_listings() with what you parsed.
         Put the results in session["search_results"].

         ⚠️ THIS IS THE BRANCH. If nothing came back:
              - put a message in session["error"] saying what the user could
                change — "No results" is not that message
              - return the session
              - do NOT call suggest_outfit with nothing

      5. Choose an item — the first result is fine. Put it in
         session["selected_item"].

      6. Call suggest_outfit() with the selected item and the wardrobe.
         Put the result in session["outfit_suggestion"].

      7. Call create_fit_card() with the outfit and the item.
         Put the result in session["fit_card"].

      8. Return the session.

    ─────────────────────────────────────────────────────────────────────────
    IN UNIT 4 you come back and add two things:

      • Trace calls. One per step. `trace.step("search_listings", inputs=...,
        returned=...)` — see trace.py. Your README needs the output.

      • A handler for ModelUnavailable, so a bad key produces a message rather
        than a stack trace. The import is already at the top of this file.
    """
    session = new_session(query, wardrobe)

    # Each step names the next one, based on what the last one returned. The
    # loop runs until a step says "done" — the empty-search branch says it
    # early.
    next_step = "parse"
    iterations = 0

    while next_step != "done":
        iterations += 1
        trace.check_iterations(iterations)

        if next_step == "parse":
            session["parsed"] = parse_query(query)
            next_step = "search"

        elif next_step == "search":
            parsed = session["parsed"]
            session["search_results"] = search_listings(
                parsed["description"], parsed["size"], parsed["max_price"]
            )
            session["tool_calls"].append({"tool": "search_listings", "item_id": None})

            # THE BRANCH. Nothing found → explain and stop. Never call
            # suggest_outfit with nothing.
            if not session["search_results"]:
                session["error"] = _no_results_message(parsed)
                next_step = "done"
            else:
                session["selected_item"] = session["search_results"][0]
                next_step = "suggest"

        elif next_step == "suggest":
            item = session["selected_item"]
            session["outfit_suggestion"] = suggest_outfit(item, session["wardrobe"])
            session["tool_calls"].append({"tool": "suggest_outfit", "item_id": item["id"]})
            next_step = "fit_card"

        elif next_step == "fit_card":
            item = session["selected_item"]
            session["fit_card"] = create_fit_card(session["outfit_suggestion"], item)
            session["tool_calls"].append({"tool": "create_fit_card", "item_id": item["id"]})
            next_step = "done"

    return session


# ── running it directly ───────────────────────────────────────────────────────

def _show(session: dict) -> None:
    if session["error"]:
        print(f"  stopped: {session['error']}")
        print(f"  fit_card is {session['fit_card']!r} — it should still be None here")
        return

    item = session["selected_item"] or {}
    print(f"  found:    {item.get('title')} — ${item.get('price')} on {item.get('platform')}")
    print(f"  outfit:   {session['outfit_suggestion']}")
    print(f"  fit card: {session['fit_card']}")


if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe

    print("=== A query the data can match ===")
    _show(run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    ))

    print("\n=== A query it can't ===")
    _show(run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    ))

    print(
        "\nThe second one should stop before the fit card. If both paths look "
        "the same,\nthe branch isn't doing anything yet."
    )
