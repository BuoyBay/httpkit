# HTTPKit example

Run with the HTTPKit package available, then visit http://127.0.0.1:8080/hello/world.

The bundled HTTPServer binds all interfaces and exposes no bind-address selector.
This example serves plaintext HTTP without authentication. Restrict inbound port
8080 with your firewall before running it. A localhost URL alone does not restrict
the listening socket. Loopback binding requires a runtime API change.
