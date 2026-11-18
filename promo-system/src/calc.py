"""1단계: 프로모션 데이터 검사 + 할인율 자동 계산.

사용법:  python3 src/calc.py  [CSV 경로]
결과:    output/계산결과.csv, output/채널가격차이.csv, output/요약.csv, logs/calc.log
"""
import sys, logging
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
(ROOT / "logs").mkdir(exist_ok=True)
LOG = ROOT / "logs" / "calc.log"
logging.basicConfig(filename=LOG, level=logging.INFO, encoding="utf-8",
                    format="%(asctime)s %(levelname)s %(message)s")

필수 = ["id", "데이터구분", "브랜드", "플랫폼", "메뉴", "정상가", "할인유형", "출처유형", "확인일"]
할인유형목록 = ["없음", "정액쿠폰", "정률", "가격인하", "배달비할인", "사이드증정"]


def 불러오기(path):
    df = pd.read_csv(path, dtype=str).fillna("")
    빠진칸 = [c for c in 필수 if c not in df.columns]
    if 빠진칸:
        raise ValueError(f"필수 열이 없습니다: {빠진칸}")
    for c in ["정상가", "할인값", "최소주문금액"]:
        df[c] = pd.to_numeric(df[c].str.replace(",", ""), errors="coerce")
    return df


def 행계산(r):
    메모 = []
    정상가, 값, 유형 = r["정상가"], r["할인값"], r["할인유형"]
    if pd.isna(정상가) or 정상가 <= 0:
        return pd.Series({"메뉴할인액": None, "할인적용가": None, "할인율(%)": None,
                          "배달비할인액": 0, "확인필요": "정상가 없음"})
    if 유형 not in 할인유형목록:
        메모.append(f"알 수 없는 할인유형({유형})")
    값 = 0 if pd.isna(값) else 값
    메뉴할인, 배달할인 = 0, 0
    if 유형 in ("정액쿠폰", "가격인하"):
        메뉴할인 = 값
    elif 유형 == "정률":
        메뉴할인 = round(정상가 * 값 / 100)
    elif 유형 == "배달비할인":
        배달할인 = 값
    elif 유형 == "사이드증정":
        메모.append("증정품 가치는 금액에 미반영")
    최소 = r["최소주문금액"]
    if 유형 != "없음" and not pd.isna(최소) and 최소 > 정상가:
        메모.append(f"단품 주문으로는 최소주문 {int(최소):,}원 미달")
    if 유형 != "없음":
        if r.get("중복적용", "") in ("", "불명"):
            메모.append("중복 적용 여부 불명확")
        if not r.get("종료일", ""):
            메모.append("종료일 불명확")
    return pd.Series({
        "메뉴할인액": 메뉴할인,
        "할인적용가": 정상가 - 메뉴할인,
        "할인율(%)": round(메뉴할인 / 정상가 * 100, 1),
        "배달비할인액": 배달할인,
        "확인필요": " / ".join(메모),
    })


def 채널가격차이(df):
    """같은 브랜드·매장·메뉴에서 자사앱 대비 각 배달앱 정상가 차이."""
    기준 = df[df["플랫폼"] == "자사앱"][["브랜드", "매장", "메뉴", "정상가", "데이터구분"]]
    기준 = 기준.rename(columns={"정상가": "자사앱가"})
    m = df[df["플랫폼"] != "자사앱"].merge(기준, on=["브랜드", "매장", "메뉴", "데이터구분"])
    m["자사앱 대비 차이"] = m["정상가"] - m["자사앱가"]
    return m[["데이터구분", "브랜드", "매장", "메뉴", "플랫폼", "정상가", "자사앱가", "자사앱 대비 차이", "확인일"]]


def 요약(df):
    행사 = df[df["할인유형"] != "없음"]
    g = 행사.groupby(["데이터구분", "브랜드"]).agg(
        행사수=("id", "count"), 평균할인액=("메뉴할인액", "mean"),
        평균할인율=("할인율(%)", "mean"), 확인필요건수=("확인필요", lambda s: (s != "").sum()))
    return g.round(1).reset_index()


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "data" / "promotions.csv"
    df = 불러오기(path)
    dup = df[df["id"].duplicated()]["id"].tolist()
    if dup:
        logging.warning(f"중복 id: {dup}")
    out = pd.concat([df, df.apply(행계산, axis=1)], axis=1)
    (ROOT / "output").mkdir(exist_ok=True)
    out.to_csv(ROOT / "output" / "계산결과.csv", index=False, encoding="utf-8-sig")
    채널가격차이(out).to_csv(ROOT / "output" / "채널가격차이.csv", index=False, encoding="utf-8-sig")
    요약(out).to_csv(ROOT / "output" / "요약.csv", index=False, encoding="utf-8-sig")
    logging.info(f"{path.name}: {len(df)}행 계산, 확인필요 {(out['확인필요'] != '').sum()}행")
    return out


if __name__ == "__main__":
    o = main()
    pd.set_option("display.width", 200); pd.set_option("display.max_columns", 20)
    print(o[["id", "데이터구분", "브랜드", "플랫폼", "메뉴", "정상가", "할인유형", "메뉴할인액", "할인적용가", "할인율(%)", "배달비할인액", "확인필요"]].to_string(index=False))
    print("\n[채널 가격 차이]"); print(pd.read_csv(ROOT / "output" / "채널가격차이.csv").to_string(index=False))
    print("\n[요약]"); print(pd.read_csv(ROOT / "output" / "요약.csv").to_string(index=False))
