# 기업분석 마케터 · 릴스 아카이브

인스타그램 '기업분석 마케터' 계정에 올린(올릴) 릴스의 **최종본**을 기업별로 모아 둔 저장소예요.
기업 자료수집 → SWOT → STP → 성장 방안 → 예상 결과 흐름으로 분석하고, 그 분석 방법을 50~60초 숏폼으로 보여 줍니다.

자세한 목록은 [reels/README.md](reels/README.md)에 있어요.

## 퍼플렉시티로 기업 자료 수집하기

`scripts/perplexity_research.py`는 퍼플렉시티 API로 기업 자료를 모아 `research/<기업>.md`에 분석 초안(자료수집 → SWOT → STP → 성장 방안 → 예상 결과 → 훅 후보 + 출처)을 만들어 줘요. 추가 설치는 필요 없어요.

```bash
export PERPLEXITY_API_KEY=pplx-...   # 키는 절대 코드나 커밋에 넣지 마세요
python3 scripts/perplexity_research.py "교촌치킨"
```

- `--effort high`: 더 깊게 찾음(비용↑, 기본은 `fast`), `--slug kyochon`: 파일 이름 지정
