-- Forward migration for the two service lines; keep old inquiry rows intact.
ALTER TABLE inquiries ADD COLUMN service TEXT NOT NULL DEFAULT 'onsite' CHECK(service IN ('onsite','duty','both'));
ALTER TABLE inquiries ADD COLUMN inspection_type TEXT NOT NULL DEFAULT 'discuss' CHECK(inspection_type IN ('discuss','periodic','annual','specific'));
ALTER TABLE inquiries ADD COLUMN shutdown_possible TEXT NOT NULL DEFAULT 'unknown' CHECK(shutdown_possible IN ('unknown','yes','limited','no'));
CREATE INDEX IF NOT EXISTS idx_inquiries_service ON inquiries(service, created_at DESC);
