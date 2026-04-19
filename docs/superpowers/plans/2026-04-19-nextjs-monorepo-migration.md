# Next.js Monorepo Migration Plan

Date: 2026-04-19
Branch: `frontend` (new, cut from `pre-frontend`; merges to `master` on success)

## 1. Goals & Constraints

- Convert the repo into a true monorepo with npm workspaces.
- New layout: `apps/web` (Next.js 15, App Router, TypeScript, shadcn/ui + Tailwind), `apps/api` (existing FastAPI, moved as-is).
- **Backend code is untouched except for one surgical edit** to make `FRONTEND_DIR` env-overridable (see §2, §4 Phase 1). No route, handler, schema, dependency, or logic changes.
- Port the existing vanilla-JS SPA (`frontend/app.js`, `frontend/index.html`, `frontend/styles.css`) into Next.js App Router components: MapLibre map, P2P tab, Coverage tab, multi-site overlay panel, profile chart.
- Package manager: npm. Router: App Router. TS: yes.
- Follow Next.js project structure from https://nextjs.org/docs/app/getting-started/project-structure.

## 2. Current-State Audit (verified, not assumed)

- Root is one git repo (branch `pre-frontend`; `master` also exists). No workspaces, no top-level `package.json` — only a stub `package-lock.json` and an accidental `node_modules/` under `frontend/`.
- `frontend/` contents: `index.html`, `app.js` (804 lines), `styles.css` (245 lines), leftover `.next/`, `next-env.d.ts`, `tsconfig.tsbuildinfo`, and a **nested `.git`** pointing at `refs/heads/master` (likely accidental — will be removed; tracking stays in the outer repo on branch `frontend`).
- Frontend loads MapLibre 4.7.1 and Plotly 2.35.2 from CDN; calls backend via same-origin `fetch('/api/...')`.
- Backend ([backend/app/main.py](backend/app/main.py)): FastAPI, uvicorn on `0.0.0.0:8000`. Routes:
  - `GET /` → serves `frontend/index.html`
  - `POST /api/p2p`
  - `POST /api/coverage`
  - `POST /api/coverage-radius`
  - `GET /static/*` → mounts `frontend/` as static
- The backend's `FRONTEND_DIR` is computed as `Path(__file__).resolve().parent.parent.parent / "frontend"`. After `git mv backend apps/api`, that resolves to `/repo/apps/frontend` (one directory deeper than before), which does not exist — breaking `GET /` and `/static/*`. **Fix: one three-line surgical edit** to [apps/api/app/main.py](apps/api/app/main.py) making the path env-overridable (details in §4 Phase 1). No other backend change.

## 3. Target Layout

```
nowires/
  package.json                # workspaces: ["apps/*"]
  package-lock.json
  .nvmrc                      # node 20 (LTS)
  .gitignore                  # updated (node_modules, .next, .turbo)
  tsconfig.base.json          # shared compiler opts
  apps/
    web/                      # Next.js 15, App Router
      package.json
      next.config.ts
      tsconfig.json
      postcss.config.mjs
      tailwind.config.ts
      components.json         # shadcn config
      next-env.d.ts
      .env.local              # NEXT_PUBLIC_* + BACKEND_URL
      public/
      src/
        app/
          layout.tsx
          page.tsx            # main SPA entry
          globals.css
        components/
          map/
            MapView.tsx       # MapLibre wrapper (client component)
            useMap.ts
          p2p/
            P2PPanel.tsx
            ProfileChart.tsx  # Plotly wrapper (dynamic import, ssr: false)
            P2PResult.tsx
          coverage/
            CoveragePanel.tsx
            SitesPanel.tsx
            Legend.tsx
          ui/                 # shadcn-generated primitives
        lib/
          api.ts              # typed fetch wrappers for /api/*
          types.ts            # shared P2PRequest/Response, Coverage* types
          site.ts             # CoverageSite class / helpers
          utils.ts            # fnum/fint, color constants, mode labels
        hooks/
          useP2P.ts
          useCoverage.ts
    api/                      # moved from top-level backend/
      app/                    # unchanged
      tests/                  # unchanged
      requirements.txt        # unchanged
      __init__.py             # unchanged
  data/                       # unchanged
  docs/                       # unchanged
  scripts/                    # unchanged
```

Rationale: a single `apps/web` is sufficient today. `packages/` is omitted — add it only when a shared package actually materializes.

## 4. Step-by-Step Plan

### Phase 0 — Branch and safety

1. From `pre-frontend`: `git checkout -b frontend`.
2. Remove accidental `frontend/.git` directory (it is not a submodule — no entry in `.gitmodules`; just `rm -rf frontend/.git`). Verify outer-repo status is clean and `frontend/` contents become tracked normally.
3. Delete stale build artifacts from `frontend/`: `.next/`, `node_modules/`, `next-env.d.ts`, `tsconfig.tsbuildinfo`, `frontend/.gitignore` (will be recreated in `apps/web`). Move the three source files (`index.html`, `app.js`, `styles.css`) to `tmp-legacy/` at the repo root for reference during the port. `tmp-legacy/` is deleted at the end of Phase 4 in the same PR. Add `tmp-legacy/` to `.gitignore`? No — track it so reviewers can see the reference, then remove it in the final commit of the PR.
4. Delete the stub top-level `package-lock.json` — it will be regenerated.

