#!/usr/bin/env python3
"""퍼플렉시티 API로 기업 자료를 수집해 릴스 기획용 분석 초안(.md)을 만듭니다.

사용법:
    export PERPLEXITY_API_KEY=pplx-...        # 키는 코드에 적지 말고 환경변수로!
    python3 scripts/perplexity_research.py "교촌치킨"
    python3 scripts/perplexity_research.py "교촌치킨" --slug kyochon --model sonar-pro

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

API_URL = "https://api.perplexity.ai/chat/completions"
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


def call_perplexity(api_key: str, company: str, model: str) -> dict:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": USER_PROMPT.format(company=company)},
        ],
        "temperature": 0.2,
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
        with urllib.request.urlopen(req, timeout=180) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:500]
        hints = {
            401: "API 키가 틀렸거나 만료됐어요. 키 앞뒤 공백/따옴표, 'pplx-'로 시작하는지 확인하세요.",
            402: "크레딧이 부족해요. Perplexity 설정 > API에서 결제 수단/크레딧을 확인하세요.",
            400: "요청 형식 오류예요. --model 이름(sonar, sonar-pro 등)을 확인하세요.",
            429: "요청이 너무 많아요. 잠시 후 다시 시도하세요.",
        }
        sys.exit(f"[오류] HTTP {e.code}: {hints.get(e.code, '응답 내용을 확인하세요.')}\n{body}")
    except urllib.error.URLError as e:
        sys.exit(f"[오류] 네트워크 연결 실패: {e.reason}")


def build_markdown(company: str, model: str, data: dict) -> str:
    content = data["choices"][0]["message"]["content"]
    # 최신 응답은 search_results(제목+URL), 예전 응답은 citations(URL만)
    sources = data.get("search_results") or [{"url": u} for u in data.get("citations", [])]

    lines = [
        f"# {company} 기업분석 초안",
        "",
        f"- 생성: {dt.date.today().isoformat()} · Perplexity `{model}`",
        "- AI가 모은 초안이에요. 영상에 쓰기 전에 숫자는 출처 링크로 꼭 다시 확인하세요.",
        "",
        content.strip(),
        "",
        "## 출처",
    ]
    for i, s in enumerate(sources, 1):
        title = s.get("title") or s["url"]
        date = f" ({s['date']})" if s.get("date") else ""
        lines.append(f"{i}. [{title}]({s['url']}){date}")
    if not sources:
        lines.append("- (응답에 출처가 없었어요)")
    return "\n".join(lines) + "\n"


def main() -> None:
    p = argparse.ArgumentParser(description="퍼플렉시티로 기업분석 초안 만들기")
    p.add_argument("company", help="분석할 기업 이름 (예: 교촌치킨)")
    p.add_argument("--slug", help="파일 이름 (기본: 기업 이름에서 자동 생성)")
    p.add_argument("--model", default="sonar", help="sonar(저렴·빠름) 또는 sonar-pro(더 깊게)")
    p.add_argument("--out-dir", default=str(ROOT / "research"), help="저장 폴더")
    args = p.parse_args()

    api_key = os.environ.get("PERPLEXITY_API_KEY", "").strip().strip('"').strip("'")
    if not api_key:
        sys.exit(
            "[오류] PERPLEXITY_API_KEY 환경변수가 없어요.\n"
            "  - 내 컴퓨터: export PERPLEXITY_API_KEY=pplx-...  (Windows: set PERPLEXITY_API_KEY=pplx-...)\n"
            "  - Claude Code 클라우드: 환경 설정 > Edit > 환경변수에 추가 후 새 세션 시작"
        )

    print(f"'{args.company}' 자료 수집 중… (모델: {args.model}, 30초~1분 걸려요)")
    data = call_perplexity(api_key, args.company, args.model)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{args.slug or slugify(args.company)}.md"
    out_path.write_text(build_markdown(args.company, args.model, data), encoding="utf-8")

    usage = data.get("usage", {})
    print(f"완료: {out_path}")
    if usage:
        print(f"토큰 사용량: 입력 {usage.get('prompt_tokens')} / 출력 {usage.get('completion_tokens')}")


if __name__ == "__main__":
    main()
