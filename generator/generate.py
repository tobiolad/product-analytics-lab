"""
Deterministic synthetic data generator for the Product Analytics &
Experimentation Lab. Running this script with the fixed SEED in
constants.py always produces byte-identical CSV output -- verified by
tests/test_generator.py.

Everything here is explicitly synthetic (see constants.py and
docs/DATA_DICTIONARY.md). Output: generator/data/raw/*.csv
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from constants import (
    SEED,
    SIGNUP_WINDOW_START,
    SIGNUP_WINDOW_END,
    TODAY,
    N_ACCOUNTS,
    ACQUISITION_CHANNELS,
    CHANNEL_WEIGHTS,
    CHANNEL_MISSING_RATE,
    PLANS,
    PLAN_WEIGHTS_AT_SIGNUP,
    ONBOARDING_STEPS,
    ACTIVATION_STEP,
    ACTIVATION_WINDOW_DAYS,
    FEATURE_EVENTS,
    EXPERIMENT_NAME,
    EXPERIMENT_START,
    EXPERIMENT_END,
    DUPLICATE_EVENT_RATE,
    LATE_ARRIVAL_RATE,
    LATE_ARRIVAL_MIN_HOURS,
    LATE_ARRIVAL_MAX_HOURS,
)

OUT_DIR = Path(__file__).resolve().parent / "data" / "raw"

# Relative "quality" of each channel: scales every step-advance probability
# and overall engagement. >1 = better-converting channel, <1 = worse.
# These are the generator's ground truth -- the whole point of the Channel
# Performance view is to recover a version of this ranking from the data.
CHANNEL_QUALITY = {
    "organic_search": 1.08,
    "paid_search": 0.90,
    "referral": 1.22,
    "content_marketing": 1.05,
    "social": 0.85,
    "partner": 1.15,
}

# Baseline (control, non-experiment) probability of advancing from one
# onboarding step to the next, before any channel-quality scaling.
BASE_STEP_ADVANCE_PROB = {
    "completed_profile": 0.75,
    "created_first_workspace": 0.70,
    "completed_key_action": 0.55,  # gated on created_first_workspace, NOT on invited_teammate (optional side-step)
}
INVITE_TEAMMATE_PROB = 0.32  # optional, gated on created_first_workspace, doesn't block activation

# The experiment's TRUE effect, baked into generation. The analysis later
# has to recover this from noisy finite-sample data -- it is not told this
# number. See docs/EXPERIMENT_METHODOLOGY.md.
TREATMENT_ACTIVATION_LIFT = 0.10  # absolute probability lift on the key-action step
TREATMENT_SPEED_SCALE = 0.6  # days-to-complete gamma scale (vs 1.0 for control) -- faster, not just more likely

FEATURE_BASE_ADOPTION = {
    "used_dashboard": 0.55,
    "used_automation_builder": 0.30,
    "used_reporting_export": 0.25,
    "used_integration_connect": 0.20,
}


def days_between(d1: date, d2: date) -> int:
    return (d2 - d1).days


@dataclass
class GeneratedData:
    accounts: pd.DataFrame
    users: pd.DataFrame
    experiment_assignments: pd.DataFrame
    sessions: pd.DataFrame
    events: pd.DataFrame


def deterministic_variant(user_id: str, experiment_name: str) -> str:
    """
    Deterministic 50/50 assignment: hash(user_id + experiment_name) mod 100.
    Same user + same experiment always yields the same variant, with no
    stored assignment table required to reproduce it -- though we do store
    one, for auditability (see db schema).
    """
    digest = hashlib.sha256(f"{experiment_name}:{user_id}".encode()).hexdigest()
    bucket = int(digest[:8], 16) % 100
    return "treatment" if bucket < 50 else "control"


def generate_accounts(rng: np.random.Generator) -> pd.DataFrame:
    window_days = days_between(SIGNUP_WINDOW_START, SIGNUP_WINDOW_END)
    offsets = rng.integers(0, window_days + 1, size=N_ACCOUNTS)
    # Mild upward trend in signup volume over the window, not perfectly flat
    offsets = np.sort(offsets)

    channel_idx = rng.choice(len(ACQUISITION_CHANNELS), size=N_ACCOUNTS, p=CHANNEL_WEIGHTS)
    channels = np.array(ACQUISITION_CHANNELS)[channel_idx]
    missing_mask = rng.random(N_ACCOUNTS) < CHANNEL_MISSING_RATE
    channels = channels.astype(object)
    channels[missing_mask] = None

    plan_idx = rng.choice(len(PLANS), size=N_ACCOUNTS, p=PLAN_WEIGHTS_AT_SIGNUP)
    plans = np.array(PLANS)[plan_idx]

    account_ids = [f"acct_{i:05d}" for i in range(N_ACCOUNTS)]
    signup_dates = [SIGNUP_WINDOW_START + timedelta(days=int(o)) for o in offsets]

    return pd.DataFrame(
        {
            "account_id": account_ids,
            "signup_date": signup_dates,
            "acquisition_channel": channels,
            "plan_id": plans,
        }
    )


def generate_users(accounts: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    rows = []
    for _, acct in accounts.iterrows():
        rows.append({"user_id": f"{acct.account_id}_u0", "account_id": acct.account_id, "role": "owner", "joined_date": acct.signup_date})
        # ~15% of accounts get 1-2 invited teammates within the first 2 weeks
        if rng.random() < 0.15:
            n_extra = rng.integers(1, 3)
            for j in range(1, n_extra + 1):
                join_offset = int(rng.integers(1, 14))
                rows.append(
                    {
                        "user_id": f"{acct.account_id}_u{j}",
                        "account_id": acct.account_id,
                        "role": "member",
                        "joined_date": acct.signup_date + timedelta(days=join_offset),
                    }
                )
    return pd.DataFrame(rows)


def generate_experiment_assignments(accounts: pd.DataFrame) -> pd.DataFrame:
    """Every account's OWNER user is assigned if the account signed up within the experiment window."""
    rows = []
    for _, acct in accounts.iterrows():
        if EXPERIMENT_START <= acct.signup_date <= EXPERIMENT_END:
            owner_id = f"{acct.account_id}_u0"
            variant = deterministic_variant(owner_id, EXPERIMENT_NAME)
            rows.append({"user_id": owner_id, "experiment_name": EXPERIMENT_NAME, "variant": variant, "assigned_at": acct.signup_date})
    return pd.DataFrame(rows)


