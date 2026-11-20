import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: path.resolve(import.meta.dirname, ".."),
    emptyOutDir: false,
    lib: {
      entry: path.resolve(import.meta.dirname, "src/main.jsx"),
      name: "FlawdHeroFx",
      formats: ["iife"],
      fileName: () => "hero-fx.bundle.js",
    },
    rollupOptions: {
      output: {
        inlineDynamicImports: true,
        assetFileNames: "hero-fx.[ext]",
      },
    },
    cssCodeSplit: false,
    sourcemap: false,
    minify: true,
  },
});
