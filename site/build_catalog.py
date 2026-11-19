#!/usr/bin/env python3
"""Generate site/catalog/*.html and refresh catalog.json from database/*.yaml."""

from __future__ import annotations

import html
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "database"
SITE = ROOT / "site"
CATALOG_DIR = SITE / "catalog"


def esc(s: str | None) -> str:
    return html.escape(s or "", quote=True)


def provenance_label(prov: str) -> tuple[str, str]:
    if prov == "github-inspired":
        return ("from public issue", "prov-issue")
    return ("synthetic", "prov-synthetic")


def load_cards() -> list[dict]:
    cards: list[dict] = []
    for path in sorted(DB.glob("FLAWD-*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if data.get("status") != "verified":
            continue
        src = data.get("source") or {}
        cards.append(
            {
                "id": data["id"],
                "num": data["id"].split("-")[-1],
                "title": data.get("title", ""),
                "summary": (data.get("summary") or "").strip(),
                "failure_mechanism": (data.get("failure_mechanism") or "").strip(),
                "category": data.get("category", ""),
                "severity": data.get("severity", ""),
                "provenance": data.get("provenance", ""),
                "mitigation": (data.get("mitigation") or "").strip(),
                "prompt": (data.get("prompt") or "").strip(),
                "reproduction_hints": data.get("reproduction_hints") or [],
                "tags": data.get("tags") or [],
                "source_type": src.get("type"),
                "source_url": src.get("url"),
                "source_note": (src.get("note") or "").strip(),
                "source_accessed": src.get("accessed"),
                "notes": (data.get("notes") or "").strip(),
            }
        )
    return cards


def render_card_page(card: dict) -> str:
    prov_label, prov_class = provenance_label(card["provenance"])
    hints = "".join(f"<li>{esc(h)}</li>" for h in card["reproduction_hints"]) or (
        "<li>See prompt and assertions in the YAML.</li>"
    )
    source_block = ""
    if card.get("source_url"):
        source_block = (
            f'<p><a class="lime" href="{esc(card["source_url"])}" rel="noopener">'
            f"Source link</a>"
        )
        if card.get("source_accessed"):
            source_block += f' · accessed {esc(str(card["source_accessed"]))}'
        source_block += "</p>"
    if card.get("source_note"):
        source_block += f'<p class="muted">{esc(card["source_note"])}</p>'

    return f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="theme-color" content="#090d0b" />
    <title>{esc(card["id"])} — {esc(card["title"])} · Flawd</title>
    <meta name="description" content="{esc(card["summary"][:180])}" />
    <link rel="icon" href="../favicon.svg" type="image/svg+xml" />
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=Syne:wght@600;700;800&display=swap" rel="stylesheet" />
    <link rel="stylesheet" href="../styles.css" />
  </head>
  <body class="page-card">
    <div class="wrap">
      <nav>
        <a class="brand" href="../">Flaw<span>d</span></a>
        <div class="navlinks" id="navlinks">
          <a href="../#quickstart">Install</a>
          <a href="../#catalog">Catalog</a>
          <a href="../#audit">Cloud</a>
          <a href="https://github.com/antonrabcuk8-lgtm/flawd/issues/new?template=submit_failure.yml">Submit a failure</a>
          <a class="nav-cta" href="../#audit">Get audited ↗</a>
        </div>
        <button class="menu" id="menuBtn" type="button" aria-label="Toggle menu">MENU</button>
      </nav>

      <main class="card-page">
        <p class="crumb"><a href="../#catalog">Catalog</a> / {esc(card["id"])}</p>
        <div class="card-meta-row">
          <span class="pill sev-{esc(card["severity"])}">{esc(card["severity"])}</span>
          <span class="pill">{esc(card["category"])}</span>
          <span class="pill {prov_class}">{esc(prov_label)}</span>
          <span class="mark-fail">FAIL</span>
          <span class="mark-pass">PASS*</span>
        </div>
        <h1>{esc(card["id"])}</h1>
        <p class="card-page-title">{esc(card["title"])}</p>
        <p class="lede-solid">{esc(card["summary"])}</p>

        <section>
          <h2>Failure mechanism</h2>
          <p>{esc(card["failure_mechanism"])}</p>
        </section>

        <section>
          <h2>Reproduction</h2>
          <p class="muted">Prompt sent to the agent:</p>
          <pre class="prompt-block">{esc(card["prompt"])}</pre>
          <ol class="steps">{hints}</ol>
        </section>

        <section>
          <h2>Mitigation</h2>
          <p>{esc(card["mitigation"])}</p>
        </section>

        <section>
          <h2>Provenance</h2>
          <p><strong>{esc(prov_label)}</strong> · field <code>provenance: {esc(card["provenance"])}</code></p>
          {source_block}
          <p class="tiny">* PASS on <code>examples/hardened_agent.py</code> — a reference agent written for this repo, not a third-party product.</p>
        </section>

        <p class="back"><a href="../#catalog">← All 28 cards</a> · <a href="https://github.com/antonrabcuk8-lgtm/flawd/blob/master/database/{esc(card["id"])}.yaml">YAML on GitHub</a></p>
      </main>

      <footer>
        <div class="footer-inner">
          <span>MIT · Catalog by <a class="lime" href="https://github.com/antonrabcuk8-lgtm">antonrabcuk8-lgtm</a> · Updated 2026-11-19</span>
          <span>BUILT FOR SAFER AGENTS.</span>
        </div>
      </footer>
    </div>
    <script>
      document.getElementById('menuBtn')?.addEventListener('click', () =>
        document.getElementById('navlinks')?.classList.toggle('open'));
    </script>
  </body>
</html>
"""


def main() -> None:
    cards = load_cards()
    CATALOG_DIR.mkdir(parents=True, exist_ok=True)
    for old in CATALOG_DIR.glob("FLAWD-*.html"):
        old.unlink()
    for card in cards:
        (CATALOG_DIR / f"{card['id']}.html").write_text(render_card_page(card), encoding="utf-8")

    payload = {
        "generated": "2026-11-19",
        "updated": "2026-11-19",
        "author": "antonrabcuk8-lgtm",
        "count": len(cards),
        "cards": cards,
    }
    (SITE / "catalog.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(cards)} pages → {CATALOG_DIR}")


if __name__ == "__main__":
    main()
