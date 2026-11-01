---
title: "HTTPKit getting started"
summary: "Required archives and explicit HTTPServer compatibility setup."
category: "Guide"
related: ["index.md", "api.md", "typed-api.md"]
---

# Getting started

Install httpkit, filesystemkit, crypto and the explicit HTTPServer-1.1.0-httpkit.1 compatibility archive together. Keep exactly one HTTPServer archive in the consumer. Import httpkit. The compatibility archive is built from the installed original by compat/build.py; it leaves the installation unchanged.

Read [API contracts](api.md) for the complete build commands, dependency paths, middleware lifecycle and static-root limitations before running a server.
