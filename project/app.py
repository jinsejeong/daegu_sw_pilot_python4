import streamlit as st
import pandas as pd
from datetime import datetime

from matching import recommend_shelters, generate_guide_text

st.set_page_config(page_title="더위쉼표", page_icon="🌤️", layout="centered")


@st.cache_data
def load_shelters():
    return pd.read_csv("shelters.csv", encoding="utf-8-sig")


df = load_shelters()

# ---------- 헤더 ----------
st.title("🌤️ 더위쉼표")
st.caption("더위로부터, 잠시 멀어지세요")
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

    if results.empty:
        st.warning(f"'{region}'에 등록된 쉼터가 없습니다.")
    else:
        n_available = (results["availability"] == "available").sum()
        st.subheader(f"{region} 무더위쉼터 ({time_str} 기준)")
        st.caption(f"지금 이용 가능한 곳 {n_available}곳을 포함해 총 {len(results)}곳을 찾았어요.")

        for _, row in results.iterrows():
            with st.container(border=True):
                st.markdown(f"**{row['status_label']}  ·  {row['name']}**")
                st.write(f"📮 {row['address']}")
                st.write(
                    f"🕐 운영시간 {row['open_time']}~{row['close_time']}"
                    + ("  ·  🌙 야간개방" if row["is_night_open"] == "Y" else "")
                )
                st.write(f"❄️ 에어컨 {row['ac_count']}대 · 선풍기 {row['fan_count']}대 · 수용 {row['capacity']}명")
                st.info(generate_guide_text(row))
else:
    st.info("지역, 시간, 활동유형을 선택하고 '쉼터 찾기'를 눌러주세요.")

# ---------- 데이터 출처 안내 ----------
st.divider()
st.caption(
    "ℹ️ 데모 버전 안내: 현재 표시되는 쉼터 데이터는 실제 서비스 스키마를 기반으로 한 샘플 데이터입니다. "
    "실제 서비스에서는 행정안전부 무더위쉼터 표준데이터(data.go.kr)와 연동됩니다."
)
