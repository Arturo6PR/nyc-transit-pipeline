# Example feed

`mta_sample.pb64` is a base64-encoded GTFS-Realtime protobuf fixture. Keeping the fixture as text
makes it portable in Git while TransitPulse decodes it to the same raw bytes before parsing.

It contains three trip-stop predictions across routes A and B plus one maintenance alert. Its
timestamps and delays are synthetic, deterministic, and modeled after NYC subway data. It is not a
live MTA recording.
