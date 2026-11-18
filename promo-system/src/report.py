"""4단계: AI 분석 보고서 자동 생성.
- '확인된 사실'은 코드가 데이터에서 직접 계산합니다(AI가 만들지 않음).
- 'AI 해석·제안'만 제미나이가 씁니다. 사실 목록에 없는 숫자는 쓰지 못하게 지시합니다.
사용법: python3 src/report.py   → output/주간보고서_YYYYMMDD.html (+ .pdf, Playwright 있을 때)
"""
import keys
import os, sys, json, datetime, logging, urllib.request, subprocess, html
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).parent))
import calc, extract

ROOT = extract.ROOT
(ROOT / "logs").mkdir(exist_ok=True)
logging.basicConfig(filename=ROOT / "logs" / "report.log", level=logging.INFO, encoding="utf-8",
                    format="%(asctime)s %(levelname)s %(message)s")


def 사실목록(df):
    d = df[df["데이터구분"] == "실제"]
    f = []
    메뉴 = d[d["할인유형"] == "없음"]
    for b, g in 메뉴.groupby("브랜드"):
        f.append(f"{b}: 확인 메뉴 {g['메뉴'].nunique()}개(기록 {len(g)}건), 정상가 {int(g['정상가'].min()):,}~{int(g['정상가'].max()):,}원 (플랫폼: {', '.join(sorted(g['플랫폼'].unique()))})")
    for _, r in calc.채널가격차이(d).iterrows():
        f.append(f"{r['브랜드']} {r['메뉴']}({r['매장']}): {r['플랫폼']} {int(r['정상가']):,}원 vs 자사앱 {int(r['자사앱가']):,}원, 차이 {int(r['자사앱 대비 차이']):+,}원")
    for _, r in d[d["할인유형"] != "없음"].iterrows():
        f.append(f"{r['브랜드']} {r['플랫폼']} 쿠폰: {int(r['메뉴할인액']):,}원 할인({r['적용조건']}), 최소주문 {int(r['최소주문금액']):,}원, 중복 {r['중복적용'] or '불명'}, 대표메뉴 {r['메뉴']} 기준 할인율 {r['할인율(%)']}%")
    태그 = d[d["비고"].str.contains("리뷰이벤트")]["브랜드"].unique()
    if len(태그): f.append(f"리뷰이벤트 꼬리표가 붙은 브랜드: {', '.join(태그)}")
    쿠폰브랜드 = set(d[d["할인유형"] != "없음"]["브랜드"])
    없음 = sorted(set(메뉴["브랜드"]) - 쿠폰브랜드)
    if 없음: f.append(f"이번 수집에서 쿠폰 화면이 확인되지 않은 브랜드: {', '.join(없음)} (쿠폰이 없다는 뜻이 아니라 캡처되지 않았다는 뜻)")
    return f


def ai해석(사실):
    prompt = ("당신은 교촌에프앤비 플랫폼운영팀의 분석 보조입니다. 아래 '확인된 사실'만 근거로 한국어 존댓말로 쓰세요.\n"
              "규칙: 사실 목록에 없는 숫자·사실을 만들지 마세요. 추정이면 '추정'이라고 쓰세요. 사실에 적히지 않은 채널(자사앱·배민 등)이나 대상을 행사에 덧붙이지 마세요. 경쟁사나 교촌을 깎아내리는 표현을 쓰지 마세요. 데이터가 적다는 한계를 1줄 밝히세요.\n"
              "형식(JSON): {\"동향요약\": 3줄 이내, \"브랜드별전략차이\": [문장들], \"플랫폼특징\": [문장들], "
              "\"교촌기회\": [문장들], \"교촌위험\": [문장들], \"검토할프로모션\": [문장들 2~3개, 각 문장 끝에 확인할 지표 포함], \"한계\": 문장}\n\n확인된 사실:\n- " + "\n- ".join(사실))
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"}}
    req = urllib.request.Request(extract.URL, data=json.dumps(body).encode(),
          headers={"Content-Type": "application/json", "x-goog-api-key": keys.get("GEMINI_API_KEY", "dummy")})
    r = json.load(urllib.request.urlopen(req, timeout=120))
    u = r.get("usageMetadata", {})
    logging.info(f"보고서 AI 호출: 입력 {u.get('promptTokenCount')} 출력 {u.get('candidatesTokenCount')} 토큰")
    return json.loads(r["candidates"][0]["content"]["parts"][0]["text"])


