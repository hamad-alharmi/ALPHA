# Project ALPHA

Phase 2 adds an independent local Companion status service to the Phase 1 Core
foundation. Communication is authenticated HTTP on **127.0.0.1 only**.

## Install (Windows PowerShell)

From the repository root, with CPython **3.14.3** and the Python launcher installed:

```powershell
py -3.14 -c "import sys; assert sys.version_info[:3] == (3, 14, 3), sys.version"
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip --isolated install -r requirements-dev.lock
.\.venv\Scripts\python.exe -m pip --isolated install --no-build-isolation --no-deps -e .
.\.venv\Scripts\python.exe -m pip check
```

For an existing Phase 1 environment, repeat the two install commands to register the
new package and CLI. No activation or execution-policy change is needed. Build tools
are version-pinned; runtime and tests use only the standard library. Installation
needs PyPI access; running and testing do not.

## Foundation commands

```powershell
.\.venv\Scripts\python.exe -m alpha_core
.\.venv\Scripts\python.exe -m alpha_core health
```

These remain one-shot local commands and do not require a token. Foundation health
does not probe Companion. JSON application logs go to stderr; health JSON goes to stdout.

## Authentication and complete Windows demonstration

Generate a fresh 256-bit token locally and keep it in the current process environment.
The child below inherits that environment. The generated value is assigned, not
displayed or written into source, command arguments, or shell history. Run these
blocks in the **same PowerShell session**, from the repository root.

```powershell
$python = (Resolve-Path .\.venv\Scripts\python.exe).Path
$env:ALPHA_COMPANION_TOKEN = & $python -c "import secrets; print(secrets.token_urlsafe(32))"
$env:ALPHA_COMPANION_PORT = '8765'
$env:ALPHA_COMPANION_TIMEOUT = '3'
$env:ALPHA_ENV = 'development'
$env:ALPHA_LOG_LEVEL = 'INFO'
$companion = [System.Diagnostics.Process]::new()
$companion.StartInfo.FileName = $python
$companion.StartInfo.Arguments = '-m alpha_companion --shutdown-on-stdin'
$companion.StartInfo.UseShellExecute = $false
$companion.StartInfo.CreateNoWindow = $true
$companion.StartInfo.RedirectStandardInput = $true
[void]$companion.Start()
```

After initialization, check actual status (retry if startup is still in progress):

```powershell
& $python -m alpha_core companion-status
& $python -m alpha_core companion-status --json
```

Status reports the Companion PID, OS, installed ALPHA version, Python version,
protocol version, and increasing uptime. On Windows the venv launcher can spawn a
child interpreter, so the reported service PID may differ from `$companion.Id`.
Demonstrate authentication rejection without displaying either token:

```powershell
$savedToken = $env:ALPHA_COMPANION_TOKEN
try {
    $env:ALPHA_COMPANION_TOKEN = & $python -c "import secrets; print(secrets.token_urlsafe(32))"
    & $python -m alpha_core companion-status
    # Exit code 3: authentication rejected.
} finally {
    $env:ALPHA_COMPANION_TOKEN = $savedToken
    Remove-Variable savedToken
}
```

Stop cleanly, verify the offline error, and discard the session token:

```powershell
$companion.StandardInput.WriteLine('stop')
$companion.StandardInput.Close()
if (-not $companion.WaitForExit(5000)) { throw 'Companion did not stop within 5 seconds' }
$companion.ExitCode  # Expected: 0
& $python -m alpha_core companion-status
# Exit code 4: Companion cannot be reached.
$companion.Dispose()
Remove-Item Env:ALPHA_COMPANION_TOKEN
```

For interactive foreground use, launch `.\.venv\Scripts\python.exe -m alpha_companion`
with the configured environment and press **Ctrl+C** to stop. `--shutdown-on-stdin`
is for a supervising parent: a `stop` line or EOF requests shutdown. It is not a
network shutdown endpoint. Installed `alpha-core.exe` and `alpha-companion.exe`
entry points are also available under `.venv\Scripts`.

Tokens are session-local; generate a new token when restarting both processes.
`.env` files are not automatically loaded. Do not paste tokens into code, logs,
CLI arguments, committed files, or chat. Environment variables are not a vault:
same-user processes and administrators may inspect them. This link is for a trusted
local Windows session, not hostile multi-user or remote deployment.

## Configuration

| Variable | Default | Rules |
| --- | --- | --- |
| `ALPHA_ENV` | `development` | `development`, `test`, `production` |
| `ALPHA_LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `ALPHA_COMPANION_TOKEN` | Required for link | Generate with `secrets.token_urlsafe(32)`; 43–128 URL-safe characters |
| `ALPHA_COMPANION_PORT` | `8765` | Integer 1–65535; same in both processes |
| `ALPHA_COMPANION_TIMEOUT` | `3` | Finite socket timeout, 0.05–30 seconds; Core client |
| `ALPHA_COMPANION_HOST` | `127.0.0.1` | Any other value is rejected |

Unavailable ports produce a clear error. Choose another port for both processes;
do not change the address. High logging thresholds may suppress INFO lifecycle logs.

Core exit codes: 0 success, 1 unexpected failure, 2 configuration/usage error,
3 authentication failure, 4 connection failure, 5 timeout, 6 invalid response.
Companion uses 0 for clean shutdown, 1 unexpected failure, 2 invalid configuration,
and 4 unavailable port. Application errors are safe JSON logs on stderr.

## Tests and Windows process smoke test

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_companion_process.py -v
```

The second command runs a real independent Companion and separate Core CLI processes,
checks actual status/PID and wrong credentials, stops Companion gracefully, and
checks the offline error. It also checks EOF shutdown, occupied ports, and missing
tokens. This suite is included in the full suite. Tests generate ephemeral tokens
in memory and use free loopback ports; no real credentials or external services.
Connect-timeout classification is mocked deterministically; read timeouts and
malformed responses use actual loopback sockets.

## Boundaries and limitations

`src/alpha_core` owns the CLI/client; `src/alpha_companion` owns the service;
`src/alpha_interfaces` defines shared settings and contracts. X remains a placeholder;
Companion is the first headless building block for Y. See [architecture](docs/architecture.md).

Only `GET /v1/status` is supported. No TLS, remote access, automatic restart, Windows
service registration, GUI, model integration, Adaptive Skill Engine, screen capture,
keyboard/mouse control, Raspberry Pi communication, cloud hosting, database,
WebSockets, or background task automation is implemented.
