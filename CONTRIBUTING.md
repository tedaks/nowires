# Contributing to NoWires

Thank you for your interest in contributing to NoWires!

## Development Setup

```bash
# Clone the repository
git clone https://github.com/tedaks/nowires.git
cd nowires

# Install dependencies
pip install -r apps/api/requirements.txt
npm install

# Run development servers
npm run dev:web          # Frontend on http://localhost:3000
cd apps/api && python -m uvicorn app.main:app --reload  # Backend on http://localhost:8000
```

## Testing

```bash
# Frontend unit tests
npm --workspace apps/web run test

# Backend tests
cd apps/api && pytest -v tests/

# Lint and typecheck
npm run lint
npm --workspace apps/web run typecheck
cd apps/api && ruff check . && ruff format --check .
```

## Code Style

- **Python**: Follow [ruff](https://docs.astral.sh/ruff/) formatting and linting rules
- **TypeScript**: Strict mode, no `any` types, use ESLint
- **UI Components**: Use shadcn/ui primitives with Tailwind CSS only

## File Structure

- Backend source: `apps/api/app/`
- Frontend source: `apps/web/src/`
- Backend tests: `apps/api/tests/test_*.py`
- Frontend tests: `apps/web/src/lib/__tests__/*.test.ts`

## 300-Line Limit

No source file should exceed 300 lines. Extract helpers and utilities into separate modules when approaching this limit.

## Submitting Changes

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Make your changes and add tests
4. Ensure all tests pass
5. Commit with a clear message
6. Push and open a pull request
