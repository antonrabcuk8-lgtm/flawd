import { createRoot } from "react-dom/client";
import { useEffect, useState } from "react";
import FaultyTerminal from "./FaultyTerminal.jsx";
import "./FaultyTerminal.css";

const MOBILE_MQ = "(max-width: 720px)";
const REDUCE_MQ = "(prefers-reduced-motion: reduce)";

function getFxMode() {
  if (typeof window === "undefined") return "static";
  if (window.matchMedia(REDUCE_MQ).matches) return "reduced";
  if (window.matchMedia(MOBILE_MQ).matches) return "mobile";
  return "live";
}

function HeroTerminal({ heroEl, userPaused, mode }) {
  const [offscreen, setOffscreen] = useState(false);

  useEffect(() => {
    if (mode !== "live" || !heroEl) {
      setOffscreen(true);
      return undefined;
    }
    const io = new IntersectionObserver(
      (entries) => {
        const on = entries.some((e) => e.isIntersecting && e.intersectionRatio > 0.02);
        setOffscreen(!on);
      },
      { threshold: [0, 0.02, 0.15] }
    );
    io.observe(heroEl);
    return () => io.disconnect();
  }, [mode, heroEl]);

  if (mode !== "live") {
    return <div className="hero-fx-static" aria-hidden="true" />;
  }

  return (
    <FaultyTerminal
      className="hero-faulty-terminal"
      scale={1.4}
      gridMul={[2, 1]}
      digitSize={1.4}
      timeScale={0.25}
      pause={userPaused || offscreen}
      scanlineIntensity={0.35}
      glitchAmount={0.25}
      flickerAmount={0.2}
      noiseAmp={0.55}
      chromaticAberration={0}
      dither={0}
      curvature={0.08}
      tint="#C6FF3D"
      mouseReact={false}
      mouseStrength={0.3}
      pageLoadAnimation={false}
      brightness={0.65}
      glyphs="characters"
      glow={0.85}
      persistence={0.35}
      scramble={0.2}
      mouseGlow={0}
      vignette={0.45}
      clickEffect="none"
      dpr={Math.min(window.devicePixelRatio || 1, 1.5)}
      style={{ width: "100%", height: "100%" }}
    />
  );
}

function App({ heroEl }) {
  const [mode, setMode] = useState(() => getFxMode());
  const [userPaused, setUserPaused] = useState(false);

  useEffect(() => {
    const sync = () => setMode(getFxMode());
    const reduceMq = window.matchMedia(REDUCE_MQ);
    const mobileMq = window.matchMedia(MOBILE_MQ);
    reduceMq.addEventListener?.("change", sync);
    mobileMq.addEventListener?.("change", sync);
    reduceMq.addListener?.(sync);
    mobileMq.addListener?.(sync);
    window.addEventListener("resize", sync);
    // Re-check after layout (covers late viewport / zoom).
    requestAnimationFrame(sync);
    return () => {
      reduceMq.removeEventListener?.("change", sync);
      mobileMq.removeEventListener?.("change", sync);
      reduceMq.removeListener?.(sync);
      mobileMq.removeListener?.(sync);
      window.removeEventListener("resize", sync);
    };
  }, []);

  useEffect(() => {
    const rootEl = document.getElementById("hero-fx-root");
    if (rootEl) rootEl.setAttribute("data-fx", mode === "live" ? "live" : "static");
  }, [mode]);

  useEffect(() => {
    const btn = document.getElementById("hero-fx-toggle");
    if (!btn) return undefined;
    const show = mode === "live";
    btn.hidden = !show;
    if (!show) return undefined;
    const onClick = () => {
      setUserPaused((p) => {
        const next = !p;
        btn.textContent = next ? "Play background" : "Pause background";
        return next;
      });
    };
    btn.addEventListener("click", onClick);
    return () => btn.removeEventListener("click", onClick);
  }, [mode]);

  return <HeroTerminal heroEl={heroEl} userPaused={userPaused} mode={mode} />;
}

function mount() {
  const rootEl = document.getElementById("hero-fx-root");
  const heroEl = document.querySelector(".hero");
  if (!rootEl) {
    console.warn("[flawd-hero-fx] #hero-fx-root missing");
    return;
  }
  rootEl.setAttribute("data-fx", "booting");
  try {
    createRoot(rootEl).render(<App heroEl={heroEl} />);
  } catch (err) {
    console.error("[flawd-hero-fx] mount failed", err);
    rootEl.setAttribute("data-fx", "error");
  }
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", mount);
} else {
  mount();
}
