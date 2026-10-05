"""
The three FitFindr tools.

Each one is a standalone function you can call and test on its own, before any
of them are wired into the loop. Build and test them one at a time — three
untested tools joined by a loop is one problem that looks like six, because you
can't tell which layer is lying to you.

    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)             → str
    create_fit_card(outfit, new_item)              → str

All three are stubs right now. They run and they do nothing — that's the
starting position and it's deliberate.

⚠️ Before you write any of them, fill in the **Tool Inventory** section of your
README (Milestone 2). Four lines per tool: what it does, each input with its
type, exactly what it returns, and what it returns when it has nothing to give.
That last line is what your loop branches on. "Returns a list" earns nothing —
the description has to say what is *in* the list.
"""

import re

import config
from generate import generate
from utils.data_loader import load_listings

# Words that say nothing about the item. Left in, "looking for a tee" would
# score every listing whose description happens to contain "for" or "a".
_FILLER = {
    "a", "an", "the", "and", "or", "for", "with", "in", "on", "of", "to", "my",
    "i", "im", "i'm", "want", "looking", "need", "some", "something", "any",
    "size", "under", "below", "max", "around", "about", "piece", "item",
}

# Same word, different spelling. Kept small on purpose — every entry is a
# guess about how people type, and a long list of guesses hides real misses.
_SYNONYMS = {"t-shirt": "tee", "tshirt": "tee", "tees": "tee", "sneaker": "sneakers",
             "trainers": "sneakers"}

_LETTER_SIZES = {"xxs", "xs", "s", "m", "l", "xl", "xxl"}


def _words(text: str) -> list[str]:
    """Lowercased words, with t-shirt kept whole and synonyms folded together."""
    found = re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)*", text.lower())
    return [_SYNONYMS.get(w, w) for w in found]


def _keywords(description: str) -> list[str]:
    seen: list[str] = []
    for word in _words(description):
        if word not in _FILLER and word not in seen:
            seen.append(word)
    return seen


def _size_tokens(size: str) -> set[str]:
    """'S/M' → {'s', 'm'}; 'US 8.5' → {'us', '8.5'}; 'W30 L30' → {'w30', 'l30'}."""
    return {t for t in re.split(r"[\s/()]+", size.lower()) if t}


def size_matches(wanted: str, listing_size: str) -> bool:
    """
    The size rule from the README's Tool Inventory.

    Token for token, never substring: "l" must not match "xl", and "8" must
    not match "us 8.5". A One Size listing fits any letter-size request but
    not a shoe or waist size.
    """
    want = _size_tokens(wanted) - {"us", "size"}
    have = _size_tokens(listing_size)
    if not want:
        return True
    if want & have:
        return True
    return "one" in have and bool(want & _LETTER_SIZES)


