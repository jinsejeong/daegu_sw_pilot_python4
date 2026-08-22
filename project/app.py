import streamlit as st
import pandas as pd
import folium
import base64
import os
import requests
from pathlib import Path
from streamlit_folium import folium_static
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()  # .env 파일에서 SHELTER_API_KEY, ANTHROPIC_API_KEY 등을 읽어옴
               # (아래 로컬 모듈들이 import 시점에 환경변수를 읽으므로 반드시 그 전에 호출)

from matching import recommend_shelters, annotate_availability
from geo import jitter_coords, REGION_CENTER
from ai_guide import generate_ai_guide_text, _ANTHROPIC_AVAILABLE
from shelter_api import load_shelters as load_shelters_api
import db

db.init_db()

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")


def call_backend_recommend(region: str, time_str: str, activity_type: str, top_n: int = 10):
    """
    FastAPI 백엔드(SIR-002)를 통해 추천 결과를 받는다.
    백엔드가 꺼져 있거나 응답이 없으면 None을 반환 (호출부에서 로컬 직접호출로 폴백).
    """
    try:
        resp = requests.post(
            f"{BACKEND_URL}/recommend",
            json={"region": region, "time": time_str, "activity_type": activity_type, "top_n": top_n},
            timeout=3,
        )
        resp.raise_for_status()
        data = resp.json()
        if not data["results"]:
            return pd.DataFrame(), data.get("expanded", False), data.get("base_radius_km", 0), data.get("using_real_api", False)

        df = pd.DataFrame(data["results"])
        return df, data["expanded"], data["base_radius_km"], data["using_real_api"]
    except Exception:
        return None

LOGO_PATH = Path(__file__).parent / "logo.png"
LOGO_WHITE_PATH = Path(__file__).parent / "logo_white.png"

# set_page_config는 반드시 스크립트에서 가장 먼저 실행되는 Streamlit 명령이어야 함
st.set_page_config(
    page_title="더위쉼표",
    page_icon=str(LOGO_PATH),
    layout="centered",
)


@st.cache_data
def get_logo_base64():
    return base64.b64encode(LOGO_PATH.read_bytes()).decode()


@st.cache_data
def get_logo_white_base64():
    return base64.b64encode(LOGO_WHITE_PATH.read_bytes()).decode()


LOGO_B64 = get_logo_base64()
LOGO_WHITE_B64 = get_logo_white_base64()

