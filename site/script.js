(() => {
  const LOOP_CATEGORIES = new Set([
    "terminal-loop",
    "rate-limit",
    "schema-retry",
    "timeout",
  ]);
  const CONTEXT_CATEGORIES = new Set(["context-loss", "context-poison"]);
  const cfg = window.FLAWD_CONFIG || {};

  const provenanceLabel = (prov) =>
    prov === "github-inspired"
      ? { text: "from public issue", cls: "prov-issue" }
      : { text: "synthetic", cls: "prov-synthetic" };

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
    const foot = document.getElementById("catalog-foot");
    if (!grid || !tpl) return;

    if (countEl) countEl.textContent = String(cards.length);
    if (foot) {
      foot.textContent = `Author: ${cfg.author || "antonrabcuk8-lgtm"} · Catalog updated ${
        cfg.catalogUpdated || "2026-11-19"
      }`;
    }
    const updated = document.getElementById("updated-date");
    if (updated && cfg.catalogUpdated) updated.textContent = cfg.catalogUpdated;

    grid.replaceChildren();
    cards.forEach((card) => {
      const node = tpl.content.firstElementChild.cloneNode(true);
      node.href = `./catalog/${card.id}.html`;
      node.querySelector(".card-id").textContent = card.id.replace("FLAWD-2026-", "");
      const sev = node.querySelector(".card-sev");
      sev.textContent = card.severity;
      sev.classList.add(card.severity);
      node.querySelector(".card-title").textContent = card.title;
      node.querySelector(".card-summary").textContent = card.summary;
      node.querySelector(".card-cat").textContent = card.category;
      const prov = provenanceLabel(card.provenance);
      const provEl = node.querySelector(".card-prov");
      provEl.textContent = prov.text;
      provEl.classList.add(prov.cls);
      grid.appendChild(node);
    });

    const apply = (filter) => {
      let shown = 0;
      grid.querySelectorAll(".card-item").forEach((el, idx) => {
        const ok = matchesFilter(cards[idx], filter);
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

  const packLabel = (pack) => {
    if (pack === "pack-15") return "3-run pack ($15)";
    if (pack === "b2b-audit") return "B2B audit call";
    return "Single run ($9)";
  };

  const setupOrderForm = () => {
    const form = document.getElementById("order-form");
    const status = document.getElementById("form-status");
    const hint = document.getElementById("form-hint");
    if (!form) return;

    if (hint) {
      if (cfg.formEndpoint) {
        hint.textContent = "Submits privately via Formspree. Nothing is posted to GitHub.";
      } else if (cfg.contactEmail) {
        hint.textContent = `Opens a private email draft to ${cfg.contactEmail}. Nothing is posted to GitHub.`;
      } else {
        hint.textContent =
          "Set formEndpoint (Formspree) or contactEmail in site/config.js. Until then, the form copies a private request and opens a blank mailto draft — still never a public issue.";
      }
    }

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const data = new FormData(form);
      const email = String(data.get("email") || "").trim();
      const target = String(data.get("target") || "").trim();
      const pack = String(data.get("pack") || "single-9");
      const notes = String(data.get("notes") || "").trim();
      const payload = {
        email,
        target,
        pack: packLabel(pack),
        notes,
        source: "flawd-showcase",
      };

      const show = (msg) => {
        if (!status) return;
        status.hidden = false;
        status.textContent = msg;
      };

      // Preferred: Formspree / compatible POST endpoint (private inbox).
      if (cfg.formEndpoint) {
        try {
          const res = await fetch(cfg.formEndpoint, {
            method: "POST",
            headers: {
              Accept: "application/json",
              "Content-Type": "application/json",
            },
            body: JSON.stringify(payload),
          });
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          form.reset();
          show("Sent privately. We’ll reply by email — no public issue created.");
          return;
        } catch (err) {
          show(`Private submit failed (${err}). Falling back to email draft.`);
        }
      }

      const body = [
        "Flawd Cloud Runner request (private)",
        "",
        `Email: ${email}`,
        `Target: ${target}`,
        `Package: ${packLabel(pack)}`,
        `Notes: ${notes || "(none)"}`,
      ].join("\n");

      try {
        await navigator.clipboard.writeText(body);
      } catch {
        /* ignore */
      }

      const to = cfg.contactEmail || "";
      const mailto = `mailto:${encodeURIComponent(to)}?subject=${encodeURIComponent(
        `[Flawd Cloud] ${packLabel(pack)}`
      )}&body=${encodeURIComponent(body)}`;
      window.location.href = mailto;
      show(
        to
          ? "Private email draft opened. Request also copied to clipboard."
          : "Mailto draft opened (add contactEmail in config.js). Request copied to clipboard — do not paste into a public issue."
      );
    });
  };

  setupCopyButtons();
  setupOrderForm();

  fetch("./catalog.json")
    .then((r) => {
      if (!r.ok) throw new Error("catalog missing");
      return r.json();
    })
    .then((data) => {
      if (data.updated) cfg.catalogUpdated = data.updated;
      if (data.author) cfg.author = data.author;
      renderCatalog(data.cards || []);
    })
    .catch(() => {
      const meta = document.getElementById("filter-meta");
      if (meta) meta.textContent = "Catalog failed to load.";
    });
})();
