# Aliali Telegram Mini App

## Boundary

The Mini App is the presentation layer. Authentication, authorization, module orchestration, evidence handling and security decisions remain server-side.

## Authentication

Telegram provides `Telegram.WebApp.initData` to the Mini App. The Aliali API validates its HMAC signature using the bot token and rejects stale or malformed payloads. `initDataUnsafe` is never used as an authentication source.

## API contract

- `GET /healthz` — liveness only.
- `POST /api/v1/session` — validates Telegram init data and returns the authenticated Telegram user plus capability flags.
- `POST /api/v1/dashboard` — validates Telegram init data and returns the enabled module catalog, a registry-derived module summary, plus explicitly nullable operational metrics.

The dashboard is read-only in this phase. Asset/change/evidence metrics remain `null` until a real persistence/provider layer supplies them; the API never invents operational counts. The module summary is derived directly from the backend registry and contains only enabled-module counts and categories. Security-sensitive operations will be added only behind the existing authorization and execution policies.

## Running the API

From the repository root:

```bash
uvicorn aliali.api.server:app --host 0.0.0.0 --port 8000
```

The runtime must provide `BOT_TOKEN`. For a browser-based Mini App hosted on a different origin, set `MINI_APP_URL` to the exact HTTPS frontend origin.

## Deployment boundary

The frontend requires an HTTPS origin suitable for Telegram Mini Apps. The API is a separate HTTPS service. No production deployment or Telegram BotFather configuration is changed by this phase.