def simulate_onboarding(
    acct_row, is_treatment: bool, rng: np.random.Generator
) -> list[dict]:
    """Returns a list of onboarding event dicts for one account's owner user."""
    quality = CHANNEL_QUALITY.get(acct_row.acquisition_channel, 1.0) if acct_row.acquisition_channel else 0.95
    owner_id = f"{acct_row.account_id}_u0"
    signup_dt = datetime.combine(acct_row.signup_date, datetime.min.time()) + timedelta(hours=float(rng.uniform(0, 23)))

    events = [{"event_name": "signed_up", "user_id": owner_id, "account_id": acct_row.account_id, "event_timestamp": signup_dt}]
    current_time = signup_dt
    reached_workspace = False

    for step in ["completed_profile", "created_first_workspace"]:
        p = min(0.98, BASE_STEP_ADVANCE_PROB[step] * quality)
        if rng.random() < p:
            delay_days = rng.gamma(shape=2.0, scale=0.7)
            current_time = current_time + timedelta(days=float(delay_days))
            events.append({"event_name": step, "user_id": owner_id, "account_id": acct_row.account_id, "event_timestamp": current_time})
            if step == "created_first_workspace":
                reached_workspace = True
        else:
            break

    if reached_workspace:
        # Optional side-step, doesn't gate activation
        if rng.random() < INVITE_TEAMMATE_PROB:
            invite_time = current_time + timedelta(days=float(rng.gamma(2.0, 1.0)))
            events.append({"event_name": "invited_teammate", "user_id": owner_id, "account_id": acct_row.account_id, "event_timestamp": invite_time})

        p_activate = BASE_STEP_ADVANCE_PROB["completed_key_action"] * quality
        if is_treatment:
            p_activate += TREATMENT_ACTIVATION_LIFT
        p_activate = min(0.98, p_activate)

        if rng.random() < p_activate:
            scale = TREATMENT_SPEED_SCALE if is_treatment else 1.0
            delay_days = rng.gamma(shape=1.8, scale=scale)
            activate_time = current_time + timedelta(days=float(delay_days))
            events.append({"event_name": ACTIVATION_STEP, "user_id": owner_id, "account_id": acct_row.account_id, "event_timestamp": activate_time})

    return events


