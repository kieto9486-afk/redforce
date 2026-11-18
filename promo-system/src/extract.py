"""2단계: 배달앱 캡처 → 표 자동 변환 (제미나이 Flash-Lite).

사용법: python3 src/extract.py <플랫폼> <확인일 YYYY-MM-DD> <캡처파일...>
  - 파일 이름 앞부분(밑줄 앞)을 브랜드로 씁니다. 예: BBQ_20261115.png
  - 결과는 data/추출대기.csv 에 쌓이고, 사람이 확인한 뒤 promotions.csv 로 옮깁니다.
API 키는 코드에 없습니다(실행 환경에서 자동 주입).
"""
import keys
import os, sys, json, base64, logging, urllib.request
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
(ROOT / "logs").mkdir(exist_ok=True)
logging.basicConfig(filename=ROOT / "logs" / "extract.log", level=logging.INFO,
                    encoding="utf-8", format="%(asctime)s %(levelname)s %(message)s")
MODEL = "gemini-3.5-flash-lite"
URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
PROMPT = """이 이미지는 배달앱의 치킨 매장 메뉴 화면 캡처입니다.
화면에 '실제로 보이는' 메뉴만 JSON 배열로 출력하세요. 보이지 않는 정보는 절대 추측하지 말고 빈 문자열로 두세요.
각 항목: {"메뉴": 메뉴명(앞의 [BEST] 같은 꼬리표 제외), "정상가": 숫자(원, 쉼표 없이),
"꼬리표": 화면의 배지(예: 주문많음, 리뷰최고, 리뷰이벤트, BEST, 대표; 여러 개면 / 로 구분),
"할인표시": 할인·쿠폰 문구가 화면에 있으면 그대로, 없으면 "",
"추천율": 엄지 아이콘 옆 % 숫자만(% 기호 제외, 괄호 안 평가 수는 무시), "리뷰수": 말풍선 아이콘 옆 "리뷰 (숫자)"의 숫자(없으면 "")}
가격이 잘려 보이지 않는 메뉴는 넣지 마세요. JSON 배열만 출력하세요."""


def 읽기(path):
    img = base64.b64encode(Path(path).read_bytes()).decode()
    body = {"contents": [{"parts": [{"text": PROMPT},
            {"inline_data": {"mime_type": "image/png", "data": img}}]}],
            "generationConfig": {"temperature": 0, "responseMimeType": "application/json"}}
    req = urllib.request.Request(URL, data=json.dumps(body).encode(),
          headers={"Content-Type": "application/json", "x-goog-api-key": keys.get("GEMINI_API_KEY", "dummy")})
    r = json.load(urllib.request.urlopen(req, timeout=120))
    text = r["candidates"][0]["content"]["parts"][0]["text"]
    use = r.get("usageMetadata", {})
    logging.info(f"{Path(path).name}: 토큰 입력 {use.get('promptTokenCount')} 출력 {use.get('candidatesTokenCount')}")
    return json.loads(text)


def main():
    플랫폼, 확인일, files = sys.argv[1], sys.argv[2], sys.argv[3:]
    rows = []
    for f in files:
        브랜드 = Path(f).stem.split("_")[0]
        try:
            items = 읽기(f)
        except Exception as e:
            logging.error(f"{f}: {e}"); print("실패:", f, e); continue
        for i, it in enumerate(items, 1):
            rows.append({"id": f"C{Path(f).stem}_{i}", "데이터구분": "실제", "브랜드": 브랜드, "플랫폼": 플랫폼,
                         "매장": "", "메뉴": it.get("메뉴", ""), "정상가": it.get("정상가", ""),
                         "할인유형": "없음" if not it.get("할인표시") else "확인필요",
                         "할인값": 0, "최소주문금액": "", "중복적용": "", "시작일": "", "종료일": "",
                         "적용조건": it.get("할인표시", ""), "출처유형": "직접캡처", "출처": Path(f).name,
                         "확인일": 확인일, "비고": " / ".join(x for x in [it.get("꼬리표", ""),
                             f"추천 {str(it['추천율']).rstrip('%')}%" if it.get("추천율") else "",
                             f"리뷰 {it['리뷰수']}" if it.get("리뷰수") else ""] if x)})
    out = ROOT / "data" / "추출대기.csv"
    df = pd.DataFrame(rows)
    if out.exists():
        df = pd.concat([pd.read_csv(out, dtype=str), df.astype(str)]).drop_duplicates("id", keep="last")
    df.to_csv(out, index=False, encoding="utf-8-sig")
    print(pd.DataFrame(rows)[["브랜드", "메뉴", "정상가", "비고"]].to_string(index=False))


if __name__ == "__main__":
    main()
