# Security Policy

Aliali is intended for defensive security operations, authorized testing, incident response, and lawful public-source investigation.

Do not use the project to access accounts, networks, devices, private records, or services without authorization.

Security-sensitive modules must:
- enforce an explicit authorization scope;
- record audit events;
- preserve evidence provenance;
- avoid storing secrets in source control;
- fail closed when authorization is missing or ambiguous.