def 만들기():
    df = calc.불러오기(ROOT / "data" / "promotions.csv")
    df = pd.concat([df, df.apply(calc.행계산, axis=1)], axis=1)
    사실 = 사실목록(df)
    ev_f = ROOT / "data" / "공식이벤트.csv"
    ev = pd.read_csv(ev_f, dtype=str).fillna("") if ev_f.exists() else pd.DataFrame()
    for _, e in ev.iterrows():
        사실.append(f"[공식 홈페이지] {e['브랜드']}: {e['이벤트명']} ({e['기간']}) {e['혜택']}".strip())
    a = ai해석(사실)
    오늘 = datetime.date.today().strftime("%Y%m%d")
    li = lambda xs: "".join(f"<li>{html.escape(str(x))}</li>" for x in (xs if isinstance(xs, list) else [xs]))
    doc = f"""<!doctype html><html lang="ko"><meta charset="utf-8"><title>경쟁사 프로모션 주간 보고서</title>
<style>body{{font-family:Pretendard,'Noto Sans KR',sans-serif;max-width:860px;margin:32px auto;color:#1e1b17;line-height:1.6;padding:0 16px}}
h1{{font-size:22px;border-bottom:3px solid #B99764;padding-bottom:6px}}h2{{font-size:16px;margin-top:22px}}
.f{{background:#faf5ea;border-left:4px solid #1e1b17;padding:8px 14px}}.a{{background:#fff;border:1px dashed #B99764;padding:8px 14px}}
.tag{{font-size:11px;font-weight:700;padding:2px 8px;border-radius:9px;color:#fff;margin-left:6px}}.t1{{background:#1e1b17}}.t2{{background:#B99764}}
.m{{font-size:12px;color:#777}}</style>
<h1>치킨 브랜드 경쟁사 프로모션 주간 보고서</h1>
<p class="m">작성 {datetime.date.today()} · 데이터: 실제 {int((df['데이터구분']=='실제').sum())}건(직접 캡처·보도), 가상 데이터는 보고서에서 제외 · 자동 생성 후 담당자 확인용 초안</p>
<h2>1. 확인된 사실<span class="tag t1">데이터에서 자동 계산 · [공식 홈페이지] 줄은 원문 글자를 AI가 정리</span></h2><div class="f"><ul>{li(사실)}</ul></div>
<h2>2. 동향 요약<span class="tag t2">AI 해석</span></h2><div class="a"><p>{html.escape(str(a.get('동향요약','')))}</p></div>
<h2>3. 브랜드별 가격·할인 전략 차이<span class="tag t2">AI 해석</span></h2><div class="a"><ul>{li(a.get('브랜드별전략차이',[]))}</ul></div>
<h2>4. 플랫폼별 특징<span class="tag t2">AI 해석</span></h2><div class="a"><ul>{li(a.get('플랫폼특징',[]))}</ul></div>
<h2>5. 교촌의 기회와 위험<span class="tag t2">AI 해석</span></h2><div class="a"><b>기회</b><ul>{li(a.get('교촌기회',[]))}</ul><b>위험</b><ul>{li(a.get('교촌위험',[]))}</ul></div>
<h2>6. 검토해 볼 프로모션<span class="tag t2">AI 제안 · 검증 전</span></h2><div class="a"><ul>{li(a.get('검토할프로모션',[]))}</ul></div>
<p class="m">한계: {html.escape(str(a.get('한계','')))}</p></html>"""
    out = ROOT / "output" / f"주간보고서_{오늘}.html"
    out.write_text(doc, encoding="utf-8")
    pdf = out.with_suffix(".pdf")
    js = f"const {{chromium}}=require('playwright');(async()=>{{const b=await chromium.launch();const p=await b.newPage();await p.goto('file://{out}');await p.pdf({{path:'{pdf}',format:'A4',margin:{{top:'12mm',bottom:'12mm'}}}});await b.close();}})();"
    try:
        subprocess.run(["node", "-e", js], check=True, timeout=120)
    except Exception as e:
        logging.warning(f"PDF 변환 실패(HTML은 생성됨): {e}")
    logging.info(f"보고서 생성: {out.name}")
    return out


if __name__ == "__main__":
    print(만들기())
