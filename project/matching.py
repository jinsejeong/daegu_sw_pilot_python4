"""
더위쉼표 - 쉼터 매칭 로직 (MVP)
RFP 대응: 지역(사용자 위치 proxy) 필터 + 활동유형별 반경 검색(FUR-004, ALR-001)
+ 운영시간 매칭(FUR-006/007) + 거리 계산(FUR-008, ALR-004) + 반경확장(ALR-007)
+ 이용가능여부·거리 순 정렬(FUR-009, ALR-005/006)

주의: 쉼터 실좌표가 없어 geo.jitter_coords()로 지역 중심 근처에 흩뿌린 좌표를 사용한다.
사용자 위치는 GPS/주소 입력 대신 '지역 선택'을 좌표 프록시로 사용한다 (geo.REGION_CENTER).
실제 서비스 전환 시 행안부 API 실좌표 + GPS/지오코딩 기반 사용자 위치로 교체 필요.
"""
import pandas as pd
from datetime import datetime, time

from geo import REGION_CENTER, jitter_coords, haversine_km, format_distance


def _parse_time(t_str: str) -> time:
    """
    'HH:MM' -> time(H, M) 변환.
    실 API 데이터에 24시(2400) 같은 비정상 값이 섞여올 수 있어 방어적으로 처리한다.
    파싱 실패/범위 초과 시 자정(00:00)으로 안전하게 대체한다.
    """
    try:
        h, m = map(int, str(t_str).split(":"))
        h = max(0, min(h, 23))
        m = max(0, min(m, 59))
        return time(h, m)
    except (ValueError, AttributeError, TypeError):
        return time(0, 0)


def _get_availability(input_time: time, open_time: time, close_time: time) -> str:
    """
    입력 시간 기준 쉼터 이용 가능 상태 판정
    반환: 'available' | 'closing_soon' | 'unavailable'
    """
    # 자정 넘어가는 운영시간은 이번 MVP 범위에서 없다고 가정 (open < close)
    if not (open_time <= input_time <= close_time):
        return "unavailable"

    # 마감 30분 이내인지 체크 (ALR-003)
    input_minutes = input_time.hour * 60 + input_time.minute
    close_minutes = close_time.hour * 60 + close_time.minute
    if close_minutes - input_minutes <= 30:
        return "closing_soon"

    return "available"


STATUS_LABEL = {
    "available": "🟢 지금 이용 가능",
    "closing_soon": "🟡 곧 마감",
    "unavailable": "🔴 운영시간 아님",
}

STATUS_ORDER = {"available": 0, "closing_soon": 1, "unavailable": 2}

# 활동유형별 기본 검색 반경(km) — RFP FUR-004 / ALR-001 / PRD §4.3
ACTIVITY_RADIUS_KM = {
    "산책": 0.5,
    "장보기·용무": 0.8,
    "업무(야외근로)": 2.0,
    "등하교": 0.5,
    "기타": 1.0,
}

# 반경 확장 배수 (ALR-007: 결과가 없으면 반경을 확장)
RADIUS_EXPAND_STEPS = [1, 2, 4, 999]  # 마지막(999)은 사실상 무제한(지역 전체) 폴백


def _ensure_coords(df: pd.DataFrame) -> pd.DataFrame:
    """
    좌표(lat/lng)를 보장한다.
    행안부 API로 받아온 실좌표(DAR-003)가 있으면 그대로 유지하고,
    좌표가 없는 행(CSV 샘플 데이터 등)만 지역 중심 기반 합성좌표로 보완한다.
    """
    df = df.copy()
    if "lat" not in df.columns:
        df["lat"] = None
    if "lng" not in df.columns:
        df["lng"] = None

    missing = df["lat"].isna() | df["lng"].isna()
    if missing.any():
        coords = df.loc[missing].apply(
            lambda row: jitter_coords(row["region"], row["shelter_id"]), axis=1
        )
        df.loc[missing, "lat"] = coords.apply(lambda c: c[0])
        df.loc[missing, "lng"] = coords.apply(lambda c: c[1])

    df["lat"] = df["lat"].astype(float)
    df["lng"] = df["lng"].astype(float)
    df["_coords_synthetic"] = missing  # 이 행의 좌표가 합성인지 표시 (투명성용)
    return df


