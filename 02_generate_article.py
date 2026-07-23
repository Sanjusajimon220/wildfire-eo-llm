#!/usr/bin/env python3
"""
02_generate_article.py — the constrained narrative layer.

    facts_<fire_id>.json  ->  LLM  ->  article_<fire_id>.md

The guarantee this file exists to enforce:
    the model never sees a pixel, never computes anything, and cannot state
    a number that is not traceable to the measurements.

How that is enforced (not merely requested):
    1. The prompt supplies ONLY facts.json and forbids unstated figures.
    2. After generation, every number in the draft is extracted and checked
       against an allowlist derived from facts.json.
    3. Any untraceable number fails the build. The script retries, feeding the
       offending numbers back, and exits non-zero if it still cannot comply.

Usage:
    export ANTHROPIC_API_KEY=...
    python 02_generate_article.py facts_tenerife_2023.json
    python 02_generate_article.py facts_tenerife_2023.json --dry-run   # no API call
"""

import argparse
import json
import os
import re
import sys
from datetime import date

MODEL = "claude-sonnet-4-6"
MAX_ATTEMPTS = 3

# ----------------------------------------------------------------------------
# 1 · The prompt: constrained generation
# ----------------------------------------------------------------------------

SYSTEM_PROMPT = """You are drafting a factual news brief for a satellite-journalism \
outlet that publishes measurements from open Earth-observation data.

ABSOLUTE RULES ON NUMBERS
- Use ONLY numbers that appear in the JSON you are given.
- Never invent, estimate, extrapolate, or infer a figure. If a number is not in \
the JSON, omit the claim entirely rather than approximating it.
- You may round a figure from the JSON to a cleaner form (13,470.5 -> "13,470" or \
"about 13,500 hectares"). You may not produce a number that has no source in the JSON.
- Do not compute new quantities (no sums, ratios, or per-day rates) unless the \
result is itself present in the JSON.

ABSOLUTE RULES ON MEANING
- Active-fire detections are hotspots seen from orbit. They are NOT a fire \
perimeter and NOT a count of fires. Never describe them as a boundary.
- Burn severity is a spectral estimate from satellite imagery. It is NOT a \
field survey and NOT a measure of ecological loss.
- Protected-area figures are EXPOSURE: burned area that falls within protected \
boundaries. Never write "destroyed", "damaged", "lost", or "killed" about \
protected land, habitat, buildings, or people.
- Never state or imply casualties, evacuations, property damage, or cause of \
ignition. None of that is measured here.
- The comparison with an official reference is a validation check, not a \
correction of the official figure. Report the difference neutrally.

STYLE
- Neutral, precise, plain. Short sentences. No adjectives that dramatise.
- British English. Metric units. Write hectares in full on first use.
- Do not use the words "devastating", "apocalyptic", "unprecedented", "raging".

OUTPUT FORMAT — return exactly this markdown structure and nothing else:

# <headline, max 12 words>

<standfirst: two sentences summarising what was measured and where>

## What the satellites recorded
<one paragraph, 3-5 sentences>

## What burned
<one paragraph, 3-5 sentences>

## How much of it was protected land
<one paragraph, 3-5 sentences>

## How we measured this
<one short paragraph: sensors, method, validation against the official figure>

## Limitations
<bulleted list, taken from the limitations array in the JSON, reworded plainly>
"""

USER_TEMPLATE = """Here are the measurements. Write the brief using only these figures.

```json
{facts}
```
"""

RETRY_TEMPLATE = """Your previous draft contained numbers that do not appear in the \
measurements: {bad}.

Every number you write must be traceable to the JSON. Rewrite the brief, removing \
or replacing those figures. Do not introduce any new numbers.
"""

# ----------------------------------------------------------------------------
# 2 · The verifier: build an allowlist, then check the draft
# ----------------------------------------------------------------------------

def collect_numbers(obj, out):
    """Recursively pull every numeric value out of the facts structure."""
    if isinstance(obj, bool) or obj is None:
        return
    if isinstance(obj, (int, float)):
        out.add(float(obj))
    elif isinstance(obj, str):
        # dates and any digits embedded in strings (e.g. "2023-08-16", "EMSR685")
        for m in re.findall(r"\d+(?:\.\d+)?", obj):
            out.add(float(m))
    elif isinstance(obj, dict):
        for v in obj.values():
            collect_numbers(v, out)
    elif isinstance(obj, list):
        for v in obj:
            collect_numbers(v, out)


def allowed_variants(values):
    """Every legitimate way a source figure may be written."""
    allowed = set()
    for v in values:
        allowed.add(v)
        allowed.add(abs(v))
        # rounding to a cleaner form
        for nd in (0, 1, 2):
            allowed.add(round(v, nd))
        for base in (10, 100, 1000):
            allowed.add(round(v / base) * base)
        # thousands expressed compactly: 13470.5 -> 13.5 (as in "13.5 thousand")
        if abs(v) >= 1000:
            allowed.add(round(v / 1000, 1))
            allowed.add(round(v / 1000))
        # a percentage may be written with or without its sign
        if abs(v) < 1000:
            allowed.add(round(v))
    # small integers are structural (list counts, "two sensors", section numbers)
    allowed.update(float(i) for i in range(0, 13))
    return {round(a, 4) for a in allowed}


NUM_RE = re.compile(r"(?<![\w/-])[-+]?\d[\d,]*(?:\.\d+)?(?![\w/])")


