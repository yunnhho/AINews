"""오프라인 스모크 테스트 — DB/네트워크 불필요. 대규모 리팩터(db.py, sources/common.py,
ai/common.py, ai/publisher.py 등) 검증용. 프레임워크/픽스처 없이 단순 assert만 사용.

실행: PYTHONPATH에 backend, pipeline을 넣고
  pytest pipeline/tests/test_refactor_smoke.py -v
"""
import os
import sys
import pathlib
from datetime import UTC, datetime

# DEMO_MODE는 demo_client.get_client()가 첫 호출될 때 메모이즈되므로 반드시
# 다른 pipeline.ai 모듈을 import/호출하기 전에 설정한다.
os.environ["DEMO_MODE"] = "true"

# PYTHONPATH 없이 단독 실행(pytest pipeline/tests/...)해도 동작하도록 경로 보정.
_THIS = pathlib.Path(__file__).resolve()
_PIPELINE_ROOT = _THIS.parents[1]          # .../pipeline
_REPO_ROOT = _PIPELINE_ROOT.parent          # .../AINews
_BACKEND_ROOT = _REPO_ROOT / "backend"
for _p in (str(_PIPELINE_ROOT), str(_BACKEND_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from pipeline.adapters.base import RawItem, SourceGroup  # noqa: E402
from pipeline.ai import demo_client  # noqa: E402
from pipeline.ai.news_processor import NewsCardData, process_news  # noqa: E402
from pipeline.ai.technique_processor import TechniqueCardData, process_technique  # noqa: E402
from pipeline.ai.backtranslate import verify_translation  # noqa: E402
from pipeline.ai.common import parse_json_response  # noqa: E402
from pipeline.filters.dedup import dedup  # noqa: E402
from pipeline.sources.common import collect_sources  # noqa: E402
from pipeline.ai.publisher import _enum_or  # noqa: E402
from app.models.card import Category  # noqa: E402

_NOW = datetime.now(UTC)


def _raw_item(url, title, content="Some article body text.", group=SourceGroup.NEWS_RSS, lang="en"):
    return RawItem(
        url=url,
        title=title,
        content=content,
        published_at=_NOW,
        source_name="test-source",
        source_group=group,
        original_lang=lang,
    )


def test_demo_client_replay():
    assert demo_client.is_demo_mode() is True
    client = demo_client.get_client()
    assert isinstance(client, demo_client.ReplayClient)


def test_process_news_demo():
    item = _raw_item("https://example.com/news-1", "GPT-5 Released")
    result = process_news(item)
    assert isinstance(result, NewsCardData)
    assert result.summary
    assert len(result.key_points) >= 1


def test_process_technique_demo():
    item = _raw_item(
        "https://example.com/repo-1", "New Prompt Caching Technique",
        group=SourceGroup.GITHUB,
    )
    result = process_technique(item)
    assert isinstance(result, TechniqueCardData)
    assert result.problem
    assert result.idea


def test_verify_translation_demo():
    passed, score, back_text, in_tok, out_tok = verify_translation("orig", "요약")
    assert passed is True
    assert score == 0.9
    assert in_tok == 210
    assert out_tok == 120


def test_parse_json_response_clean():
    assert parse_json_response('{"a": 1, "b": "x"}') == {"a": 1, "b": "x"}


def test_parse_json_response_noisy():
    raw = 'Sure, here is the JSON:\n{"a": 1}\nHope that helps!'
    assert parse_json_response(raw) == {"a": 1}


def test_parse_json_response_broken():
    assert parse_json_response("not json at all, sorry") is None


def test_dedup_url_duplicate():
    items = [
        _raw_item("https://x.com/1", "Same URL Item"),
        _raw_item("https://x.com/1", "Same URL Item (dup)"),
    ]
    result, count = dedup(items)
    assert len(result) == 1
    assert count == 1


def test_dedup_near_duplicate_title_keeps_longer_content():
    short_item = _raw_item("https://x.com/2", "OpenAI announces GPT-5 today", content="short")
    long_item = _raw_item(
        "https://x.com/3", "OpenAI announces GPT-5 today",
        content="a much longer piece of content " * 20,
    )
    result, count = dedup([short_item, long_item])
    assert len(result) == 1
    assert count == 1
    assert result[0].content == long_item.content


def _patch_health_svc():
    """pipeline.models.source_health 모듈 속성을 스텁으로 교체. (원본, 복원용 dict) 반환."""
    import pipeline.models.source_health as health_svc

    originals = {
        "run_sync": health_svc.run_sync,
        "get_disabled_sources": health_svc.get_disabled_sources,
        "record_success": health_svc.record_success,
        "record_failure": health_svc.record_failure,
    }

    calls = {"success": [], "failure": [], "disabled": frozenset()}

    health_svc.run_sync = lambda x: x  # 인자가 이미 동기 값이므로 그대로 통과
    health_svc.get_disabled_sources = lambda: calls["disabled"]
    health_svc.record_success = lambda name, group: calls["success"].append((name, group))
    health_svc.record_failure = lambda name, group, error, disable_on_404=False: calls[
        "failure"
    ].append((name, group, error, disable_on_404))

    return health_svc, originals, calls


def _restore_health_svc(health_svc, originals):
    for attr, val in originals.items():
        setattr(health_svc, attr, val)


def test_collect_sources_normal_two_fetchers_sum():
    health_svc, originals, calls = _patch_health_svc()
    try:
        def fetch1(since):
            return [_raw_item("https://a.com/1", "A1")]

        def fetch2(since):
            return [_raw_item("https://a.com/2", "A2")]

        result = collect_sources("test", "NEWS_RSS", [("src1", fetch1), ("src2", fetch2)])
        assert len(result) == 2
        assert len(calls["success"]) == 2
        assert calls["failure"] == []
    finally:
        _restore_health_svc(health_svc, originals)


def test_collect_sources_exception_isolated_others_continue():
    health_svc, originals, calls = _patch_health_svc()
    try:
        def fetch_boom(since):
            raise RuntimeError("boom")

        def fetch_ok(since):
            return [_raw_item("https://a.com/ok", "OK")]

        result = collect_sources("test", "NEWS_RSS", [("bad", fetch_boom), ("good", fetch_ok)])
        assert len(result) == 1
        assert result[0].url == "https://a.com/ok"
        assert len(calls["failure"]) == 1
        assert calls["failure"][0][0] == "bad"
        assert calls["failure"][0][3] is False  # disable_on_404 기본값
        assert len(calls["success"]) == 1
    finally:
        _restore_health_svc(health_svc, originals)


def test_collect_sources_disabled_source_skipped():
    health_svc, originals, calls = _patch_health_svc()
    try:
        calls["disabled"] = frozenset({"skip-me"})

        def fetch_should_not_run(since):
            raise AssertionError("disabled 소스의 fetch가 호출되면 안 됨")

        def fetch_ok(since):
            return [_raw_item("https://a.com/ok2", "OK2")]

        result = collect_sources("test", "NEWS_RSS", [("skip-me", fetch_should_not_run), ("ok", fetch_ok)])
        assert len(result) == 1
        assert calls["failure"] == []
        assert len(calls["success"]) == 1
    finally:
        _restore_health_svc(health_svc, originals)


def test_collect_sources_disable_on_404_value_error():
    health_svc, originals, calls = _patch_health_svc()
    try:
        def fetch_404(since):
            raise ValueError("404 not found")

        result = collect_sources("test", "GITHUB", [("gh-src", fetch_404)], disable_on_404=True)
        assert result == []
        assert len(calls["failure"]) == 1
        assert calls["failure"][0][0] == "gh-src"
        assert calls["failure"][0][3] is True  # disable_on_404=True로 기록됨
    finally:
        _restore_health_svc(health_svc, originals)


def test_enum_or_valid_and_fallback():
    assert _enum_or(Category, "CODING", Category.GENERAL) == Category.CODING
    assert _enum_or(Category, "NOT_A_REAL_CATEGORY", Category.GENERAL) == Category.GENERAL


if __name__ == "__main__":
    # ponytail: pytest 없이도 빠른 자가 점검 — 실제 검증은 pytest로 실행.
    import traceback

    tests = [v for k, v in list(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except Exception:
            failed += 1
            print(f"FAIL {t.__name__}")
            traceback.print_exc()
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
