# 01 — Project Scaffold

## What was built
The bare skeleton of the project: folder structure, tooling config, and the first screen you see in the browser. No search logic yet — just the foundation everything else sits on.

---

## The tools and why we chose them

### Vite
Vite is a build tool. Its job is to take your TypeScript and React files and turn them into plain HTML/CSS/JS the browser understands. It also runs a local development server so you can see changes instantly without refreshing.

Why Vite over the older Create React App? It's much faster. Vite serves files directly during development without bundling everything first. You feel this immediately — the dev server starts in under a second.

### React + TypeScript
React is a library for building UIs as components — reusable pieces of HTML/logic. TypeScript adds types to JavaScript, which catches bugs before you run the code and makes refactoring safer.

### Tailwind CSS
Instead of writing a separate `.css` file, you write styles directly on elements using class names (`bg-zinc-950`, `text-white`, `flex`, etc.). It sounds messy but it keeps styles co-located with the markup, making it very fast to build and easy to read.

We're using the new `@tailwindcss/vite` plugin (Tailwind v4) which integrates directly into the Vite build — no separate config file needed.

---

## Folder structure decisions

```
liner-labs/
├── public/data/        ← songs.json and index.json live here (served as static files)
├── scripts/            ← Python scripts that run locally, never deployed
├── src/                ← all React/TypeScript code
│   ├── types/          ← shared TypeScript type definitions
│   ├── lib/            ← pure logic (no React) — tokenizer, search algorithm
│   ├── components/     ← React UI components
│   └── hooks/          ← custom React hooks
└── learning/           ← you are here
```

**Why `public/data/` for JSON?** Files in `public/` are served as-is by the web server, not processed by Vite. This means the browser can fetch `songs.json` and `index.json` directly via URL. The React app loads them once on startup with a `fetch()` call.

**Why is `scripts/` separate from `src/`?** The Python scripts are a data-preparation tool, not part of the app. They run on your machine, produce JSON files, and are never deployed to the web server.

---

## What "build" means
When you run `npm run build`, Vite:
1. Compiles TypeScript → JavaScript
2. Bundles all `src/` files into a handful of optimised `.js` files
3. Outputs everything to `dist/`

You then host the `dist/` folder on any static hosting (Netlify, Vercel, GitHub Pages). The JSON files in `public/data/` get copied into `dist/data/` automatically.

---

## Key files created
- `vite.config.ts` — Vite config, registers React and Tailwind plugins
- `src/index.css` — single import line `@import "tailwindcss"` activates all utility classes
- `src/App.tsx` — shell UI (header + placeholder content)
- `scripts/fetch_lyrics.py` — data pipeline step 1: fetch from Genius API
- `scripts/build_index.py` — data pipeline step 2: build the inverted index
- `scripts/requirements.txt` — Python dependencies
- `scripts/.env.example` — template for your Genius API token

---

## If something breaks
- **Dev server won't start**: run `npm install` first. If still broken, delete `node_modules/` and run `npm install` again.
- **Tailwind classes not applying**: check that `src/index.css` has `@import "tailwindcss"` and that `main.tsx` imports `./index.css`.
- **TypeScript errors in the terminal**: these are warnings during dev, not crashes. Fix them before shipping.
