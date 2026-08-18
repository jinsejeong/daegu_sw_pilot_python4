# 더위쉼표 MVP

## 실행 방법
```bash
pip install streamlit pandas
cd heatway-mvp
streamlit run app.py
```

## 파일 구성
- `app.py` — Streamlit 화면 (입력 → 결과 출력)
- `matching.py` — 핵심 로직 (지역 필터 + 운영시간 매칭 + 정렬 + 안내문구 생성)
- `shelters.csv` — 샘플 쉼터 데이터 107개 (대구 8개 구·군)

## 다음에 시간 남으면 추가할 것
1. UI 색상/폰트 다듬기 (톤: "더위로부터 잠시 멀어지자")
2. Folium 지도 추가
3. generate_guide_text()를 Claude API 호출로 교체 (지금은 템플릿 기반)
4. 실제 행안부 API 연동으로 shelters.csv 교체
