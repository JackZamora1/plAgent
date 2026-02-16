"""Regression tests for source context handling in agentic loop."""
from copy import deepcopy
from types import SimpleNamespace

from agent import PLAgentSDK
from schema import OfficerBio


def _mock_response(stop_reason, content, input_tokens=10, output_tokens=5):
    """Create a minimal mock Anthropic response object."""
    return SimpleNamespace(
        stop_reason=stop_reason,
        content=content,
        usage=SimpleNamespace(input_tokens=input_tokens, output_tokens=output_tokens),
    )


def test_source_text_is_preserved_across_tool_turns():
    """
    Ensure the original source text is included in single-pass prompt construction.

    The extraction request should remain grounded in the source text.
    """
    sdk = PLAgentSDK(require_db=False, use_few_shot=False)

    source_text = "新华社厦门9月1日电 林炳尧同志，1961年入伍，2002年晋升中将。"
    source_url = "https://www.news.cn/20250901/example/c.html"
    captured_messages = []

    # Single-pass returns JSON payload in one response.
    responses = [
        _mock_response(
            stop_reason="end_turn",
            content=[
                SimpleNamespace(
                    type="text",
                    text=(
                        '{"name":"林炳尧","source_url":"https://placeholder","source_type":"obituary",'
                        '"confidence_score":0.9,"extraction_notes":"Mock extraction for context regression test."}'
                    ),
                )
            ]
        ),
    ]

    def fake_call_api_with_retry(messages, system_prompt, tools_override=None, max_tokens=4096):
        del system_prompt  # Not needed for this test
        del tools_override
        del max_tokens
        captured_messages.append(deepcopy(messages))
        return responses[len(captured_messages) - 1]

    sdk._call_api_with_retry = fake_call_api_with_retry

    result = sdk.extract_bio_agentic(
        source_text=source_text,
        source_url=source_url,
    )

    assert result.success is True
    assert len(captured_messages) == 1

    first_turn_user_prompt = captured_messages[0][0]["content"]
    assert source_text in first_turn_user_prompt
    assert result.officer_bio is not None
    assert result.officer_bio.name == "林炳尧"


def test_notable_positions_normalized_to_source_order():
    """Ensure notable_positions are reordered to source appearance order."""
    sdk = PLAgentSDK(require_db=False, use_few_shot=False)
    source_text = "先任排长，后任连长，再任团长。"
    officer = OfficerBio(
        name="测试",
        source_url="https://example.com",
        notable_positions=["团长", "连长", "排长"],
        confidence_score=0.5,
    )

    sdk._normalize_position_order(officer, source_text)
    assert officer.notable_positions == ["排长", "连长", "团长"]


def test_inferred_date_fields_are_annotated():
    """Ensure inferred date fields are tagged in extraction_notes."""
    sdk = PLAgentSDK(require_db=False, use_few_shot=False)
    source_text = "Comrade Lin passed away on August 18 in Xiamen."
    officer = OfficerBio(
        name="林炳尧",
        source_url="https://example.com",
        death_date="2025-08-18",
        confidence_score=0.5,
    )

    sdk._annotate_inferred_fields(officer, source_text)
    assert officer.extraction_notes is not None
    assert "death_date" in officer.extraction_notes
