"""
더위쉼표 - FastAPI 백엔드 (RFP SIR-002)

기존 matching.py / geo.py / ai_guide.py / shelter_api.py 로직을 그대로 재사용하고,
여기에 REST API 계층 + SQLite 저장(db.py)만 얹은 구조.

실행:
    uvicorn api_server:app --reload --port 8000

Streamlit(app.py)은 이 서버가 켜져 있으면 API를 통해 데이터를 받고,
서버가 꺼져 있으면 자동으로 로컬 직접호출로 폴백한다 (app.py 참고).
"""
from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()  # .env 파일에서 SHELTER_API_KEY, ANTHROPIC_API_KEY 등을 읽어옴
               # (별도 프로세스이므로 app.py의 load_dotenv()와 별개로 여기서도 필요)

from matching import recommend_shelters, annotate_availability
from ai_guide import generate_ai_guide_text
from shelter_api import load_shelters as load_shelters_api
import db

app = FastAPI(title="더위쉼표 API", version="1.0")
db.init_db()

# 쉼터 데이터는 프로세스 내 메모리에 캐싱 (요청마다 CSV/API 재조회 방지)
_cache = {"df": None, "using_real_api": False}


def _get_df():
    if _cache["df"] is None:
        df, using_real_api = load_shelters_api("shelters.csv", region_keyword="대구")
        _cache["df"] = df
        _cache["using_real_api"] = using_real_api
        db.upsert_shelters(df)  # DAR-004
    return _cache["df"], _cache["using_real_api"]


class RecommendRequest(BaseModel):
    region: str
    time: str  # "HH:MM"
    activity_type: str = "기타"
    top_n: int = 10


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/regions")
def get_regions():
    df, _ = _get_df()
    return sorted(df["region"].unique().tolist())


@app.post("/recommend")
def recommend(req: RecommendRequest):
    """
    FUR-001~012, ALR-001~008 핵심 추천 흐름을 REST API로 노출.
    호출마다 DAR-005/006/007에 따라 요청·결과·AI안내문을 SQLite에 저장한다.
    """
    df, using_real_api = _get_df()
    results = recommend_shelters(df, req.region, req.time, req.activity_type, top_n=req.top_n)

    if results.empty:
        return {
            "results": [], "expanded": False, "base_radius_km": None,
            "using_real_api": using_real_api, "request_id": None,
        }

    expanded = bool(results["_expanded"].iloc[0])
    base_radius = float(results["_base_radius_km"].iloc[0])

    # DAR-005, DAR-006: 요청·결과 저장
    request_id = db.save_recommendation(
        req.region, req.time, req.activity_type, base_radius, expanded, using_real_api, results
    )

    items = []
    for _, row in results.iterrows():
        guide_text = generate_ai_guide_text(row)
        db.save_guide_text(request_id, row["shelter_id"], guide_text)  # DAR-007

        items.append({
            "shelter_id": str(row["shelter_id"]),
            "name": row["name"],
            "region": row["region"],
            "address": row["address"],
            "open_time": row["open_time"],
            "close_time": row["close_time"],
            "is_night_open": row["is_night_open"],
            "ac_count": int(row["ac_count"]),
            "fan_count": int(row["fan_count"]),
            "capacity": int(row["capacity"]),
            "availability": row["availability"],
            "status_label": row["status_label"],
            "distance_km": float(row["distance_km"]),
            "distance_label": row["distance_label"],
            "guide_text": guide_text,
            "lat": float(row["lat"]),
            "lng": float(row["lng"]),
            "_coords_synthetic": bool(row.get("_coords_synthetic", False)),
        })

    return {
        "request_id": request_id,
        "results": items,
        "expanded": expanded,
        "base_radius_km": base_radius,
        "using_real_api": using_real_api,
    }


@app.get("/shelters/all")
def shelters_all(time: str):
    """"전체 쉼터 보기" 화면용 - 지역 필터 없이 전체 쉼터 + 이용가능여부"""
    df, using_real_api = _get_df()
    annotated = annotate_availability(df, time)
    return {
        "using_real_api": using_real_api,
        "items": annotated.to_dict(orient="records"),
    }


@app.get("/requests/recent")
def recent_requests(limit: int = 20):
    """운영/디버그용: 최근 추천 요청 이력 (DAR-005 저장 확인용)"""
    return db.get_recent_requests(limit)
