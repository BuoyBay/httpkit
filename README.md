# HTTP router — middleware, static responses, bundled HTTPServer

An additive router and middleware package over the bundled HTTPServer:
case-sensitive route captures and final wildcards, method-aware dispatch,
ordered middleware, SHA-256 ETags and bounded binary static responses.

## Install

From a Buoy consumer project with BPM installed:

```sh
bpm add httpkit --git https://github.com/BuoyBay/httpkit.git --rev refs/heads/main
```

BPM records the resolved commit in its lockfile. Keep that lockfile with the
consumer project for reproducible installs.
BPM also resolves `filesystemkit`.

## API entrypoints

- `HttpKitHandler.Handle(context As HttpKitContext)`
- `HttpKitServer`
- `Route(method, pattern, handler)`
- `Listen()`
- `RunLoop.Run()`

## Platform and scope

Requires the modified `HTTPServer-1.1.0-httpkit.1` compatibility archive, not just the installed original HTTPServer. See [toolchain requirements](TOOLCHAIN-REQUIREMENTS.md) before building.

## Build and API reference

Source is in `modules/`, with native/runtime inputs where required. Use the
[package guide](docs/API.md) for backend-specific build prerequisites, ownership
rules and supported targets. Rebuilding a native backend requires that target's
compiler and SDK; sealing an archive alone does not rebuild the backend.

## Local Buoy setup

On your own machine, install Buoy and run:

```sh
buoy ai init --both
```


## Contributing

[Contributing](CONTRIBUTING.md) · [License](LICENSE)
