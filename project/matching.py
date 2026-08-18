"""
더위쉼표 - 쉼터 매칭 로직 (MVP)
PRD §4 축소판: 지역 필터 + 운영시간 매칭 + 정렬
"""
import pandas as pd
from datetime import datetime, time


def _parse_time(t_str: str) -> time:
    """'09:00' -> time(9, 0)"""
    h, m = map(int, t_str.split(":"))
    return time(h, m)


def _get_availability(input_time: time, open_time: time, close_time: time) -> str:
    """
    입력 시간 기준 쉼터 이용 가능 상태 판정
    반환: 'available' | 'closing_soon' | 'unavailable'
    """
    # 자정 넘어가는 운영시간은 이번 MVP 범위에서 없다고 가정 (open < close)
    if not (open_time <= input_time <= close_time):
        return "unavailable"

    # 마감 30분 이내인지 체크
    input_minutes = input_time.hour * 60 + input_time.minute
    close_minutes = close_time.hour * 60 + close_time.minute
    if close_minutes - input_minutes <= 30:
        return "closing_soon"

    return "available"


# 활동유형별 표시용 우선 시설 유형 (필터링이 아니라 정렬 보정용, MVP 간소화)
ACTIVITY_PREFERRED_TYPE = {
    "산책": ["사회복지시설", "공공시설"],
    "장보기·용무": ["금융통신시설", "공공시설"],
    "업무(야외근로)": ["공공시설", "사회복지시설"],
    "등하교": ["공공시설"],
    "기타": [],
}

STATUS_LABEL = {
    "available": "🟢 지금 이용 가능",
    "closing_soon": "🟡 곧 마감",
    "unavailable": "🔴 운영시간 아님",
}

STATUS_ORDER = {"available": 0, "closing_soon": 1, "unavailable": 2}


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
    region : 예) "대구 북구"
    input_time_str : "HH:MM" 형식
    activity_type : ACTIVITY_PREFERRED_TYPE 키 중 하나
    top_n : 최대 반환 개수
    """
    input_time = _parse_time(input_time_str)

    # 1) 지역 필터
    result = df[df["region"] == region].copy()
    if result.empty:
        return result

    # 2) 운영시간 매칭
    result["availability"] = result.apply(
        lambda row: _get_availability(
            input_time, _parse_time(row["open_time"]), _parse_time(row["close_time"])
        ),
        axis=1,
    )
    result["status_label"] = result["availability"].map(STATUS_LABEL)

    # 3) 정렬: 이용가능 여부 우선, 그 다음 활동유형 선호 시설, 그 다음 냉방기 많은 순
    preferred_types = ACTIVITY_PREFERRED_TYPE.get(activity_type, [])
    result["_status_rank"] = result["availability"].map(STATUS_ORDER)
    result["_type_rank"] = result["facility_type"].apply(
        lambda t: preferred_types.index(t) if t in preferred_types else len(preferred_types)
    )

    result = result.sort_values(
        by=["_status_rank", "_type_rank", "ac_count"],
        ascending=[True, True, False],
    )

    result = result.drop(columns=["_status_rank", "_type_rank"])

    return result.head(top_n).reset_index(drop=True)


def generate_guide_text(row: pd.Series) -> str:
    """AI 없이 템플릿 기반 안내 문구 생성 (F2 축소판)"""
    status = row["status_label"]
    name = row["name"]
    address = row["address"]
    open_t, close_t = row["open_time"], row["close_time"]
    ac = row["ac_count"]

    if row["availability"] == "unavailable":
        return (
            f"{name}은(는) 현재 운영시간이 아닙니다 (운영시간: {open_t}~{close_t}). "
            f"다른 쉼터를 확인해보세요."
        )
    elif row["availability"] == "closing_soon":
        return (
            f"{name}은(는) 곧 문을 닫습니다 (마감: {close_t}). "
            f"서두르시면 이용 가능합니다."
        )
    else:
        return (
            f"{name}({address})은(는) 지금 이용 가능합니다. "
            f"에어컨 {ac}대가 있어 잠깐이라도 더위로부터 멀어지는 시간을 가지실 수 있어요."
        )
