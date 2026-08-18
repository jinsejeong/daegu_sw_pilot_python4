import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
from datetime import datetime

from matching import recommend_shelters
from geo import jitter_coords, REGION_CENTER
from ai_guide import generate_ai_guide_text, _ANTHROPIC_AVAILABLE

st.set_page_config(page_title="더위쉼표", page_icon="🌤️", layout="centered")

# ---------- 스타일 ----------
st.markdown(
    """
    <style>
    /* 전체 배경 - 은은한 민트/스카이 그라데이션 */
    .stApp {
        background: linear-gradient(180deg, #F3FAF9 0%, #FFFFFF 35%);
    }

    /* 상단 메뉴바 */
    .heatway-navbar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 10px 4px;
        margin-bottom: 14px;
    }
    .heatway-navbar .brand {
        font-size: 1.15rem;
        font-weight: 800;
        color: #256F8D;
        display: flex;
        align-items: center;
        gap: 6px;
    }

    /* 히어로 헤더 */
    .heatway-hero {
        background: linear-gradient(120deg, #3AAFA9 0%, #2E86AB 100%);
        border-radius: 20px;
        padding: 28px 24px;
        margin-bottom: 12px;
        box-shadow: 0 8px 24px rgba(46, 134, 171, 0.18);
    }
    .heatway-hero h1 {
        color: white;
        font-size: 1.8rem;
        margin: 0 0 4px 0;
    }
    .heatway-hero p {
        color: rgba(255,255,255,0.9);
        margin: 0;
        font-size: 1rem;
    }

    /* 버튼 - 기본(주요 CTA: 쉼터 찾기) */
    button[kind="primary"] {
        background: linear-gradient(120deg, #3AAFA9 0%, #2E86AB 100%) !important;
        color: white !important;
        border-radius: 999px !important;
        height: 3em;
        font-weight: 700 !important;
        border: none !important;
        box-shadow: 0 4px 14px rgba(46, 134, 171, 0.25);
        transition: transform 0.15s ease;
    }
    button[kind="primary"]:hover {
        transform: translateY(-1px);
        background: linear-gradient(120deg, #2E9C96 0%, #256F8D 100%) !important;
        color: white !important;
    }

    /* 버튼 - 보조(홈 버튼 등) */
    button[kind="secondary"] {
        background: white !important;
        color: #2E86AB !important;
        border: 1.5px solid #BFE3E0 !important;
        border-radius: 999px !important;
        font-weight: 600 !important;
        box-shadow: none !important;
    }
    button[kind="secondary"]:hover {
        background: #EAF7F6 !important;
        color: #256F8D !important;
    }

    /* 결과 요약 캡션 */
    .heatway-summary {
        background: #EAF7F6;
        border-radius: 12px;
        padding: 10px 16px;
        color: #1f5f5c;
        font-size: 0.92rem;
        margin-bottom: 14px;
    }

    /* 쉼터 카드 */
    .heatway-card {
        border-radius: 14px;
        padding: 16px 18px;
        margin-bottom: 12px;
        background: #FFFFFF;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    }
    .heatway-card.status-available { border-left: 5px solid #2FAE7A; }
    .heatway-card.status-closing_soon { border-left: 5px solid #E8A93D; }
    .heatway-card.status-unavailable { border-left: 5px solid #B0B7BD; }

    .heatway-card .card-title {
        font-size: 1.05rem;
        font-weight: 700;
        margin-bottom: 6px;
        color: #1F2937;
    }
    .heatway-card .card-meta {
        color: #4B5563;
        font-size: 0.9rem;
        margin: 2px 0;
    }
    .heatway-card .card-guide {
        margin-top: 10px;
        background: #F3FAF9;
        border-radius: 10px;
        padding: 10px 12px;
        color: #1f5f5c;
        font-size: 0.9rem;
        line-height: 1.5;
    }

    /* 빈 상태 안내 */
    .heatway-empty {
        text-align: center;
        padding: 40px 20px;
        color: #6B7280;
    }
    .heatway-empty .icon { font-size: 2.4rem; margin-bottom: 8px; }

    /* 하단 캡션 */
    .heatway-footer {
        color: #9CA3AF;
        font-size: 0.78rem;
        text-align: center;
        margin-top: 8px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data
def load_shelters():
    return pd.read_csv("shelters.csv", encoding="utf-8-sig")


df = load_shelters()

# ---------- 세션 상태 초기화 ----------
if "results" not in st.session_state:
    st.session_state.results = None
    st.session_state.search_region = None
    st.session_state.search_time_str = None

# ---------- 상단 메뉴바 ----------
nav_left, nav_right = st.columns([4, 1])
with nav_left:
    st.markdown('<div class="heatway-navbar"><span class="brand">🌤️ 더위쉼표</span></div>', unsafe_allow_html=True)
with nav_right:
    home_clicked = st.button("🏠 홈", type="secondary", key="home_btn", use_container_width=True)

if home_clicked:
    st.session_state.results = None
    st.session_state.search_region = None
    st.session_state.search_time_str = None
    st.rerun()

# ---------- 헤더 ----------
st.markdown(
    """
    <div class="heatway-hero">
        <h1>🌤️ 더위쉼표</h1>
        <p>더위로부터, 잠시 멀어지세요</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------- 입력 ----------
col1, col2 = st.columns(2)
with col1:
    region = st.selectbox("📍 지역", sorted(df["region"].unique()))
with col2:
    # 기본값을 세션에 한 번만 저장 (매 rerun마다 datetime.now()가 재계산되어
    # 사용자가 고른 시간을 덮어쓰는 문제 방지)
    if "default_time" not in st.session_state:
        st.session_state.default_time = datetime.now().time()
    input_time = st.time_input(
        "🕐 방문 예정 시간",
        value=st.session_state.default_time,
        key="visit_time",
    )

activity_type = st.selectbox(
    "🚶 활동유형",
    ["산책", "장보기·용무", "업무(야외근로)", "등하교", "기타"],
)

search_clicked = st.button("쉼터 찾기", type="primary", use_container_width=True)

st.divider()

# ---------- 결과 ----------
if search_clicked:
    time_str = input_time.strftime("%H:%M")
    st.session_state.results = recommend_shelters(df, region, time_str, activity_type, top_n=10)
    st.session_state.search_region = region
    st.session_state.search_time_str = time_str

if st.session_state.results is not None:
    results = st.session_state.results
    region = st.session_state.search_region
    time_str = st.session_state.search_time_str

    # 엣지케이스 1: 지역 내 쉼터 자체가 없는 경우
    if results.empty:
        st.warning(f"'{region}'에 등록된 쉼터가 없습니다. 다른 지역을 선택해보세요.")

    else:
        n_available = (results["availability"] == "available").sum()
        n_closing = (results["availability"] == "closing_soon").sum()

        # 엣지케이스 2: 전부 운영시간 밖인 경우
        if n_available == 0 and n_closing == 0:
            next_open = results.sort_values("open_time").iloc[0]
            st.error(
                f"지금은 운영 중인 쉼터가 없습니다. "
                f"가장 빨리 여는 곳은 **{next_open['name']}** (운영시간 {next_open['open_time']}~{next_open['close_time']})입니다."
            )
        else:
            st.subheader(f"{region} 무더위쉼터 ({time_str} 기준)")
            st.markdown(
                f'<div class="heatway-summary">🟢 지금 이용 가능한 곳 {n_available}곳을 포함해 총 {len(results)}곳을 찾았어요.</div>',
                unsafe_allow_html=True,
            )

        # ---------- 지도 ----------
        center_lat, center_lng = REGION_CENTER.get(region, (35.8714, 128.6014))
        m = folium.Map(
            location=[center_lat, center_lng],
            zoom_start=13,
            tiles="CartoDB positron",  # 더 깔끔하고 밝은 베이스맵
        )

        # 브랜드 컬러 기반 상태별 색상 (마커/팝업 공통)
        STATUS_COLOR = {
            "available": "#2E9C96",     # 브랜드 틸(메인 컬러)
            "closing_soon": "#E8A93D",  # 앰버
            "unavailable": "#E4572E",   # 레드
        }

        for _, row in results.iterrows():
            lat, lng = jitter_coords(region, row["shelter_id"])
            color = STATUS_COLOR.get(row["availability"], "#9CA3AF")

            # 브랜드 컬러의 커스텀 원형 마커 (DivIcon)
            marker_html = f"""
                <div style="
                    width: 18px; height: 18px;
                    background: {color};
                    border: 3px solid white;
                    border-radius: 50%;
                    box-shadow: 0 2px 6px rgba(0,0,0,0.35);
                "></div>
            """

            # 팝업: 상태색 테두리를 가진 미니 카드
            popup_html = f"""
                <div style="
                    border-left: 4px solid {color};
                    padding: 6px 10px;
                    font-family: sans-serif;
                    min-width: 160px;
                ">
                    <div style="font-weight:700; font-size:0.95rem; margin-bottom:2px;">{row['name']}</div>
                    <div style="color:{color}; font-size:0.85rem; font-weight:600;">{row['status_label']}</div>
                </div>
            """

            folium.Marker(
                location=[lat, lng],
                tooltip=row["name"],
                popup=folium.Popup(popup_html, max_width=220),
                icon=folium.DivIcon(html=marker_html),
            ).add_to(m)

        # st_folium 대신 folium_static 사용 (버전 호환성 이슈 회피)
        folium_static(m, width=700, height=420)
        st.caption(
            "⚠️ 지도상 위치는 실제 주소가 아닌 지역 내 임의 배치입니다 (샘플 데이터 특성상 좌표 미포함). "
            "핀 색상 · 팝업 테두리는 이용 가능 여부를 나타냅니다 (틸=가능 / 주황=곧마감 / 빨강=불가)."
        )

        # ---------- 카드 리스트 ----------
        for _, row in results.iterrows():
            night_badge = " · 🌙 야간개방" if row["is_night_open"] == "Y" else ""
            guide_text = generate_ai_guide_text(row)
            st.markdown(
                f"""
                <div class="heatway-card status-{row['availability']}">
                    <div class="card-title">{row['status_label']} · {row['name']}</div>
                    <div class="card-meta">📮 {row['address']}</div>
                    <div class="card-meta">🕐 운영시간 {row['open_time']}~{row['close_time']}{night_badge}</div>
                    <div class="card-meta">❄️ 에어컨 {row['ac_count']}대 · 선풍기 {row['fan_count']}대 · 수용 {row['capacity']}명</div>
                    <div class="card-guide">{guide_text}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

else:
    st.markdown(
        """
        <div class="heatway-empty">
            <div class="icon"></div>
            지역, 시간, 활동유형을 선택하고<br>'쉼터 찾기'를 눌러주세요.
        </div>
        """,
        unsafe_allow_html=True,
    )

# ---------- 하단 안내 ----------
st.divider()
ai_status = "Claude API 연동됨" if _ANTHROPIC_AVAILABLE else "템플릿 문구 사용 중 (ANTHROPIC_API_KEY 미설정)"
st.markdown(
    f"""
    <div class="heatway-footer">
        ℹ️ 데모 버전 안내: 쉼터 데이터는 실제 서비스 스키마를 기반으로 한 샘플입니다.
        실제 서비스에서는 행정안전부 무더위쉼터 표준데이터(data.go.kr)와 연동됩니다.<br>
        안내문구 생성: {ai_status}
    </div>
    """,
    unsafe_allow_html=True,
)