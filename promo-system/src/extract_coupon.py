"""2단계(쿠폰): 쿠폰 화면 캡처 → 행사 데이터 자동 변환 (제미나이 Flash-Lite).

사용법: python3 src/extract_coupon.py <플랫폼> <확인일> <브랜드> <캡처파일>
- 쿠폰은 해당 브랜드의 대표 메뉴(본표에서 '주문많음' 꼬리표, 없으면 가장 먼저 입력된 메뉴)에 적용해 할인율을 계산합니다.
- 결과는 data/추출대기.csv 에 쌓이고, 확인 후 approve.py 로 본표에 옮깁니다.
"""
import sys, json, logging
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).parent))
import extract

PROMPT = """이 이미지는 배달앱의 쿠폰·혜택 화면 캡처입니다. 화면에 '실제로 보이는' 쿠폰만 JSON 배열로 출력하세요. 추측 금지, 없으면 빈 문자열.
각 항목: {"쿠폰명": 그대로, "할인액": 원 단위 숫자(정률이면 ""), "할인율": % 숫자(정액이면 ""),
"주문방식": "배달" 또는 "포장" 또는 "", "최소주문금액": 숫자, "만료": 화면 문구 그대로(예: 오늘 만료, 11/30까지),
"중복": 쿠폰이 '중복 가능한 할인' 같은 제목 아래 있거나 '중복 가능'이 보이면 "예", '중복 불가'면 "아니오", 없으면 ""}
플랫폼 공통 혜택(예: 멤버십 배달비 0원)은 {"쿠폰명": 문구, "플랫폼혜택": true} 로 따로 넣으세요. JSON 배열만 출력하세요."""


def main():
    플랫폼, 확인일, 브랜드, f = sys.argv[1:5]
    extract.PROMPT = PROMPT
    items = extract.읽기(f)
    본표 = pd.read_csv(extract.ROOT / "data" / "promotions.csv", dtype=str).fillna("")
    후보 = 본표[(본표["브랜드"] == 브랜드) & (본표["플랫폼"] == 플랫폼) & (본표["데이터구분"] == "실제") & (본표["할인유형"] == "없음")]
    대표 = 후보[후보["비고"].str.contains("주문많음")].head(1)
    if 대표.empty: 대표 = 후보.head(1)
    메뉴, 가격 = (대표.iloc[0]["메뉴"], 대표.iloc[0]["정상가"]) if len(대표) else ("", "")
    rows, 혜택 = [], []
    for i, it in enumerate(items, 1):
        if it.get("플랫폼혜택"):
            혜택.append(it.get("쿠폰명", "")); continue
        정률 = str(it.get("할인율", "")).strip() != ""
        rows.append({"id": f"K{Path(f).stem}_{i}", "데이터구분": "실제", "브랜드": 브랜드, "플랫폼": 플랫폼, "매장": "",
                     "메뉴": 메뉴, "정상가": 가격, "할인유형": "정률" if 정률 else "정액쿠폰",
                     "할인값": it.get("할인율") if 정률 else it.get("할인액"), "최소주문금액": it.get("최소주문금액", ""),
                     "중복적용": it.get("중복", ""), "시작일": "",
                     "종료일": 확인일 if "오늘" in str(it.get("만료", "")) else "",
                     "적용조건": f"{it.get('쿠폰명','')} · {it.get('주문방식','')} · {it.get('만료','')}",
                     "출처유형": "직접캡처", "출처": Path(f).name, "확인일": 확인일,
                     "비고": f"할인율은 대표 메뉴({메뉴}) 기준 계산" + (f" / 플랫폼 혜택: {', '.join(혜택)}" if 혜택 else "")})
    for r in rows:
        if 혜택 and "플랫폼 혜택" not in r["비고"]:
            r["비고"] += f" / 플랫폼 혜택: {', '.join(혜택)}"
    out = extract.ROOT / "data" / "추출대기.csv"
    df = pd.DataFrame(rows).astype(str)
    if out.exists():
        df = pd.concat([pd.read_csv(out, dtype=str), df]).drop_duplicates("id", keep="last")
    df.to_csv(out, index=False, encoding="utf-8-sig")
    print(pd.DataFrame(rows)[["브랜드", "메뉴", "정상가", "할인유형", "할인값", "최소주문금액", "중복적용", "종료일", "적용조건"]].to_string(index=False))
    print("플랫폼 혜택:", 혜택)


if __name__ == "__main__":
    main()
