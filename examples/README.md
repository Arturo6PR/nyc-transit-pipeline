# Example data

`mta_sample.pb64` is a base64-encoded GTFS-Realtime protobuf fixture. Keeping the fixture as text
makes it portable in Git while TransitPulse decodes it to the same raw bytes before parsing.

It contains three trip-stop predictions across routes A and B plus one maintenance alert. Its
timestamps and delays are synthetic, deterministic, and modeled after NYC subway data. It is not a
live MTA recording.

`gtfs_schedule/` contains matching static routes, trips, stops, and stop times plus the supporting
agency and service-calendar files. It exercises cross-file validation and includes a post-midnight
`25:00:00` service time. The directory can be ingested directly or packaged as a standard GTFS ZIP.
