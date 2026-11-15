-- Version 1: additive, explicit initialization only. No destructive statements.
CREATE TABLE IF NOT EXISTS schema_versions (version integer PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS users (
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 username text NOT NULL UNIQUE, password_hash text NOT NULL,
 role text NOT NULL CHECK (role IN ('admin','staff','viewer','driver')),
 active boolean NOT NULL DEFAULT true, failed_attempts integer NOT NULL DEFAULT 0,
 locked_until timestamptz
);
CREATE TABLE IF NOT EXISTS auth_sessions (
 token_hash text PRIMARY KEY, user_id bigint NOT NULL REFERENCES users(id),
 expires_at timestamptz NOT NULL
);
CREATE TABLE IF NOT EXISTS orders (
 id text PRIMARY KEY, payload jsonb NOT NULL, confirmed jsonb,
 status text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','confirmed','rejected')),
 version integer NOT NULL DEFAULT 1 CHECK (version > 0),
 created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS orders_status_created ON orders(status, created_at);
CREATE TABLE IF NOT EXISTS customers (
 id text PRIMARY KEY, order_id text NOT NULL REFERENCES orders(id),
 kind text NOT NULL CHECK (kind IN ('recipient','sender')), details jsonb NOT NULL,
 UNIQUE (order_id, kind)
);
CREATE TABLE IF NOT EXISTS deliveries (
 order_id text PRIMARY KEY REFERENCES orders(id),
 status text NOT NULL DEFAULT 'unassigned' CHECK (status IN ('unassigned','assigned','in_transit','delivered')),
 driver_id bigint REFERENCES users(id), details jsonb NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS order_events (
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 order_id text NOT NULL REFERENCES orders(id), actor_id bigint REFERENCES users(id),
 kind text NOT NULL, detail jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now()
);
INSERT INTO schema_versions(version) VALUES (1) ON CONFLICT DO NOTHING;
