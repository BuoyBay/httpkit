---
title: "httpkit API contracts"
summary: "Usage and behavioral contracts for httpkit."
category: "Reference"
symbols: ["HttpKitContext", "HttpKitHandler", "HttpKitMiddleware", "HttpKitServer", "HttpKitStaticFiles"]
related: ["index.md", "getting-started.md", "typed-api.md"]
---

# HTTPKit 0.1.0

An additive router and middleware package over Buoy's bundled HTTPServer:
case-sensitive route captures and final wildcards, method-aware dispatch,
ordered middleware, SHA-256 ETags and bounded binary static responses.

## Dependencies and compatibility archive

Consumers must copy **all four** archives into their `packages/` directory:

- The `httpkit` package built from this repository.
- The `filesystemkit` package installed through the declared BPM dependency.
- `crypto-1.0.0.buipkg` from the Buoy installation.
- `HTTPServer-1.1.0-httpkit.1.buipkg`, the explicit local compatibility build.

Keep exactly one HTTPServer archive in a consumer. Buoy resolves by package name,
not by version priority. Do not also install the unpatched HTTPServer archive.
Import `httpkit`; its module imports the dependencies. The BPM manifest resolves the filesystem package; the compiler-supplied crypto
and explicit HTTPServer compatibility archives must be provisioned separately.

The compatibility builder reads the **installed** original archive, verifies the
HTTPServer source SHA-256, applies narrowly scoped response-framing changes, and
seals a distinct local archive. It never changes the installation or original
archive. An unfamiliar source version fails closed and requires patch review.

```sh
python3 compat/build.py --output packages/HTTPServer-1.1.0-httpkit.1.buipkg
/usr/bin/buoy pkg seal . -o packages/httpkit-0.1.0.buipkg
```

This compatibility archive contains a local framing patch; it does not imply an upstream HTTPServer fix. The source builder leaves the installed original archive unchanged.

## Router and handlers

Implement `HttpKitHandler.Handle(context As HttpKitContext)`. Construct
`HttpKitServer`, set its inherited port/limits/TLS configuration, register with
`Route(method, pattern, handler)`, and call `Listen()` followed by `RunLoop.Run()`.
The complete example defines a greeting handler.

The context exposes the original `Request` and `Response`, `Param(name)` as an
Optional String, and `Write(text)`. Write buffers the representation normally;
the compatibility serializer suppresses HEAD bytes while preserving its length.
Static HEAD responses explicitly set the selected representation length.

Supported method registration tokens are GET, HEAD, POST, PUT, PATCH, DELETE,
OPTIONS, and `*`. A GET route also handles HEAD; explicit HEAD takes priority
among equally specific patterns, followed by GET, then `*`. A matching path with
no compatible method returns 405 and Allow. A missing path returns 404.
OPTIONS is explicit; it is not synthesized.

`:name` captures one nonempty segment; a final `*name` captures the remaining
segments, including an empty tail. Paths are case-sensitive and trailing slashes
are significant except for the empty wildcard tail. Candidate specificity is
100 points per literal segment plus one per parameter; final wildcards add zero.
Method exactness breaks specificity ties and registration order breaks remaining
ties. This score rule is not the bundled router's positional precedence rule.
Duplicate capture names and empty capture names reject at registration.

HTTPKit dispatches through `OnNotFound` on its HTTPServer subclass. **Use Route,
not inherited Get/Post/Any/WebSocket registration:** inherited registrations
bypass HTTPKit middleware and routing. Route/middleware configuration freezes
permanently on the first Listen attempt, even after Close. Configure from one
thread before listening. SetCapture is available for adapters; application
handlers normally only read captures. Middleware Before runs before route
selection, so captures become available to the handler and After callbacks.

Request paths are already percent-decoded once by HTTPServer. HTTPKit rejects
control characters, percent signs, backslashes, query/fragment markers, colon
segments, dot/dot-dot segments, empty interior segments and paths over 8192
Unicode scalars. This deliberately restricts otherwise valid URL characters.
`%00` never reaches this check: the compatibility archive rejects it with 400
first. Under the original archive the decoded NUL and the rest of the path are
silently dropped (BUI-003), which is one more reason not to use that archive.
Query parameters remain available through the underlying request API.

