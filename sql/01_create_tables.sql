-- Part 1: Raw GTFS-RT payload storage
-- Used for replay, debugging, and auditing
CREATE TABLE IF NOT EXISTS gtfs_rt_raw (
  id BIGSERIAL PRIMARY KEY,
  feed_path TEXT NOT NULL,
  fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  http_status INTEGER NOT NULL,
  payload BYTEA,
  payload_size_bytes INTEGER,
  error TEXT
);

-- Part 2: Parsed trip updates
-- Populated after GTFS-RT parsing
CREATE TABLE IF NOT EXISTS trip_updates (
  id BIGSERIAL PRIMARY KEY,
  feed_path TEXT NOT NULL,
  fetched_at TIMESTAMPTZ NOT NULL,
  trip_id TEXT,
  route_id TEXT,
  stop_id TEXT,
  stop_sequence INTEGER,
  arrival_time BIGINT,
  arrival_delay INTEGER,
  departure_time BIGINT,
  departure_delay INTEGER
);

-- Part 3: Parsed alerts
CREATE TABLE IF NOT EXISTS alerts (
  id BIGSERIAL PRIMARY KEY,
  feed_path TEXT NOT NULL,
  fetched_at TIMESTAMPTZ NOT NULL,
  alert_id TEXT,
  cause TEXT,
  effect TEXT,
  header_text TEXT,
  description_text TEXT
);