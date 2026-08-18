"""
더위쉼표 - SQLite 저장 계층 (RFP DAR-004~007)

DAR-004 쉼터 데이터 저장/캐싱
DAR-005 추천 요청 저장 (위치, 요청시간, 활동유형, 검색반경)
DAR-006 추천 결과 저장 (요청-쉼터 관계, 순위, 거리, 이용상태)
DAR-007 AI 안내문 저장 (추천 요청과 연결)
"""
import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime
from contextlib import contextmanager

DB_PATH = Path(__file__).parent / "heatway.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS shelters (
    shelter_id TEXT PRIMARY KEY,
    name TEXT,
    region TEXT,
    dong TEXT,
    facility_type TEXT,
    address TEXT,
    open_time TEXT,
    close_time TEXT,
    is_night_open TEXT,
    ac_count INTEGER,
    fan_count INTEGER,
    capacity INTEGER,
    last_synced_at TEXT
);

CREATE TABLE IF NOT EXISTS recommendation_requests (
    request_id INTEGER PRIMARY KEY AUTOINCREMENT,
    region TEXT,
    requested_time TEXT,
    activity_type TEXT,
    base_radius_km REAL,
    expanded INTEGER,
    using_real_api INTEGER,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS recommendation_results (
    result_id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id INTEGER NOT NULL,
    shelter_id TEXT NOT NULL,
    rank INTEGER,
    distance_km REAL,
    availability TEXT,
    FOREIGN KEY (request_id) REFERENCES recommendation_requests(request_id)
);

CREATE TABLE IF NOT EXISTS guide_texts (
    guide_id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id INTEGER NOT NULL,
    shelter_id TEXT NOT NULL,
    generated_text TEXT,
    created_at TEXT,
    FOREIGN KEY (request_id) REFERENCES recommendation_requests(request_id)
);
"""


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)


def upsert_shelters(df: pd.DataFrame):
    """DAR-004: 쉼터 데이터 캐싱 (API/CSV에서 불러온 데이터를 DB에 반영)"""
    now = datetime.now().isoformat()
    with get_conn() as conn:
        for _, row in df.iterrows():
            conn.execute(
                """
                INSERT INTO shelters
                    (shelter_id, name, region, dong, facility_type, address,
                     open_time, close_time, is_night_open, ac_count, fan_count, capacity, last_synced_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(shelter_id) DO UPDATE SET
                    name=excluded.name, region=excluded.region, dong=excluded.dong,
                    facility_type=excluded.facility_type, address=excluded.address,
                    open_time=excluded.open_time, close_time=excluded.close_time,
                    is_night_open=excluded.is_night_open, ac_count=excluded.ac_count,
                    fan_count=excluded.fan_count, capacity=excluded.capacity,
                    last_synced_at=excluded.last_synced_at
                """,
                (
                    str(row["shelter_id"]), row["name"], row["region"], row.get("dong", ""),
                    row["facility_type"], row["address"], row["open_time"], row["close_time"],
                    row["is_night_open"], int(row["ac_count"]), int(row["fan_count"]), int(row["capacity"]),
                    now,
                ),
            )


def save_recommendation(
    region: str,
    requested_time: str,
    activity_type: str,
    base_radius_km: float,
    expanded: bool,
    using_real_api: bool,
    results_df: pd.DataFrame,
) -> int:
    """DAR-005, DAR-006: 추천 요청 + 결과 저장. request_id 반환"""
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO recommendation_requests
                (region, requested_time, activity_type, base_radius_km, expanded, using_real_api, created_at)
            VALUES (?,?,?,?,?,?,?)
            """,
            (region, requested_time, activity_type, base_radius_km, int(expanded), int(using_real_api),
             datetime.now().isoformat()),
        )
        request_id = cur.lastrowid

        for rank, (_, row) in enumerate(results_df.iterrows(), start=1):
            conn.execute(
                """
                INSERT INTO recommendation_results (request_id, shelter_id, rank, distance_km, availability)
                VALUES (?,?,?,?,?)
                """,
                (request_id, str(row["shelter_id"]), rank, float(row["distance_km"]), row["availability"]),
            )
        return request_id


def save_guide_text(request_id: int, shelter_id: str, text: str):
    """DAR-007: AI 안내문을 추천 요청과 연결해 저장"""
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO guide_texts (request_id, shelter_id, generated_text, created_at)
            VALUES (?,?,?,?)
            """,
            (request_id, str(shelter_id), text, datetime.now().isoformat()),
        )


def get_recent_requests(limit: int = 20):
    """운영/디버그용: 최근 추천 요청 이력 조회"""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM recommendation_requests ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
