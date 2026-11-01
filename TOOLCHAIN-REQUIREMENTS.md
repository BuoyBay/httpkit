# HTTPKit toolchain requirements

BPM installs filesystemkit from BuoyBay. It does not download compiler-supplied packages.
The installed Buoy distribution must supply crypto 1.0.0 and the original HTTPServer 1.1.0
used by compat/build.py. HTTPKit runtime use remains blocked until the consumer explicitly
builds and installs HTTPServer-1.1.0-httpkit.1.buipkg as documented in README.md.
The unmodified installed HTTPServer is insufficient. Keep exactly one HTTPServer archive.
No BuoyBay HTTPServer or crypto repository is implied by this manifest.
