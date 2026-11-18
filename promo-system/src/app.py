"""프로모션 분석 시스템 2.0.  실행: streamlit run src/app.py"""
import sys
from pathlib import Path
import pandas as pd, plotly.express as px, streamlit as st
sys.path.insert(0, str(Path(__file__).parent))
import calc, keys, profit

ROOT = Path(__file__).resolve().parent.parent
GOLD, BLACK, HONEY, GRAY = "#B99764", "#1e1b17", "#F9BA15", "#9a9184"
st.set_page_config(page_title="치킨 프로모션 분석 시스템", page_icon="🍗", layout="wide")
st.markdown("""<style>
.block-container{padding-top:3.2rem;max-width:1280px}
h1,h2,h3{letter-spacing:-.02em}
div[data-testid="stMetric"]{background:#fff;border:1px solid #ecdcc0;border-radius:14px;padding:12px 16px;box-shadow:0 3px 10px rgba(143,111,62,.07)}
div[data-testid="stMetricValue"]{font-weight:800}
.hero{background:#1e1b17;color:#fff;border-radius:18px;padding:18px 24px;margin-bottom:10px}
.hero b{color:#F9BA15}.hero small{color:#cfc6b8}
.note{background:#f8efdf;border-radius:12px;padding:10px 14px;font-size:.92rem}
.big{font-size:1.25rem;font-weight:800}
</style>""", unsafe_allow_html=True)
원 = lambda v: f"{v:,.0f}원"
만 = lambda v, sign=False: (f"{v/1e4:+,.0f}만원" if sign else f"{v/1e4:,.0f}만원")

st.markdown('<div class="hero"><span style="font-size:1.6rem;font-weight:800">치킨 브랜드 <b>프로모션 분석 시스템</b> 2.0</span><br>'
            '<small>경쟁사 가격·행사 비교 · 공시 기반 손익 계산 · 주간 보고서</small></div>', unsafe_allow_html=True)


@st.cache_data
def load(p):
    df = calc.불러오기(p)
    return pd.concat([df, df.apply(calc.행계산, axis=1)], axis=1)


with st.sidebar:
    st.header("분석 범위")
    up = st.file_uploader("CSV 업로드 (선택)", type="csv")
    전체 = load(up if up else ROOT / "data" / "promotions.csv")
    구분 = st.radio("데이터", ["실제 데이터만", "가상 시험 데이터 포함"])
    df = 전체[전체["데이터구분"] == "실제"] if 구분 == "실제 데이터만" else 전체
    브랜드 = st.multiselect("브랜드", sorted(df["브랜드"].unique()), default=sorted(df["브랜드"].unique()))
    플랫폼 = st.multiselect("플랫폼", sorted(df["플랫폼"].unique()), default=sorted(df["플랫폼"].unique()))
    df = df[df["브랜드"].isin(브랜드) & df["플랫폼"].isin(플랫폼)]
    st.divider()
    st.caption("연결 상태")
    st.write(("🟢" if keys.있음("OPENDART_API_KEY") else "⚪") + " 전자공시(DART)")
    st.write(("🟢" if keys.있음("GEMINI_API_KEY") else "⚪") + " 제미나이 AI")

탭 = st.tabs(["📊 요약", "💰 가격 비교", "🎟️ 행사 기록", "🧮 손익 계산기", "📄 보고서"])