### Phase 1 — Relocate backend (path-only move, no content edits)

5. `git mv backend apps/api`. Confirm zero content diff (`git diff -- apps/api` should show only renames).
6. **Surgical backend edit** — [apps/api/app/main.py](apps/api/app/main.py), replace the single `FRONTEND_DIR = PROJECT_DIR / "frontend"` line with an env-overridable form. Add `import os` to the existing stdlib imports at the top (already imported — verify). The change:
   ```python
   # before
   FRONTEND_DIR = PROJECT_DIR / "frontend"
   # after
   FRONTEND_DIR = Path(os.environ.get("FRONTEND_DIR", PROJECT_DIR / "frontend"))
   ```
   Default behavior is preserved when the env var is unset. For the moved layout, set `FRONTEND_DIR=/abs/path/to/repo/frontend` (or wherever the legacy HTML is served from) in the backend process environment. If nothing should be served there post-migration, leave `FRONTEND_DIR` pointing at an empty directory — `/` and `/static` will return cleanly instead of crashing, and no other change is needed.
7. Verify backend still runs from the new path:
   ```
   cd apps/api && python -m uvicorn app.main:app --reload --port 8000
   ```
   Confirm `POST /api/p2p` still responds.
8. Update any non-code references to `backend/`: `README.md`, `scripts/*`, `docs/*`.

### Phase 2 — Monorepo scaffold

9. Write root `package.json`:
   ```json
   {
     "name": "nowires",
     "private": true,
     "workspaces": ["apps/*"],
     "scripts": {
       "dev:web": "npm --workspace apps/web run dev",
       "build:web": "npm --workspace apps/web run build",
       "lint": "npm --workspace apps/web run lint"
     }
   }
   ```
10. Add `.nvmrc` (`20`), root `tsconfig.base.json` (strict, `moduleResolution: "bundler"`, `jsx: "preserve"`, `target: "ES2022"`), and update root `.gitignore` to add `node_modules/`, `.next/`, `.turbo/`, `*.tsbuildinfo`, `.env*.local`.

### Phase 3 — Scaffold `apps/web`

11. Create Next.js app via official initializer, inside the workspace, without overwriting the monorepo root:
    ```
    npx create-next-app@latest apps/web \
      --ts --app --tailwind --eslint --src-dir \
      --import-alias "@/*" --no-turbopack --use-npm
    ```
12. Initialize shadcn/ui inside `apps/web`:
    ```
    cd apps/web && npx shadcn@latest init
    ```
    Accept defaults (App Router, base color, CSS variables). Generate the primitives actually needed for the port: `button`, `input`, `label`, `tabs`, `card`, `slider`, `checkbox`, `select`, `separator`, `badge`. Install only what the UI uses — no speculative additions.
13. Install runtime deps in `apps/web`:
    - `maplibre-gl` (replace CDN script)
    - `plotly.js-basic-dist-min` + `react-plotly.js` (basic build is sufficient — the existing chart only uses `scatter`)
    - `@types/react-plotly.js` (dev)
14. Configure API proxy in `apps/web/next.config.ts`:
    ```ts
    const BACKEND = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";
    export default {
      async rewrites() {
        return [{ source: "/api/:path*", destination: `${BACKEND}/api/:path*` }];
      },
    };
    ```
    Add `.env.local.example` with `BACKEND_URL=http://127.0.0.1:8000`. This keeps the frontend's `fetch('/api/...')` calls working unchanged and avoids any backend CORS/change.

### Phase 4 — Port the SPA into React components

The port is mechanical — preserve behavior and wire identifiers. Do not redesign.

15. **Types** (`src/lib/types.ts`): mirror the Pydantic request bodies used by `app.js`:
    - `P2PRequest` / `P2PResponse` (profile points, horizons, flags, link_budget, mode)
    - `CoverageRequest` / `CoverageResponse` (png_base64, bounds, legend, stats, rx_sensitivity_dbm, eirp_dbm, from_cache)
    - `CoverageRadiusResponse` (avg_radius_km, min_radius_km, max_radius_km)
    - Derive shapes from [backend/app/main.py:48-96](apps/api/app/main.py) (after move) and the usage sites in [frontend/app.js](frontend/app.js).
