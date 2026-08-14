import os
import json
from datetime import date, timedelta

import requests
import pandas as pd
import duckdb
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.environ["NASA_API_KEY"]
DB_PATH = "warehouse/space_data.duckdb"


def fetch_gst(start_date, end_date):
    url = "https://api.nasa.gov/DONKI/GST"
    params = {"startDate": start_date, "endDate": end_date, "api_key": API_KEY}
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def flatten_gst(records):
    gst_rows = []
    kp_rows = []

    for gst in records:
        gst_id = gst["gstID"]

        gst_rows.append({
            "gstID": gst_id,
            "startTime": gst.get("startTime"),
            "link": gst.get("link"),
            "linkedEvents": json.dumps(gst.get("linkedEvents")) if gst.get("linkedEvents") is not None else None,
            "submissionTime": gst.get("submissionTime"),
            "versionId": gst.get("versionId"),
            "sentNotifications": json.dumps(gst.get("sentNotifications")) if gst.get("sentNotifications") is not None else None,
        })

        for i, kp in enumerate(gst.get("allKpIndex") or []):
            kp_rows.append({
                "kp_id": f"{gst_id}-kp-{i}",
                "gstID": gst_id,
                "observedTime": kp.get("observedTime"),
                "kpIndex": kp.get("kpIndex"),
                "source": kp.get("source"),
            })

    return pd.DataFrame(gst_rows), pd.DataFrame(kp_rows)


def upsert_table(con, df, table, create_sql, pk, update_cols):
    if df.empty:
        print(f"No rows for {table} — nothing to upsert.")
        return

    con.execute(create_sql)
    con.register("df_new", df)

    set_clause = ", ".join(f"{c} = EXCLUDED.{c}" for c in update_cols)
    con.execute(f"""
        INSERT INTO {table}
        SELECT * FROM df_new
        ON CONFLICT ({pk}) DO UPDATE SET {set_clause}
    """)

    count = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    print(f"Upsert complete. {table} now has {count} rows.")


def upsert_all(gst_df, kp_df):
    con = duckdb.connect(DB_PATH)

    upsert_table(
        con, gst_df, "raw_gst",
        """
        CREATE TABLE IF NOT EXISTS raw_gst (
            gstID TEXT PRIMARY KEY,
            startTime TEXT,
            link TEXT,
            linkedEvents TEXT,
            submissionTime TEXT,
            versionId INTEGER,
            sentNotifications TEXT
        )
        """,
        pk="gstID",
        update_cols=["startTime", "link", "linkedEvents", "submissionTime",
                     "versionId", "sentNotifications"],
    )

    upsert_table(
        con, kp_df, "raw_gst_kp_index",
        """
        CREATE TABLE IF NOT EXISTS raw_gst_kp_index (
            kp_id TEXT PRIMARY KEY,
            gstID TEXT,
            observedTime TEXT,
            kpIndex DOUBLE,
            source TEXT
        )
        """,
        pk="kp_id",
        update_cols=["gstID", "observedTime", "kpIndex", "source"],
    )

    con.close()


def main():
    end = date.today()
    start = end - timedelta(days=7)
    records = fetch_gst(start.isoformat(), end.isoformat())
    gst_df, kp_df = flatten_gst(records)
    upsert_all(gst_df, kp_df)


if __name__ == "__main__":
    main()