"""DART(전자공시) 자동 수집: 회사명 → 최근 연도 손익(매출·원가·이익).

상장사: 재무제표 API(fnlttSinglAcntAll)로 바로 가져옵니다.
비상장사(BBQ·bhc 등): 감사보고서 원문을 받아 손익계산서 표를 읽습니다.
  1차 = 표의 숫자를 규칙으로 읽기, 2차(실패 시) = 제미나이 AI로 읽기(→ '확인 필요' 표시).
"""
import io, json, re, ssl, zipfile, datetime, urllib.parse, urllib.request
from pathlib import Path
import pandas as pd
import keys

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "dart_cache"
CACHE.mkdir(parents=True, exist_ok=True)
API = "https://opendart.fss.or.kr/api/"
MODEL = "gemini-3.5-flash-lite"


def _get(url, raw=False, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": "promo-analyzer"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        b = r.read()
    return b if raw else json.loads(b.decode("utf-8"))


def _q(path, **p):
    p["crtfc_key"] = keys.get("OPENDART_API_KEY", "dummy")
    return API + path + "?" + urllib.parse.urlencode(p)


# ---------- 1. 회사 찾기 ----------
@__import__("functools").lru_cache(maxsize=1)
def _목록():
    return pd.read_csv(ROOT / "data" / "dart_기업목록.csv", dtype=str).fillna("")


def 회사찾기(이름, 최대=8):
    """이름이 들어간 회사 목록. 상장사·정확히 일치·짧은 이름 순."""
    df = _목록()
    이름 = 이름.strip()
    별칭 = {"교촌": "교촌에프앤비", "bbq": "제너시스비비큐", "BBQ": "제너시스비비큐", "비비큐": "제너시스비비큐",
          "bhc": "다이닝브랜즈그룹", "BHC": "다이닝브랜즈그룹", "비에이치씨": "다이닝브랜즈그룹"}
    이름 = 별칭.get(이름, 이름)
    m = df[df["회사명"].str.contains(re.escape(이름), case=False)].copy()
    if m.empty:
        return m
    m["점수"] = (m["회사명"] == 이름) * 100 + (m["종목코드"] != "") * 10 - m["회사명"].str.len() * 0.1
    return m.sort_values("점수", ascending=False).head(최대).drop(columns="점수")


# ---------- 2. 상장사: 재무제표 API ----------
항목 = {"매출액": ["매출액", "수익(매출액)", "영업수익", "매출"],
      "매출원가": ["매출원가", "영업비용"],
      "매출총이익": ["매출총이익"],
      "판매비와관리비": ["판매비와관리비", "판매비와 관리비"],
      "영업이익": ["영업이익", "영업이익(손실)"]}


def _숫자(v):
    v = str(v).replace(",", "").strip()
    neg = v.startswith("(") or v.startswith("-")
    v = re.sub(r"[^\d]", "", v)
    return (-int(v) if neg else int(v)) if v else None


def _api재무(corp, 연도, fs):
    d = _get(_q("fnlttSinglAcntAll.json", corp_code=corp, bsns_year=연도, reprt_code="11011", fs_div=fs))
    if d.get("status") != "000":
        return None
    rows = [r for r in d["list"] if r.get("sj_div") in ("IS", "CIS")]
    out = {}
    for k, names in 항목.items():
        for r in rows:
            if r["account_nm"].replace(" ", "") in [n.replace(" ", "") for n in names]:
                out[k] = _숫자(r["thstrm_amount"])
                break
    return out if out.get("매출액") else None


# ---------- 3. 비상장사: 감사보고서 원문 ----------
def _감사보고서(corp, 연도):
    d = _get(_q("list.json", corp_code=corp, bgn_de=f"{연도+1}0101", end_de=f"{연도+1}1231",
                pblntf_ty="F", page_count=100))
    if d.get("status") != "000":
        return None
    for r in d["list"]:
        if "감사보고서" in r["report_nm"] and "연결" not in r["report_nm"]:
            return r["rcept_no"]
    for r in d["list"]:
        if "감사보고서" in r["report_nm"]:
            return r["rcept_no"]
    return None


def _원문텍스트(rcept):
    b = _get(_q("document.xml", rcept_no=rcept), raw=True, timeout=120)
    z = zipfile.ZipFile(io.BytesIO(b))
    t = " ".join(z.read(n).decode("utf-8", "ignore") for n in z.namelist())
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", t)


def _손익구간(t):
    """'매출원가'와 '영업이익'이 가까이 붙어 있는 첫 구간 = 손익계산서 표."""
    for m in re.finditer("매출원가", t):
        seg = t[max(0, m.start() - 300): m.start() + 1500]
        if "영업이익" in seg or "영업손실" in seg:
            return seg
    return None


def _규칙읽기(seg):
    out = {}
    for k, names in 항목.items():
        for n in names:
            m = re.search(re.escape(n) + r"\s*(?:[\d,]{1,8}\s+)?(\(?[\d,]{5,}\)?)", seg)
            if m:
                out[k] = _숫자(m.group(1))
                break
    return out if out.get("매출액") and out.get("영업이익") else None


def _AI읽기(seg):
    if not keys.있음("GEMINI_API_KEY"):
        return None
    q = ("아래는 감사보고서의 손익계산서 일부입니다. 당기(가장 최근 연도) 금액만 원 단위 정수로 "
         'JSON 하나로 답하세요. 키: 매출액, 매출원가, 매출총이익, 판매비와관리비, 영업이익. 없으면 null.\n\n' + seg)
    body = json.dumps({"contents": [{"parts": [{"text": q}]}],
                       "generationConfig": {"responseMimeType": "application/json", "temperature": 0}}).encode()
    req = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent", data=body,
        headers={"Content-Type": "application/json", "x-goog-api-key": keys.get("GEMINI_API_KEY", "dummy")})
    with urllib.request.urlopen(req, timeout=90) as r:
        txt = json.loads(r.read())["candidates"][0]["content"]["parts"][0]["text"]
    d = json.loads(txt)
    return {k: (int(v) if v is not None else None) for k, v in d.items() if k in 항목}


