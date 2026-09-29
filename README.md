# Aliali

Cyber Security Operations Platform — modular, extensible, authorization-first security tooling.

## Interfaces

- **Telegram Bot** — entry point, notifications and quick actions.
- **Telegram Mini App** — React/Vite operational interface.
- **Aliali API** — FastAPI boundary for authenticated Mini App sessions and future module operations.

The Mini App is a presentation layer. Security-sensitive authorization, orchestration, evidence and execution remain server-side.

## Network Management

The Mini App groups enabled network modules under **إدارة الشبكات**. Authorized operators can submit an IP or MAC target for server-side validation; IP targets can also use reverse DNS and TCP connectivity checks. These operations require authenticated Telegram Mini App session data and execute from the API service's network context.

## Development

### Backend

```bash
pip install -e ".[dev]"
python -m pytest
python -m ruff check .
```

### Mini App

```bash
cd frontend
npm install
npm run build
```

Set `MINI_APP_URL` for the Telegram bot and `VITE_API_BASE_URL` for the frontend API origin.

Production deployments must be verified against the deployed commit and healthcheck before the release is considered complete.
