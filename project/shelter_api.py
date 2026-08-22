"""
더위쉼표 - 재난안전데이터공유플랫폼(safetydata.go.kr) 무더위쉼터 API 연동 (DAR-001, SIR-003)

API: 재난안전데이터공유플랫폼 (data.go.kr이 아님! 별도 플랫폼)
기본주소: https://www.safetydata.go.kr
데이터ID: /V2/api/DSSP-IF-10942

호출 규칙(이 플랫폼 공통 패턴):
    GET {기본주소}{데이터ID}?serviceKey=...&returnType=json&pageNo=1&numOfRows=100
    응답: {"header": {...}, "body": [ {...}, {...}, ... ]}  ← body가 바로 리스트

사용법:
    export SHELTER_API_KEY="발급받은_서비스키"

동작 원리:
    - SHELTER_API_KEY가 설정되어 있고 API 호출이 성공하면 실데이터 사용
    - 키가 없거나 API 호출 실패 시 shelters.csv 샘플 데이터로 자동 폴백
      (ai_guide.py의 AI/템플릿 폴백과 동일한 설계 원칙 — NFR-002 안정성)

주의:
    - 정확한 필드명(시설명/주소/좌표 등)은 실제 응답을 받아봐야 확정 가능해
      방어적으로 여러 후보 키를 시도한다. 실제 응답이 다르면 _extract_field()
      후보 목록을 조정할 것 (raw 응답은 fetch_shelters_from_api 호출 시
      st.session_state["_shelter_api_raw_sample"]에 1건 저장해둔다 — 디버깅용).
"""
import os
import re
import requests
import pandas as pd
import streamlit as st

BASE_URL = "https://www.safetydata.go.kr"
DATA_PATH = "/V2/api/DSSP-IF-10942"

# 시도 정식명칭 -> 우리 앱에서 쓰는 축약형
SIDO_ALIAS = {
    "대구광역시": "대구", "서울특별시": "서울", "부산광역시": "부산",
    "인천광역시": "인천", "광주광역시": "광주", "대전광역시": "대전",
    "울산광역시": "울산", "세종특별자치시": "세종", "경기도": "경기",
}
_SIDO_FULL_BY_SHORT = {v: k for k, v in SIDO_ALIAS.items()}

_REGION_PATTERN = re.compile(r"(\S+?(?:광역시|특별시|특별자치시|도))\s+(\S+?(?:구|군|시))")


def _address_matches_region(addr: str, region_keyword: str) -> bool:
    """
    주소가 특정 지역인지 정확히 판별한다.
    단순 substring 매칭("대구" in addr)은 '해운대구'(부산) 같은 구 이름에도
    우연히 걸리거나, 상호명의 '대구'(생선 이름) 등에 오탐할 수 있어
    시도 정식명칭("대구광역시") 단위로 매칭한다.
    """
    full_name = _SIDO_FULL_BY_SHORT.get(region_keyword)
    if full_name:
        return full_name in addr
    return region_keyword in addr  # SIDO_ALIAS에 없는 키워드는 기존 방식으로 폴백


def _extract_region(address: str, default: str = "대구 기타") -> str:
    """도로명주소 문자열에서 '대구 남구' 같은 지역명을 뽑아낸다"""
    if not address:
        return default
    m = _REGION_PATTERN.search(address)
    if not m:
        return default
    sido_raw, gu_gun = m.group(1), m.group(2)
    sido = SIDO_ALIAS.get(sido_raw, sido_raw)
    return f"{sido} {gu_gun}"


def _extract_field(item: dict, *candidates, default=""):
    """여러 후보 키 이름 중 실제 존재하는 값을 찾아 반환 (필드명 불확실성 대응)"""
    for key in candidates:
        if key in item and item[key] not in (None, ""):
            return item[key]
    return default


def _parse_time_field(raw, fallback: str) -> str:
    """
    '09:00', '0900', '09시' 등 다양한 형태를 'HH:MM'으로 정규화 시도.
    24시(2400) 같은 비정상 값은 23:59로 안전하게 보정하고,
    범위를 벗어나는 값은 fallback으로 대체한다.
    """
    if not raw:
        return fallback
    raw = str(raw).strip().replace("시", ":").replace("분", "")

    h, m = None, None
    if ":" in raw:
        parts = raw.split(":")
        try:
            h, m = int(parts[0]), int(parts[1][:2]) if len(parts) > 1 else 0
        except (ValueError, IndexError):
            return fallback
    elif raw.isdigit() and len(raw) == 4:
        h, m = int(raw[:2]), int(raw[2:])
    else:
        return fallback

    if h == 24:  # '2400'(자정까지 운영) 같은 표기 보정
        h, m = 23, 59
    if not (0 <= h <= 23 and 0 <= m <= 59):
        return fallback

    return f"{h:02d}:{m:02d}"


