CREATE TABLE IF NOT EXISTS user_guilds (
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    guild_id TEXT NOT NULL,
    seen_at INTEGER NOT NULL,
    PRIMARY KEY (user_id, guild_id)
);
