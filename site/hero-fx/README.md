# Hero FX (isolated FaultyTerminal)

The Flawd landing page is **plain HTML**. This mini-app is the only React island:

- Source: React Bits `FaultyTerminal` (WebGL2 CRT glyphs)
- Tint `#C6FF3D`, brightness `0.45`, low glitch/flicker
- Disabled on `prefers-reduced-motion: reduce` and viewports `≤720px`
- Paused via `IntersectionObserver` when the hero is off-screen
- Optional “Pause background” control (WCAG 2.2.2)

```bash
cd site/hero-fx
npm ci
npm run build
# writes ../hero-fx.bundle.js + ../hero-fx.css
```
