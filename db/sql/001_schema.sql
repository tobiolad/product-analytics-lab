-- Product Analytics & Experimentation Lab — schema
--
-- events_raw intentionally allows duplicate event_id values (the generator
-- injects ~1% duplicate-fire events, simulating a real client retry bug).
-- All analysis reads from the `events` VIEW (002_views.sql), which
-- deduplicates by event_id and uses event_timestamp (not received_at) as
-- the authoritative time for cohorting — see docs/DATA_DICTIONARY.md.

CREATE TABLE accounts (
    account_id          VARCHAR PRIMARY KEY,
    signup_date          DATE NOT NULL,
    acquisition_channel  VARCHAR,  -- nullable: ~3% of accounts have no recorded channel
    plan_id              VARCHAR NOT NULL
);

CREATE TABLE users (
    user_id      VARCHAR PRIMARY KEY,
    account_id   VARCHAR NOT NULL REFERENCES accounts(account_id),
    role         VARCHAR NOT NULL,  -- 'owner' | 'member'
    joined_date  DATE NOT NULL
);

CREATE TABLE experiment_assignments (
    user_id          VARCHAR NOT NULL REFERENCES users(user_id),
    experiment_name  VARCHAR NOT NULL,
    variant           VARCHAR NOT NULL,  -- 'control' | 'treatment'
    assigned_at       DATE NOT NULL,
    PRIMARY KEY (user_id, experiment_name)
);

CREATE TABLE sessions (
    session_id   VARCHAR PRIMARY KEY,
    user_id      VARCHAR NOT NULL REFERENCES users(user_id),
    account_id   VARCHAR NOT NULL REFERENCES accounts(account_id),
    started_at   TIMESTAMP NOT NULL,
    ended_at     TIMESTAMP
);

-- NOT deduplicated, NOT a unique event_id constraint -- see header note.
CREATE TABLE events_raw (
    event_id          VARCHAR NOT NULL,
    user_id           VARCHAR NOT NULL REFERENCES users(user_id),
    account_id        VARCHAR NOT NULL REFERENCES accounts(account_id),
    session_id        VARCHAR,  -- nullable: onboarding funnel events aren't tied to a browsing session
    event_name        VARCHAR NOT NULL,
    event_timestamp   TIMESTAMP NOT NULL,  -- when the event actually happened (client clock)
    received_at       TIMESTAMP NOT NULL   -- when it reached the server -- can lag event_timestamp (late arrival)
);
