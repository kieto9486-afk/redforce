"""5단계: 공식 홈페이지 이벤트 변경 감지 → 정리 → 보고서 자동 갱신.
사용법: python3 src/monitor.py
1) 각 브랜드 이벤트 목록 페이지의 글자를 저장(data/snapshots)
2) 지난번 저장본과 비교해 새로 생긴 줄 / 사라진 줄을 찾음
3) 변경(또는 첫 실행)이 있으면 제미나이가 이벤트명·기간·혜택만 표로 정리 → data/공식이벤트.csv
4) 변경이 있으면 주간 보고서를 다시 만듦
"""
import os, sys, json, subprocess, datetime, logging, urllib.request
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).parent))
import extract

ROOT = extract.ROOT
(ROOT / "logs").mkdir(exist_ok=True)
SNAP = ROOT / "data" / "snapshots"
log = logging.getLogger("monitor")
h = logging.FileHandler(ROOT / "logs" / "monitor.log", encoding="utf-8")
h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s")); log.addHandler(h); log.setLevel(logging.INFO)
PROMPT = ("아래는 치킨 브랜드 공식 홈페이지 '진행 중 이벤트' 페이지의 글자입니다. 메뉴바·회사소개 같은 줄은 무시하고, 실제 이벤트만 JSON 배열로 정리하세요. "
          "추측 금지, 글자에 없는 정보는 빈 문자열. 각 항목: {\"이벤트명\":..., \"기간\": 글자 그대로, \"혜택\": 할인·증정 내용이 글자에 있으면 그대로}. JSON 배열만.\n\n")


def 찍기(url):
    out = subprocess.run(["node", str(ROOT / "src" / "snap.js"), url], capture_output=True, text=True, timeout=120)
    return json.loads(out.stdout)


def 정리(lines):
    body = {"contents": [{"parts": [{"text": PROMPT + "\n".join(lines)}]}],
            "generationConfig": {"temperature": 0, "responseMimeType": "application/json"}}
    req = urllib.request.Request(extract.URL, data=json.dumps(body).encode(),
          headers={"Content-Type": "application/json", "x-goog-api-key": os.environ.get("GEMINI_API_KEY", "dummy")})
    r = json.load(urllib.request.urlopen(req, timeout=120))
    return json.loads(r["candidates"][0]["content"]["parts"][0]["text"])


def main():
    SNAP.mkdir(exist_ok=True)
    오늘 = datetime.date.today().isoformat()
    sites = json.load(open(ROOT / "src" / "sites.json", encoding="utf-8"))
    결과, 이벤트 = [], []
    for 브랜드, url in sites.items():
        if not url.startswith("http"):
            결과.append({"브랜드": 브랜드, "상태": url}); continue
        d = 찍기(url)
        if not d.get("ok") or d.get("status") != 200:
            log.error(f"{브랜드}: 접속 실패 {d.get('status')} {d.get('error','')}")
            결과.append({"브랜드": 브랜드, "상태": f"접속 실패({d.get('status')})"}); continue
        이전파일 = sorted(SNAP.glob(f"{브랜드}_*.json"))
        이전 = set(json.load(open(이전파일[-1], encoding="utf-8"))["lines"]) if 이전파일 else None
        지금 = set(d["lines"])
        json.dump(d, open(SNAP / f"{브랜드}_{오늘}.json", "w", encoding="utf-8"), ensure_ascii=False)
        if 이전 is None:
            상태, 새줄, 빠진줄 = "첫 수집", [], []
        else:
            새줄, 빠진줄 = sorted(지금 - 이전), sorted(이전 - 지금)
            상태 = f"변경 있음(+{len(새줄)} / -{len(빠진줄)}줄)" if (새줄 or 빠진줄) else "변경 없음"
        log.info(f"{브랜드}: {상태}")
        결과.append({"브랜드": 브랜드, "상태": 상태, "새로 생긴 줄": " | ".join(새줄[:5]), "사라진 줄": " | ".join(빠진줄[:5])})
        if 이전 is None or 새줄 or 빠진줄:
            try:
                for e in 정리(d["lines"]):
                    이벤트.append({"브랜드": 브랜드, **e, "출처": url, "확인일": 오늘, "정리방식": "AI 정리(원문 글자 기준)"})
            except Exception as ex:
                log.error(f"{브랜드}: AI 정리 실패 {ex}")
    pd.DataFrame(결과).to_csv(ROOT / "output" / "변경감지_결과.csv", index=False, encoding="utf-8-sig")
    if 이벤트:
        f = ROOT / "data" / "공식이벤트.csv"
        new = pd.DataFrame(이벤트)
        if f.exists():
            old = pd.read_csv(f, dtype=str)
            new = pd.concat([old[~old["브랜드"].isin(new["브랜드"].unique())], new])
        new.to_csv(f, index=False, encoding="utf-8-sig")
        import report
        print("보고서 갱신:", report.만들기())
    print(pd.DataFrame(결과)[["브랜드", "상태"]].to_string(index=False))


if __name__ == "__main__":
    main()
