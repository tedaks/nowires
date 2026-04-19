# NoWires — Agent Instructions

## Project Overview
Radio propagation analysis system using NTIA Irregular Terrain Model (ITM).
- **Backend**: Python/FastAPI at `apps/api/` with Numba JIT acceleration
- **Frontend**: Next.js 16 + TypeScript + Tailwind + MapLibre at `apps/web/`

## Commands

### Frontend
```bash
npm run dev:web          # Start Next.js dev server
npm run build:web        # Production build
npm run lint             # ESLint
npm run typecheck        # TypeScript check (tsc --noEmit)
npm run test:watch       # vitest watch mode
npm run test:e2e         # Playwright E2E tests
```

### Backend
```bash
npm run dev:api          # Start FastAPI dev server (uvicorn)
cd apps/api && pytest -v tests/            # Unit + API tests
cd apps/api && ruff check . && ruff format --check .   # Lint + format
```

### Full CI
```bash
npm run lint && npm run typecheck && npm run build:web
npm run dev:api & sleep 3 && npm run test:e2e
cd apps/api && ruff check . && ruff format --check . && pytest -v tests/
```

## Architecture
- `apps/api/app/main.py` — FastAPI app, endpoints `/api/p2p`, `/api/coverage`, `/api/coverage-radius`
- `apps/api/app/p2p.py` — Point-to-point link analysis
- `apps/api/app/coverage.py` — Coverage map computation with ProcessPoolExecutor + PNG cache
- `apps/api/app/coverage_radius.py` — Per-bearing coverage radius sweep
- `apps/api/app/coverage_workers.py` — ITM workers for coverage and radius
- `apps/api/app/coverage_render.py` — PNG rendering with signal legend
- `apps/api/app/math_kernels.py` — Numba JIT Fresnel profile + coverage coloring
- `apps/api/app/elevation_grid.py` — SRTM1/GLO30 terrain elevation + bilinear sampling
- `apps/api/app/elevation_fetch.py` — GLO30/SRTM1 rasterio fetching + API fallback
- `apps/api/app/itm_bridge.py` — pyitm library wrapper
- `apps/api/app/signal_levels.py` — dBm thresholds, colors, profile utilities
- `apps/api/app/terrain.py` — Haversine, bearing, profile generation
- `apps/api/app/antenna.py` — Antenna gain patterns
- `apps/web/src/components/map/MapView.tsx` — MapLibre GL map component
- `apps/web/src/components/p2p/` — P2P analysis panel + profile chart
- `apps/web/src/components/coverage/` — Coverage panel + sites panel + legend

## Environment Variables
Backend vars are in root `.env` (see `.env.example`). Key ones:
- `SRTM1_TILES_DIR` — SRTM1 GeoTIFF tiles directory
- `GLO30_TILES_DIR` — Copernicus GLO-30 tiles directory
- `LANDCOVER_DIR` — ESA WorldCover land cover tiles directory

Frontend vars are in `apps/web/.env.local` (see `apps/web/.env.local.example`):
- `BACKEND_URL` — Backend URL for Next.js proxy (default: http://127.0.0.1:8000)
- `DEV_ORIGINS` — Comma-separated allowed dev origins (e.g. `http://192.168.2.16:3000`). Next.js requires the `http://` prefix; `next.config.ts` auto-adds it if missing.

## Key Conventions
- Python: ruff for lint/format, Numba JIT for hot paths
- TypeScript: ESLint + strict mode, no any types
- Test files: `apps/api/tests/test_*.py`, `apps/web/e2e/*.spec.ts`
- API responses use snake_case, TypeScript types mirror the Python Pydantic models

## Strict Rules

### 300-Line File Limit
No source file shall exceed 300 lines. If a file reaches this limit, extract sub-components, utilities, or helpers into separate modules before adding more code.

### UI Components: shadcn + Tailwind Only
All UI components MUST use shadcn/ui primitives and Tailwind CSS utility classes exclusively. No custom UI primitives, no invented component patterns, no third-party UI libraries beyond shadcn. When a UI element is needed:
1. Check `apps/web/src/components/ui/` for existing shadcn components.
2. If missing, install via `npx shadcn@latest add <component>`.
3. If shadcn doesn't offer it, build it using Tailwind utilities on a native HTML element — never introduce another component library.
4. Never copy-paste shadcn code from external sources with modifications that deviate from the canonical shadcn pattern.
5. Styling must be Tailwind utility classes only — no inline styles, no CSS modules, no styled-components, no creative alternatives.