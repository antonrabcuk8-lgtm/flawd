import { createRoot } from "react-dom/client";
import { useEffect, useState } from "react";
import FaultyTerminal from "./FaultyTerminal.jsx";
import "./FaultyTerminal.css";

const MOBILE_MQ = "(max-width: 720px)";
const REDUCE_MQ = "(prefers-reduced-motion: reduce)";

function shouldEnableFx() {
  if (typeof window === "undefined") return false;
  if (window.matchMedia(REDUCE_MQ).matches) return false;
  if (window.matchMedia(MOBILE_MQ).matches) return false;
  return true;
}

function HeroTerminal({ heroEl, userPaused }) {
  const [offscreen, setOffscreen] = useState(false);
  const [enabled, setEnabled] = useState(() => shouldEnableFx());

  useEffect(() => {
    const reduceMq = window.matchMedia(REDUCE_MQ);
    const mobileMq = window.matchMedia(MOBILE_MQ);
    const sync = () => setEnabled(shouldEnableFx());
    reduceMq.addEventListener?.("change", sync);
    mobileMq.addEventListener?.("change", sync);
    reduceMq.addListener?.(sync);
    mobileMq.addListener?.(sync);
    return () => {
      reduceMq.removeEventListener?.("change", sync);
      mobileMq.removeEventListener?.("change", sync);
      reduceMq.removeListener?.(sync);
      mobileMq.removeListener?.(sync);
    };
  }, []);

  useEffect(() => {
    if (!enabled || !heroEl) {
      setOffscreen(true);
      return undefined;
    }
    // Pause WebGL when the hero leaves the viewport
    // (modern-web-guidance: efficient-background-processing / IntersectionObserver fallback).
    const io = new IntersectionObserver(
      (entries) => {
        const on = entries.some((e) => e.isIntersecting && e.intersectionRatio > 0.05);
        setOffscreen(!on);
      },
      { threshold: [0, 0.05, 0.2] }
    );
    io.observe(heroEl);
    return () => io.disconnect();
  }, [enabled, heroEl]);

  if (!enabled) return null;

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
      brightness={0.45}
      glyphs="characters"
      glow={0.7}
      persistence={0.35}
      scramble={0.2}
      mouseGlow={0}
      vignette={0.55}
      clickEffect="none"
      dpr={Math.min(window.devicePixelRatio || 1, 1.5)}
      style={{ width: "100%", height: "100%" }}
    />
  );
}

function App({ heroEl }) {
  const [userPaused, setUserPaused] = useState(false);

  useEffect(() => {
    const btn = document.getElementById("hero-fx-toggle");
    if (!btn || !shouldEnableFx()) return undefined;
    btn.hidden = false;
    const onClick = () => {
      setUserPaused((p) => {
        const next = !p;
        btn.textContent = next ? "Play background" : "Pause background";
        return next;
      });
    };
    btn.addEventListener("click", onClick);
    return () => btn.removeEventListener("click", onClick);
  }, []);

  return <HeroTerminal heroEl={heroEl} userPaused={userPaused} />;
}

function mount() {
  const rootEl = document.getElementById("hero-fx-root");
  const heroEl = document.querySelector(".hero");
  if (!rootEl) return;

  if (!shouldEnableFx()) {
    rootEl.setAttribute("data-fx", "static");
    return;
  }

  rootEl.setAttribute("data-fx", "live");
  createRoot(rootEl).render(<App heroEl={heroEl} />);
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", mount);
} else {
  mount();
}
