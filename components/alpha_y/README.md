# ALPHA Y

Phase 2 implements the headless Companion in `src/alpha_companion` as an independent
Windows-compatible process. It exposes only authenticated loopback status through
the shared `alpha_interfaces` protocol. See the root README for exact commands.

There is no graphical desktop interface, screen capture, or computer control.
The service reuses existing Core configuration/logging helpers; it does not invoke
Core intelligence. UI framework and desktop integration remain deferred.
