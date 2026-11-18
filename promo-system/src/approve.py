"""확인을 마친 추출대기.csv 행을 본표(promotions.csv)로 옮깁니다.
사용법: python3 src/approve.py [플랫폼]   (플랫폼을 주면 '확인필요'로 둔 플랫폼 칸을 채웁니다)
"""
import sys, logging
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parent.parent
(ROOT / "logs").mkdir(exist_ok=True)
logging.basicConfig(filename=ROOT / "logs" / "approve.log", level=logging.INFO, encoding="utf-8",
                    format="%(asctime)s %(levelname)s %(message)s")
대기, 본표 = ROOT / "data" / "추출대기.csv", ROOT / "data" / "promotions.csv"
w = pd.read_csv(대기, dtype=str).fillna("")
if len(sys.argv) > 1:
    w.loc[w["플랫폼"] == "확인필요", "플랫폼"] = sys.argv[1]
m = pd.read_csv(본표, dtype=str).fillna("")
합 = pd.concat([m, w[m.columns]]).drop_duplicates("id", keep="last")
합.to_csv(본표, index=False, encoding="utf-8-sig")
대기.unlink()
logging.info(f"{len(w)}행 본표로 이동 (본표 {len(합)}행)")
print(f"{len(w)}행 이동, 본표 {len(합)}행")