def recommend_shelters(
    df: pd.DataFrame,
    region: str,
    input_time_str: str,
    activity_type: str = "기타",
    top_n: int = 10,
) -> pd.DataFrame:
    """
    위치(지역)·시간·활동유형을 받아 추천 쉼터 리스트 반환

    Parameters
    ----------
    df : 전체 쉼터 데이터프레임 (shelters.csv 로드 결과)
    region : 예) "대구 북구" — 사용자 위치의 프록시로 사용 (지역 중심좌표)
    input_time_str : "HH:MM" 형식
    activity_type : ACTIVITY_RADIUS_KM 키 중 하나, 검색 반경 결정에 사용
    top_n : 최대 반환 개수
    """
    input_time = _parse_time(input_time_str)
    base_radius = ACTIVITY_RADIUS_KM.get(activity_type, 1.0)

    # 1) 지역 필터 (사용자 위치가 속한 지역의 쉼터 후보군)
    candidates = df[df["region"] == region].copy()
    if candidates.empty:
        return candidates

    user_lat, user_lng = REGION_CENTER.get(region, (35.8714, 128.6014))

    # 2) 쉼터별 좌표 확보 + 사용자 위치 기준 거리 계산 (FUR-008, ALR-004)
    #    실좌표(행안부 API)는 그대로 쓰고, 없는 경우만 합성좌표로 보완 (DAR-003)
    candidates = _ensure_coords(candidates)
    candidates["distance_km"] = candidates.apply(
        lambda row: haversine_km(user_lat, user_lng, row["lat"], row["lng"]), axis=1
    )

    # 3) 활동유형별 반경 검색 + 결과 없으면 반경 확장 (ALR-001, ALR-007)
    result = pd.DataFrame()
    expanded = False
    for i, multiplier in enumerate(RADIUS_EXPAND_STEPS):
        radius = base_radius * multiplier
        result = candidates[candidates["distance_km"] <= radius].copy()
        if not result.empty:
            expanded = i > 0
            break
    if result.empty:
        # 반경 무제한으로도 없으면 지역 후보 전체를 그대로 사용 (최후 폴백)
        result = candidates.copy()
        expanded = True

    # 4) 운영시간 매칭 (FUR-006, FUR-007)
    result["availability"] = result.apply(
        lambda row: _get_availability(
            input_time, _parse_time(row["open_time"]), _parse_time(row["close_time"])
        ),
        axis=1,
    )
    result["status_label"] = result["availability"].map(STATUS_LABEL)
    result["distance_label"] = result["distance_km"].apply(format_distance)

    # 5) 정렬: 이용가능 여부 우선 → 거리순 → 냉방기 많은 순 (FUR-009, ALR-005, ALR-006)
    result["_status_rank"] = result["availability"].map(STATUS_ORDER)

    result = result.sort_values(
        by=["_status_rank", "distance_km", "ac_count"],
        ascending=[True, True, False],
    )

    result = result.drop(columns=["_status_rank"])
    result["_expanded"] = expanded
    result["_base_radius_km"] = base_radius

    return result.head(top_n).reset_index(drop=True)


def annotate_availability(df: pd.DataFrame, input_time_str: str) -> pd.DataFrame:
    """
    지역 필터 없이 전체 쉼터에 이용 가능 여부만 부여한다.
    "전체 쉼터 보기" 화면처럼 필터링 없이 전체를 보여줄 때 사용.
    """
    input_time = _parse_time(input_time_str)
    result = df.copy()
    result["availability"] = result.apply(
        lambda row: _get_availability(
            input_time, _parse_time(row["open_time"]), _parse_time(row["close_time"])
        ),
        axis=1,
    )
    result["status_label"] = result["availability"].map(STATUS_LABEL)
    result = _ensure_coords(result)  # 지도 표시용 좌표 보장 (실좌표 우선, 없으면 합성)
    return result


def generate_guide_text(row: pd.Series) -> str:
    """AI 없이 템플릿 기반 안내 문구 생성 (F2 축소판)"""
    name = row["name"]
    address = row["address"]
    open_t, close_t = row["open_time"], row["close_time"]
    ac = row["ac_count"]
    distance = row.get("distance_label", None)
    distance_txt = f"{distance} 거리에 있으며, " if distance else ""

    if row["availability"] == "unavailable":
        return (
            f"{name}은(는) {distance_txt}현재 운영시간이 아닙니다 (운영시간: {open_t}~{close_t}). "
            f"다른 쉼터를 확인해보세요."
        )
    elif row["availability"] == "closing_soon":
        return (
            f"{name}은(는) {distance_txt}곧 문을 닫습니다 (마감: {close_t}). "
            f"서두르시면 이용 가능합니다."
        )
    else:
        return (
            f"{name}({address})은(는) {distance_txt}지금 이용 가능합니다. "
            f"에어컨 {ac}대가 있어 잠깐이라도 더위로부터 멀어지는 시간을 가지실 수 있어요."
        )