# ---------------- 요약 ----------------
with 탭[0]:
    st.caption(f"확인일 {df['확인일'].min()} ~ {df['확인일'].max()} · 실제 {(df['데이터구분']=='실제').sum()}건 / 가상 {(df['데이터구분']=='가상').sum()}건 "
               "· 실제 = 직접 캡처·보도, 가상 = 기능 시험용")
    c = st.columns(4)
    c[0].metric("브랜드", df["브랜드"].nunique())
    c[1].metric("메뉴·행사 기록", len(df))
    c[2].metric("평균 정상가", 원(df["정상가"].mean()) if len(df) else "-")
    c[3].metric("확인 필요", int((df["확인필요"] != "").sum()))
    st.subheader("브랜드별 메뉴 가격 범위")
    g = df.groupby("브랜드")["정상가"].agg(["min", "mean", "max"]).reset_index().sort_values("mean")
    fig = px.bar(g, y="브랜드", x="mean", orientation="h", color_discrete_sequence=[GOLD],
                 error_x=g["max"] - g["mean"], error_x_minus=g["mean"] - g["min"],
                 labels={"mean": "평균 정상가(원)", "브랜드": ""}, text=g["mean"].map(lambda v: f"{v:,.0f}"))
    fig.update_traces(textposition="inside", insidetextanchor="start", textfont_color="white")
    fig.update_layout(height=360, margin=dict(l=0, r=10, t=10, b=0), plot_bgcolor="#fff")
    st.plotly_chart(fig, width="stretch")
    st.caption("막대 = 평균, 선 = 최저~최고 · 캡처에 보인 메뉴 기준(1인 세트 포함)")

# ---------------- 가격 비교 ----------------
with 탭[1]:
    st.subheader("같은 메뉴, 채널별 가격 차이")
    gap = calc.채널가격차이(df)
    if len(gap):
        rows = []
        for _, r in gap.iterrows():
            항목 = f"{r['브랜드']} {r['메뉴']} ({r['매장']})"
            rows += [{"항목": 항목, "채널": "자사앱", "가격": r["자사앱가"]}, {"항목": 항목, "채널": r["플랫폼"], "가격": r["정상가"]}]
        cmp_df = pd.DataFrame(rows).drop_duplicates()
        fig2 = px.bar(cmp_df, x="채널", y="가격", color="채널", facet_col="항목", text="가격",
                      color_discrete_map={"자사앱": GOLD, "쿠팡이츠": BLACK, "배민": HONEY, "요기요": GRAY},
                      labels={"가격": "정상가(원)", "채널": ""})
        fig2.update_traces(texttemplate="%{text:,}원", textposition="outside", width=0.5)
        fig2.update_yaxes(range=[0, cmp_df["가격"].max() * 1.2])
        fig2.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
        fig2.update_layout(height=380, showlegend=False, margin=dict(l=0, r=10, t=30, b=0), plot_bgcolor="#fff")
        st.plotly_chart(fig2, width="stretch")
        for _, r in gap.iterrows():
            st.markdown(f"- **{r['브랜드']} {r['메뉴']}**: {r['플랫폼']}가 자사앱보다 **{int(r['자사앱 대비 차이']):+,}원**")
    else:
        st.info("같은 매장의 자사앱 가격이 있어야 계산됩니다.")

# ---------------- 행사 기록 ----------------
with 탭[2]:
    행사 = df[df["할인유형"] != "없음"]
    st.subheader("할인 행사 비교")
    if len(행사):
        fig3 = px.bar(행사, x="브랜드", y="할인율(%)", color="할인유형", barmode="group",
                      hover_data=["플랫폼", "메뉴", "메뉴할인액", "최소주문금액", "적용조건", "데이터구분"],
                      color_discrete_sequence=[GOLD, BLACK, HONEY, GRAY, "#8f6f3e"])
        fig3.update_layout(height=340, margin=dict(l=0, r=10, t=10, b=0), plot_bgcolor="#fff")
        st.plotly_chart(fig3, width="stretch")
    else:
        st.info("선택한 범위에 할인 행사 기록이 없습니다. 쿠폰 화면 캡처를 넣으면 채워집니다.")
    cols = ["데이터구분", "브랜드", "플랫폼", "매장", "메뉴", "정상가", "할인유형", "메뉴할인액", "할인적용가", "할인율(%)", "확인필요", "출처", "확인일", "비고"]
    st.dataframe(df[cols].style.apply(lambda row: ["background-color:#fff3d6" if row["확인필요"] else "" for _ in row], axis=1),
                 width="stretch", hide_index=True)
    st.download_button("현재 표 CSV로 내려받기", df[cols].to_csv(index=False).encode("utf-8-sig"), "프로모션_분석.csv")