# ---------- 스타일 ----------
st.markdown(
    """
    <style>
    /* 전체 배경 - 로고 블루 톤의 아주 은은한 화이티쉬 그라데이션 */
    .stApp {
        background: linear-gradient(180deg, #F4F8FE 0%, #FFFFFF 35%);
    }

    /* 햄버거 토글 메뉴 */
    .heatway-topbar {
        display: flex;
        align-items: center;
        padding: 4px 0 12px 0;
    }
    .heatway-topbar .brand {
        font-size: 1.15rem;
        font-weight: 800;
        color: #2E6BB0;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .heatway-topbar .brand img {
        height: 44px;
        width: 44px;
        object-fit: contain;
    }

    /* 브랜드(로고+텍스트) 클릭 시 홈으로: 보이는 HTML 위에 투명 버튼을 겹쳐서 클릭을 받는다 */
    .st-key-brand_home_area {
        position: relative;
        cursor: pointer;
        width: fit-content;
    }
    .st-key-brand_home_area .heatway-topbar {
        pointer-events: none; /* 시각 요소는 클릭을 통과시키고 아래 버튼이 받도록 */
    }
    .st-key-brand_home_area .st-key-brand_home_btn {
        position: absolute;
        inset: 0;
        z-index: 10;
    }
    .st-key-brand_home_area .st-key-brand_home_btn button {
        width: 100%;
        height: 100%;
        opacity: 0;
        border: none !important;
        background: transparent !important;
        box-shadow: none !important;
        padding: 0 !important;
        cursor: pointer;
    }

    /* 햄버거 버튼 - 화면 흐름 안에서 왼쪽 위에 배치 (position:fixed는 Streamlit 자체
       상단 툴바와 겹쳐 가려지는 버전이 있어 제거, 대신 항상 확실히 보이는 방식으로) */
    .st-key-hamburger_btn button {
        background: rgba(255,255,255,0.9) !important;
        border: 1px solid #D6E9FC !important;
        color: #374151 !important;
        font-size: 1.4rem !important;
        width: 42px !important;
        height: 42px !important;
        min-height: 42px !important;
        padding: 0 !important;
        border-radius: 10px !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08) !important;
    }
    .st-key-hamburger_btn button:hover {
        background: #EAF2FE !important;
        color: #2E6BB0 !important;
    }

    /* 히어로 헤더 - 로고 블루를 화이티쉬하게 톤다운한 그라데이션 */
    .heatway-hero {
        background: linear-gradient(120deg, #6FAEF2 0%, #4897EC 100%);
        border-radius: 20px;
        padding: 28px 24px;
        margin-bottom: 12px;
        box-shadow: 0 8px 24px rgba(72, 151, 236, 0.2);
    }
    .heatway-hero h1 {
        color: white;
        font-size: 2.1rem;
        margin: 0 0 4px 0;
        display: flex;
        align-items: center;
        gap: 14px;
    }
    .heatway-hero h1 img {
        height: 76px;
        width: 76px;
        object-fit: contain;
    }
    .heatway-hero p {
        color: rgba(255,255,255,0.9);
        margin: 0;
        font-size: 1rem;
    }

    /* 버튼 - 기본(주요 CTA: 쉼터 찾기) - 로고 블루 */
    button[kind="primary"] {
        background: linear-gradient(120deg, #6FAEF2 0%, #4897EC 100%) !important;
        color: white !important;
        border-radius: 999px !important;
        height: 3em;
        font-weight: 700 !important;
        border: none !important;
        box-shadow: 0 4px 14px rgba(72, 151, 236, 0.3);
        transition: transform 0.15s ease;
    }
    button[kind="primary"]:hover {
        transform: translateY(-1px);
        background: linear-gradient(120deg, #4897EC 0%, #2E6BB0 100%) !important;
        color: white !important;
    }

    /* 버튼 - 보조(홈 버튼 등) */
    button[kind="secondary"] {
        background: white !important;
        color: #4897EC !important;
        border: 1.5px solid #D6E9FC !important;
        border-radius: 999px !important;
        font-weight: 600 !important;
        box-shadow: none !important;
    }
    button[kind="secondary"]:hover {
        background: #EAF2FE !important;
        color: #2E6BB0 !important;
    }
    .heatway-summary {
        background: #EAF2FE;
        border-radius: 12px;
        padding: 10px 16px;
        color: #2E6BB0;
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
        background: #EAF2FE;
        border-radius: 10px;
        padding: 10px 12px;
        color: #2E6BB0;
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
        color: #2E6BB0;
        margin-top: 0;
    }
    .heatway-step {
        display: flex;
        align-items: flex-start;
        gap: 12px;
        margin-bottom: 14px;
    }
    .heatway-step .num {
        background: linear-gradient(120deg, #6FAEF2 0%, #4897EC 100%);
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
        "available": "#2FAE7A",
        "closing_soon": "#E8A93D",
        "unavailable": "#E4572E",
    }

    for _, row in rows_df.iterrows():
        lat, lng = row["lat"], row["lng"]
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


df, using_real_api = load_shelters_api("shelters.csv", region_keyword="대구")

# ---------- 세션 상태 초기화 ----------
if "results" not in st.session_state:
    st.session_state.results = None
    st.session_state.search_region = None
    st.session_state.search_time_str = None
if "view" not in st.session_state:
    st.session_state.view = "search"  # search | info | all_shelters
if "menu_open" not in st.session_state:
    st.session_state.menu_open = False

# ---------- 상단 바: 햄버거 토글 + 브랜드 (클릭하면 홈으로) ----------
top_ham_col, top_brand_col = st.columns([0.8, 5])

with top_ham_col:
    hamburger_clicked = st.button("☰", key="hamburger_btn")

if hamburger_clicked:
    st.session_state.menu_open = not st.session_state.menu_open

# st.container(key=...)는 최신 Streamlit(1.32+)에서만 지원됨.
# 구버전 호환을 위해 지원 안 되면 일반 컨테이너로 조용히 폴백 (로고 클릭 기능만 비활성화됨)
try:
    _brand_container = top_brand_col.container(key="brand_home_area")
except TypeError:
    _brand_container = top_brand_col.container()

with _brand_container:
    st.markdown(
        f'<div class="heatway-topbar"><span class="brand">'
        f'<img src="data:image/png;base64,{LOGO_B64}" alt="더위쉼표 로고"/>더위쉼표</span></div>',
        unsafe_allow_html=True,
    )
    brand_clicked = st.button("더위쉼표 홈으로", key="brand_home_btn")

home_clicked = info_clicked = all_clicked = guardian_clicked = False

if brand_clicked:
    home_clicked = True

# ---------- 토글로 열고 닫히는 메뉴 패널 ----------
if st.session_state.menu_open:
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        home_clicked = st.button("🏠 홈", type="secondary", key="home_btn", use_container_width=True) or home_clicked
    with m2:
        info_clicked = st.button("ℹ️ 소개·이용방법", type="secondary", key="info_btn", use_container_width=True)
    with m3:
        all_clicked = st.button("🗺️ 전체 쉼터", type="secondary", key="all_btn", use_container_width=True)
    with m4:
        guardian_clicked = st.button("👪 보호자 모드", type="secondary", key="guardian_btn", use_container_width=True)

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
if guardian_clicked:
    st.session_state.view = "guardian"
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
                더위쉼표는 위치·시간을 입력하면, 그 조건에서 <b>지금 실제로 이용 가능한</b>
                무더위쉼터를 추천해주는 서비스예요.<br>
                복잡한 판단은 서비스가 대신하고, 사용자는 잠깐이라도 더위로부터 멀어질 곳을 바로 찾을 수 있도록 만들었어요.
            </p>
        </div>
        <div class="heatway-panel">
            <h3>📋 이용 방법</h3>
            <div class="heatway-step"><div class="num">1</div><div class="txt">지역과 방문 예정 시간을 선택하세요.</div></div>
            <div class="heatway-step"><div class="num">2</div><div class="txt">'쉼터 찾기'를 누르면 지금 이용 가능한 쉼터부터 정렬해서 보여드려요.</div></div>
            <div class="heatway-step"><div class="num">3</div><div class="txt">지도에서 색깔로 상태를 확인하고, 카드에서 상세 정보와 안내 문구를 읽어보세요.</div></div>
            <div class="heatway-step"><div class="num">4</div><div class="txt">언제든 화면 위쪽의 '더위쉼표' 로고를 누르면 바로 홈 화면으로 돌아올 수 있어요.</div></div>
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
    n_synthetic = int(annotated["_coords_synthetic"].sum()) if "_coords_synthetic" in annotated.columns else 0
    if n_synthetic > 0:
        st.caption(
            f"⚠️ {n_synthetic}곳은 실좌표가 없어 지역 내 임의 위치로 표시됩니다. "
            f"나머지는 행정안전부 API 실좌표입니다."
        )
    else:
        st.caption("📍 지도상 위치는 행정안전부 무더위쉼터 API의 실제 좌표입니다.")
    if st.button("← 검색으로 돌아가기"):
        st.session_state.view = "search"
        st.rerun()

# =========================================================
# 뷰: 보호자 모드 (PRD F5 — RFP 구현제외 항목, 팀 결정으로 보너스 구현)
# =========================================================
elif st.session_state.view == "guardian":
    st.subheader("👪 보호자 모드")
    st.caption(
        "고령자·어린이 등 취약계층의 외출 여정을 보호자가 확인할 수 있는 기능입니다. "
        "실제 로그인 계정 없이, 이름으로 외출 세션을 구분합니다."
    )

    sub_tab = st.radio(
        "화면 선택", ["🚶 나가는 사람", "👨‍👩‍👧 보호자로 보기"],
        horizontal=True, label_visibility="collapsed", key="guardian_subtab",
    )
    st.divider()

    # ---------------------------------------------------
    # 서브뷰 A: 나가는 사람 화면
    # ---------------------------------------------------
    if sub_tab == "🚶 나가는 사람":
        name = st.text_input("이름", key="dep_name", placeholder="예: 김영자")

        active = db.get_active_outing(name) if name else None

        if active is None:
            st.markdown("아직 진행 중인 외출이 없어요. 외출을 시작해보세요.")

            # 직전 검색 결과가 있으면 목적지 쉼터로 바로 선택 가능하게
            shelter_options = ["(직접 입력)"]
            if st.session_state.get("results") is not None and not st.session_state.results.empty:
                shelter_options += st.session_state.results["name"].tolist()

            picked = st.selectbox("목적지 쉼터", shelter_options, key="dep_shelter_pick")
            manual_shelter = ""
            if picked == "(직접 입력)":
                manual_shelter = st.text_input("쉼터명 직접 입력 (선택)", key="dep_shelter_manual")

            return_time = st.time_input("귀가 예정 시간", key="dep_return_time")

            if st.button("🚶 외출 시작", type="primary", use_container_width=True):
                if not name:
                    st.warning("이름을 입력해주세요.")
                else:
                    shelter_name = manual_shelter if picked == "(직접 입력)" else picked
                    shelter_id = None
                    if picked != "(직접 입력)" and st.session_state.get("results") is not None:
                        match = st.session_state.results[st.session_state.results["name"] == picked]
                        if not match.empty:
                            shelter_id = str(match.iloc[0]["shelter_id"])
                    return_dt = datetime.now().replace(
                        hour=return_time.hour, minute=return_time.minute, second=0
                    ).isoformat()
                    db.start_outing(name, return_dt, shelter_id, shelter_name or None)
                    st.rerun()

        else:
            status_label = {
                "in_progress": "🔵 외출 중", "checked_in": "🟢 쉼터 도착",
                "need_help": "🆘 도움 요청됨",
            }.get(active["status"], active["status"])
            st.markdown(f"### {status_label}")

            st.markdown(
                f"""
                <div class="heatway-card status-available">
                    <div class="card-title">{active['dependent_name']}님의 외출</div>
                    <div class="card-meta">🚶 출발: {active['start_time'][11:16]}</div>
                    <div class="card-meta">🏠 목적지: {active['shelter_name'] or '미지정'}</div>
                    <div class="card-meta">🕐 귀가 예정: {active['expected_return_time'][11:16] if len(active['expected_return_time'])>10 else active['expected_return_time']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            col_a, col_b = st.columns(2)
            with col_a:
                if active["status"] == "in_progress":
                    if st.button("🏠 쉼터 도착 체크인", use_container_width=True):
                        db.checkin_shelter(active["session_id"])
                        st.rerun()
            with col_b:
                if st.button("✅ 무사히 귀가", use_container_width=True):
                    db.mark_returned(active["session_id"])
                    st.rerun()

            st.divider()
            st.markdown("**보호자에게 지금 상태를 알려주세요**")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("😊 괜찮아요", use_container_width=True):
                    db.send_checkin(active["session_id"], "ok")
                    st.success("안부가 전달됐어요.")
            with c2:
                if st.button("🆘 도움이 필요해요", use_container_width=True):
                    db.send_checkin(active["session_id"], "need_help")
                    st.error("도움 요청이 보호자에게 전달됐어요.")

    # ---------------------------------------------------
    # 서브뷰 B: 보호자로 보기
    # ---------------------------------------------------
    else:
        outings = db.get_all_active_outings()
        if not outings:
            st.info("현재 진행 중인 외출이 없어요.")
        else:
            now = datetime.now()
            for o in outings:
                try:
                    expected = datetime.fromisoformat(o["expected_return_time"])
                    overdue = now > expected and o["status"] != "returned"
                except ValueError:
                    overdue = False

                if o["status"] == "need_help":
                    border_status = "unavailable"  # 빨강
                elif overdue:
                    border_status = "closing_soon"  # 주황
                else:
                    border_status = "available"  # 초록

                checkin_note = "아직 응답 없음"
                if o["last_checkin_at"]:
                    label = "😊 괜찮아요" if o["last_checkin_status"] == "ok" else "🆘 도움 필요"
                    checkin_note = f"{label} ({o['last_checkin_at'][11:16]})"

                overdue_badge = " · ⚠️ 귀가 예정 시간 초과, 응답 확인 필요" if overdue else ""

                st.markdown(
                    f"""
                    <div class="heatway-card status-{border_status}">
                        <div class="card-title">{o['dependent_name']}님{overdue_badge}</div>
                        <div class="card-meta">🚶 외출 시작: {o['start_time'][11:16]}</div>
                        <div class="card-meta">🏠 목적지: {o['shelter_name'] or '미지정'} · 상태: {o['status']}</div>
                        <div class="card-meta">🕐 귀가 예정: {o['expected_return_time'][11:16] if len(o['expected_return_time'])>10 else o['expected_return_time']}</div>
                        <div class="card-guide">최근 안부: {checkin_note}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    if st.button("← 검색으로 돌아가기"):
        st.session_state.view = "search"
        st.rerun()

else:
    # ---------- 헤더 ----------
    st.markdown(
        f"""
        <div class="heatway-hero">
            <h1><img src="data:image/png;base64,{LOGO_WHITE_B64}" alt="더위쉼표 로고"/>더위쉼표</h1>
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
        backend_result = call_backend_recommend(region, time_str, activity_type, top_n=10)

        if backend_result is not None:
            # SIR-002: FastAPI 백엔드 경유 (요청/결과/AI안내문 SQLite 저장까지 완료된 상태)
            results, expanded, base_radius, using_real_api = backend_result
            st.session_state.backend_used = True
        else:
            # 백엔드 미기동/응답없음 → 로컬 직접호출로 자동 폴백
            results = recommend_shelters(df, region, time_str, activity_type, top_n=10)
            expanded = bool(results["_expanded"].iloc[0]) if not results.empty else False
            base_radius = results["_base_radius_km"].iloc[0] if not results.empty else 0
            using_real_api = using_real_api  # 전역 로컬 df 로드시 판단된 값 그대로 사용
            st.session_state.backend_used = False

        st.session_state.results = results
        st.session_state.search_region = region
        st.session_state.search_time_str = time_str
        st.session_state.search_expanded = expanded
        st.session_state.search_base_radius = base_radius

    if st.session_state.results is not None:
        results = st.session_state.results
        region = st.session_state.search_region
        time_str = st.session_state.search_time_str

        backend_note = "⚙️ FastAPI 백엔드 경유" if st.session_state.get("backend_used") else "⚙️ 로컬 직접호출 (백엔드 미기동)"
        st.caption(backend_note)

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

            # ALR-007: 기본 반경 내 결과가 없어 검색 반경을 확장한 경우 안내
            if st.session_state.get("search_expanded"):
                base_r = st.session_state.get("search_base_radius")
                st.caption(f"📡 기본 반경({base_r}km) 내 쉼터가 부족해 검색 범위를 넓혀 안내해드려요.")

            # ---------- 지도 ----------
            center_lat, center_lng = REGION_CENTER.get(region, (35.8714, 128.6014))
            build_shelter_map(results, center_lat, center_lng, zoom_start=13, map_height=420)
            n_synthetic = int(results["_coords_synthetic"].sum()) if "_coords_synthetic" in results.columns else 0
            coord_note = (
                f"{n_synthetic}곳은 실좌표가 없어 지역 내 임의 위치로 표시됩니다."
                if n_synthetic > 0 else "모든 위치는 행정안전부 API 실좌표입니다."
            )
            st.caption(
                f"📍 {coord_note} "
                "핀 색상 · 팝업 테두리는 이용 가능 여부를 나타냅니다 (초록=가능 / 주황=곧마감 / 빨강=불가)."
            )

            # ---------- 카드 리스트 ----------
            for idx, row in results.iterrows():
                night_badge = " · 🌙 야간개방" if row["is_night_open"] == "Y" else ""
                # 백엔드 경유 시 이미 생성된 안내문구 재사용 (AI 중복호출/비용 방지)
                guide_text = row["guide_text"] if "guide_text" in row and pd.notna(row["guide_text"]) else generate_ai_guide_text(row)
                st.markdown(
                    f"""
                    <div class="heatway-card status-{row['availability']}">
                        <div class="card-title">{row['status_label']} · {row['name']}</div>
                        <div class="card-meta">📏 {row['distance_label']} · 📮 {row['address']}</div>
                        <div class="card-meta">🕐 운영시간 {row['open_time']}~{row['close_time']}{night_badge}</div>
                        <div class="card-meta">❄️ 에어컨 {row['ac_count']}대 · 선풍기 {row['fan_count']}대 · 수용 {row['capacity']}명</div>
                        <div class="card-guide">{guide_text}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                if st.button(f"👪 이 쉼터로 외출 시작", key=f"outing_start_{idx}"):
                    st.session_state.view = "guardian"
                    st.session_state.guardian_subtab = "🚶 나가는 사람"
                    st.session_state.dep_shelter_pick = row["name"]
                    st.rerun()

    else:
        st.markdown(
            """
            <div class="heatway-empty">
                <div class="icon">🌿</div>
                지역, 시간을 선택하고<br>'쉼터 찾기'를 눌러주세요.
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ---------- 하단 안내 ----------
    st.divider()
    ai_status = "Claude API 연동됨" if _ANTHROPIC_AVAILABLE else "템플릿 문구 사용 중 (ANTHROPIC_API_KEY 미설정)"
    data_status = (
        "행정안전부 무더위쉼터 표준데이터 API 실연동 중"
        if using_real_api
        else "샘플 데이터 사용 중 (SHELTER_API_KEY 미설정 또는 API 응답 없음)"
    )
    st.markdown(
        f"""
        <div class="heatway-footer">
            ℹ️ 데이터: {data_status}<br>
            안내문구 생성: {ai_status}
        </div>
        """,
        unsafe_allow_html=True,
    )