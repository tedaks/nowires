# NoWires — Agent Instructions

## Project Overview
Radio propagation analysis system for the Philippines using NTIA Irregular Terrain Model (ITM).
- **Backend**: Python/FastAPI at `apps/api/` with Numba JIT acceleration
- **Frontend**: Next.js 16 + TypeScript + Tailwind + MapLibre at `apps/web/`

## Commands

### Frontend
```bash
npm run dev:web          # Start Next.js dev server
npm run build:web        # Production build
npm run lint             # ESLint
npm run typecheck        # TypeScript check (tsc --noEmit)
npm run test:e2e         # Playwright E2E tests
```

### Backend
```bash
cd apps/api
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000   # Dev server
pytest -v tests/                                                # Unit + API tests
ruff check .                                                    # Lint
ruff format --check .                                           # Format check
```

### Full CI
```bash
cd apps/web && npm run lint && npm run typecheck && npm run build
cd apps/api && ruff check . && ruff format --check . && pytest -v tests/
```

## Architecture
- `apps/api/app/main.py` — FastAPI app, endpoints `/api/p2p`, `/api/coverage`, `/api/coverage-radius`
- `apps/api/app/p2p.py` — Point-to-point link analysis
- `apps/api/app/coverage.py` — Coverage map computation with process pool
- `apps/api/app/math_kernels.py` — Numba JIT Fresnel profile + coverage coloring
- `apps/api/app/elevation_grid.py` — SRTM1/GLO30 terrain elevation
- `apps/api/app/itm_bridge.py` — ITM library wrapper
- `apps/web/src/components/map/MapView.tsx` — MapLibre GL map component
- `apps/web/src/components/p2p/` — P2P analysis panel + profile chart
- `apps/web/src/components/coverage/` — Coverage panel + multi-site panel

## Environment Variables
See `.env.example` for all variables. Key ones:
- `SRTM1_TILES_DIR` — SRTM1 GeoTIFF tiles directory
- `GLO30_TILES_DIR` — Copernicus GLO-30 tiles directory
- `LANDCOVER_DIR` — ESA WorldCover land cover tiles directory
- `DEV_ORIGINS` — Comma-separated Next.js allowed dev origins (for HMR from other devices)
- `BACKEND_URL` — Backend URL for Next.js proxy (default: http://127.0.0.1:8000)

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