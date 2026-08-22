"""
더위쉼표 - AI 방문 안내 문구 생성 (F2)
설계 원칙(PRD §3 F2): LLM은 새 판단을 하지 않고, 이미 계산된 사실(쉼터명/거리/운영시간)만
문장으로 조립한다. 쉼터명 등 고유명사는 프롬프트에 명시적으로 제공하고,
API 호출 실패 시 템플릿 문구로 폴백한다.
"""
import os
from matching import generate_guide_text as _template_guide_text

_client = None
_ANTHROPIC_AVAILABLE = False

try:
    import anthropic

    if os.environ.get("ANTHROPIC_API_KEY"):
        _client = anthropic.Anthropic()
        _ANTHROPIC_AVAILABLE = True
except ImportError:
    pass


def generate_ai_guide_text(row) -> str:
    """
    row: matching.recommend_shelters()가 반환한 DataFrame의 한 행 (Series)
    """
    if not _ANTHROPIC_AVAILABLE:
        return _template_guide_text(row)

    distance_line = f"거리: {row['distance_label']}\n" if "distance_label" in row and row["distance_label"] else ""
    facts = (
        f"쉼터명: {row['name']}\n"
        f"주소: {row['address']}\n"
        f"{distance_line}"
        f"운영시간: {row['open_time']}~{row['close_time']}\n"
        f"현재 상태: {row['status_label']}\n"
        f"에어컨 {row['ac_count']}대, 선풍기 {row['fan_count']}대, 수용인원 {row['capacity']}명"
    )

    prompt = f"""다음 사실 정보만을 사용해서, 폭염 취약계층에게 무더위쉼터를 안내하는 짧은 문구를 1~2문장으로 작성해줘.

[사실 정보]
{facts}

[작성 규칙]
- 제공된 사실 외의 새로운 정보나 판단을 추가하지 마라.
- 위 정보에 없는 거리, 시간, 시설명을 지어내지 마라.
- 어조는 담백하고 여유 있게. "더위로부터 잠시 멀어지세요" 같은 휴식 제안형 톤.
- 경고나 위협적인 표현은 쓰지 마라.
- 문구만 출력하고 다른 설명은 붙이지 마라.
"""

    try:
        response = _client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(
            block.text for block in response.content if block.type == "text"
        ).strip()
        return text if text else _template_guide_text(row)
    except Exception:
        # API 실패 시 조용히 템플릿으로 폴백 (데모 중 에러로 끊기지 않도록)
        return _template_guide_text(row)
