CREATE TABLE campaigns (
    slug TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    guild_id TEXT NOT NULL,
    narrator_id TEXT NOT NULL,
    system TEXT NOT NULL DEFAULT 'fate',
    content_source TEXT NOT NULL DEFAULT 'vault'
        CHECK (content_source IN ('vault', 'local')),
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);

CREATE TABLE members (
    campaign_slug TEXT NOT NULL REFERENCES campaigns(slug) ON DELETE CASCADE,
    user_id TEXT NOT NULL,
    display_name TEXT,
    joined_at INTEGER NOT NULL,
    PRIMARY KEY (campaign_slug, user_id)
);

CREATE TABLE sheet_files (
    path TEXT PRIMARY KEY,
    harpi_id TEXT NOT NULL,
    campaign TEXT NOT NULL REFERENCES campaigns(slug) ON DELETE CASCADE,
    rev INTEGER NOT NULL DEFAULT 0,
    hash TEXT NOT NULL,
    last_text TEXT NOT NULL,
    base_json TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pendente'
        CHECK (status IN ('pendente', 'ativo', 'arquivado')),
    owner_id TEXT,
    state TEXT NOT NULL DEFAULT 'ok'
        CHECK (state IN ('ok', 'conflito', 'ausente', 'invalido', 'desconhecido')),
    updated_at INTEGER NOT NULL
);

CREATE INDEX sheet_files_by_campaign ON sheet_files (campaign, state);
CREATE INDEX sheet_files_by_harpi_id ON sheet_files (harpi_id);
CREATE INDEX sheet_files_by_owner ON sheet_files (campaign, owner_id, status);

CREATE TABLE sheet_conflicts (
    id TEXT PRIMARY KEY,
    path TEXT NOT NULL REFERENCES sheet_files(path) ON DELETE CASCADE,
    field_path TEXT NOT NULL,
    base TEXT,
    ours TEXT,
    theirs TEXT,
    created_at INTEGER NOT NULL,
    resolved_at INTEGER,
    resolved_by TEXT
);

CREATE TABLE character_visibility (
    campaign_slug TEXT NOT NULL REFERENCES campaigns(slug) ON DELETE CASCADE,
    character_id TEXT NOT NULL,
    revealed_at INTEGER NOT NULL,
    revealed_by TEXT NOT NULL,
    PRIMARY KEY (campaign_slug, character_id)
);
