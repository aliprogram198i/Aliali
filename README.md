# Aliali

Telegram Mini App + FastAPI service for a simple, authenticated network lookup.

## What the app does

When the Mini App opens, the user sees one field:

- **IP address** — looks up the public network/organization, ISP, ASN, domain and approximate location.
- **MAC address** — looks up the registered hardware vendor.

The backend performs the lookup on the server after validating Telegram Mini App initData.

Private IP ranges such as 10.0.0.0/8, 172.16.0.0/12 and 192.168.0.0/16 are not treated as public Internet addresses, so the app does not invent a network identity for them. citeturn0search1turn0search2

MAC lookup identifies the registered hardware vendor/OUI; a MAC address does not provide a public Internet network name. The implementation uses MACVendors' public lookup API for vendor identification. citeturn1search0turn1search5

## Runtime

- Frontend: React + Vite
- Backend: FastAPI
- Authentication: Telegram Mini App initData
- IP lookup: public IP/network metadata
- MAC lookup: vendor/OUI lookup
- No port scanning
- No network discovery
- No fabricated results

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
