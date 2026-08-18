# 더위쉼표 MVP (v3 — FastAPI 백엔드 + SQLite 저장 추가)

## 실행 방법

### 옵션 A. 백엔드 없이 (가장 간단, 로컬 직접호출로 자동 폴백)
```bash
pip install streamlit pandas folium streamlit-folium anthropic requests
streamlit run app.py
```
화면 상단에 "⚙️ 로컬 직접호출 (백엔드 미기동)"이라고 뜨면 정상입니다.

### 옵션 B. FastAPI 백엔드 포함 (SIR-002 요구사항 충족, RFP 전체 반영)
터미널 2개 필요:

```bash
# 터미널 1: 백엔드
pip install fastapi uvicorn
uvicorn api_server:app --reload --port 8000

# 터미널 2: 프론트엔드
streamlit run app.py
```
화면 상단에 "⚙️ FastAPI 백엔드 경유"라고 뜨면 성공입니다.
백엔드 API 문서는 http://localhost:8000/docs 에서 자동 생성된 Swagger UI로 확인 가능합니다.

## 공공데이터 API 연동 (선택)
```bash
export SHELTER_API_KEY="발급받은_디코딩_인증키"
```
키가 없으면 자동으로 shelters.csv 샘플 데이터를 사용합니다.

## 파일 구성
- `app.py` — Streamlit 화면. 백엔드 우선 호출, 실패 시 로컬 직접호출로 자동 폴백
- `api_server.py` — FastAPI 백엔드 (SIR-002). `/recommend`, `/shelters/all`, `/regions`, `/requests/recent` 제공
- `db.py` — SQLite 저장 계층 (DAR-004~007): 쉼터 캐싱, 추천요청/결과, AI안내문 저장
- `matching.py` — 핵심 매칭 로직 (지역/반경 필터 + 운영시간 매칭 + 거리계산 + 정렬)
- `geo.py` — 좌표 처리 + Haversine 거리계산
- `ai_guide.py` — Claude API 안내문구 생성 (실패 시 템플릿 폴백)
- `shelter_api.py` — 행안부 공공데이터 API 연동 (실패 시 CSV 폴백)
- `shelters.csv` — 샘플 쉼터 데이터 107개 (대구 8개 구·군)
- `heatway.db` — 최초 실행 시 자동 생성되는 SQLite 파일 (git에는 포함하지 마세요)

## 폴백 계층 구조 (설계 철학)
이 프로젝트는 모든 외부 의존성에 대해 "실패해도 죽지 않는" 폴백 구조를 일관되게 적용했습니다:
1. FastAPI 백엔드 → 응답 없으면 로컬 직접호출
2. 행안부 API → 응답 없으면 CSV 샘플 데이터
3. Claude AI 안내문 → 응답 없으면 f-string 템플릿 문구

## RFP 반영 현황 (최신)
- FUR/ALR 전체: ✅ (거리계산·반경검색·반경확장·정렬 전부 실제 동작 확인)
- DAR-004~007 (SQLite 저장): ✅ 이번에 추가
- SIR-002 (FastAPI): ✅ 이번에 추가
- SIR-003 (행안부 API): ✅ (승인 대기 중이면 자동으로 샘플 데이터 폴백)
- SIR-006 (기상청 API), FUR-002 (GPS/주소입력), FUR-018 (방문기록): 미구현 (선택 요구사항)

## 알려진 제약사항
- 쉼터 좌표는 실주소 지오코딩이 아닌 지역중심 기준 합성좌표(jitter)를 사용합니다.
  거리 계산 로직(Haversine, 반경검색, 정렬) 자체는 실제로 작동하지만, 기반 좌표가 샘플이라는 점을 발표 시 명시하는 것을 권장합니다.
