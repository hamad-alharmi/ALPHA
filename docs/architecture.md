# ALPHA architecture: Phase 2

One Python distribution retains the `src` layout with three packages:

- `alpha_core`: environment configuration, logging, CLI startup, and local health.
- `alpha_interfaces`: standard-library-only shared data types. It cannot depend on Core, X, or Y.
- `alpha_companion`: independent headless process with authenticated loopback status.

Core and Companion depend on shared interfaces. Companion reuses Phase 1 Core's
configuration/error/logging helpers as infrastructure; it does not invoke the Core
CLI or intelligence. This preserves existing code without restructuring it. Shared
infrastructure can be extracted if independent distributions become necessary.
The component directories contain documentation; Companion is Y's first headless
building block. X hardware and the Y graphical interface remain deferred.

Core startup and health remain one-shot local commands requiring no link settings.
`companion-status` connects directly to 127.0.0.1 over HTTP; no proxy discovery or
redirect following. Companion runs until a shutdown request and serves only status.

The existing ALPHA_ENV and ALPHA_LOG_LEVEL settings remain. Link configuration adds
ALPHA_COMPANION_TOKEN, PORT, TIMEOUT, and HOST (each with the ALPHA_COMPANION_ prefix).
HOST must be exactly 127.0.0.1. Generate a 32-byte random token using secrets and
inherit it through the process environment. No credential files are created or loaded.
Validation checks token syntax/length, not entropy; use the documented generator.
Secrets are excluded from repr and never logged. Request/access logging is disabled;
errors never include request headers, response bodies, or raw exception details.

Core exit codes: 0 success, 1 unexpected failure, 2 configuration/usage error,
3 authentication failure, 4 connection failure, 5 timeout, 6 invalid response.
Companion returns 0 on clean shutdown, 1 unexpected failure, 2 configuration error,
4 bind failure. Application events use JSON stderr; argparse uses text help/errors.
Status uses human-readable stdout or JSON with --json.

## Protocol v1

`GET /v1/status` requires exactly one `Authorization: Bearer <token>` header.
Missing, incorrect, or duplicate credentials receive 401 with no status data;
authenticated unknown paths receive 404; unsupported methods receive 501.
Success is 200 with application/json, Content-Length, and Cache-Control: no-store.

| Field | Meaning |
| --- | --- |
| protocol_version | Integer 1 |
| component | alpha-companion |
| status | ok |
| pid | Positive OS process ID |
| platform | Runtime platform.system() |
| version | Installed alpha-foundation version |
| python_version | Runtime interpreter version |
| uptime_seconds | Nonnegative monotonic time since service construction |

The client rejects missing/extra fields, wrong types (including booleans used as
numbers), unsupported versions, nonfinite uptime, control characters, malformed
HTTP/JSON, wrong content types, redirects, truncated responses, and bodies over 8 KiB.
The protocol requires explicit Content-Length and no transfer coding. Incompatible
changes require a new version/path.

## Lifecycle and security limits

HTTPServer handles one request per connection, sequentially, with a 0.5-second
socket inactivity timeout. Its event loop polls for shutdown; Ctrl+C/SIGINT, SIGTERM,
and Windows SIGBREAK set a stop event. Supervised --shutdown-on-stdin mode stops on
a `stop` line or EOF. The listener closes on exit. Windows uses SO_EXCLUSIVEADDRUSE
to reject occupied ports. Force-killing is not a graceful shutdown.

Core's default three-second timeout accommodates Windows loopback refusal latency.
Timeouts apply to socket operations, not an absolute overall deadline; a deliberately
trickling peer may extend request duration. No retries are made. Connections always
close. Token comparisons use compare_digest.

This is plaintext HTTP for a trusted local session. It does not protect against
same-user/privileged malware, a malicious local listener stealing the configured
port, or determined local denial of service. Environment variables are not a vault.
Never expose or proxy the service to a network. No TLS, CORS, filesystem serving,
remote address selection, or command endpoint is provided.

## Validation

Phase 1 tests remain unchanged. New tests use real loopback sockets for authentication,
status, malformed responses, and read timeouts. Connect-timeout classification is
mocked deterministically. Independent-process tests verify the live Windows service
PID (which can differ from its venv launcher PID), Core CLI output, authentication
rejection, clean stdin/EOF shutdown, occupied ports, and offline errors.

See standard-library [HTTP client](https://docs.python.org/3.14/library/http.client.html)
and [HTTP server](https://docs.python.org/3.14/library/http.server.html) documentation.
This limited loopback service is not intended as a public production web server.

Deferred: autonomous computer control, Skill Builder, model APIs, memory implementation,
database schemas, WebSockets, hardware, desktop UI, cloud hosting, background tasks,
and remote transport/authentication contracts.
