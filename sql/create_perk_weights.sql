-- Create perk_weights table for persisting per-user weighted sampling data.
-- Only perks with weight < 1.0 (decayed) are stored; absent = 1.0.
CREATE TABLE IF NOT EXISTS perk_weights (
    user_id   BIGINT       NOT NULL,
    perk_name VARCHAR(255) NOT NULL,
    weight    FLOAT        NOT NULL DEFAULT 1.0,
    PRIMARY KEY (user_id, perk_name),
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (perk_name) REFERENCES perks(name)
);
