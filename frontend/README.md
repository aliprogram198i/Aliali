# Aliali Telegram Mini App

React + Vite presentation layer for the Aliali Telegram Mini App.

## Development

1. Copy `.env.example` to `.env`.
2. Set `VITE_API_BASE_URL` to the HTTPS Aliali API origin.
3. Run `npm install` then `npm run dev`.

The production Mini App must be opened from Telegram. The backend validates `Telegram.WebApp.initData`; the frontend never treats `initDataUnsafe` as an authentication source.
