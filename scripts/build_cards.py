#!/usr/bin/env python3
"""Build the Selected work cards in assets/cards.

Standard library only. The project data below is the single source of truth:
edit it and run `python3 scripts/build_cards.py`, then commit the SVGs.
Each card is a self-contained flat dark panel, so it reads the same on light
and dark GitHub themes and can be a plain link (GitHub's renderer breaks a link
wrapped around a theme-switching <picture>).
"""
import html
import os
import textwrap

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "cards")
WIDTH, HEIGHT = 440, 196
FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"

C = dict(bg="#0d1117", border="#30363d", title="#f0f6fc", text="#9198a1", muted="#7d8590", link="#4493f8", rule="#21262d")

# slug, category, title, link label, description, date, stack
PROJECTS = [
    ("documind", "AI · RAG", "DocuMind", "GITHUB",
     "Chat with your PDFs. RAG pipeline with cited sources, streamed answers, multi-document search and RAGAS evaluation.",
     "Apr 2026", "Python · FastAPI · LangChain · ChromaDB · React"),
    ("habitforge", "BACKEND · AI", "HabitForge", "LIVE",
     "Habit-tracking REST API with streaks, badges, 365-day analytics and weekly AI coaching insights.",
     "May 2026", "Python · FastAPI · PostgreSQL · Groq"),
    ("ad-engine", "ML · FULL-STACK", "Ad Engine", "GITHUB",
     "Ad analytics platform: CTR, CPC and ROAS metrics, performance forecasting, ad clustering and plain-English insights.",
     "Jan – Sep 2026", "FastAPI · scikit-learn · Pandas · Next.js"),
    ("rounak-paints", "FULL-STACK · LIVE", "Rounak Paints", "LIVE",
     "Live website for a family-owned paint manufacturer, with a catalogue across 12 categories and WhatsApp lead generation.",
     "Jun 2026", "Next.js · React · TypeScript · Tailwind CSS"),
]


def esc(text):
    return html.escape(text, quote=True)


def card(category, title, link, description, date, stack):
    c = C
    lines = textwrap.wrap(description, width=50, break_on_hyphens=False)[:3]
    desc = "\n".join(
        f'    <text x="24" y="{104 + i * 21}" font-size="14" fill="{c["text"]}">{esc(line)}</text>' for i, line in enumerate(lines)
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-label="{esc(title)}: {esc(description)}">
  <title>{esc(title)}</title>
  <rect x="0.5" y="0.5" width="{WIDTH - 1}" height="{HEIGHT - 1}" rx="10" fill="{c['bg']}" stroke="{c['border']}"/>
  <g font-family="{FONT}">
    <text x="24" y="34" font-size="11" font-weight="600" letter-spacing="1.6" fill="{c['muted']}">{esc(category)}</text>
    <text x="{WIDTH - 24}" y="34" font-size="11" font-weight="600" letter-spacing="1.4" text-anchor="end" fill="{c['link']}">{esc(link)} ↗</text>
    <text x="24" y="72" font-size="21" font-weight="600" fill="{c['title']}">{esc(title)}</text>
{desc}
    <line x1="24" y1="158" x2="{WIDTH - 24}" y2="158" stroke="{c['rule']}"/>
    <text x="24" y="180" font-size="12" font-weight="600" fill="{c['link']}">{esc(date)}</text>
    <text x="{WIDTH - 24}" y="180" font-size="12" text-anchor="end" fill="{c['muted']}">{esc(stack)}</text>
  </g>
</svg>
"""


def main():
    os.makedirs(OUT, exist_ok=True)
    for slug, *fields in PROJECTS:
        with open(os.path.join(OUT, f"{slug}.svg"), "w", encoding="utf-8") as f:
            f.write(card(*fields))
    print(f"wrote {len(PROJECTS)} cards to {os.path.normpath(OUT)}")


if __name__ == "__main__":
    main()
