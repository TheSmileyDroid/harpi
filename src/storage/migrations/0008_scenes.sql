CREATE TABLE scenes (
    id TEXT PRIMARY KEY,
    campaign_slug TEXT NOT NULL REFERENCES campaigns(slug) ON DELETE CASCADE,
    name TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'image' CHECK (source IN ('image', 'sketch')),
    blueprint_path TEXT NOT NULL,
    blueprint_hash TEXT NOT NULL,
    image_path TEXT NOT NULL,
    image_width INTEGER NOT NULL CHECK (image_width > 0),
    image_height INTEGER NOT NULL CHECK (image_height > 0),
    grid_json TEXT NOT NULL,
    zones_json TEXT NOT NULL,
    fog_outside INTEGER NOT NULL DEFAULT 0 CHECK (fog_outside IN (0, 1)),
    rev INTEGER NOT NULL DEFAULT 1,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    UNIQUE (campaign_slug, blueprint_path)
);

CREATE INDEX scenes_by_campaign ON scenes (campaign_slug, name);
