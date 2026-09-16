# Security Policy

## Supported versions

Only the latest minor release is supported during the `0.x` phase.

## Reporting a vulnerability

Do not open a public issue. Use GitHub private vulnerability reporting for this repository. Include affected versions, reproduction steps, impact, and any suggested mitigation. Maintainers should acknowledge a report within five business days.

The service binds to localhost by default. Production deployments should configure `THAIDOC_API_KEY`, TLS at the reverse proxy, restricted artifact volumes, and a retention period appropriate to the data.

