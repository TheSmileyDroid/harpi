CREATE TABLE sheet_notices (
    id TEXT PRIMARY KEY,
    campaign_slug TEXT NOT NULL REFERENCES campaigns(slug) ON DELETE CASCADE,
    path TEXT NOT NULL,
    sheet_id TEXT NOT NULL,
    character_id TEXT,
    owner_id TEXT,
    name TEXT NOT NULL,
    state TEXT NOT NULL
        CHECK (state IN ('conflito', 'ausente', 'invalido', 'desconhecido')),
    channel_id TEXT,
    message_id TEXT,
    fields_json TEXT NOT NULL DEFAULT '[]',
    created_at INTEGER NOT NULL,
    resolved_at INTEGER,
    resolved_by TEXT
);

CREATE UNIQUE INDEX sheet_notices_one_open
    ON sheet_notices (campaign_slug, path, state)
    WHERE resolved_at IS NULL;

CREATE INDEX sheet_notices_by_campaign
    ON sheet_notices (campaign_slug, resolved_at, created_at);
