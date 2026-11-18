-- Canonical, deduplicated event stream. Every metric query and the API
-- read from THIS view, never from events_raw directly, so "deduplication"
-- is a single, auditable definition rather than repeated ad hoc logic.
CREATE OR REPLACE VIEW events AS
SELECT DISTINCT ON (event_id)
    event_id, user_id, account_id, session_id, event_name, event_timestamp, received_at
FROM events_raw
ORDER BY event_id, event_timestamp;

-- One row per (user, onboarding step actually reached), with days-since-signup.
-- The base table every funnel/activation query builds on.
CREATE OR REPLACE VIEW onboarding_progress AS
SELECT
    e.user_id,
    e.account_id,
    e.event_name AS step,
    e.event_timestamp AS step_completed_at,
    a.signup_date,
    date_diff('day', a.signup_date, CAST(e.event_timestamp AS DATE)) AS days_since_signup
FROM events e
JOIN accounts a ON a.account_id = e.account_id
WHERE e.event_name IN ('signed_up', 'completed_profile', 'created_first_workspace', 'invited_teammate', 'completed_key_action');

-- One row per account's owner user with their activation outcome. The
-- single source of truth for "is this account activated" everywhere else.
CREATE OR REPLACE VIEW account_activation AS
SELECT
    a.account_id,
    a.signup_date,
    a.acquisition_channel,
    a.plan_id,
    MIN(CASE WHEN op.step = 'completed_key_action' THEN op.days_since_signup END) AS days_to_activation,
    (MIN(CASE WHEN op.step = 'completed_key_action' THEN op.days_since_signup END) <= 7) AS activated_within_7d
FROM accounts a
LEFT JOIN onboarding_progress op ON op.account_id = a.account_id
GROUP BY a.account_id, a.signup_date, a.acquisition_channel, a.plan_id;