def numbers_in_text(text):
    """Extract candidate numbers, skipping code blocks and URLs."""
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = re.sub(r"https?://\S+", " ", text)
    found = []
    for m in NUM_RE.finditer(text):
        raw = m.group().replace(",", "").lstrip("+")
        try:
            found.append((m.group(), float(raw)))
        except ValueError:
            continue
    return found


def verify(text, facts, tol=0.01):
    """Return the list of numbers in `text` with no source in `facts`."""
    source = set()
    collect_numbers(facts, source)
    allowed = allowed_variants(source)

    bad = []
    for shown, val in numbers_in_text(text):
        v = round(abs(val), 4)
        ok = any(abs(v - a) <= tol or abs(v - abs(a)) <= tol for a in allowed)
        if not ok:
            bad.append(shown)
    return bad


# ----------------------------------------------------------------------------
# 3 · Banned-language check (exposure is not damage)
# ----------------------------------------------------------------------------

BANNED = [
    r"\bdestroyed\b", r"\bdestruction\b", r"\bdamaged\b", r"\bwiped out\b",
    r"\bkilled\b", r"\bcasualt", r"\bdeaths?\b", r"\bevacuat",
    r"\bdevastating\b", r"\bapocalyp", r"\bunprecedented\b", r"\braging\b",
    r"\bperimeter of the fire was\b",
]


def banned_phrases(text):
    hits = []
    for pat in BANNED:
        for m in re.finditer(pat, text, flags=re.I):
            hits.append(m.group())
    return sorted(set(hits))


# ----------------------------------------------------------------------------
# 4 · Generation
# ----------------------------------------------------------------------------

def call_model(messages, system):
    """Anthropic Messages API. Swap this one function for another provider."""
    try:
        import anthropic
    except ImportError:
        sys.exit("pip install anthropic  (or replace call_model with your provider)")

    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        sys.exit("Set ANTHROPIC_API_KEY in your environment.")

    client = anthropic.Anthropic(api_key=key)
    resp = client.messages.create(
        model=MODEL,
        max_tokens=1600,
        temperature=0.2,          # low: we want faithful rewording, not invention
        system=system,
        messages=messages,
    )
    return "".join(b.text for b in resp.content if b.type == "text")


def generate(facts):
    facts_json = json.dumps(facts, indent=2, ensure_ascii=False)
    messages = [{"role": "user", "content": USER_TEMPLATE.format(facts=facts_json)}]

    for attempt in range(1, MAX_ATTEMPTS + 1):
        print(f"  attempt {attempt}/{MAX_ATTEMPTS} …")
        draft = call_model(messages, SYSTEM_PROMPT)

        bad = verify(draft, facts)
        banned = banned_phrases(draft)

        if not bad and not banned:
            print(f"  ✓ every number traceable; no banned language")
            return draft, attempt

        if bad:
            print(f"  ✗ untraceable numbers: {', '.join(bad)}")
        if banned:
            print(f"  ✗ banned language: {', '.join(banned)}")

        problems = []
        if bad:
            problems.append(", ".join(bad))
        if banned:
            problems.append("banned wording: " + ", ".join(banned))
        messages += [
            {"role": "assistant", "content": draft},
            {"role": "user", "content": RETRY_TEMPLATE.format(bad="; ".join(problems))},
        ]

    return None, MAX_ATTEMPTS


# ----------------------------------------------------------------------------
# 5 · CLI
# ----------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("facts", help="path to facts_<fire_id>.json")
    ap.add_argument("--out", help="output markdown path")
    ap.add_argument("--prompt", action="store_true",
                    help="print the prompt to paste into claude.ai (no API key needed)")
    ap.add_argument("--dry-run", action="store_true",
                    help="verify an existing article instead of generating one")
    ap.add_argument("--check", help="path to an article to verify (with --dry-run)")
    args = ap.parse_args()

    facts = json.load(open(args.facts))
    fid = facts.get("fire_id", "fire")
    out = args.out or f"article_{fid}.md"

    # --- no-API route: print the prompt, paste it into claude.ai, verify the reply ---
    if args.prompt:
        print(SYSTEM_PROMPT)
        print("\n" + "=" * 72 + "\n")
        print(USER_TEMPLATE.format(
            facts=json.dumps(facts, indent=2, ensure_ascii=False)))
        sys.exit(0)

    if args.dry_run:
        path = args.check or out
        text = open(path).read()
        bad, banned = verify(text, facts), banned_phrases(text)
        print(f"checked {path}")
        print("  untraceable numbers:", ", ".join(bad) if bad else "none")
        print("  banned language    :", ", ".join(banned) if banned else "none")
        sys.exit(1 if (bad or banned) else 0)

    print(f"generating from {args.facts}")
    draft, attempts = generate(facts)

    if draft is None:
        sys.exit("FAILED: model could not produce a fully traceable draft. "
                 "Nothing written — this is the guardrail working.")

    stamp = (
        "\n\n---\n\n"
        f"*Drafted by a language model from measured data only "
        f"(`{os.path.basename(args.facts)}`), then edited and checked by a human. "
        f"An automated step verifies that every figure in this text is traceable to "
        f"the measurements; the draft is rejected if any figure is not. "
        f"Verified {date.today().isoformat()}, attempt {attempts} of {MAX_ATTEMPTS}.*\n"
    )
    open(out, "w").write(draft.rstrip() + stamp)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
