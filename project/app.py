import streamlit as st
import pandas as pd
import folium
import base64
from pathlib import Path
from streamlit_folium import folium_static
from datetime import datetime

from matching import recommend_shelters, annotate_availability
from geo import jitter_coords, REGION_CENTER
from ai_guide import generate_ai_guide_text, _ANTHROPIC_AVAILABLE

LOGO_PATH = Path(__file__).parent / "logo.png"

# set_page_config는 반드시 스크립트에서 가장 먼저 실행되는 Streamlit 명령이어야 함
st.set_page_config(
    page_title="더위쉼표",
    page_icon=str(LOGO_PATH),
    layout="centered",
)


@st.cache_data
def get_logo_base64():
    return base64.b64encode(LOGO_PATH.read_bytes()).decode()


LOGO_B64 = get_logo_base64()

# ---------- 스타일 ----------
st.markdown(
    """
    <style>
    /* 전체 배경 - 은은한 민트/스카이 그라데이션 */
    .stApp {
        background: linear-gradient(180deg, #F3FAF9 0%, #FFFFFF 35%);
    }

    /* 햄버거 토글 메뉴 */
    .heatway-topbar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 4px 0 12px 0;
    }
    .heatway-topbar .brand {
        font-size: 1.15rem;
        font-weight: 800;
        color: #256F8D;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .heatway-topbar .brand img {
        height: 30px;
        width: 30px;
        object-fit: contain;
    }
    .heatway-menu-panel {
        background: linear-gradient(180deg, #EAF7F6 0%, #F7FBFB 100%);
        border-radius: 16px;
        padding: 14px;
        margin-bottom: 16px;
        box-shadow: 0 4px 16px rgba(0,0,0,0.06);
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
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .heatway-hero h1 img {
        height: 40px;
        width: 40px;
        object-fit: contain;
        background: white;
        border-radius: 10px;
        padding: 4px;
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

    /* 패널 공통 (소개/이용법/폭염정보) */
    .heatway-panel {
        background: white;
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0 2px 12px rgba(0,0,0,0.06);
        margin-bottom: 16px;
    }
    .heatway-panel h3 {
        color: #256F8D;
        margin-top: 0;
    }
    .heatway-step {
        display: flex;
        align-items: flex-start;
        gap: 12px;
        margin-bottom: 14px;
    }
    .heatway-step .num {
        background: linear-gradient(120deg, #3AAFA9 0%, #2E86AB 100%);
        color: white;
        width: 28px; height: 28px;
        border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-weight: 700;
        flex-shrink: 0;
        font-size: 0.9rem;
    }
    .heatway-step .txt { color: #374151; padding-top: 3px; }

    /* 폭염 정보 배너 (홈 화면 상단에 통합) - 카드 톤에 맞춘 절제된 스타일 */
    .heat-banner {
        background: #FFFFFF;
        border-left: 4px solid #E4572E;
        border-radius: 12px;
        padding: 14px 18px;
        margin-bottom: 16px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .heat-banner .icon { font-size: 1.5rem; }
    .heat-banner .headline { font-size: 0.95rem; font-weight: 700; margin-bottom: 2px; color: #1F2937; }
    .heat-banner .sub { font-size: 0.85rem; color: #6B7280; }
    </style>
    """,
    unsafe_allow_html=True,
)


