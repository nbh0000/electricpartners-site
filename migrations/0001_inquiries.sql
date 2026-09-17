-- Private application data: never expose SELECT through an unauthenticated route.
CREATE TABLE IF NOT EXISTS inquiries (
 id TEXT PRIMARY KEY,
 created_at TEXT NOT NULL,
 expires_at TEXT NOT NULL,
 province TEXT NOT NULL,
 city TEXT NOT NULL,
 facility TEXT NOT NULL,
 request_type TEXT NOT NULL,
 start_preference TEXT NOT NULL,
 work_type TEXT NOT NULL,
 capacity TEXT NOT NULL DEFAULT '',
 contact_name TEXT NOT NULL DEFAULT '',
 phone TEXT NOT NULL,
 email TEXT NOT NULL DEFAULT '',
 message TEXT NOT NULL DEFAULT '',
 entry_path TEXT NOT NULL DEFAULT '/',
 attribution_json TEXT NOT NULL DEFAULT '{}',
 privacy_version TEXT NOT NULL,
 privacy_consent INTEGER NOT NULL CHECK(privacy_consent=1),
 transfer_consent INTEGER NOT NULL CHECK(transfer_consent IN (0,1)),
 status TEXT NOT NULL DEFAULT 'new' CHECK(status IN ('new','contacted','quoted','won','closed'))
);
CREATE INDEX IF NOT EXISTS idx_inquiries_created ON inquiries(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_inquiries_expiry ON inquiries(expires_at);
CREATE TABLE IF NOT EXISTS request_limits (
 fingerprint TEXT PRIMARY KEY,
 count INTEGER NOT NULL,
 expires_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_request_limits_expiry ON request_limits(expires_at);
