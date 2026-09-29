# Aliali Telegram Mini App

## Boundary

The Mini App is the presentation layer. Authentication, authorization, module orchestration, evidence handling and security decisions remain server-side.

## Authentication

Telegram provides `Telegram.WebApp.initData` to the Mini App. The Aliali API validates its HMAC signature using the bot token and rejects stale or malformed payloads. `initDataUnsafe` is never used as an authentication source.

## API contract

- `GET /healthz` — liveness only.
- `POST /api/v1/session` — validates Telegram init data and returns the authenticated Telegram user plus capability flags.

The session endpoint is intentionally small in Phase 1. Network operations and other security-sensitive actions will be added only behind the existing authorization and execution policies.

## Deployment boundary

The frontend requires an HTTPS origin suitable for Telegram Mini Apps. The API is a separate HTTPS service. No production deployment or Telegram BotFather configuration is changed by this phase.
