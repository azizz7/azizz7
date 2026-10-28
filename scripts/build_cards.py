#!/usr/bin/env python3
"""Build the Selected work cards in assets/cards.

Standard library only. The project data below is the single source of truth:
edit it and run `python3 scripts/build_cards.py`, then commit the SVGs.
Each card is a self-contained dark panel, so it looks the same on light and
dark GitHub themes.
"""
import html
import os
import textwrap

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "cards")
WIDTH, HEIGHT = 440, 208
FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"

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


def card(slug, category, title, link, description, date, stack):
    lines = textwrap.wrap(description, width=50, break_on_hyphens=False)[:3]
    desc = "\n".join(
        f'  <text x="24" y="{108 + i * 21}" font-size="14" fill="#aab4c5">{esc(line)}</text>' for i, line in enumerate(lines)
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-label="{esc(title)}: {esc(description)}">
  <title>{esc(title)}</title>
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#10162a"/><stop offset="1" stop-color="#0a0e19"/></linearGradient>
    <radialGradient id="glow" cx="0" cy="0" r="1"><stop offset="0" stop-color="#6d5dfc" stop-opacity=".22"/><stop offset="1" stop-color="#6d5dfc" stop-opacity="0"/></radialGradient>
    <linearGradient id="accent" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#f59e0b"/><stop offset="1" stop-color="#60a5fa"/></linearGradient>
    <clipPath id="r"><rect width="{WIDTH}" height="{HEIGHT}" rx="14"/></clipPath>
  </defs>
  <g clip-path="url(#r)">
    <rect width="{WIDTH}" height="{HEIGHT}" fill="url(#bg)"/>
    <rect width="{WIDTH}" height="{HEIGHT}" fill="url(#glow)" transform="scale(1.6 1.2)"/>
    <rect x="24" width="44" height="3" fill="url(#accent)"/>
  </g>
  <rect x="0.5" y="0.5" width="{WIDTH - 1}" height="{HEIGHT - 1}" rx="13.5" fill="none" stroke="#252d45"/>
  <g font-family="{FONT}">
    <text x="24" y="34" font-size="11" font-weight="600" letter-spacing="1.6" fill="#8b9bb8">{esc(category)}</text>
    <text x="{WIDTH - 24}" y="34" font-size="11" font-weight="600" letter-spacing="1.4" text-anchor="end" fill="#7aa7ff">{esc(link)} ↗</text>
    <text x="24" y="76" font-size="22" font-weight="600" fill="#f5f7fb">{esc(title)}</text>
{desc}
    <line x1="24" y1="168" x2="{WIDTH - 24}" y2="168" stroke="#1f2740"/>
    <text x="24" y="191" font-size="12" font-weight="600" fill="#7aa7ff">{esc(date)}</text>
    <text x="{WIDTH - 24}" y="191" font-size="12" text-anchor="end" fill="#7f8aa3">{esc(stack)}</text>
  </g>
</svg>
"""


def main():
    os.makedirs(OUT, exist_ok=True)
    for project in PROJECTS:
        with open(os.path.join(OUT, f"{project[0]}.svg"), "w", encoding="utf-8") as f:
            f.write(card(*project))
    print(f"wrote {len(PROJECTS)} cards to {os.path.normpath(OUT)}")


if __name__ == "__main__":
    main()
