# Aliali

Telegram Mini App + FastAPI service for evidence-first reverse phone intelligence.

## What the app does

The Mini App authenticates through Telegram Mini App initData, then analyzes a phone number using public numbering-plan metadata.

The result separates:

- Number validity, possibility, type, country/region, carrier metadata, geographic area and possible time zones.
- Verified/public identity evidence, when an authorized or public source actually provides it.
- Current device location, which remains unavailable unless a separate authorized live-location source exists.
- Social-platform verification, which is never inferred from the phone number alone.
- Evidence coverage, source registry, consistency checks, known/unknown facts and a request-scoped social evidence ledger.

## Social verification architecture

Social checks use isolated provider adapters behind a deterministic provider registry.

Current providers:

- WhatsApp — authorized-provider boundary, disabled until an authorized integration is configured.
- Telegram — authorized-provider boundary, disabled until an authorized integration is configured.
- Signal — authorized-provider boundary, disabled until an authorized integration is configured.
- LinkedIn — public-association boundary, disabled until a documented public association source is configured.

The application does not scrape platforms, enumerate accounts, use leaked/private datasets, guess identifiers, or convert an unavailable provider into a negative account claim.

The evidence ledger is request-scoped and contains provider result evidence only; it does not store the queried phone number.

Provider registrations also carry bounded-client policy metadata (timeout_seconds and max_calls_per_minute). Actual third-party adapters must enforce their own network timeout and authorization requirements before being enabled.

## AI layer

AI analysis is optional and disabled by default. When enabled, it receives sanitized evidence rather than unrestricted identifying data and cannot be used to infer a person's identity, private accounts, address, or current device location.

## Runtime

- Frontend: React + Vite
- Backend: FastAPI
- Authentication: Telegram Mini App initData plus short-lived Aliali session tokens
- Phone metadata: phonenumbers / libphonenumber metadata
- Social verification: authorized/public evidence only
- No port scanning
- No network discovery
- No fabricated results
- No raw phone-number persistence

## Development

### Backend

    pip install -e ".[dev]"
    python -m pytest
    python -m ruff check .

### Mini App

    cd frontend
    npm install
    npm run build

Set MINI_APP_URL for the API CORS origin and VITE_API_BASE_URL for the frontend API origin.

## Output guarantees

The service distinguishes evidence from unknowns. Number metadata does not become identity, carrier metadata does not become a live device location, and an unavailable social provider does not become a claim that an account does not exist.
