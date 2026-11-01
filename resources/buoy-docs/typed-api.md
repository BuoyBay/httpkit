---
title: "httpkit typed API"
summary: "Source-derived public signatures, properties, parameters, defaults, and return values."
category: "Reference"
order: 21
types: ["HttpKitContext", "HttpKitHandler", "HttpKitMiddleware", "HttpKitServer", "HttpKitStaticFiles"]
dependencies: []
symbols: ["HttpKitContext", "HttpKitHandler", "HttpKitMiddleware", "HttpKitServer", "HttpKitStaticFiles"]
related: ["api.md", "getting-started.md", "index.md"]
---

# httpkit typed API

Generated from the package source declarations. Platform guards are shown where present; inherited members are documented on the base type. See the [API contracts](api.md) for behavior and limitations.

## HttpKitContext

`Public Class HttpKitContext`

One request; route captures are separate from the bundled router's captures.

### Properties

| Name | Type | Read-Only | Shared | Default | Description |
| --- | --- | --- | --- | --- | --- |
| `Request` | `HttpRequest` | No | No | — | — |
| `Response` | `HttpResponse` | No | No | — | — |

### Constructor

`Public Sub Constructor(requestValue As HttpRequest, responseValue As HttpResponse)`

#### Parameters

| Name | Type | Passing | Default |
| --- | --- | --- | --- |
| `requestValue` | `HttpRequest` | `ByVal` | Required |
| `responseValue` | `HttpResponse` | `ByVal` | Required |

Returns: no value.

### Param

`Public Function Param(name As String) As Optional Of String`

#### Parameters

| Name | Type | Passing | Default |
| --- | --- | --- | --- |
| `name` | `String` | `ByVal` | Required |

#### Returns

| Type |
| --- |
| `Optional Of String` |

### SetCapture

`Public Sub SetCapture(name As String, captured As String)`

#### Parameters

| Name | Type | Passing | Default |
| --- | --- | --- | --- |
| `name` | `String` | `ByVal` | Required |
| `captured` | `String` | `ByVal` | Required |

Returns: no value.

### Write

`Public Sub Write(text As String)`

The compatibility serializer computes HEAD length and suppresses its body.

#### Parameters

| Name | Type | Passing | Default |
| --- | --- | --- | --- |
| `text` | `String` | `ByVal` | Required |

Returns: no value.

## HttpKitHandler

`Public Interface HttpKitHandler`

### Handle

`Sub Handle(context As HttpKitContext)`

#### Parameters

| Name | Type | Passing | Default |
| --- | --- | --- | --- |
| `context` | `HttpKitContext` | `ByVal` | Required |

Returns: no value.

## HttpKitMiddleware

`Public Interface HttpKitMiddleware`

### Before

`Function Before(context As HttpKitContext) As Boolean`

False short-circuits routing. After still runs for this middleware.

#### Parameters

| Name | Type | Passing | Default |
| --- | --- | --- | --- |
| `context` | `HttpKitContext` | `ByVal` | Required |

#### Returns

| Type |
| --- |
| `Boolean` |

### After

`Sub After(context As HttpKitContext)`

#### Parameters

| Name | Type | Passing | Default |
| --- | --- | --- | --- |
| `context` | `HttpKitContext` | `ByVal` | Required |

Returns: no value.

## HTTPKit functions

### HttpKitETagMatches

`Public Function HttpKitETagMatches(ifNoneMatch As String, etag As String) As Boolean`

HTTP helpers use case-sensitive entity tags and RFC 9110 weak matching for GET/HEAD.

#### Parameters

| Name | Type | Passing | Default |
| --- | --- | --- | --- |
| `ifNoneMatch` | `String` | `ByVal` | Required |
| `etag` | `String` | `ByVal` | Required |

#### Returns

| Type |
| --- |
| `Boolean` |

### HttpKitETag

`Public Function HttpKitETag(data As Bytes) As String`

Strong SHA-256 validator of exactly the supplied representation bytes.

#### Parameters

| Name | Type | Passing | Default |
| --- | --- | --- | --- |
| `data` | `Bytes` | `ByVal` | Required |

#### Returns

| Type |
| --- |
| `String` |

### HttpKitNotModified

`Public Function HttpKitNotModified(context As HttpKitContext, etag As String) As Boolean`

Set the validator; return True after producing a bodyless 304 for GET/HEAD.

#### Parameters

| Name | Type | Passing | Default |
| --- | --- | --- | --- |
| `context` | `HttpKitContext` | `ByVal` | Required |
| `etag` | `String` | `ByVal` | Required |

#### Returns

| Type |
| --- |
| `Boolean` |

## HttpKitServer

`Public Class HttpKitServer Inherits HTTPServer`

A configure-before-Listen router with ordered, short-circuiting middleware.

### Listen

`Public Overrides Sub Listen()`

No parameters.

Returns: no value.

### Use

`Public Sub Use(middleware As HttpKitMiddleware)`

#### Parameters

| Name | Type | Passing | Default |
| --- | --- | --- | --- |
| `middleware` | `HttpKitMiddleware` | `ByVal` | Required |

Returns: no value.

### Route

`Public Sub Route(method As String, pattern As String, handler As HttpKitHandler)`

:name captures one segment; final *name captures zero or more segments.

#### Parameters

| Name | Type | Passing | Default |
| --- | --- | --- | --- |
| `method` | `String` | `ByVal` | Required |
| `pattern` | `String` | `ByVal` | Required |
| `handler` | `HttpKitHandler` | `ByVal` | Required |

Returns: no value.

### OnNotFound

`Public Overrides Sub OnNotFound(request As HttpRequest, response As HttpResponse)`

#### Parameters

| Name | Type | Passing | Default |
| --- | --- | --- | --- |
| `request` | `HttpRequest` | `ByVal` | Required |
| `response` | `HttpResponse` | `ByVal` | Required |

Returns: no value.

## HttpKitStaticFiles

`Public Class HttpKitStaticFiles Implements HttpKitHandler`

Bounded whole-file responses; no directory listings or implicit index files.

### Constructor

`Public Sub Constructor(root As String, captureName As String = "file", maxFileBytes As Integer = 8388608)`

#### Parameters

| Name | Type | Passing | Default |
| --- | --- | --- | --- |
| `root` | `String` | `ByVal` | Required |
| `captureName` | `String` | `ByVal` | `"file"` |
| `maxFileBytes` | `Integer` | `ByVal` | `8388608` |

Returns: no value.

### Handle

`Public Sub Handle(context As HttpKitContext)`

#### Parameters

| Name | Type | Passing | Default |
| --- | --- | --- | --- |
| `context` | `HttpKitContext` | `ByVal` | Required |

Returns: no value.