def build_shelter_map(rows_df, center_lat, center_lng, zoom_start=13, map_height=420):
    """공통 지도 렌더링 함수 (검색 결과 / 전체 쉼터 보기 둘 다 사용)"""
    m = folium.Map(location=[center_lat, center_lng], zoom_start=zoom_start, tiles="CartoDB positron")

    STATUS_COLOR = {
        "available": "#2E9C96",
        "closing_soon": "#E8A93D",
        "unavailable": "#E4572E",
    }

    for _, row in rows_df.iterrows():
        lat, lng = jitter_coords(row["region"], row["shelter_id"])
        color = STATUS_COLOR.get(row["availability"], "#9CA3AF")

        marker_html = f"""
            <div style="
                width: 16px; height: 16px;
                background: {color};
                border: 3px solid white;
                border-radius: 50%;
                box-shadow: 0 2px 6px rgba(0,0,0,0.35);
            "></div>
        """
        popup_html = f"""
            <div style="border-left: 4px solid {color}; padding: 6px 10px; font-family: sans-serif; min-width: 160px;">
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

    folium_static(m, width=700, height=map_height)


@st.cache_data
def load_shelters():
    return pd.read_csv("shelters.csv", encoding="utf-8-sig")


df = load_shelters()

# ---------- 세션 상태 초기화 ----------
if "results" not in st.session_state:
    st.session_state.results = None
    st.session_state.search_region = None
    st.session_state.search_time_str = None
if "view" not in st.session_state:
    st.session_state.view = "search"  # search | info | all_shelters
if "menu_open" not in st.session_state:
    st.session_state.menu_open = False

# ---------- 상단 바: 브랜드 + 햄버거 토글 ----------
top_left, top_right = st.columns([5, 1])
with top_left:
    st.markdown(
        f'<div class="heatway-topbar"><span class="brand">'
        f'<img src="data:image/png;base64,{LOGO_B64}" alt="더위쉼표 로고"/>더위쉼표</span></div>',
        unsafe_allow_html=True,
    )
with top_right:
    hamburger_clicked = st.button("☰", key="hamburger_btn", use_container_width=True)

if hamburger_clicked:
    st.session_state.menu_open = not st.session_state.menu_open

home_clicked = info_clicked = all_clicked = False

# ---------- 토글로 열고 닫히는 메뉴 패널 ----------
if st.session_state.menu_open:
    st.markdown('<div class="heatway-menu-panel">', unsafe_allow_html=True)
    m1, m2, m3 = st.columns(3)
    with m1:
        home_clicked = st.button("🏠 홈", type="secondary", key="home_btn", use_container_width=True)
    with m2:
        info_clicked = st.button("ℹ️ 소개·이용방법", type="secondary", key="info_btn", use_container_width=True)
    with m3:
        all_clicked = st.button("🗺️ 전체 쉼터", type="secondary", key="all_btn", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

if home_clicked:
    st.session_state.view = "search"
    st.session_state.results = None
    st.session_state.search_region = None
    st.session_state.search_time_str = None
    st.session_state.menu_open = False
    st.rerun()
if info_clicked:
    st.session_state.view = "info"
    st.session_state.menu_open = False
if all_clicked:
    st.session_state.view = "all_shelters"
    st.session_state.menu_open = False

# =========================================================
# 뷰: 서비스 소개 + 이용방법
# =========================================================
if st.session_state.view == "info":
    st.markdown(
        """
        <div class="heatway-panel">
            <h3>🌤️ 더위쉼표는요</h3>
            <p style="color:#374151; line-height:1.7;">
                더위쉼표는 위치·시간·활동유형을 입력하면, 그 조건에서 <b>지금 실제로 이용 가능한</b>
                무더위쉼터를 추천해주는 서비스예요.<br>
                복잡한 판단은 서비스가 대신하고, 사용자는 잠깐이라도 더위로부터 멀어질 곳을 바로 찾을 수 있도록 만들었어요.
            </p>
        </div>
        <div class="heatway-panel">
            <h3>📋 이용 방법</h3>
            <div class="heatway-step"><div class="num">1</div><div class="txt">지역, 방문 예정 시간, 활동유형을 선택하세요.</div></div>
            <div class="heatway-step"><div class="num">2</div><div class="txt">'쉼터 찾기'를 누르면 지금 이용 가능한 쉼터부터 정렬해서 보여드려요.</div></div>
            <div class="heatway-step"><div class="num">3</div><div class="txt">지도에서 색깔로 상태를 확인하고, 카드에서 상세 정보와 안내 문구를 읽어보세요.</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("← 검색으로 돌아가기"):
        st.session_state.view = "search"
        st.rerun()

# =========================================================
# 뷰: 전체 쉼터 보기
# =========================================================
elif st.session_state.view == "all_shelters":
    now_str = datetime.now().strftime("%H:%M")
    annotated = annotate_availability(df, now_str)
    n_avail = (annotated["availability"] == "available").sum()

    st.subheader(f"대구 전체 무더위쉼터 ({now_str} 기준)")
    st.markdown(
        f'<div class="heatway-summary">📍 총 {len(annotated)}곳 중 지금 이용 가능한 곳 {n_avail}곳</div>',
        unsafe_allow_html=True,
    )
    build_shelter_map(annotated, 35.8714, 128.6014, zoom_start=11, map_height=460)
    st.caption("⚠️ 지도상 위치는 실제 주소가 아닌 지역 내 임의 배치입니다 (샘플 데이터 특성상 좌표 미포함).")
    if st.button("← 검색으로 돌아가기"):
        st.session_state.view = "search"
        st.rerun()

# =========================================================
# 뷰: 오늘의 폭염 정보 (예시 — 실 API 미연동)
# =========================================================
# 뷰: 검색 (기본) — 폭염정보 배너를 여기에 통합
# =========================================================
else:
    # ---------- 헤더 ----------
    st.markdown(
        f"""
        <div class="heatway-hero">
            <h1><img src="data:image/png;base64,{LOGO_B64}" alt="더위쉼표 로고"/>더위쉼표</h1>
            <p>더위로부터, 잠시 멀어지세요</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ---------- 오늘의 폭염 정보 (홈 화면 통합, 예시) ----------
    st.markdown(
        """
        <div class="heat-banner">
            <div class="icon">🌡️</div>
            <div>
                <div class="headline">대구 전역 폭염경보 발효 중 (예시)</div>
                <div class="sub">체감온도 37℃ · 습도 높음 · 야외활동 자제 권고</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption(
        "* 위 정보는 데모용 예시입니다. 실제 서비스에서는 기상청 영향예보 API와 연동되어 "
        "실시간 폭염 특보 단계가 표시됩니다."
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
            build_shelter_map(results, center_lat, center_lng, zoom_start=13, map_height=420)
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
                <div class="icon">🌿</div>
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