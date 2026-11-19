(() => {
  const btn = document.querySelector("[data-copy]");
  if (!btn) return;

  const label = () => {
    btn.textContent = "Copy";
    btn.classList.remove("copied");
  };

  btn.addEventListener("click", async () => {
    const text = btn.getAttribute("data-copy") || "";
    try {
      await navigator.clipboard.writeText(text);
      btn.textContent = "Copied";
      btn.classList.add("copied");
      window.setTimeout(label, 1600);
    } catch {
      btn.textContent = "Select + copy";
      window.setTimeout(label, 1600);
    }
  });
})();
