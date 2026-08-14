import json
import duckdb

DB_PATH = "warehouse/space_data.duckdb"
OUTPUT_DIR = "docs/data"

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

    with open(f"{OUTPUT_DIR}/timeline.json", "w") as f:
        json.dump(rows, f, indent=2)

    print(f"Exported timeline.json ({len(rows)} records)")


def main():
    con = duckdb.connect(DB_PATH, read_only=True)
    export_aurora_forecast(con)
    export_timeline(con)
    con.close()


if __name__ == "__main__":
    main()