## Middleware

Implement `HttpKitMiddleware.Before(context) As Boolean` and `After(context)`;
add instances using `server.Use(middleware)`. Before runs in registration order.
False skips later middleware and routing. After runs in reverse order for every
entered middleware, including the one that returned False. A handler/Before
exception still enters the Finally unwind; an After exception stops remaining
After calls and propagates to HTTPServer's error handling. If a handler threw
first, that original exception is replaced by the After exception, so
`OnUnhandledError` sees only the After failure; keep After callbacks non-throwing. HTTPServer discards the
failed response and emits its normal 500, so diagnostic After headers from failed
requests are not retained. Override OnUnhandledError for an application policy.

All callbacks run concurrently on HTTPServer connection threads. Instances are
retained by the server; shared mutable state requires application synchronization.
Do not call UI objects directly. Body buffering is per response; there is no
aggregate memory or concurrency budget.

## Entity tags

`HttpKitETag(bytes)` returns a quoted strong SHA-256 tag for exactly those bytes.
`HttpKitETagMatches(ifNoneMatch, etag)` performs case-sensitive opaque-tag matching,
accepts weak tags and comma-separated quoted lists, and recognizes `*`. The weak
prefix must be exactly `W/`; lowercase `w/` rejects. Invalid
request tag syntax returns False; invalid supplied expected tags throw
InvalidArgumentException. Whitespace inside opaque tags and embedded quotes or
controls reject; opaque commas are permitted. No normalization/case folding occurs.

`HttpKitNotModified(context, etag)` sets ETag and returns True after selecting 304
for a matching GET/HEAD condition. Return immediately when True. Other methods
receive ETag but no automatic status change; unsafe-method If-None-Match/412
semantics are application-owned. The helper supports neither If-Modified-Since nor
If-Range, and it must run before writing a response or flushing headers.

## Static files

`New HttpKitStaticFiles(root, captureName = "file", maxFileBytes = 8388608)`
implements HttpKitHandler. Register it at a route such as `/assets/*file` for GET.
HEAD falls back to GET. Constructor requires an existing real directory; its
configured ancestors are trusted. Missing files/directories return 404, encountered
symlinks/reparse points 403 (hard links are ordinary files and are served even
when they share an inode with a file outside the root), and files above the budget 413. The configurable budget
is 0..64 MiB; zero permits empty files. Permission/metadata failures return 404.
Read failures propagate to HTTPServer's error policy. No directory listing, index
lookup, MIME guessing or range responses occur.

Every component is inspected without following its final link, then the final
regular file is opened and read up to its checked length. Empty files produce
empty Bytes without a spurious EOF read. Responses use application/octet-stream,
X-Content-Type-Options: nosniff, Cache-Control: no-cache and a byte-derived ETag.
A matching conditional request returns 304; otherwise the exact buffered bytes
are sent. Each request rereads and hashes the asset.

**Use trusted, immutable asset trees.** Inspection and open are separate operations;
a concurrent attacker can replace a checked component with a link or special file.
This path-based implementation is not a race-resistant sandbox, and its file read
can block if the trusted tree is concurrently replaced. No guarantee is made for
mutable untrusted roots. The root may be relative and is interpreted against the
process working directory; avoid changing cwd after construction. FileSystemKit
rejects non-text native filenames.

## Platform requirements and limits

The installed Linux HTTPServer requires its bundled TLS archives to be linked,
even for plain HTTP. Ensure the extracted bundled Crypto wrapper, rather than a
same-named system library, is selected by the linker and native loader.

HTTPServer binds all interfaces; HTTPKit cannot select a loopback bind address or
expose remote addresses. Windows idle-timeout and upstream TLS certificate-chain
limitations remain. Use a reverse proxy when the application needs capabilities
that the underlying server lacks.