# ---------------- 손익 계산기 ----------------
with 탭[3]:
    st.subheader("프로모션 손익 계산기")
    모드 = st.radio("방식", ["⚡ 자동 분석 (회사명만 입력)", "✍️ 수기 입력 (내부 자료로 상세 분석)"], horizontal=True, label_visibility="collapsed")

    with st.expander("주문 1건 가정값 (바꿀 수 있습니다)", expanded=False):
        a = st.columns(5)
        주문금액 = a[0].number_input("주문 금액", value=profit.기본가정["주문금액"], step=500)
        공급금액 = a[1].number_input("본사 공급 금액", value=profit.기본가정["공급금액"], step=100, help="점주가 본사에서 사는 원재료 등 (가정)")
        배달비 = a[2].number_input("점주 배달비 부담", value=profit.기본가정["배달비부담"], step=100)
        플수 = a[3].number_input("플랫폼 수수료율(%)", value=profit.기본가정["플랫폼수수료율"], step=0.1)
        결수 = a[4].number_input("결제 수수료율(%)", value=profit.기본가정["결제수수료율"], step=0.1)
        st.caption("모두 가정값입니다. 실제 계약 조건을 알면 바꿔 넣으세요.")

    if "자동" in 모드:
        st.markdown('<div class="note">회사명을 넣으면 전자공시(DART)에서 최근 손익을 가져와 <b>쿠폰 금액별 본전 기준</b>을 계산합니다. '
                    '쿠폰 사용률·증분 주문 같은 내부 자료는 공시에 없으므로, 여기서는 "몇 건이 새로 생겨야 본전인지" 기준선을 보여드립니다.</div>', unsafe_allow_html=True)
        q = st.text_input("회사명", value="교촌", placeholder="예: 교촌, BBQ, bhc, 굽네")
        if q:
            try:
                import dart
                후보 = dart.회사찾기(q)
            except Exception as e:
                후보 = pd.DataFrame(); st.error(f"회사 목록을 읽지 못했습니다: {e}")
            if 후보.empty:
                st.warning("공시 목록에서 회사를 찾지 못했습니다. 정식 회사명으로 넣어 보세요.")
            else:
                라벨 = [f"{r.회사명} ({'상장' if r.종목코드 else '비상장'})" for r in 후보.itertuples()]
                i = st.selectbox("회사 선택", range(len(라벨)), format_func=lambda k: 라벨[k])
                sel = 후보.iloc[i]
                if not keys.있음("OPENDART_API_KEY"):
                    st.error("DART 인증키가 없습니다. 설정.txt 에 OPENDART_API_KEY 를 넣어 주세요.")
                else:
                    with st.spinner("전자공시에서 손익을 가져오는 중… (비상장사는 감사보고서 원문을 읽어 30초 정도 걸립니다)"):
                        r = st.cache_data(dart.손익가져오기)(sel["corp_code"], sel["회사명"])
                    if not r:
                        st.warning("최근 3년 손익 자료를 찾지 못했습니다.")
                    else:
                        gm = r["매출총이익"] / r["매출액"]
                        m = st.columns(4)
                        m[0].metric("매출액", f"{r['매출액']/1e8:,.0f}억")
                        m[1].metric("매출총이익률", f"{gm*100:.1f}%")
                        m[2].metric("영업이익", f"{r['영업이익']/1e8:,.0f}억")
                        m[3].metric("영업이익률", f"{r['영업이익']/r['매출액']*100:.1f}%")
                        st.caption(f"출처: {r['출처']} · {r['기준']} 기준" + (f" · ⚠️ {r['확인필요']}" if r["확인필요"] else ""))
                        구조 = profit.건당구조(gm, 주문금액, 공급금액, 배달비, 플수, 결수)
                        st.session_state["구조"] = 구조
                        st.markdown("#### 주문 1건에서 남는 돈")
                        b = st.columns(3)
                        b[0].metric("본사 이익", 원(구조["본사 이익"]), help="본사 공급 금액 × 매출총이익률")
                        b[1].metric("점주 잔여액", 원(구조["점주 잔여액"]), help="주문 금액 − 공급 − 배달비 − 수수료 (인건비·임대료 차감 전)")
                        b[2].metric("추정 기여액 (본사+점주)", 원(구조["추정 기여액"]))
                        st.markdown("#### 쿠폰 금액별 본전 기준")
                        부담 = st.slider("쿠폰 비용 중 본사 부담 비율(%)", 0, 100, 50, 10)
                        t = profit.본전표(구조, 본사부담=부담)
                        c1, c2 = st.columns([3, 2])
                        with c1:
                            fig = px.bar(t, x=t["쿠폰 금액"].map(lambda v: f"{v:,}원"), y=t.columns[1], text=t.columns[1],
                                         color_discrete_sequence=[GOLD], labels={"x": "쿠폰 금액", t.columns[1]: "본전에 필요한 증분 비율(%)"})
                            fig.update_traces(texttemplate="%{text:.0f}%", textposition="outside")
                            fig.update_layout(height=320, margin=dict(l=0, r=0, t=20, b=0), plot_bgcolor="#fff")
                            st.plotly_chart(fig, width="stretch")
                        with c2:
                            for _, row in t.iterrows():
                                st.markdown(f"<div class='note' style='margin-bottom:6px'><b>{int(row['쿠폰 금액']):,}원 쿠폰</b>: 쿠폰 쓴 주문 100건 중 "
                                            f"<span class='big'>{row.iloc[1]:.0f}건</span> 이상이 새로 생긴 주문이어야 본전</div>", unsafe_allow_html=True)
                        st.dataframe(t.style.format({t.columns[1]: "{:.1f}%", t.columns[2]: "{:.1f}%", "쿠폰 금액": "{:,}원"}), hide_index=True, width="stretch")
                        st.caption("본전 증분 비율 = 쿠폰 금액 ÷ 1건 추정 기여액. 실제 쿠폰 사용률·증분은 내부 자료가 있어야 하므로 '수기 입력'에서 확인하세요.")
    else:
        st.markdown('<div class="note">회사 내부 자료(쿠폰 사용률, 새로 생긴 주문 수 등)를 넣으면 행사 1회의 <b>이익·손실과 확대/조정/중단 판단</b>을 계산합니다. '
                    '1차·2차 행사를 나란히 비교할 수 있습니다.</div>', unsafe_allow_html=True)
        구조 = st.session_state.get("구조") or profit.건당구조(0.2755, 주문금액, 공급금액, 배달비, 플수, 결수)
        if "구조" not in st.session_state:
            st.caption("매출총이익률은 교촌 2025년 공시값(27.6%)을 기본으로 씁니다. 자동 분석에서 회사를 고르면 그 값으로 바뀝니다.")
        공통 = st.columns(4)
        기여액 = 공통[0].number_input("1건 추정 기여액", value=int(구조["추정 기여액"]), step=100)
        본사이익 = 공통[1].number_input("1건 본사 이익", value=int(구조["본사 이익"]), step=100)
        부담 = 공통[2].slider("본사 부담 비율(%)", 0, 100, 50, 10)
        매장수 = 공통[3].number_input("참여 매장 수", value=100, step=10)
        결과 = {}
        cols = st.columns(2)
        for k, (이름, 기본) in enumerate([("1차 행사", (20000, 30, 1000, 3000, 0, 0)), ("2차 행사", (20000, 20, 1500, 2000, 0, 500))]):
            with cols[k]:
                st.markdown(f"##### {이름}")
                x = st.columns(3)
                주문 = x[0].number_input("행사 기간 주문 수", value=기본[0], step=1000, key=f"o{k}")
                사용률 = x[1].number_input("쿠폰 사용률(%)", value=기본[1], step=5, key=f"u{k}")
                증분 = x[2].number_input("새로 생긴 주문 수", value=기본[2], step=100, key=f"i{k}", help="행사가 없었으면 안 생겼을 주문 (비교 지역·기간과 대조해 추정)")
                y = st.columns(3)
                쿠폰 = y[0].number_input("쿠폰 금액", value=기본[3], step=500, key=f"c{k}")
                변동비 = y[1].number_input("매장 추가 변동비(1건)", value=기본[4], step=500, key=f"v{k}", help="행사로 늘어나는 포장·인건비 등")
                지원 = y[2].number_input("플랫폼 지원금(1건)", value=기본[5], step=100, key=f"p{k}")
                r = profit.행사계산(주문, 사용률, 증분, 쿠폰, 기여액, 본사이익, 변동비, 부담, 지원)
                결과[이름] = dict(r, 주문=주문, 증분주문=증분, 쿠폰=쿠폰, 지원=지원)
                색 = {"확대": "#2e7d32", "유지·조정": GOLD, "조정": "#c77700", "중단 검토": "#b23b3b"}[r["판단"]]
                st.markdown(f"<div style='border:2px solid {색};border-radius:14px;padding:12px 16px;background:#fff'>"
                            f"<span style='color:{색};font-weight:800;font-size:1.3rem'>판단: {r['판단']}</span><br>"
                            f"행사 손익 <span class='big'>{r['손익']:+,.0f}원</span> (매장당 {r['손익']/max(매장수,1):+,.0f}원)<br>"
                            f"새로 생긴 주문 비율 <b>{r['증분 비율']:.1f}%</b> / 본전 기준 <b>{r['본전 기준']:.1f}%</b></div>", unsafe_allow_html=True)
                칸 = "".join(f"<div style='flex:1;background:#fff;border:1px solid #ecdcc0;border-radius:12px;padding:8px 12px'><small style='color:#5f5850'>{a}</small><br><b style='font-size:1.15rem'>{b}</b></div>"
                            for a, b in [("할인비", 만(r["할인비"])), ("본사 손익", 만(r["본사 손익"], True)), ("점주 손익", 만(r["점주 손익"], True))])
                st.markdown(f"<div style='display:flex;gap:8px;margin-top:8px'>{칸}</div>", unsafe_allow_html=True)
        st.markdown("#### 1차 vs 2차")
        비교 = pd.DataFrame({n: {"행사 손익": v["손익"], "할인비": v["할인비"], "증분 이익": v["증분 이익"],
                                "본사 손익": v["본사 손익"], "점주 손익": v["점주 손익"]} for n, v in 결과.items()}) / 1e4
        fig = px.bar(비교.reset_index().melt(id_vars="index"), x="index", y="value", color="variable", barmode="group",
                     color_discrete_sequence=[GRAY, GOLD], labels={"index": "", "value": "만원", "variable": ""}, text_auto=",.0f")
        fig.update_layout(height=320, margin=dict(l=0, r=0, t=10, b=0), plot_bgcolor="#fff")
        st.plotly_chart(fig, width="stretch")
        st.markdown("#### 민감도: 쿠폰 사용률 × 매장 추가 변동비 (2차 행사 기준 손익)")
        v2 = 결과["2차 행사"]
        s = profit.민감도(v2["주문"], v2["증분주문"], v2["쿠폰"], 기여액, v2["지원"])
        st.dataframe(s.style.format("{:+,.0f}").map(lambda v: f"color:{'#b23b3b' if v < 0 else '#2e7d32'};font-weight:700"), width="stretch")
        st.caption("빨간 칸 = 손실. 사용률이 높을수록 할인비가 늘어나므로, 같은 증분이라도 손익이 줄어듭니다.")
        st.download_button("계산 결과 CSV", pd.DataFrame(결과).T.to_csv().encode("utf-8-sig"), "행사손익_계산.csv")

# ---------------- 보고서 ----------------
with 탭[4]:
    st.subheader("주간 보고서")
    파일 = sorted((ROOT / "output").glob("주간보고서_*.pdf"), reverse=True)
    if 파일:
        for f in 파일:
            st.download_button(f"⬇️ {f.stem}", f.read_bytes(), f.name, key=f.name)
    else:
        st.info("아직 만든 보고서가 없습니다.")
    st.caption("새 보고서는 'python src/report.py' 로 만듭니다 (제미나이 키 필요).")

st.divider()
st.caption("본 시스템은 공개 자료(전자공시·앱 화면 캡처·보도)와 가정값으로 계산한 참고용 분석입니다. 실제 계약 조건·내부 자료와 다를 수 있습니다.")