16. **API layer** (`src/lib/api.ts`): three typed async functions (`postP2P`, `postCoverage`, `postCoverageRadius`). No `API_BASE` prefix — relative `/api/...` goes through the rewrite.
17. **MapView** (`src/components/map/MapView.tsx`, `"use client"`): owns the MapLibre map instance, hillshade + OSM layers, `path-line` and `horizons` sources, and click handling. Exposes imperative methods via `useImperativeHandle` (`drawPath`, `drawHorizons`, `addCoverageOverlay`, `addSiteLayer`, `removeSiteLayer`, `setSiteVisibility`, `setSiteOpacity`). Accepts `onMapClick(lngLat)` callback.
18. **ProfileChart** (`src/components/p2p/ProfileChart.tsx`): dynamic-import `react-plotly.js` with `ssr: false`, wired to `plotly.js-basic-dist-min` via `createPlotlyComponent`. Port `renderProfileChart` trace construction verbatim.
19. **P2PPanel**: form inputs (shadcn `Input`/`Label`), Analyze button, result card. On submit → `postP2P` → call `MapView.drawPath`/`drawHorizons`, render `P2PResult`, feed `ProfileChart`.
20. **CoveragePanel**: TX selector (click-driven), antenna pattern select, compute-radius button, generate button (with the animated-dots behavior from `runCoverage`), result stats card, opacity slider.
21. **SitesPanel**: port `CoverageSite`, `SITE_COLORS`, `sitesCoverage`, `addSiteLayer`/`removeSiteLayer`/visibility/opacity handlers, aggregate stats. Held in a React context or `useReducer` so both the coverage panel and the sites panel can mutate it.
22. **Tabs wiring** (`src/app/page.tsx`): shadcn `Tabs` with `p2p`/`coverage`. Switching tabs clears TX/RX markers (matches `setupTabs`).
23. **Styles**: rewrite `frontend/styles.css` into `globals.css` + Tailwind utility classes where trivial; keep bespoke map/panel CSS under `globals.css`. Visual parity is the bar — no redesign.
24. Delete the legacy `frontend/` directory and the `tmp-legacy/` reference folder once the port reaches parity (final commit of this PR).

### Phase 5 — Verify

25. `npm install` at repo root — confirm workspace resolution.
26. Start backend: `cd apps/api && python -m uvicorn app.main:app --port 8000`.
27. Start web: `npm run dev:web` → `http://localhost:3000`.
28. Manual test matrix (browser):
    - P2P: place TX then RX, click Analyze, confirm path line, horizons, profile chart, link-budget card match legacy behavior against the same inputs.
    - Coverage: select TX, compute radius (note: 1–2 min), generate coverage, confirm PNG overlay, legend, stats, cache hit on re-run.
    - Multi-site: save 2+ sites, toggle visibility, slide opacity, delete, clear all.
    - Tab switch clears markers.
29. `npm run build:web` succeeds. `npm run lint` clean.
30. No behavior regression against a baseline captured before the port (suggest: screenshot + one recorded P2P run + one coverage run from `pre-frontend`).

### Phase 6 — Land

31. Open PR `frontend` → `master`. PR body lists: structural moves, deleted files, new deps, manual-test evidence, the single surgical `FRONTEND_DIR` edit in `apps/api/app/main.py`.
32. Squash-merge after review.

## 5. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Plotly bundle bloat on client | Use `plotly.js-basic-dist-min` if `scatter` is sufficient; dynamic-import with `ssr: false`. |
| MapLibre SSR errors | Component is `"use client"`; map instance created in `useEffect`. |
| CORS on the backend after split | Avoided entirely via Next.js `rewrites()` (same-origin to the browser). |
| State sprawl porting globals (`txMarker`, `sitesCoverage`, etc.) | Scope to component state + one small context for multi-site; no Redux/Zustand unless it proves necessary. |
| Hidden coupling to legacy DOM ids (`'tx-coords'`, etc.) | Replaced with React state — ids are cosmetic. |
| Accidental nested `.git` removal losing work | Verify `git -C frontend log` shows only commits already present in the outer repo before `rm -rf`. If divergent, stop and surface to user. |

## 6. Out of Scope

- Any backend code change (including adding CORS, fixing `FRONTEND_DIR`, or deleting the `/` and `/static` routes).
- Turborepo, pnpm, or yarn adoption.
- Adding tests for the web app (can be a follow-up).
- Docker / deployment config.
- Auth, i18n, analytics.

## 7. Rollback

Branch is isolated. If the port fails, abandon `frontend` and keep `pre-frontend`/`master` untouched. The backend move is a pure `git mv` and is reverted by checking out `master`.

## 8. Estimated Effort

- Phases 0–3 (scaffold): ~1 session.
- Phase 4 (port): ~2–3 sessions, dominated by MapView + Coverage/Sites fidelity.
- Phase 5 (verify): ~0.5 session.

## 9. Resolved Decisions

All pre-execution open items are resolved:

1. **Backend `/` and `/static` breakage** — resolved via a 3-line surgical edit in [apps/api/app/main.py](apps/api/app/main.py) making `FRONTEND_DIR` env-overridable (§4 Phase 1, step 6). Default behavior preserved.
2. **Legacy source files** — moved to `tmp-legacy/` at repo root during the port; deleted in the final commit of this PR (§4 Phase 0 step 3, Phase 4 step 24).
3. **Plotly bundle** — use `plotly.js-basic-dist-min` (scatter-only, ~1MB) since the existing chart only uses `scatter` (§4 Phase 3 step 13, Phase 4 step 18).
4. **`packages/` workspace** — omitted; `package.json` uses `"workspaces": ["apps/*"]` (§3, §4 Phase 2 step 9). Add `packages/` only when a shared package materializes.
