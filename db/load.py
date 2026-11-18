"""
Builds the DuckDB analytical database from the generated CSVs. Reproducible
and idempotent: deletes any existing database file and rebuilds fresh.

Usage:
    python db/load.py
"""
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "generator" / "data" / "raw"
DB_PATH = ROOT / "db" / "analytics.duckdb"
SQL_DIR = Path(__file__).resolve().parent / "sql"


def main():
    if DB_PATH.exists():
        DB_PATH.unlink()

    con = duckdb.connect(str(DB_PATH))

    for sql_file in ["001_schema.sql", "002_views.sql"]:
        con.execute((SQL_DIR / sql_file).read_text())

    # Column lists are explicit (not `SELECT *`) so load order never depends
    # on whatever column order the generator happened to write a CSV in.
    con.execute(
        f"""INSERT INTO accounts (account_id, signup_date, acquisition_channel, plan_id)
            SELECT account_id, signup_date, acquisition_channel, plan_id
            FROM read_csv_auto('{RAW_DIR / 'accounts.csv'}')"""
    )
    con.execute(
        f"""INSERT INTO users (user_id, account_id, role, joined_date)
            SELECT user_id, account_id, role, joined_date
            FROM read_csv_auto('{RAW_DIR / 'users.csv'}')"""
    )
    con.execute(
        f"""INSERT INTO experiment_assignments (user_id, experiment_name, variant, assigned_at)
            SELECT user_id, experiment_name, variant, assigned_at
            FROM read_csv_auto('{RAW_DIR / 'experiment_assignments.csv'}')"""
    )
    con.execute(
        f"""INSERT INTO sessions (session_id, user_id, account_id, started_at, ended_at)
            SELECT session_id, user_id, account_id, started_at, ended_at
            FROM read_csv_auto('{RAW_DIR / 'sessions.csv'}')"""
    )
    con.execute(
        f"""INSERT INTO events_raw (event_id, user_id, account_id, session_id, event_name, event_timestamp, received_at)
            SELECT event_id, user_id, account_id, session_id, event_name, event_timestamp, received_at
            FROM read_csv_auto('{RAW_DIR / 'events.csv'}')"""
    )

    # Views reference tables created above, but CREATE VIEW happened before
    # data was loaded -- DuckDB views are query-time, so this is fine. Re-run
    # here anyway for clarity/idempotency if someone re-executes just this file.
    con.execute((SQL_DIR / "002_views.sql").read_text())

    counts = con.execute(
        """
        SELECT 'accounts', COUNT(*) FROM accounts
        UNION ALL SELECT 'users', COUNT(*) FROM users
        UNION ALL SELECT 'experiment_assignments', COUNT(*) FROM experiment_assignments
        UNION ALL SELECT 'sessions', COUNT(*) FROM sessions
        UNION ALL SELECT 'events_raw', COUNT(*) FROM events_raw
        UNION ALL SELECT 'events (deduplicated)', COUNT(*) FROM events
        """
    ).fetchall()
    for name, count in counts:
        print(f"{name:28} {count:,}")

    con.close()
    print(f"\nBuilt {DB_PATH}")


if __name__ == "__main__":
    main()
