"""
Shared constants for the synthetic data generator. Centralized here so the
event taxonomy and plan/channel names documented in docs/EVENT_TAXONOMY.md
and docs/DATA_DICTIONARY.md are the SAME strings the generator actually
emits — not a separately maintained description that can drift.
"""
from datetime import date

SEED = 42

# Observation window. Signups happen throughout; "today" is the data
# generation cutoff used to compute days-since-signup for every user.
SIGNUP_WINDOW_START = date(2026, 1, 1)
SIGNUP_WINDOW_END = date(2026, 6, 30)
TODAY = date(2026, 7, 15)

N_ACCOUNTS = 2000

ACQUISITION_CHANNELS = ["organic_search", "paid_search", "referral", "content_marketing", "social", "partner"]
# Relative signup volume weights (not quality -- quality is modeled separately below)
CHANNEL_WEIGHTS = [0.28, 0.24, 0.12, 0.16, 0.14, 0.06]
# Fraction of accounts on this channel missing entirely (simulates a dropped UTM param)
CHANNEL_MISSING_RATE = 0.03

PLANS = ["free", "starter", "pro", "enterprise"]
PLAN_WEIGHTS_AT_SIGNUP = [0.82, 0.12, 0.05, 0.01]  # almost everyone starts free (freemium)
PLAN_PRICE_MONTHLY = {"free": 0, "starter": 29, "pro": 99, "enterprise": 499}

# Ordered onboarding funnel. "signed_up" is implicit (account creation);
# the rest are the events tracked for funnel analysis, in required order --
# a user must complete step N-1 before N is eligible to occur.
ONBOARDING_STEPS = [
    "signed_up",
    "completed_profile",
    "created_first_workspace",
    "invited_teammate",
    "completed_key_action",
]
# "Activated" is defined as reaching this step within ACTIVATION_WINDOW_DAYS
# of signup -- see docs/METRIC_DEFINITIONS.md for why this step was chosen.
ACTIVATION_STEP = "completed_key_action"
ACTIVATION_WINDOW_DAYS = 7

FEATURE_EVENTS = ["used_dashboard", "used_automation_builder", "used_reporting_export", "used_integration_connect"]

EXPERIMENT_NAME = "onboarding_redesign_v1"
EXPERIMENT_START = date(2026, 3, 1)
EXPERIMENT_END = date(2026, 4, 15)  # accounts created in this window are eligible

# Data quality edge cases, injected deliberately (see docs/DATA_DICTIONARY.md "Known data quality issues")
DUPLICATE_EVENT_RATE = 0.01
LATE_ARRIVAL_RATE = 0.02
LATE_ARRIVAL_MIN_HOURS = 6
LATE_ARRIVAL_MAX_HOURS = 72
