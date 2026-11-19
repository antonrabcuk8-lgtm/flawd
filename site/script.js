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

  const packLabel = (pack) => {
    if (pack === "pack-15") return "3-run pack ($15)";
    if (pack === "b2b-audit") return "B2B audit call";
    return "Single run ($9)";
  };

  const setupNav = () => {
    const btn = document.getElementById("menuBtn");
    const links = document.getElementById("navlinks");
    if (!btn || !links) return;
    const setOpen = (open) => {
      links.classList.toggle("open", open);
      btn.setAttribute("aria-expanded", open ? "true" : "false");
      btn.textContent = open ? "CLOSE" : "MENU";
    };
    btn.setAttribute("aria-expanded", "false");
    btn.addEventListener("click", () => setOpen(!links.classList.contains("open")));
    links.querySelectorAll("a").forEach((a) => a.addEventListener("click", () => setOpen(false)));
  };

  const setupCopy = () => {
    document.querySelectorAll(".copy").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const text = btn.getAttribute("data-copy") || "";
        try {
          await navigator.clipboard.writeText(text);
          btn.textContent = "COPIED";
          btn.classList.add("copied");
          window.setTimeout(() => {
            btn.textContent = "COPY";
            btn.classList.remove("copied");
          }, 1400);
        } catch {
          btn.textContent = "SELECT TEXT";
        }
      });
    });
  };

  const setupPlans = () => {
    document.querySelectorAll(".plan").forEach((label) => {
      label.addEventListener("click", () => {
        document.querySelectorAll(".plan").forEach((p) => p.classList.remove("selected"));
        label.classList.add("selected");
        const input = label.querySelector("input");
        if (input) input.checked = true;
      });
    });
  };

  const renderCatalog = (cards) => {
    const grid = document.getElementById("cards");
    const meta = document.getElementById("catalogMeta");
    const countEl = document.getElementById("card-count");
    const foot = document.getElementById("catalogFoot");
    if (!grid) return;

    if (countEl) countEl.textContent = String(cards.length);
    if (foot) {
      foot.textContent = `Author: ${cfg.author || "antonrabcuk8-lgtm"} · Catalog updated ${
        cfg.catalogUpdated || "2026-11-19"
      }`;
    }
    const updated = document.getElementById("updated-date");
    if (updated && cfg.catalogUpdated) updated.textContent = cfg.catalogUpdated;

    const paint = (filter) => {
      const visible = cards.filter((c) => matchesFilter(c, filter));
      grid.innerHTML = visible
        .map((card) => {
          const prov = provenanceLabel(card.provenance);
          const short = card.id.replace("FLAWD-2026-", "");
          return `<a class="failure" href="./catalog/${card.id}.html">
            <div class="failure-top">
              <span class="id">FLAWD-2026-${short}</span>
              <span class="severity ${card.severity}">${card.severity}</span>
            </div>
            <h4>${escapeHtml(card.title)}</h4>
            <p>${escapeHtml(card.summary)}</p>
            <div class="tagrow">
              <span>${escapeHtml(card.category)}</span>
              <span class="${prov.cls}">${prov.text}</span>
            </div>
          </a>`;
        })
        .join("");
      if (meta) {
        meta.textContent =
          filter === "all"
            ? `Showing all ${visible.length} verified cards`
            : `Showing ${visible.length} of ${cards.length} verified cards`;
      }
    };

    document.querySelectorAll(".filter").forEach((btn) => {
      btn.addEventListener("click", () => {
        document.querySelectorAll(".filter").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        paint(btn.dataset.filter || "all");
      });
    });

    paint("all");
  };

  const escapeHtml = (s) =>
    String(s || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");

  const setupForm = () => {
    const form = document.getElementById("auditForm");
    const status = document.getElementById("formMessage");
    const hint = document.getElementById("formHint");
    if (!form) return;

    if (hint) {
      if (cfg.formEndpoint) {
        hint.textContent = "Submits privately via Formspree. Nothing is posted to GitHub.";
      } else if (cfg.contactEmail) {
        hint.textContent = `Opens a private email draft to ${cfg.contactEmail}. Nothing is posted to GitHub.`;
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
        status.style.display = "block";
      };

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
          document.querySelectorAll(".plan").forEach((p, i) => {
            p.classList.toggle("selected", i === 0);
          });
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
      window.location.href = `mailto:${encodeURIComponent(to)}?subject=${encodeURIComponent(
        `[Flawd Cloud] ${packLabel(pack)}`
      )}&body=${encodeURIComponent(body)}`;
      show(
        to
          ? "Private email draft opened. Request also copied to clipboard."
          : "Mailto draft opened (set contactEmail in config.js). Copied to clipboard — do not paste into a public issue."
      );
    });
  };

  setupNav();
  setupCopy();
  setupPlans();
  setupForm();

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
      const meta = document.getElementById("catalogMeta");
      if (meta) meta.textContent = "Catalog failed to load.";
    });
})();
