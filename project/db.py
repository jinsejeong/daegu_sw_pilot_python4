"""
더위쉼표 - 데이터 저장 계층 (RFP DAR-004~007)
듀얼 백엔드: .env에 DATABASE_URL(Supabase/Postgres)이 있으면 그걸 쓰고,
없으면 로컬 SQLite로 자동 폴백한다 (이 프로젝트 전반의 폴백 설계 원칙과 동일).

DAR-004 쉼터 데이터 저장/캐싱
DAR-005 추천 요청 저장 (위치, 요청시간, 활동유형, 검색반경)
DAR-006 추천 결과 저장 (요청-쉼터 관계, 순위, 거리, 이용상태)
DAR-007 AI 안내문 저장 (추천 요청과 연결)

주의: app.py / api_server.py는 이 파일의 public 함수(start_outing, save_recommendation 등)만
호출하므로, 백엔드가 바뀌어도 그쪽 코드는 전혀 수정할 필요가 없다.
"""
import os
import pandas as pd
from pathlib import Path
from datetime import datetime
from contextlib import contextmanager
from dotenv import load_dotenv

load_dotenv()  # db.py가 어떤 경로로 import되든(app.py 경유든, 단독 테스트든) 항상 .env를 읽도록 자체 보장

DB_PATH = Path(__file__).parent / "heatway.db"
DATABASE_URL = os.environ.get("DATABASE_URL")  # Supabase 등에서 발급받은 Postgres 연결문자열
BACKEND = "postgres" if DATABASE_URL else "sqlite"

if BACKEND == "postgres":
    import psycopg2
    from psycopg2.extras import RealDictCursor
else:
    import sqlite3

# ---------------------------------------------------------------------------
# 스키마 (SQLite / Postgres 각각 문법 차이 — AUTOINCREMENT vs SERIAL)
# ---------------------------------------------------------------------------

SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS shelters (
    shelter_id TEXT PRIMARY KEY,
    name TEXT, region TEXT, dong TEXT, facility_type TEXT, address TEXT,
    open_time TEXT, close_time TEXT, is_night_open TEXT,
    ac_count INTEGER, fan_count INTEGER, capacity INTEGER, last_synced_at TEXT
);
CREATE TABLE IF NOT EXISTS recommendation_requests (
    request_id INTEGER PRIMARY KEY AUTOINCREMENT,
    region TEXT, requested_time TEXT, activity_type TEXT,
    base_radius_km REAL, expanded INTEGER, using_real_api INTEGER, created_at TEXT
);
CREATE TABLE IF NOT EXISTS recommendation_results (
    result_id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id INTEGER NOT NULL, shelter_id TEXT NOT NULL,
    rank INTEGER, distance_km REAL, availability TEXT,
    FOREIGN KEY (request_id) REFERENCES recommendation_requests(request_id)
);
CREATE TABLE IF NOT EXISTS guide_texts (
    guide_id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id INTEGER NOT NULL, shelter_id TEXT NOT NULL,
    generated_text TEXT, created_at TEXT,
    FOREIGN KEY (request_id) REFERENCES recommendation_requests(request_id)
);
CREATE TABLE IF NOT EXISTS outing_sessions (
    session_id INTEGER PRIMARY KEY AUTOINCREMENT,
    dependent_name TEXT NOT NULL, shelter_id TEXT, shelter_name TEXT,
    start_time TEXT NOT NULL, expected_return_time TEXT NOT NULL,
    actual_return_time TEXT, status TEXT NOT NULL DEFAULT 'in_progress',
    last_checkin_at TEXT, last_checkin_status TEXT, created_at TEXT
);
"""

SCHEMA_POSTGRES = """
CREATE TABLE IF NOT EXISTS shelters (
    shelter_id TEXT PRIMARY KEY,
    name TEXT, region TEXT, dong TEXT, facility_type TEXT, address TEXT,
    open_time TEXT, close_time TEXT, is_night_open TEXT,
    ac_count INTEGER, fan_count INTEGER, capacity INTEGER, last_synced_at TEXT
);
CREATE TABLE IF NOT EXISTS recommendation_requests (
    request_id SERIAL PRIMARY KEY,
    region TEXT, requested_time TEXT, activity_type TEXT,
    base_radius_km REAL, expanded INTEGER, using_real_api INTEGER, created_at TEXT
);
CREATE TABLE IF NOT EXISTS recommendation_results (
    result_id SERIAL PRIMARY KEY,
    request_id INTEGER NOT NULL REFERENCES recommendation_requests(request_id),
    shelter_id TEXT NOT NULL,
    rank INTEGER, distance_km REAL, availability TEXT
);
CREATE TABLE IF NOT EXISTS guide_texts (
    guide_id SERIAL PRIMARY KEY,
    request_id INTEGER NOT NULL REFERENCES recommendation_requests(request_id),
    shelter_id TEXT NOT NULL,
    generated_text TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS outing_sessions (
    session_id SERIAL PRIMARY KEY,
    dependent_name TEXT NOT NULL, shelter_id TEXT, shelter_name TEXT,
    start_time TEXT NOT NULL, expected_return_time TEXT NOT NULL,
    actual_return_time TEXT, status TEXT NOT NULL DEFAULT 'in_progress',
    last_checkin_at TEXT, last_checkin_status TEXT, created_at TEXT
);
"""


# ---------------------------------------------------------------------------
# 연결/쿼리 헬퍼 (여기서만 백엔드 차이를 흡수, 아래 함수들은 백엔드 무관하게 동일)
# ---------------------------------------------------------------------------

@contextmanager
def get_conn():
    if BACKEND == "postgres":
        conn = psycopg2.connect(DATABASE_URL)
    else:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _cursor(conn):
    if BACKEND == "postgres":
        return conn.cursor(cursor_factory=RealDictCursor)
    return conn.cursor()


def Q(sql: str) -> str:
    """SQLite '?' 플레이스홀더 -> Postgres '%s' 변환 (쿼리는 항상 '?'로 작성)"""
    return sql.replace("?", "%s") if BACKEND == "postgres" else sql


def init_db():
    schema = SCHEMA_POSTGRES if BACKEND == "postgres" else SCHEMA_SQLITE
    with get_conn() as conn:
        if BACKEND == "postgres":
            cur = conn.cursor()
            for stmt in schema.strip().split(";"):
                stmt = stmt.strip()
                if stmt:
                    cur.execute(stmt)
        else:
            conn.executescript(schema)


# ---------------------------------------------------------------------------
# 쉼터 캐시 (DAR-004)
# ---------------------------------------------------------------------------

def upsert_shelters(df: pd.DataFrame):
    now = datetime.now().isoformat()
    with get_conn() as conn:
        cur = _cursor(conn)
        for _, row in df.iterrows():
            cur.execute(
                Q("""
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
                """),
                (
                    str(row["shelter_id"]), row["name"], row["region"], row.get("dong", ""),
                    row["facility_type"], row["address"], row["open_time"], row["close_time"],
                    row["is_night_open"], int(row["ac_count"]), int(row["fan_count"]), int(row["capacity"]),
                    now,
                ),
            )


# ---------------------------------------------------------------------------
# 추천 요청/결과/AI안내문 (DAR-005~007)
# ---------------------------------------------------------------------------

def save_recommendation(region, requested_time, activity_type, base_radius_km,
                         expanded, using_real_api, results_df: pd.DataFrame) -> int:
    sql = """
        INSERT INTO recommendation_requests
            (region, requested_time, activity_type, base_radius_km, expanded, using_real_api, created_at)
        VALUES (?,?,?,?,?,?,?)
    """
    if BACKEND == "postgres":
        sql += " RETURNING request_id"

    with get_conn() as conn:
        cur = _cursor(conn)
        cur.execute(
            Q(sql),
            (region, requested_time, activity_type, base_radius_km, int(expanded), int(using_real_api),
             datetime.now().isoformat()),
        )
        request_id = cur.fetchone()["request_id"] if BACKEND == "postgres" else cur.lastrowid

        for rank, (_, row) in enumerate(results_df.iterrows(), start=1):
            cur.execute(
                Q("INSERT INTO recommendation_results (request_id, shelter_id, rank, distance_km, availability) "
                  "VALUES (?,?,?,?,?)"),
                (request_id, str(row["shelter_id"]), rank, float(row["distance_km"]), row["availability"]),
            )
        return request_id


def save_guide_text(request_id: int, shelter_id: str, text: str):
    with get_conn() as conn:
        cur = _cursor(conn)
        cur.execute(
            Q("INSERT INTO guide_texts (request_id, shelter_id, generated_text, created_at) VALUES (?,?,?,?)"),
            (request_id, str(shelter_id), text, datetime.now().isoformat()),
        )


def get_recent_requests(limit: int = 20):
    with get_conn() as conn:
        cur = _cursor(conn)
        cur.execute(Q("SELECT * FROM recommendation_requests ORDER BY created_at DESC LIMIT ?"), (limit,))
        return [dict(r) for r in cur.fetchall()]


# ---------------------------------------------------------------------------
# 보호자 모드 (PRD F5) — RFP 구현제외 항목이나 팀 결정으로 풀버전 구현
# ---------------------------------------------------------------------------

def start_outing(dependent_name: str, expected_return_time: str,
                  shelter_id: str = None, shelter_name: str = None) -> int:
    now = datetime.now().isoformat()
    sql = """
        INSERT INTO outing_sessions
            (dependent_name, shelter_id, shelter_name, start_time,
             expected_return_time, status, created_at)
        VALUES (?,?,?,?,?, 'in_progress', ?)
    """
    if BACKEND == "postgres":
        sql += " RETURNING session_id"

    with get_conn() as conn:
        cur = _cursor(conn)
        cur.execute(Q(sql), (dependent_name, shelter_id, shelter_name, now, expected_return_time, now))
        return cur.fetchone()["session_id"] if BACKEND == "postgres" else cur.lastrowid


def checkin_shelter(session_id: int):
    with get_conn() as conn:
        cur = _cursor(conn)
        cur.execute(Q("UPDATE outing_sessions SET status='checked_in' WHERE session_id=?"), (session_id,))


def mark_returned(session_id: int):
    with get_conn() as conn:
        cur = _cursor(conn)
        cur.execute(
            Q("UPDATE outing_sessions SET status='returned', actual_return_time=? WHERE session_id=?"),
            (datetime.now().isoformat(), session_id),
        )


def send_checkin(session_id: int, status: str):
    now = datetime.now().isoformat()
    with get_conn() as conn:
        cur = _cursor(conn)
        cur.execute(
            Q("UPDATE outing_sessions SET last_checkin_at=?, last_checkin_status=? WHERE session_id=?"),
            (now, status, session_id),
        )
        if status == "need_help":
            cur.execute(Q("UPDATE outing_sessions SET status='need_help' WHERE session_id=?"), (session_id,))


def get_active_outing(dependent_name: str):
    with get_conn() as conn:
        cur = _cursor(conn)
        cur.execute(
            Q("""
            SELECT * FROM outing_sessions
            WHERE dependent_name=? AND status IN ('in_progress','checked_in','need_help')
            ORDER BY created_at DESC LIMIT 1
            """),
            (dependent_name,),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def get_all_active_outings():
    with get_conn() as conn:
        cur = _cursor(conn)
        cur.execute("""
            SELECT * FROM outing_sessions
            WHERE status IN ('in_progress','checked_in','need_help')
            ORDER BY created_at DESC
        """)
        return [dict(r) for r in cur.fetchall()]


def get_outing_by_id(session_id: int):
    with get_conn() as conn:
        cur = _cursor(conn)
        cur.execute(Q("SELECT * FROM outing_sessions WHERE session_id=?"), (session_id,))
        row = cur.fetchone()
        return dict(row) if row else None
