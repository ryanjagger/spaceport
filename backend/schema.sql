-- Source of truth for the database. Applied on every startup by app/init_db.py.
-- Every statement is IF NOT EXISTS, so re-running it on an existing database is a no-op.
-- An edited constraint is NOT picked up by an existing table: reset the database instead.

CREATE EXTENSION IF NOT EXISTS btree_gist;

CREATE TABLE IF NOT EXISTS ships (
  id   integer PRIMARY KEY,
  name text NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS bookings (
  id           bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  ship_id      integer NOT NULL REFERENCES ships(id),
  pilot_name   text NOT NULL CHECK (char_length(btrim(pilot_name)) BETWEEN 1 AND 100),
  start_time   timestamptz NOT NULL,
  end_time     timestamptz NOT NULL,
  status       text NOT NULL DEFAULT 'active',
  created_at   timestamptz NOT NULL DEFAULT now(),
  cancelled_at timestamptz,
  CONSTRAINT valid_interval CHECK (end_time > start_time),
  CONSTRAINT valid_status CHECK (status IN ('active', 'cancelled')),
  -- R1 (no overlap) and R2 (30-minute refuel buffer) as one rule: extend every
  -- booking's end by 30 minutes and forbid the extended ranges from overlapping.
  -- tsrange of UTC values, not tstzrange: index expressions must be immutable,
  -- and timestamptz + interval is only stable.
  CONSTRAINT no_overlap_with_buffer EXCLUDE USING gist (
    ship_id WITH =,
    tsrange(
      start_time AT TIME ZONE 'UTC',
      (end_time AT TIME ZONE 'UTC') + interval '30 minutes',
      '[)'
    ) WITH &&
  ) WHERE (status = 'active')
);

-- The bookings list and nearest-dates look bookings up by start time across the fleet.
CREATE INDEX IF NOT EXISTS bookings_start_time_idx ON bookings (start_time);
