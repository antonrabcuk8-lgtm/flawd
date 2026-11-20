import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: path.resolve(import.meta.dirname, ".."),
    emptyOutDir: false,
    cssCodeSplit: false,
    sourcemap: false,
    minify: true,
    rollupOptions: {
      input: path.resolve(import.meta.dirname, "src/main.jsx"),
      output: {
        format: "iife",
        name: "FlawdHeroFx",
        entryFileNames: "hero-fx.bundle.js",
        assetFileNames: "hero-fx.[ext]",
        inlineDynamicImports: true,
      },
    },
  },
});