# ---------- 4. 한 번에 ----------
def 손익가져오기(corp, 회사명="", 연도=None):
    """결과: dict(회사명, 연도, 기준, 출처, 확인필요, 매출액, ...). 최근 3개 연도까지 거슬러 찾습니다."""
    올해 = 연도 or datetime.date.today().year
    for y in range(올해 - 1, 올해 - 4, -1):
        f = CACHE / f"{corp}_{y}.json"
        if f.exists():
            return json.loads(f.read_text(encoding="utf-8"))
        r = None
        for fs, 이름 in (("OFS", "별도"), ("CFS", "연결")):
            v = _api재무(corp, y, fs)
            if v:
                r = dict(v, 기준=이름, 출처=f"DART 사업보고서 재무제표 ({y})", 확인필요="")
                break
        if not r:
            rc = _감사보고서(corp, y)
            if rc:
                seg = _손익구간(_원문텍스트(rc))
                if seg:
                    v = _규칙읽기(seg)
                    if v:
                        r = dict(v, 기준="감사보고서", 출처=f"DART 감사보고서 원문 ({y}, 접수번호 {rc})", 확인필요="")
                    else:
                        v = _AI읽기(seg)
                        if v and v.get("매출액"):
                            r = dict(v, 기준="감사보고서", 출처=f"DART 감사보고서 원문 ({y}, 접수번호 {rc})",
                                     확인필요="AI가 원문에서 읽은 값입니다. 원문과 한 번 대조해 주세요.")
        if r:
            if not r.get("매출총이익") and r.get("매출액") and r.get("매출원가"):
                r["매출총이익"] = r["매출액"] - r["매출원가"]
            r.update(회사명=회사명, 연도=y, corp_code=corp)
            f.write_text(json.dumps(r, ensure_ascii=False), encoding="utf-8")
            return r
    return None


if __name__ == "__main__":
    import sys
    for n in sys.argv[1:] or ["교촌", "BBQ"]:
        c = 회사찾기(n)
        print(n, "→", c.head(3).to_dict("records"))
        if len(c):
            print(손익가져오기(c.iloc[0]["corp_code"], c.iloc[0]["회사명"]))
