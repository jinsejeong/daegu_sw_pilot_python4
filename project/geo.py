"""
더위쉼표 - 지도/거리 계산용 좌표 처리 (MVP)
실제 쉼터 데이터에 좌표가 없으므로, 지역 대표 좌표 주변에 흩뿌려서 사용한다.
이 좌표는 지도 표시뿐 아니라 RFP FUR-008(거리 계산)의 실제 거리 산출에도 사용된다.
(실 서비스 전환 시 행안부 API 실좌표 또는 지오코딩으로 교체 — PRD §13 참고)
"""
import random
import math

# 대구 8개 구·군 대표 좌표 (구청 위치 기준 근사치)
REGION_CENTER = {
    "대구 중구": (35.8693, 128.6062),
    "대구 동구": (35.8869, 128.6357),
    "대구 서구": (35.8716, 128.5593),
    "대구 남구": (35.8461, 128.5972),
    "대구 북구": (35.8858, 128.5828),
    "대구 수성구": (35.8580, 128.6310),
    "대구 달서구": (35.8299, 128.5326),
    "대구 달성군": (35.7746, 128.4315),
}


def jitter_coords(region: str, seed_key: str, spread: float = 0.01):
    """
    지역 중심 좌표에서 seed_key(예: shelter_id)를 기준으로
    일관되게 흩뿌려진 좌표를 생성한다. (매번 랜덤이 바뀌지 않도록 시드 고정)
    """
    base_lat, base_lng = REGION_CENTER.get(region, (35.8714, 128.6014))  # fallback: 대구시청
    rng = random.Random(str(seed_key))
    lat = base_lat + rng.uniform(-spread, spread)
    lng = base_lng + rng.uniform(-spread, spread)
    return lat, lng


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    두 좌표 사이의 거리를 km 단위로 계산 (Haversine 공식, RFP ALR-004)
    """
    R = 6371.0  # 지구 반지름(km)
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lng2 - lng1)

    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def format_distance(km: float) -> str:
    """거리를 사람이 읽기 좋은 형태로 변환 (예: 350m, 1.2km)"""
    if km < 1:
        return f"{round(km * 1000)}m"
    return f"{km:.1f}km"