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

-- 보호자 모드 (PRD F5, RFP 명시적 구현제외 항목이나 팀 결정으로 보너스 구현)
CREATE TABLE IF NOT EXISTS outing_sessions (
    session_id INTEGER PRIMARY KEY AUTOINCREMENT,
    dependent_name TEXT NOT NULL,
    shelter_id TEXT,
    shelter_name TEXT,
    start_time TEXT NOT NULL,
    expected_return_time TEXT NOT NULL,
    actual_return_time TEXT,
    status TEXT NOT NULL DEFAULT 'in_progress',
        -- in_progress | checked_in | returned | need_help
    last_checkin_at TEXT,
    last_checkin_status TEXT,  -- ok | need_help
    created_at TEXT
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


# ---------------------------------------------------------------------------
# 보호자 모드 (PRD F5) — RFP 구현제외 항목이나 팀 결정으로 풀버전 구현
# ---------------------------------------------------------------------------

def start_outing(dependent_name: str, expected_return_time: str,
                  shelter_id: str = None, shelter_name: str = None) -> int:
    """외출 시작 기록. session_id 반환"""
    now = datetime.now().isoformat()
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO outing_sessions
                (dependent_name, shelter_id, shelter_name, start_time,
                 expected_return_time, status, created_at)
            VALUES (?,?,?,?,?, 'in_progress', ?)
            """,
            (dependent_name, shelter_id, shelter_name, now, expected_return_time, now),
        )
        return cur.lastrowid


def checkin_shelter(session_id: int):
    """쉼터 도착 체크인"""
    with get_conn() as conn:
        conn.execute(
            "UPDATE outing_sessions SET status='checked_in' WHERE session_id=?",
            (session_id,),
        )


def mark_returned(session_id: int):
    """귀가 완료 처리"""
    with get_conn() as conn:
        conn.execute(
            "UPDATE outing_sessions SET status='returned', actual_return_time=? WHERE session_id=?",
            (datetime.now().isoformat(), session_id),
        )


def send_checkin(session_id: int, status: str):
    """
    안부 확인 응답 (외출자가 누름): status는 'ok' 또는 'need_help'.
    'need_help'면 세션 상태 자체도 need_help로 바꿔 보호자 화면에서 즉시 눈에 띄게 함.
    """
    now = datetime.now().isoformat()
    with get_conn() as conn:
        conn.execute(
            "UPDATE outing_sessions SET last_checkin_at=?, last_checkin_status=? WHERE session_id=?",
            (now, status, session_id),
        )
        if status == "need_help":
            conn.execute(
                "UPDATE outing_sessions SET status='need_help' WHERE session_id=?",
                (session_id,),
            )


def get_active_outing(dependent_name: str):
    """특정 이름의 진행중(in_progress/checked_in/need_help) 외출 세션 1건 조회"""
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT * FROM outing_sessions
            WHERE dependent_name=? AND status IN ('in_progress','checked_in','need_help')
            ORDER BY created_at DESC LIMIT 1
            """,
            (dependent_name,),
        ).fetchone()
        return dict(row) if row else None


def get_all_active_outings():
    """보호자 화면용: 진행중인 모든 외출 세션 조회 (최신순)"""
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT * FROM outing_sessions
            WHERE status IN ('in_progress','checked_in','need_help')
            ORDER BY created_at DESC
            """
        ).fetchall()
        return [dict(r) for r in rows]


def get_outing_by_id(session_id: int):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM outing_sessions WHERE session_id=?", (session_id,)
        ).fetchone()
        return dict(row) if row else None