def simulate_engagement(
    user_id: str, account_id: str, signup_dt: datetime, activated: bool, channel_quality: float, rng: np.random.Generator
) -> tuple[list[dict], list[dict]]:
    """Generates sessions + feature-usage events for one user's lifetime in the dataset."""
    observation_days = min(days_between(signup_dt.date(), TODAY), 45)
    if observation_days <= 0:
        return [], []

    engagement = rng.beta(2, 5) * channel_quality
    if activated:
        engagement *= 1.6
    engagement = float(np.clip(engagement, 0.02, 0.97))

    n_active_days = max(1, round(engagement * observation_days))
    day_range = np.arange(0, observation_days + 1)
    weights = np.exp(-day_range / 20.0)
    weights /= weights.sum()
    n_active_days = min(n_active_days, observation_days + 1)
    active_offsets = sorted(set(rng.choice(day_range, size=n_active_days, replace=False, p=weights).tolist()))

    sessions = []
    events = []

    adopted_features = {}
    for feat, base_p in FEATURE_BASE_ADOPTION.items():
        p_adopt = base_p * (1.5 if activated else 0.55) * channel_quality
        if rng.random() < min(p_adopt, 0.95):
            adopted_features[feat] = active_offsets[int(rng.integers(0, max(1, len(active_offsets) // 2 + 1)))]

    for offset in active_offsets:
        session_start = signup_dt + timedelta(days=int(offset), hours=float(rng.uniform(0, 23)))
        duration_min = float(rng.gamma(2.0, 8.0)) + 2
        session_id = f"sess_{rng.bytes(6).hex()}"
        sessions.append(
            {
                "session_id": session_id,
                "user_id": user_id,
                "account_id": account_id,
                "started_at": session_start,
                "ended_at": session_start + timedelta(minutes=duration_min),
            }
        )
        for feat, discover_offset in adopted_features.items():
            if offset >= discover_offset and rng.random() < 0.5:
                events.append(
                    {
                        "event_name": feat,
                        "user_id": user_id,
                        "account_id": account_id,
                        "session_id": session_id,
                        "event_timestamp": session_start + timedelta(minutes=float(rng.uniform(0.5, duration_min))),
                    }
                )

    return sessions, events


def inject_data_quality_issues(events: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    events = events.copy()
    events["event_id"] = [f"evt_{rng.bytes(8).hex()}" for _ in range(len(events))]
    events["received_at"] = events["event_timestamp"]

    late_mask = rng.random(len(events)) < LATE_ARRIVAL_RATE
    late_hours = rng.uniform(LATE_ARRIVAL_MIN_HOURS, LATE_ARRIVAL_MAX_HOURS, size=len(events))
    events.loc[late_mask, "received_at"] = events.loc[late_mask, "event_timestamp"] + pd.to_timedelta(late_hours[late_mask], unit="h")

    dup_mask = rng.random(len(events)) < DUPLICATE_EVENT_RATE
    duplicates = events.loc[dup_mask].copy()
    events = pd.concat([events, duplicates], ignore_index=True)
    return events


def generate_all(seed: int = SEED) -> GeneratedData:
    rng = np.random.default_rng(seed)

    accounts = generate_accounts(rng)
    users = generate_users(accounts, rng)
    experiment_assignments = generate_experiment_assignments(accounts)
    treatment_lookup = dict(zip(experiment_assignments.user_id, experiment_assignments.variant)) if len(experiment_assignments) else {}

    all_onboarding_events: list[dict] = []
    all_sessions: list[dict] = []
    all_feature_events: list[dict] = []

    for _, acct in accounts.iterrows():
        owner_id = f"{acct.account_id}_u0"
        is_treatment = treatment_lookup.get(owner_id) == "treatment"
        onboarding_events = simulate_onboarding(acct, is_treatment, rng)
        all_onboarding_events.extend(onboarding_events)

        activated_times = [e for e in onboarding_events if e["event_name"] == ACTIVATION_STEP]
        is_activated_within_window = bool(activated_times) and days_between(
            acct.signup_date, activated_times[0]["event_timestamp"].date()
        ) <= ACTIVATION_WINDOW_DAYS
        quality = CHANNEL_QUALITY.get(acct.acquisition_channel, 1.0) if acct.acquisition_channel else 0.95

        signup_dt = onboarding_events[0]["event_timestamp"]
        sessions, feature_events = simulate_engagement(owner_id, acct.account_id, signup_dt, is_activated_within_window, quality, rng)
        all_sessions.extend(sessions)
        all_feature_events.extend(feature_events)

    events_df = pd.DataFrame(all_onboarding_events + all_feature_events)
    events_df = inject_data_quality_issues(events_df, rng)
    sessions_df = pd.DataFrame(all_sessions)

    return GeneratedData(
        accounts=accounts,
        users=users,
        experiment_assignments=experiment_assignments,
        sessions=sessions_df,
        events=events_df,
    )


def main():
    data = generate_all()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    data.accounts.to_csv(OUT_DIR / "accounts.csv", index=False)
    data.users.to_csv(OUT_DIR / "users.csv", index=False)
    data.experiment_assignments.to_csv(OUT_DIR / "experiment_assignments.csv", index=False)
    data.sessions.to_csv(OUT_DIR / "sessions.csv", index=False)
    data.events.sort_values("event_timestamp").to_csv(OUT_DIR / "events.csv", index=False)

    print(f"accounts:               {len(data.accounts):,}")
    print(f"users:                  {len(data.users):,}")
    print(f"experiment_assignments: {len(data.experiment_assignments):,}")
    print(f"sessions:               {len(data.sessions):,}")
    print(f"events:                 {len(data.events):,}")
    print(f"Written to {OUT_DIR}")


if __name__ == "__main__":
    main()
