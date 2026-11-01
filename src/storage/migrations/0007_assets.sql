CREATE TABLE assets (
    campaign_slug TEXT NOT NULL REFERENCES campaigns(slug) ON DELETE CASCADE,
    name TEXT NOT NULL,
    size INTEGER NOT NULL CHECK (size >= 0),
    created_by TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    PRIMARY KEY (campaign_slug, name)
);

CREATE INDEX assets_by_campaign ON assets (campaign_slug, size);