def _score(listing: dict, keywords: list[str]) -> int:
    strong = " ".join([listing["title"], *listing["style_tags"]])
    weak = " ".join([listing["description"], listing["category"],
                     *listing["colors"], listing.get("brand") or ""])
    strong_words, weak_words = set(_words(strong)), set(_words(weak))
    score = 0
    for word in keywords:
        if word in strong_words:
            score += 2
        elif word in weak_words:
            score += 1
    return score


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the listings data for items matching a description, and optionally a
    size and a price ceiling.

    This is the tool that doesn't call the model, which makes it the easiest one
    to test and the one to move onto MCP in unit 4.

    Args:
        description: keywords describing what the user wants
                     (e.g. "vintage graphic tee").
        size:        a size string to filter by, or None to skip size filtering.
                     Match case-insensitively — "M" should match "S/M".

                     ⚠️ Read the sizes in the data before you reach for a plain
                     substring test. `"s" in "us 9"` is True, and so is
                     `"l" in "xl"`. A filter that returns shoes when someone
                     asked for a small top reads like a broken search, and it
                     will quietly cost you in unit 4 when you test criterion 1.
                     What counts as a size match is part of your spec — decide
                     it and write it into your Tool Inventory.
        max_price:   maximum price, inclusive, or None to skip price filtering.

    Returns:
        A list of matching listing dicts, best match first.
        **Returns an empty list when nothing matches — an empty list, not None,
        and not an exception.** Your loop branches on this.

    Each listing dict has these fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand (str or None), platform

    Note that `brand` is None for most listings. That is deliberate and
    realistic — thrift listings often have no brand. If something you write
    assumes a brand is always there, you will find out in unit 4.

    TODO:
        1. Load every listing with load_listings().
        2. Filter by max_price and by size, when each is provided.
        3. Score what's left by keyword overlap with `description`.
        4. Drop anything scoring zero.
        5. Sort by score, highest first, and return the listing dicts —
           at most config.SEARCH_RESULT_LIMIT of them.

    Test it from a terminal before you move on:
        python -c "from tools import search_listings; print(search_listings('graphic tee', max_price=30))"
    """
    candidates = load_listings()

    if max_price is not None:
        candidates = [l for l in candidates if l["price"] <= max_price]
    if size:
        candidates = [l for l in candidates if size_matches(size, l["size"])]

    keywords = _keywords(description or "")
    scored = [(_score(l, keywords), l) for l in candidates]
    scored = [(score, l) for score, l in scored if score > 0]
    scored.sort(key=lambda pair: (-pair[0], pair[1]["price"]))

    return [l for _, l in scored[: config.SEARCH_RESULT_LIMIT]]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest one or two outfits.

    This one calls the model, through `generate()`. You don't need to think
    about rate limits — the adapter handles pacing for you.

    Args:
        new_item: a listing dict — the item the user is considering.
        wardrobe: a wardrobe dict with an 'items' key holding a list of items.
                  **It may be empty.** Handle that.

    Returns:
        A non-empty string with outfit suggestions.
        With an empty wardrobe, return general styling advice rather than
        raising or returning "". Unit 4 has you trigger the empty wardrobe on
        purpose, so decide now what it should do.

    TODO:
        1. Check whether wardrobe['items'] is empty.
        2. If it is, ask the model for general styling ideas for this item.
        3. If it isn't, format the wardrobe items into the prompt and ask for
           specific combinations naming pieces the user already owns.
        4. Return the model's response.

    Test it from a terminal before you move on:
        python -c "from tools import suggest_outfit; from utils.data_loader import get_example_wardrobe, load_listings; print(suggest_outfit(load_listings()[0], get_example_wardrobe()))"
    """
    if not new_item:
        return "No item to style: search found nothing to build an outfit around."

    item = _describe_item(new_item)
    items = (wardrobe or {}).get("items") or []

    if not items:
        advice = generate(
            f"Someone is thinking about buying this thrifted piece:\n{item}\n\n"
            "They haven't told you what else they own. Suggest one or two "
            "outfits built around it, using common basics anyone could own. "
            "Keep it to about four sentences.",
            system=_STYLIST,
        )
        return f"No saved wardrobe yet, so here are general ideas: {advice.strip()}"

    owned = "\n".join(
        f"- {w['name']} ({w['category']}; colors: {', '.join(w['colors'])}"
        f"{'; ' + w['notes'] if w.get('notes') else ''})"
        for w in items
    )
    return generate(
        f"Someone is thinking about buying this thrifted piece:\n{item}\n\n"
        f"Here is what they already own:\n{owned}\n\n"
        "Suggest one or two outfits built around the new piece. Each outfit must "
        "name the pieces they already own exactly as listed above. Keep it to "
        "about four sentences.",
        system=_STYLIST,
    ).strip()


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Write a short caption someone would actually post about the find.

    This calls the model too.

    Args:
        outfit:   the outfit suggestion string from suggest_outfit().
        new_item: the listing dict for the item.

    Returns:
        A two-to-four sentence caption.
        If `outfit` is empty or whitespace, return a descriptive message rather
        than raising.

    The caption should read like a real post rather than a product description,
    mention the item and its price and platform once each, and be specific about
    the vibe.

    It should also come out **differently for different inputs**. If you run
    this three times on the same item and get three word-for-word identical
    strings, it's one of two things, and both are near the top of `config.py`:

        • CACHE_ENABLED — the adapter handed back an answer it already had
        • TEMPERATURE   — at 0.0 the model gives the same words every time

    TODO:
        1. Guard against an empty or whitespace-only `outfit`.
        2. Build a prompt with the item details and the outfit.
        3. Call generate() and return the response.

    Test it from a terminal before you move on:
        python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('jeans and white sneakers', load_listings()[0]))"
    """
    if not outfit or not outfit.strip():
        return "Can't write a fit card without an outfit suggestion."

    price = f"${new_item['price']:g}"
    return generate(
        f"The find:\n{_describe_item(new_item)}\n\n"
        f"How they plan to wear it:\n{outfit.strip()}\n\n"
        "Write the caption they'd post about this find. Rules:\n"
        "- 2 to 4 sentences. Hashtags or emoji are fine at the end.\n"
        f"- Mention the item, the price written exactly as {price}, and the "
        f"platform ({new_item['platform']}) — once each.\n"
        "- Sound like a person posting, not a product listing. Be specific "
        "about the vibe of the outfit.\n"
        "Reply with the caption only.",
        system="You write short, natural social media captions about thrift finds.",
    ).strip()


# ── shared by the two model tools ─────────────────────────────────────────────

_STYLIST = (
    "You are a practical stylist. Suggest outfits someone could put together "
    "today. Be specific and brief. Don't invent pieces for the user's wardrobe."
)


def _describe_item(item: dict) -> str:
    """One listing as plain text for a prompt. Brand is left out when it's None."""
    parts = [
        f"{item['title']} — ${item['price']:g} on {item['platform']}",
        f"category: {item['category']}, size {item['size']}, condition {item['condition']}",
        f"colors: {', '.join(item['colors'])}; style: {', '.join(item['style_tags'])}",
    ]
    if item.get("brand"):
        parts.append(f"brand: {item['brand']}")
    parts.append(item["description"])
    return "\n".join(parts)
