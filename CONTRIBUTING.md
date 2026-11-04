# Contributing

## Development setup

1. Copy `.env.example` to `.env`.
2. Start the services with `docker compose up --build`.
3. Run backend tests with `cd backend && pytest`.
4. Run frontend checks with `cd frontend && npm run typecheck && npm run build`.

## Pull requests

- Explain the user-facing change and testing performed.
- Add or update tests for behavior changes.
- Keep provider-specific logic behind service interfaces.
- Do not commit `.env`, API keys, local databases, or generated media.
- Keep timestamp and grounding behavior covered.
