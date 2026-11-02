# Python policy for httpkit

Python files are ignored by default. New production tooling belongs in Buoy or BuoyScript.

The following exact files remain temporary production compatibility exceptions:

| File | Required capability |
| --- | --- |
| `compat/build.py` | Builds the pinned HTTPServer compatibility archive required by HTTPKit; checks the upstream source digest before applying its framing patch. |

An exception may be removed after its native replacement passes the corresponding build or runtime checks.
Review additions file by file; directory-wide and wildcard Python exceptions are not allowed.
