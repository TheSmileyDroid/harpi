CREATE TABLE tables (
    id TEXT PRIMARY KEY,
    campaign_slug TEXT NOT NULL REFERENCES campaigns(slug) ON DELETE CASCADE,
    channel_id TEXT NOT NULL,
    name TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('open', 'closed')),
    current_scene_id TEXT REFERENCES scenes(id) ON DELETE SET NULL,
    round INTEGER NOT NULL DEFAULT 1 CHECK (round >= 1),
    spectators INTEGER NOT NULL DEFAULT 0 CHECK (spectators IN (0, 1)),
    rev INTEGER NOT NULL DEFAULT 1,
    opened_by TEXT NOT NULL,
    opened_at INTEGER NOT NULL,
    closed_by TEXT,
    closed_at INTEGER,
    snapshot_path TEXT,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);

CREATE UNIQUE INDEX tables_one_open_per_campaign
    ON tables (campaign_slug) WHERE status = 'open';

CREATE UNIQUE INDEX tables_one_open_per_channel
    ON tables (channel_id) WHERE status = 'open';

CREATE TABLE tokens (
    id TEXT PRIMARY KEY,
    table_id TEXT NOT NULL REFERENCES tables(id) ON DELETE CASCADE,
    scene_id TEXT NOT NULL REFERENCES scenes(id) ON DELETE CASCADE,
    character_id TEXT,
    label TEXT NOT NULL,
    owner_id TEXT,
    x REAL NOT NULL,
    y REAL NOT NULL,
    w INTEGER NOT NULL DEFAULT 1 CHECK (w > 0),
    h INTEGER NOT NULL DEFAULT 1 CHECK (h > 0),
    color TEXT NOT NULL,
    visible INTEGER NOT NULL DEFAULT 1 CHECK (visible IN (0, 1)),
    rev INTEGER NOT NULL DEFAULT 1,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);

CREATE INDEX tokens_by_table_scene ON tokens (table_id, scene_id);
CREATE INDEX tokens_by_owner ON tokens (table_id, owner_id);

CREATE TABLE turns (
    id TEXT PRIMARY KEY,
    table_id TEXT NOT NULL REFERENCES tables(id) ON DELETE CASCADE,
    scene_id TEXT NOT NULL REFERENCES scenes(id) ON DELETE CASCADE,
    round INTEGER NOT NULL CHECK (round >= 1),
    token_id TEXT REFERENCES tokens(id) ON DELETE SET NULL,
    character_id TEXT,
    label TEXT NOT NULL,
    started_at INTEGER NOT NULL,
    ended_at INTEGER,
    started_by TEXT NOT NULL,
    ended_by TEXT,
    CHECK (ended_at IS NULL OR ended_at >= started_at)
);

CREATE UNIQUE INDEX turns_one_open_per_table
    ON turns (table_id) WHERE ended_at IS NULL;

CREATE UNIQUE INDEX turns_one_per_token_round
    ON turns (table_id, scene_id, token_id, round)
    WHERE token_id IS NOT NULL;

CREATE INDEX turns_by_table_round ON turns (table_id, round, started_at);

CREATE TABLE rolls (
    id TEXT PRIMARY KEY,
    table_id TEXT NOT NULL REFERENCES tables(id) ON DELETE CASCADE,
    scene_id TEXT REFERENCES scenes(id) ON DELETE SET NULL,
    scene_label TEXT NOT NULL DEFAULT '',
    turn_id TEXT REFERENCES turns(id) ON DELETE SET NULL,
    actor_id TEXT,
    actor_label TEXT NOT NULL,
    source TEXT NOT NULL CHECK (source IN ('panel', 'discord')),
    expression TEXT NOT NULL,
    total INTEGER NOT NULL,
    dice_json TEXT NOT NULL,
    text TEXT NOT NULL,
    discord_message_id TEXT,
    created_at INTEGER NOT NULL
);

CREATE UNIQUE INDEX rolls_one_per_discord_message
    ON rolls (discord_message_id)
    WHERE discord_message_id IS NOT NULL;

CREATE INDEX rolls_by_table ON rolls (table_id, created_at, id);
