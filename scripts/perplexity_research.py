#!/usr/bin/env python3
"""퍼플렉시티 API로 기업 자료를 수집해 릴스 기획용 분석 초안(.md)을 만듭니다.

사용법:
    export PERPLEXITY_API_KEY=pplx-...        # 키는 코드에 적지 말고 환경변수로!
    python3 scripts/perplexity_research.py "교촌치킨"
    python3 scripts/perplexity_research.py "교촌치킨" --slug kyochon --effort medium

결과: research/<slug>.md  (자료수집 → SWOT → STP → 성장 방안 → 예상 결과 + 출처 목록)
추가 설치 없이 파이썬 표준 라이브러리만 씁니다.
"""

import argparse
import datetime as dt
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

API_URL = "https://api.perplexity.ai/v1/agent"  # 2026-09 Sonar Chat Completions 종료 → Agent API
ROOT = Path(__file__).resolve().parent.parent

SYSTEM_PROMPT = """너는 인스타그램 '기업분석 마케터' 계정의 리서처야.
최신 공개 자료(공시, 언론 보도, 회사 발표)를 웹에서 찾아 한국어로 정리해.
숫자에는 기준 연도와 출처 번호([1], [2] …)를 꼭 붙이고, 확인되지 않은 내용은 '추정'이라고 표시해."""

USER_PROMPT = """기업: {company}

아래 순서와 제목 그대로 마크다운으로 정리해 줘.

## 1. 자료수집
- 기업 개요, 주력 사업/브랜드, 최근 3년 매출·영업이익, 매장 수, 최근 이슈

## 2. SWOT
- 강점 / 약점 / 기회 / 위협 각 3개씩, 근거 포함

## 3. STP
- 세분화, 타깃, 포지셔닝

## 4. 성장 방안
- 실행 가능한 방안 3개 (작은 가게 사장님도 따라 할 수 있는 관점 포함)

## 5. 예상 결과
- 각 방안의 기대 효과 (가정치임을 명시)

## 6. 릴스 첫 장면 훅 후보
- 숫자나 반전이 들어간 한 문장 5개
"""


def slugify(text: str) -> str:
    slug = re.sub(r"[^0-9A-Za-z가-힣]+", "-", text).strip("-").lower()
    return slug or "company"



def call_perplexity(api_key: str, company: str, effort: str) -> dict:
    payload = {
        "effort": effort,
        "instructions": SYSTEM_PROMPT,
        "input": USER_PROMPT.format(company=company),
        "tools": [{"type": "web_search"}],
    }
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=600) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:500]
        if "paid credit" in body:
            hint = "유료 크레딧이 필요해요. console.perplexity.ai에서 크레딧을 충전하세요."
        else:
            hint = {
                401: "API 키가 없거나 틀렸어요. 내 컴퓨터라면 PERPLEXITY_API_KEY를 설정하고, "
                "클라우드라면 시크릿(api.perplexity.ai, Bearer)을 등록한 뒤 새 세션에서 실행하세요.",
                402: "크레딧이 부족해요. console.perplexity.ai에서 크레딧을 충전하세요.",
                400: "요청 형식 오류예요. --effort 값(fast, low, medium, high, xhigh)을 확인하세요.",
                429: "요청이 너무 많아요. 잠시 후 다시 시도하세요.",
            }.get(e.code, "응답 내용을 확인하세요.")
        sys.exit(f"[오류] HTTP {e.code}: {hint}\n{body}")
    except urllib.error.URLError as e:
        sys.exit(f"[오류] 네트워크 연결 실패: {e.reason}")


def build_markdown(company: str, effort: str, data: dict) -> str:
    # Agent API 응답: output[] 안에 message(본문)와 search_results(출처)가 섞여 있어요.
    texts, sources = [], []
    for item in data.get("output", []):
        if item.get("type") == "message":
            texts += [c.get("text", "") for c in item.get("content", []) if c.get("type") == "output_text"]
        elif item.get("type") == "search_results":
            sources += item.get("results", [])
    content = "\n".join(t for t in texts if t).strip() or "(응답에 본문이 없었어요)"
    sources.sort(key=lambda r: r.get("id", 0))

    lines = [
        f"# {company} 기업분석 초안",
        "",
        f"- 생성: {dt.date.today().isoformat()} · Perplexity Agent API (effort `{effort}`)",
        "- AI가 모은 초안이에요. 영상에 쓰기 전에 숫자는 출처 링크로 꼭 다시 확인하세요.",
        "",
        content,
        "",
        "## 출처",
    ]
    for i, s in enumerate(sources, 1):
        num = s.get("id", i)  # 본문의 [n] 번호와 맞춰요
        title = s.get("title") or s["url"]
        date = f" ({s['date']})" if s.get("date") else ""
        lines.append(f"{num}. [{title}]({s['url']}){date}")
    if not sources:
        lines.append("- (응답에 출처가 없었어요)")
    return "\n".join(lines) + "\n"


def main() -> None:
    p = argparse.ArgumentParser(description="퍼플렉시티로 기업분석 초안 만들기")
    p.add_argument("company", help="분석할 기업 이름 (예: 교촌치킨)")
    p.add_argument("--slug", help="파일 이름 (기본: 기업 이름에서 자동 생성)")
    p.add_argument("--effort", default="fast", choices=["fast", "low", "medium", "high", "xhigh"],
                   help="검색 깊이: fast(저렴·빠름) … high/xhigh(깊은 리서치, 비용↑)")
    p.add_argument("--out-dir", default=str(ROOT / "research"), help="저장 폴더")
    args = p.parse_args()

    api_key = os.environ.get("PERPLEXITY_API_KEY", "").strip().strip('"').strip("'")
    if not api_key:
        # Claude Code 클라우드에서 '시크릿 추가'(api.perplexity.ai, Bearer)로 등록했다면
        # 프록시가 진짜 키로 바꿔 넣어 주므로 자리표시용 값만 보내면 돼요.
        api_key = "pplx-proxy-injected"
        print("PERPLEXITY_API_KEY가 없어 클라우드 시크릿(프록시 주입) 방식으로 요청해요.")

    print(f"'{args.company}' 자료 수집 중… (effort: {args.effort}, 30초~몇 분 걸려요)")
    data = call_perplexity(api_key, args.company, args.effort)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{args.slug or slugify(args.company)}.md"
    out_path.write_text(build_markdown(args.company, args.effort, data), encoding="utf-8")
    print(f"완료: {out_path}")
    if data.get("usage"):
        print(f"사용량: {data['usage']}")


if __name__ == "__main__":
    main()
