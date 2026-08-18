# 더위쉼표 MVP (v2)

## 실행 방법
```bash
pip install streamlit pandas folium streamlit-folium anthropic
cd heatway-mvp
streamlit run app.py
```

## AI 안내문구 (선택)
Claude API로 자연스러운 안내문구를 생성하려면 환경변수 설정:
```bash
export ANTHROPIC_API_KEY="your-key-here"
streamlit run app.py
```
키가 없으면 자동으로 템플릿 문구(f-string 기반)로 폴백되므로, 키 없이도 정상 작동합니다.

## 파일 구성
- `app.py` — Streamlit 화면 (입력 → 지도 → 결과 카드)
- `matching.py` — 핵심 매칭 로직 (지역 필터 + 운영시간 매칭 + 정렬) + 템플릿 안내문구
- `geo.py` — 지도용 좌표 처리 (지역 대표 좌표 + 지터링, 실좌표 없을 때 대체 방식)
- `ai_guide.py` — Claude API 안내문구 생성 (실패 시 템플릿 자동 폴백)
- `shelters.csv` — 샘플 쉼터 데이터 107개 (대구 8개 구·군)

## v2에서 추가된 것
1. ✅ Folium 지도 (이용가능=초록, 곧마감=주황, 불가=회색 마커)
2. ✅ AI 안내문구 실연동 (Claude API, 실패 시 안전하게 템플릿 폴백)
3. ✅ UI 폴리싱 (버튼 색상, 카드 라운딩)
4. ✅ 엣지케이스 처리 (쉼터 없음 / 전체 운영시간 밖 → "가장 빨리 여는 곳" 안내)

## 알려진 제약사항 (발표 시 참고)
- 좌표가 없는 샘플 데이터라 지도 마커는 지역 내 임의 배치입니다. 화면에도 안내 문구로 명시해뒀습니다.
- 실 서비스 전환 시 행정안전부 무더위쉼터 API(data.go.kr) 연동으로 shelters.csv를 교체하면 됩니다.

## 다음에 시간 남으면
- 활동유형별 실제 반경/필터링 고도화 (PRD §4.3)
- 쉼터 상세 페이지 분리
- 모바일 반응형 레이아웃 점검