def _normalize_item(item: dict, idx: int) -> dict:
    """API 응답 1건을 우리 앱의 shelters.csv 스키마로 변환 (실제 응답 필드 확인 완료)"""
    address = _extract_field(item, "RN_DTL_ADRES", "DTL_ADRES", default="")

    return {
        "shelter_id": _extract_field(item, "RSTR_FCLTY_NO", default=f"api_{idx}"),
        "name": _extract_field(item, "RSTR_NM", default="이름없음"),
        "region": _extract_region(address),
        "dong": "",
        # 시설유형 코드(FCLTY_TY)의 코드-명칭 매핑표를 확보하지 못해 임시로 고정값 사용
        "facility_type": "공공시설",
        "address": address,
        "open_time": _parse_time_field(_extract_field(item, "WKDAY_OPER_BEGIN_TIME"), "09:00"),
        "close_time": _parse_time_field(_extract_field(item, "WKDAY_OPER_END_TIME"), "18:00"),
        "is_night_open": "Y" if str(
            _extract_field(item, "CHCK_MATTER_NIGHT_OPN_AT", default="N")
        ).upper().startswith("Y") else "N",
        "ac_count": int(_extract_field(item, "COLR_HOLD_ARCNDTN", default=0) or 0),
        "fan_count": int(_extract_field(item, "COLR_HOLD_ELEFN", default=0) or 0),
        "capacity": int(_extract_field(item, "USE_PSBL_NMPR", default=20) or 20),
        "lat": _extract_field(item, "LA", default=None),
        "lng": _extract_field(item, "LO", default=None),
    }


@st.cache_data(ttl=3600)
def fetch_shelters_from_api(region_keyword: str = "대구", page_size: int = 1000, max_pages: int = 15):
    """
    재난안전데이터공유플랫폼에서 실제 쉼터 데이터를 조회한다.
    전국 데이터가 페이지 단위로 오기 때문에, 원본 주소에 region_keyword가
    포함된 건만 먼저 걸러낸 뒤 정규화한다 (지역 오분류 방지 — 정규화 이후가 아니라
    원본 주소 문자열 기준으로 필터링해야 세종/부산 등 다른 지역이 섞이지 않는다).
    실패 시 None을 반환 (호출부에서 CSV 폴백 처리)
    """
    api_key = os.environ.get("SHELTER_API_KEY")
    if not api_key:
        return None

    matched_raw = []
    try:
        for page_no in range(1, max_pages + 1):
            params = {
                "serviceKey": api_key,
                "returnType": "json",
                "pageNo": page_no,
                "numOfRows": page_size,
            }
            resp = requests.get(BASE_URL + DATA_PATH, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            items = data.get("body", [])
            if items and page_no == 1:
                st.session_state["_shelter_api_raw_sample"] = items[0]  # 디버깅용

            if not items:
                break  # 더 이상 페이지 없음

            # 원본 주소 문자열 기준으로 먼저 필터링 (지역 오분류 방지 핵심)
            for item in items:
                addr = _extract_field(item, "RN_DTL_ADRES", "DTL_ADRES", default="")
                if _address_matches_region(addr, region_keyword):
                    matched_raw.append(item)

            total_count = data.get("totalCount", 0)
            if page_no * page_size >= total_count:
                break  # 전체 데이터 다 훑음

        if not matched_raw:
            st.session_state["_shelter_api_error"] = f"'{region_keyword}' 포함 주소를 찾지 못함 (최대 {max_pages}페이지 검색)"
            return None

        rows = [_normalize_item(item, i) for i, item in enumerate(matched_raw)]
        df = pd.DataFrame(rows)
        return df if not df.empty else None

    except Exception as e:
        st.session_state["_shelter_api_error"] = str(e)
        return None


def load_shelters(csv_path: str, region_keyword: str = "대구") -> tuple[pd.DataFrame, bool]:
    """
    쉼터 데이터 로드 (실 API 우선, 실패 시 CSV 폴백)
    반환: (데이터프레임, 실API사용여부)
    """
    api_df = fetch_shelters_from_api(region_keyword)
    if api_df is not None and not api_df.empty:
        return api_df, True

    return pd.read_csv(csv_path, encoding="utf-8-sig"), False

