"""
더위쉼표 - 지도용 좌표 처리 (MVP)
실제 쉼터 데이터에 좌표가 없으므로, 지역 대표 좌표 주변에 흩뿌려서 표시한다.
(실 서비스 전환 시 행안부 API 실좌표 또는 지오코딩으로 교체 — PRD §13 참고)
"""
import random

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
