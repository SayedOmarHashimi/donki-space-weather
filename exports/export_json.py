import json
import os
import duckdb

DB_PATH = "warehouse/space_data.duckdb"
OUTPUT_DIR = "docs/data"
TIMELINE_PATH = f"{OUTPUT_DIR}/timeline.json"

def export_aurora_forecast(con):
    result = con.execute("""
        SELECT
            gst_id,
            last_observed_time,
            last_kp_index,
            source,
            aurora_chance,
            calculated_at
        FROM aurora_forecast
    """).fetchall()

    columns = [desc[0] for desc in con.description]
    rows = [dict(zip(columns, row)) for row in result]

    # Convert datetime objects to ISO strings so json.dumps doesn't choke on them
    for row in rows:
        for key, value in row.items():
            if hasattr(value, "isoformat"):
                row[key] = value.isoformat()

    data = rows[0] if rows else None

    with open(f"{OUTPUT_DIR}/aurora_forecast.json", "w") as f:
        json.dump(data, f, indent=2)

    print(f"Exported aurora_forecast.json ({'1 record' if data else 'no data'})")


def load_existing_timeline() -> list[dict]:
    """Read the previously committed timeline so history survives even if the
    DuckDB warehouse cache is lost. The committed JSON in git is the durable
    archive; the warehouse is only a rolling working set."""
    if not os.path.exists(TIMELINE_PATH):
        return []
    try:
        with open(TIMELINE_PATH) as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def export_timeline(con):
    result = con.execute("""
        SELECT
            event_id,
            event_type,
            event_time,
            description,
            severity_score
        FROM space_weather_timeline
        ORDER BY event_time DESC
    """).fetchall()

    columns = [desc[0] for desc in con.description]
    rows = [dict(zip(columns, row)) for row in result]

    for row in rows:
        for key, value in row.items():
            if hasattr(value, "isoformat"):
                row[key] = value.isoformat()

    # Merge fresh rows into the committed archive, keyed by event_id. Newly
    # exported events win on conflict (so DONKI revisions propagate), while
    # events that have aged out of the warehouse window are preserved.
    merged = {e["event_id"]: e for e in load_existing_timeline() if e.get("event_id")}
    for e in rows:
        merged[e["event_id"]] = e

    combined = sorted(
        merged.values(), key=lambda e: e.get("event_time") or "", reverse=True
    )

    with open(TIMELINE_PATH, "w") as f:
        json.dump(combined, f, indent=2)

    print(
        f"Exported timeline.json ({len(combined)} records total, "
        f"{len(rows)} from this run's warehouse)"
    )


def main():
    con = duckdb.connect(DB_PATH, read_only=True)
    export_aurora_forecast(con)
    export_timeline(con)
    con.close()


if __name__ == "__main__":
    main()