import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
from datetime import datetime

st.set_page_config(page_title="카카오 캠페인 대시보드", layout="wide", page_icon="💛")

# ── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;600;700;900&display=swap');

  html, body, [class*="css"] { font-family: 'Pretendard', sans-serif; }

  [data-testid="stAppViewContainer"] { background: #07090F; }
  [data-testid="stHeader"]           { background: transparent; }
  section.main > div                 { padding-top: 1.8rem; }
  #MainMenu, footer, header          { visibility: hidden; }

  .kpi-card {
    background: linear-gradient(145deg, #10162A, #181F35);
    border: 1px solid rgba(255,224,0,.18);
    border-radius: 18px;
    padding: 22px 24px 18px;
    height: 110px;
  }
  .kpi-label {
    font-size: 12px; font-weight: 700;
    letter-spacing: 1.4px; text-transform: uppercase;
    color: #8BA3CC; margin-bottom: 10px;
  }
  .kpi-value        { font-size: 26px; font-weight: 800; color: #FFE000; }
  .kpi-value-green  { font-size: 26px; font-weight: 800; color: #34D399; }
  .kpi-value-orange { font-size: 26px; font-weight: 800; color: #FB923C; }
  .kpi-value-purple { font-size: 26px; font-weight: 800; color: #A78BFA; }
  .kpi-value-blue   { font-size: 26px; font-weight: 800; color: #60A5FA; }

  .sec-wrap  { display:flex; align-items:center; gap:12px; margin:32px 0 14px; }
  .sec-label { font-size:12px; font-weight:700; letter-spacing:2px;
               text-transform:uppercase; color:#FFE000; white-space:nowrap; }
  .sec-line  { flex:1; height:1px;
               background:linear-gradient(90deg,rgba(255,224,0,.4),transparent); }

  .chart-card {
    background: #10162A;
    border: 1px solid #1E2D50;
    border-radius: 16px;
    padding: 18px 16px 6px;
  }
  .chart-title {
    font-size:14px; font-weight:700; color:#C4D4EE;
    letter-spacing:.5px; margin-bottom:4px;
  }

  .report-header {
    border-bottom: 1px solid #1A2340;
    padding-bottom: 18px;
    margin-bottom: 24px;
  }
  .report-title {
    font-size: 30px; font-weight: 900; letter-spacing: -0.8px;
    background: linear-gradient(90deg, #FFE000 0%, #34D399 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  }
  .report-sub { font-size: 13px; color: #5B6E92; margin-top: 4px; }

  .upload-box {
    background: #10162A;
    border: 1px dashed #2A3A60;
    border-radius: 12px;
    padding: 24px;
    text-align: center;
  }

  .weather-card {
    background: linear-gradient(145deg, #0D1525, #131D38);
    border: 1px solid rgba(96,165,250,.25);
    border-radius: 18px;
    padding: 20px 24px 16px;
  }
  .weather-temp {
    font-size: 40px; font-weight: 900; color: #60A5FA; line-height: 1.1;
  }
  .weather-label {
    font-size: 12px; font-weight: 700; letter-spacing: 1.4px;
    text-transform: uppercase; color: #8BA3CC; margin-bottom: 8px;
  }
  .weather-sub {
    font-size: 13px; color: #6B83A8; margin-top: 6px;
  }

  [data-testid="stDataFrame"] { border-radius: 12px; overflow: hidden; }
  [data-testid="stFileUploader"] { background: #10162A !important; border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

PLOT_BG    = "#10162A"
GRID_COLOR = "#1A2D50"
FONT_COLOR = "#A8BDD8"
KAKAO_COLORS = ["#FFE000", "#34D399", "#FB923C", "#A78BFA", "#F472B6", "#60A5FA"]

LAYOUT_BASE = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor=PLOT_BG,
    font_color=FONT_COLOR,
    margin=dict(l=8, r=8, t=28, b=8),
)


def section(label):
    st.markdown(f"""
    <div class="sec-wrap">
      <span class="sec-label">{label}</span>
      <div class="sec-line"></div>
    </div>""", unsafe_allow_html=True)


def kpi(col, label, value, cls="kpi-value"):
    col.markdown(f"""
    <div class="kpi-card">
      <div class="kpi-label">{label}</div>
      <div class="{cls}">{value}</div>
    </div>""", unsafe_allow_html=True)


def wrap_label(text, max_chars=8):
    """긴 레이블을 max_chars 기준으로 2줄로 분할 (plotly HTML 사용)."""
    if len(text) <= max_chars:
        return text
    mid = len(text) // 2
    # 공백이 있으면 공백 기준으로 분할
    for i in range(mid, len(text)):
        if text[i] == ' ':
            return text[:i] + '<br>' + text[i+1:]
    for i in range(mid, -1, -1):
        if text[i] == ' ':
            return text[:i] + '<br>' + text[i+1:]
    return text[:mid] + '<br>' + text[mid:]


# ── 헤더 ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="report-header">
  <div class="report-title">카카오 캠페인 통합 대시보드</div>
  <div class="report-sub">고객정보 × 캠페인반응 데이터 통합 분석</div>
</div>
""", unsafe_allow_html=True)

# ── 날씨 섹션 ─────────────────────────────────────────────────────────────────
section("서울 날씨 (실시간)")

@st.cache_data(ttl=600, show_spinner=False)
def fetch_weather():
    url = (
        "https://api.open-meteo.com/v1/forecast"
        "?latitude=37.5665&longitude=126.9780"
        "&current=temperature_2m,apparent_temperature,weathercode"
        "&hourly=temperature_2m"
        "&timezone=Asia%2FSeoul"
        "&forecast_days=1"
    )
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    return resp.json()

try:
    weather = fetch_weather()
    cur = weather["current"]
    cur_temp   = cur["temperature_2m"]
    feel_temp  = cur["apparent_temperature"]

    # 오늘 시간별 기온 (0~23시)
    hours   = weather["hourly"]["time"]        # ISO 형식
    h_temps = weather["hourly"]["temperature_2m"]
    now_hour = datetime.now().hour
    hour_labels = [h.split("T")[1][:5] for h in hours]  # "HH:MM"

    wc1, wc2, wc3 = st.columns([1, 1, 3])

    with wc1:
        st.markdown(f"""
        <div class="weather-card">
          <div class="weather-label">현재 기온</div>
          <div class="weather-temp">{cur_temp:.1f}°C</div>
          <div class="weather-sub">서울특별시 기준</div>
        </div>""", unsafe_allow_html=True)

    with wc2:
        st.markdown(f"""
        <div class="weather-card">
          <div class="weather-label">체감 기온</div>
          <div class="weather-temp" style="color:#34D399">{feel_temp:.1f}°C</div>
          <div class="weather-sub">Open-Meteo 제공</div>
        </div>""", unsafe_allow_html=True)

    with wc3:
        st.markdown('<div class="chart-card"><div class="chart-title">오늘 시간별 기온 (°C)</div>', unsafe_allow_html=True)
        df_w = pd.DataFrame({"시간": hour_labels, "기온(°C)": h_temps})
        fig_w = go.Figure()
        fig_w.add_trace(go.Scatter(
            x=df_w["시간"], y=df_w["기온(°C)"],
            mode="lines+markers",
            line=dict(color="#60A5FA", width=2.5),
            marker=dict(size=5, color="#60A5FA"),
            fill="tozeroy",
            fillcolor="rgba(96,165,250,0.08)",
        ))
        # 현재 시간 강조
        fig_w.add_vline(
            x=hour_labels[now_hour],
            line_dash="dot", line_color="#FFE000", line_width=1.5,
            annotation_text="현재", annotation_font_color="#FFE000",
            annotation_font_size=11,
        )
        fig_w.update_layout(
            **LAYOUT_BASE, height=160,
            xaxis=dict(gridcolor=GRID_COLOR, title="", tickangle=0, tickfont_size=11),
            yaxis=dict(gridcolor=GRID_COLOR, title="°C", tickfont_size=11),
        )
        st.plotly_chart(fig_w, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

except Exception as e:
    st.warning(f"날씨 데이터를 불러오지 못했습니다. ({e})")

# ── 파일 업로드 ───────────────────────────────────────────────────────────────
col_up1, col_up2 = st.columns(2)
with col_up1:
    st.markdown("**📋 고객정보 파일 업로드**")
    file_customer = st.file_uploader(
        "카카오_고객정보_더미데이터.xlsx",
        type=["xlsx", "xls"],
        key="customer",
        label_visibility="collapsed",
    )
with col_up2:
    st.markdown("**📣 캠페인반응 파일 업로드**")
    file_campaign = st.file_uploader(
        "카카오_캠페인반응_더미데이터.xlsx",
        type=["xlsx", "xls"],
        key="campaign",
        label_visibility="collapsed",
    )

if not file_customer or not file_campaign:
    st.info("두 파일을 모두 업로드하면 대시보드가 표시됩니다.", icon="💡")
    st.stop()

# ── 데이터 로드 & Merge ───────────────────────────────────────────────────────
@st.cache_data(show_spinner="데이터를 불러오는 중...")
def load_and_merge(f1, f2):
    df_c  = pd.read_excel(f1)
    df_cp = pd.read_excel(f2)
    merged = pd.merge(df_cp, df_c, on="USER_ID", how="left")
    merged["발송일"] = pd.to_datetime(merged["발송일"], errors="coerce")
    merged["가입일"] = pd.to_datetime(merged["가입일"], errors="coerce")
    merged["구매여부"] = merged["최종행동"] == "구매"
    return df_c, df_cp, merged

df_customer, df_campaign, df = load_and_merge(file_customer, file_campaign)

# ── 사이드바 필터 ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 필터")

    channels = ["전체"] + sorted(df["발송채널"].dropna().unique().tolist())
    sel_channel = st.selectbox("발송채널", channels)

    grades = ["전체"] + sorted(df["멤버십등급"].dropna().unique().tolist())
    sel_grade = st.selectbox("멤버십등급", grades)

    campaigns = ["전체"] + sorted(df["캠페인명"].dropna().unique().tolist())
    sel_campaign = st.selectbox("캠페인명", campaigns)

filt = df.copy()
if sel_channel  != "전체": filt = filt[filt["발송채널"]  == sel_channel]
if sel_grade    != "전체": filt = filt[filt["멤버십등급"] == sel_grade]
if sel_campaign != "전체": filt = filt[filt["캠페인명"]   == sel_campaign]

# ── KPI ───────────────────────────────────────────────────────────────────────
total_events   = len(filt)
purchase_rate  = filt["구매여부"].mean() * 100 if total_events else 0
total_revenue  = filt.loc[filt["구매여부"], "구매금액"].sum()
avg_response   = filt["반응소요시간_분"].mean() if total_events else 0
coupon_rate    = (filt["쿠폰사용여부"] == "Y").mean() * 100 if total_events else 0

k1, k2, k3, k4, k5 = st.columns(5)
kpi(k1, "캠페인 발송 건수",  f"{total_events:,} 건")
kpi(k2, "구매 전환율",       f"{purchase_rate:.1f} %",    "kpi-value-green")
kpi(k3, "총 구매 금액",      f"₩{total_revenue:,.0f}",    "kpi-value-orange")
kpi(k4, "평균 반응 소요시간", f"{avg_response:.1f} 분",    "kpi-value-purple")
kpi(k5, "쿠폰 사용률",       f"{coupon_rate:.1f} %")

# ── 섹션 1 : 캠페인 성과 ─────────────────────────────────────────────────────
section("캠페인 성과 분석")

ch1, ch2 = st.columns(2)

with ch1:
    st.markdown('<div class="chart-card"><div class="chart-title">캠페인별 구매 전환율</div>', unsafe_allow_html=True)
    camp_df = (
        filt.groupby("캠페인명")["구매여부"]
        .agg(전환율="mean", 발송수="count")
        .reset_index()
    )
    camp_df["전환율"] = (camp_df["전환율"] * 100).round(1)
    camp_df["캠페인명_표시"] = camp_df["캠페인명"].apply(wrap_label)
    fig = px.bar(
        camp_df, x="캠페인명_표시", y="전환율",
        color="전환율", color_continuous_scale=["#1A2D50", "#FFE000"],
        text="전환율",
    )
    fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside", marker_line_width=0)
    fig.update_layout(**LAYOUT_BASE, height=320,
                      coloraxis_showscale=False, showlegend=False,
                      xaxis=dict(gridcolor=GRID_COLOR, title="", tickangle=0,
                                 tickfont=dict(size=12, color="#C4D4EE")),
                      yaxis=dict(gridcolor=GRID_COLOR, title="전환율 (%)",
                                 tickfont=dict(size=12)))
    st.plotly_chart(fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

with ch2:
    st.markdown('<div class="chart-card"><div class="chart-title">발송채널별 최종행동 분포</div>', unsafe_allow_html=True)
    ch_action = filt.groupby(["발송채널", "최종행동"]).size().reset_index(name="건수")
    fig2 = px.bar(
        ch_action, x="발송채널", y="건수", color="최종행동",
        color_discrete_sequence=KAKAO_COLORS, barmode="stack",
    )
    fig2.update_layout(**LAYOUT_BASE, height=320,
                       xaxis=dict(gridcolor=GRID_COLOR, title="", tickangle=0,
                                  tickfont=dict(size=12, color="#C4D4EE")),
                       yaxis=dict(gridcolor=GRID_COLOR, title="건수",
                                  tickfont=dict(size=12)),
                       legend=dict(bgcolor="rgba(0,0,0,0)", font_size=12))
    st.plotly_chart(fig2, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ── 섹션 2 : 고객 세그먼트 분석 ──────────────────────────────────────────────
section("고객 세그먼트 분석")

ch3, ch4, ch5 = st.columns(3)

with ch3:
    st.markdown('<div class="chart-card"><div class="chart-title">멤버십등급별 구매 전환율</div>', unsafe_allow_html=True)
    grade_df = (
        filt.groupby("멤버십등급")["구매여부"]
        .agg(전환율="mean").reset_index()
    )
    grade_df["전환율"] = (grade_df["전환율"] * 100).round(1)
    fig3 = px.bar(
        grade_df, x="멤버십등급", y="전환율",
        color="멤버십등급", color_discrete_sequence=KAKAO_COLORS,
        text="전환율",
    )
    fig3.update_traces(texttemplate="%{text:.1f}%", textposition="outside", marker_line_width=0)
    fig3.update_layout(**LAYOUT_BASE, height=280, showlegend=False,
                       xaxis=dict(gridcolor=GRID_COLOR, title="", tickangle=0,
                                  tickfont=dict(size=12, color="#C4D4EE")),
                       yaxis=dict(gridcolor=GRID_COLOR, title="전환율 (%)",
                                  tickfont=dict(size=12)))
    st.plotly_chart(fig3, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

with ch4:
    st.markdown('<div class="chart-card"><div class="chart-title">연령대별 캠페인 반응 분포</div>', unsafe_allow_html=True)
    age_df = filt.groupby(["연령대", "최종행동"]).size().reset_index(name="건수")
    order  = sorted(filt["연령대"].dropna().unique())
    fig4   = px.bar(
        age_df, x="연령대", y="건수", color="최종행동",
        color_discrete_sequence=KAKAO_COLORS, barmode="group",
        category_orders={"연령대": order},
    )
    fig4.update_layout(**LAYOUT_BASE, height=280,
                       xaxis=dict(gridcolor=GRID_COLOR, title="", tickangle=0,
                                  tickfont=dict(size=12, color="#C4D4EE")),
                       yaxis=dict(gridcolor=GRID_COLOR, title="건수",
                                  tickfont=dict(size=12)),
                       legend=dict(bgcolor="rgba(0,0,0,0)", font_size=11))
    st.plotly_chart(fig4, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

with ch5:
    st.markdown('<div class="chart-card"><div class="chart-title">최종행동 비중</div>', unsafe_allow_html=True)
    action_cnt = filt["최종행동"].value_counts().reset_index()
    action_cnt.columns = ["최종행동", "건수"]
    fig5 = px.pie(
        action_cnt, values="건수", names="최종행동",
        color_discrete_sequence=KAKAO_COLORS, hole=0.55,
    )
    fig5.update_traces(textposition="inside", textinfo="percent+label",
                       textfont_size=12, textfont_color="#FFFFFF")
    fig5.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", font_color=FONT_COLOR,
        margin=dict(l=0, r=0, t=20, b=0), height=280,
        showlegend=False,
    )
    st.plotly_chart(fig5, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ── 섹션 3 : 구매 금액 분석 ───────────────────────────────────────────────────
section("구매 금액 분석")

ch6, ch7 = st.columns(2)

with ch6:
    st.markdown('<div class="chart-card"><div class="chart-title">쿠폰 사용 여부에 따른 평균 구매금액</div>', unsafe_allow_html=True)
    coupon_df = (
        filt[filt["구매여부"]]
        .groupby("쿠폰사용여부")["구매금액"]
        .mean().reset_index()
    )
    coupon_df["쿠폰사용여부"] = coupon_df["쿠폰사용여부"].map({"Y": "쿠폰 사용", "N": "미사용"})
    fig6 = px.bar(
        coupon_df, x="쿠폰사용여부", y="구매금액",
        color="쿠폰사용여부", color_discrete_sequence=["#FFE000", "#4B5E85"],
        text="구매금액",
    )
    fig6.update_traces(texttemplate="₩%{text:,.0f}", textposition="outside", marker_line_width=0)
    fig6.update_layout(**LAYOUT_BASE, height=300, showlegend=False,
                       xaxis=dict(gridcolor=GRID_COLOR, title="", tickangle=0,
                                  tickfont=dict(size=13, color="#C4D4EE")),
                       yaxis=dict(gridcolor=GRID_COLOR, title="평균 구매금액 (원)",
                                  tickfont=dict(size=12)))
    st.plotly_chart(fig6, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

with ch7:
    st.markdown('<div class="chart-card"><div class="chart-title">지역별 총 구매금액</div>', unsafe_allow_html=True)
    region_df = (
        filt[filt["구매여부"]]
        .groupby("지역")["구매금액"]
        .sum().reset_index()
        .sort_values("구매금액", ascending=True)
    )
    fig7 = px.bar(
        region_df, x="구매금액", y="지역", orientation="h",
        color="구매금액", color_continuous_scale=["#1A2D50", "#FFE000"],
        text="구매금액",
    )
    fig7.update_traces(texttemplate="₩%{text:,.0f}", textposition="outside", marker_line_width=0)
    fig7.update_layout(**LAYOUT_BASE, height=300, coloraxis_showscale=False,
                       xaxis=dict(gridcolor=GRID_COLOR, title="", tickfont=dict(size=12)),
                       yaxis=dict(gridcolor=GRID_COLOR, title="",
                                  tickfont=dict(size=13, color="#C4D4EE")))
    st.plotly_chart(fig7, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ── 섹션 4 : Merge된 원본 데이터 ─────────────────────────────────────────────
section("통합 데이터 테이블")

show_cols = [
    "EVENT_ID", "USER_ID", "고객명", "연령대", "지역", "멤버십등급",
    "캠페인명", "발송채널", "발송일", "최종행동", "쿠폰사용여부", "구매금액",
    "반응소요시간_분", "누적구매금액",
]
display_df = filt[[c for c in show_cols if c in filt.columns]].copy()
display_df["발송일"] = display_df["발송일"].dt.strftime("%Y-%m-%d")

st.dataframe(display_df, use_container_width=True, hide_index=True, height=320)

st.caption(f"총 {len(display_df):,}건 표시 중 (전체 {len(df):,}건)")
