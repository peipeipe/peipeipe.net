-- IP addresses, query strings and referrers are never stored.
CREATE TABLE views (
  day TEXT NOT NULL,
  visitor TEXT NOT NULL,
  path TEXT NOT NULL,
  country TEXT NOT NULL,
  region TEXT NOT NULL,
  city TEXT NOT NULL,
  pv INTEGER NOT NULL DEFAULT 1,
  first_seen INTEGER NOT NULL,
  last_seen INTEGER NOT NULL,
  PRIMARY KEY (day, visitor, path)
) WITHOUT ROWID;

-- Durable outbox. A lease prevents concurrent cron executions sending together.
CREATE TABLE notifications (
  id TEXT PRIMARY KEY,
  day TEXT NOT NULL,
  content TEXT NOT NULL,
  state TEXT NOT NULL DEFAULT 'pending',
  lease_until INTEGER NOT NULL DEFAULT 0,
  attempts INTEGER NOT NULL DEFAULT 0,
  next_attempt INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX notification_due ON notifications(state, next_attempt);
