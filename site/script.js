(() => {
  const LOOP_CATEGORIES = new Set([
    "terminal-loop",
    "rate-limit",
    "schema-retry",
    "timeout",
  ]);
  const CONTEXT_CATEGORIES = new Set([
    "context-loss",
    "context-poison",
  ]);

  const familyOf = (card) => {
    if (card.category === "idempotency") return "idempotency";
    if (card.category === "prompt-injection") return "injection";
    if (card.category === "tool-policy") return "tool-policy";
    if (LOOP_CATEGORIES.has(card.category)) return "loop";
    if (CONTEXT_CATEGORIES.has(card.category)) return "context";
    if (card.category === "timeout") return "timeout";
    return card.category;
  };

  const matchesFilter = (card, filter) => {
    if (filter === "all") return true;
    if (filter === "loop") return LOOP_CATEGORIES.has(card.category);
    if (filter === "injection") return card.category === "prompt-injection";
    if (filter === "context") return CONTEXT_CATEGORIES.has(card.category);
    if (filter === "timeout") return card.category === "timeout";
    return card.category === filter;
  };

  const setupCopyButtons = () => {
    document.querySelectorAll("[data-copy]").forEach((btn) => {
      const reset = () => {
        btn.textContent = "Copy";
        btn.classList.remove("copied");
      };
      btn.addEventListener("click", async () => {
        const text = (btn.getAttribute("data-copy") || "").replace(/&#10;/g, "\n");
        try {
          await navigator.clipboard.writeText(text);
          btn.textContent = "Copied";
          btn.classList.add("copied");
          window.setTimeout(reset, 1600);
        } catch {
          btn.textContent = "Select + copy";
          window.setTimeout(reset, 1600);
        }
      });
    });
  };

  const renderCatalog = (cards) => {
    const grid = document.getElementById("catalog-grid");
    const tpl = document.getElementById("card-template");
    const meta = document.getElementById("filter-meta");
    const countEl = document.getElementById("card-count");
    if (!grid || !tpl) return;

    if (countEl) countEl.textContent = String(cards.length);

    grid.replaceChildren();
    cards.forEach((card) => {
      const node = tpl.content.firstElementChild.cloneNode(true);
      node.dataset.family = familyOf(card);
      node.dataset.category = card.category;
      node.querySelector(".card-id").textContent = card.id.replace("FLAWD-2026-", "");
      const sev = node.querySelector(".card-sev");
      sev.textContent = card.severity;
      sev.classList.add(card.severity);
      node.querySelector(".card-title").textContent = card.title;
      node.querySelector(".card-summary").textContent = card.summary;
      node.querySelector(".card-cat").textContent = card.category;
      const link = node.querySelector(".card-link");
      link.href = `https://github.com/antonrabcuk8-lgtm/flawd/blob/master/database/${card.id}.yaml`;
      grid.appendChild(node);
    });

    const apply = (filter) => {
      let shown = 0;
      grid.querySelectorAll(".card-item").forEach((el, idx) => {
        const card = cards[idx];
        const ok = matchesFilter(card, filter);
        el.classList.toggle("is-hidden", !ok);
        if (ok) shown += 1;
      });
      if (meta) {
        meta.textContent =
          filter === "all"
            ? `Showing all ${shown} verified cards`
            : `Showing ${shown} of ${cards.length} · filter: ${filter}`;
      }
    };

    document.querySelectorAll(".chip").forEach((chip) => {
      chip.addEventListener("click", () => {
        document.querySelectorAll(".chip").forEach((c) => c.classList.remove("active"));
        chip.classList.add("active");
        apply(chip.dataset.filter || "all");
      });
    });

    apply("all");
  };

  const setupOrderForm = () => {
    const form = document.getElementById("order-form");
    const status = document.getElementById("form-status");
    if (!form) return;

    form.addEventListener("submit", (event) => {
      event.preventDefault();
      const data = new FormData(form);
      const email = String(data.get("email") || "").trim();
      const target = String(data.get("target") || "").trim();
      const pack = String(data.get("pack") || "single-9");
      const notes = String(data.get("notes") || "").trim();

      const packLabel =
        pack === "pack-15"
          ? "3-run pack ($15)"
          : pack === "b2b-audit"
            ? "B2B audit call"
            : "Single run ($9)";

      const title = encodeURIComponent(`[Cloud Runner] ${packLabel} request`);
      const body = encodeURIComponent(
        [
          "## Cloud Runner / B2B request",
          "",
          `- **Email:** ${email}`,
          `- **Target URL:** ${target}`,
          `- **Package:** ${packLabel}`,
          `- **Notes:** ${notes || "_none_"}`,
          "",
          "_Submitted from the Flawd showcase site. No payment collected yet._",
        ].join("\n")
      );

      const url = `https://github.com/antonrabcuk8-lgtm/flawd/issues/new?title=${title}&body=${body}&labels=cloud-runner`;
      window.open(url, "_blank", "noopener");

      if (status) {
        status.hidden = false;
        status.textContent =
          "Issue draft opened — submit it on GitHub to queue the request.";
      }
    });
  };

  setupCopyButtons();
  setupOrderForm();

  fetch("./catalog.json")
    .then((r) => {
      if (!r.ok) throw new Error("catalog missing");
      return r.json();
    })
    .then((data) => renderCatalog(data.cards || []))
    .catch(() => {
      const meta = document.getElementById("filter-meta");
      if (meta) meta.textContent = "Catalog failed to load.";
    });
})();
