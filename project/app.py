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
    .stButton>button {
        background-color: #2E86AB;
        color: white;
        border-radius: 10px;
        height: 3em;
        font-weight: 600;
        border: none;
    }
    .stButton>button:hover {
        background-color: #1f5f7a;
        color: white;
    }
    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 12px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data
def load_shelters():
    return pd.read_csv("shelters.csv", encoding="utf-8-sig")


df = load_shelters()

# ---------- 헤더 ----------
st.title("🌤️ 더위쉼표")
st.markdown("##### 더위로부터, 잠시 멀어지세요")
st.divider()

# ---------- 입력 ----------
col1, col2 = st.columns(2)
with col1:
    region = st.selectbox("📍 지역", sorted(df["region"].unique()))
with col2:
    input_time = st.time_input("🕐 방문 예정 시간", value=datetime.now().time())

activity_type = st.selectbox(
    "🚶 활동유형",
    ["산책", "장보기·용무", "업무(야외근로)", "등하교", "기타"],
)

search_clicked = st.button("쉼터 찾기", type="primary", use_container_width=True)

st.divider()

# ---------- 결과 ----------
if search_clicked:
    time_str = input_time.strftime("%H:%M")
    results = recommend_shelters(df, region, time_str, activity_type, top_n=10)

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
            st.caption(f"지금 이용 가능한 곳 {n_available}곳을 포함해 총 {len(results)}곳을 찾았어요.")

        # ---------- 지도 ----------
        center_lat, center_lng = REGION_CENTER.get(region, (35.8714, 128.6014))
        m = folium.Map(location=[center_lat, center_lng], zoom_start=13)

        color_map = {"available": "green", "closing_soon": "orange", "unavailable": "gray"}

        for _, row in results.iterrows():
            lat, lng = jitter_coords(region, row["shelter_id"])
            folium.Marker(
                location=[lat, lng],
                popup=f"{row['name']} ({row['status_label']})",
                tooltip=row["name"],
                icon=folium.Icon(color=color_map.get(row["availability"], "blue")),
            ).add_to(m)

        # st_folium 대신 folium_static 사용 (버전 호환성 이슈 회피)
        folium_static(m, width=700, height=400)
        st.caption(
            "⚠️ 지도상 위치는 실제 주소가 아닌 지역 내 임의 배치입니다 (샘플 데이터 특성상 좌표 미포함)."
        )

        # ---------- 카드 리스트 ----------
        for _, row in results.iterrows():
            with st.container(border=True):
                st.markdown(f"**{row['status_label']}  ·  {row['name']}**")
                st.write(f"📮 {row['address']}")
                st.write(
                    f"🕐 운영시간 {row['open_time']}~{row['close_time']}"
                    + ("  ·  🌙 야간개방" if row["is_night_open"] == "Y" else "")
                )
                st.write(
                    f"❄️ 에어컨 {row['ac_count']}대 · 선풍기 {row['fan_count']}대 · 수용 {row['capacity']}명"
                )
                st.info(generate_ai_guide_text(row))

else:
    st.info("지역, 시간, 활동유형을 선택하고 '쉼터 찾기'를 눌러주세요.")

# ---------- 하단 안내 ----------
st.divider()
ai_status = "Claude API 연동됨" if _ANTHROPIC_AVAILABLE else "템플릿 문구 사용 중 (ANTHROPIC_API_KEY 미설정)"
st.caption(
    f"ℹ️ 데모 버전 안내: 쉼터 데이터는 실제 서비스 스키마를 기반으로 한 샘플입니다. "
    f"실제 서비스에서는 행정안전부 무더위쉼터 표준데이터(data.go.kr)와 연동됩니다. · 안내문구: {ai_status}"
)