CREATE TABLE approvals (
    id TEXT PRIMARY KEY,
    campaign_slug TEXT NOT NULL REFERENCES campaigns(slug) ON DELETE CASCADE,
    sheet_path TEXT NOT NULL,
    sheet_id TEXT,
    character_id TEXT,
    status TEXT NOT NULL CHECK (status IN ('pending', 'approved', 'rejected')),
    note TEXT NOT NULL DEFAULT '',
    requested_by TEXT NOT NULL,
    requested_at INTEGER NOT NULL,
    decided_by TEXT,
    decided_at INTEGER
);

CREATE UNIQUE INDEX approvals_one_pending_per_sheet
    ON approvals (campaign_slug, sheet_path)
    WHERE status = 'pending';

CREATE INDEX approvals_by_campaign_status
    ON approvals (campaign_slug, status, requested_at);
