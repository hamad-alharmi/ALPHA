# Phase 1 architecture

One Python distribution provides two packages with a `src` layout:

- `alpha_core`: environment configuration, logging, CLI startup, and local health.
- `alpha_interfaces`: standard-library-only shared data types. It cannot depend on Core, X, or Y.

Core depends on shared interfaces. Future X and Y adapters can depend on shared
interfaces without importing Core. The component directories contain documentation
only until those components are approved. Separate distributions can be considered
when independent deployment is required; no packaging split is needed yet.

Startup validates the environment, initializes JSON logging, checks local foundation
readiness, and exits. There is no background service or HTTP endpoint. Health output
is a local CLI result, not a promise that intelligence, memory, devices, or integrations
work. No external services, network connections, or persistent storage are involved.

Only ALPHA_ENV and ALPHA_LOG_LEVEL are read. No credential settings exist. Logs use
fixed messages or validated configuration error messages. Unexpected exceptions have
a generic error message; neither exception values nor tracebacks are logged. The
formatter is not a general-purpose secret redactor: future callers must not log secrets.

Exit codes: 0 success, 1 unexpected initialization failure, 2 invalid configuration
or CLI usage. Argument parsing uses argparse's ordinary text help/errors; application
events use JSON on stderr. Health JSON alone goes to stdout.

Deferred: autonomous computer control, Skill Builder, model APIs, memory implementation,
database schemas, WebSockets, hardware, desktop UI, and transport/authentication contracts.
