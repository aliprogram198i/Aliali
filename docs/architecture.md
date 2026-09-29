# Aliali Architecture

Aliali is designed as a modular security operations platform.

## Layers

- **Bot/UI**: Telegram presentation and callback routing.
- **Core**: module registry, authorization context, cases, evidence, audit, reporting.
- **Platform modules**: Facebook, Instagram, Telegram, WhatsApp, YouTube, TikTok.
- **Network modules**: asset discovery, device classification, IoT/camera indicators, exposure assessment, topology.
- **Identity intelligence**: lawful public-source phone/domain/email intelligence.
- **Data layer**: persistent cases, findings, evidence metadata and audit events.

## Module contract

Every functional capability is a module with a stable key, metadata, input contract and structured result. Modules must not bypass the authorization boundary.

## Safety boundary

Network active scanning, account actions, or access to non-public data require explicit authorization and appropriate credentials. Public-source analysis must preserve source, timestamp and confidence rather than treating correlation as proof.

## Extensibility

New modules are registered through the module registry rather than hard-coded into the main handler. This keeps the Telegram UI, orchestration and platform integrations decoupled.
