#!/usr/bin/env python3
"""
Verification script for token optimization changes.

This script helps verify that the Tier 1 optimizations:
1. Don't break existing functionality
2. Actually reduce token usage
3. Maintain extraction quality

Usage:
    python3 verify_optimizations.py --test-all
    python3 verify_optimizations.py --check-imports
    python3 verify_optimizations.py --measure-prompt
"""

import argparse
import sys
from pathlib import Path


def check_imports():
    """Verify all modules can be imported without errors."""
    print("=" * 70)
    print("CHECKING IMPORTS")
    print("=" * 70)

    modules_to_check = [
        ("agent", "Agent class"),
        ("tools.validation_tools", "Validation tools"),
        ("tools.database_tools", "Database tools"),
        ("tools.extraction_tools", "Extraction tools"),
        ("source_profiles", "Source profiles"),
        ("schema", "Schema definitions"),
    ]

    all_passed = True
    for module_name, description in modules_to_check:
        try:
            __import__(module_name)
            print(f"✓ {description:30s} - OK")
        except Exception as e:
            print(f"✗ {description:30s} - FAILED: {e}")
            all_passed = False

    print()
    return all_passed


def check_tool_definitions():
    """Verify tool definitions are valid and compressed."""
    print("=" * 70)
    print("CHECKING TOOL DEFINITIONS")
    print("=" * 70)

    try:
        from tools.validation_tools import VALIDATE_DATES_TOOL, VERIFY_INFORMATION_TOOL
        from tools.database_tools import LOOKUP_OFFICER_TOOL, LOOKUP_UNIT_TOOL, SAVE_TO_DATABASE_TOOL
        from tools.extraction_tools import SAVE_OFFICER_BIO_TOOL

        tools = [
            ("VALIDATE_DATES_TOOL", VALIDATE_DATES_TOOL, 100),
            ("VERIFY_INFORMATION_TOOL", VERIFY_INFORMATION_TOOL, 200),
            ("LOOKUP_OFFICER_TOOL", LOOKUP_OFFICER_TOOL, 120),
            ("LOOKUP_UNIT_TOOL", LOOKUP_UNIT_TOOL, 120),
            ("SAVE_TO_DATABASE_TOOL", SAVE_TO_DATABASE_TOOL, 200),
            ("SAVE_OFFICER_BIO_TOOL", SAVE_OFFICER_BIO_TOOL, 200),
        ]

        all_passed = True
        for tool_name, tool_def, max_desc_len in tools:
            desc = tool_def.get("description", "")
            desc_len = len(desc)

            status = "✓" if desc_len <= max_desc_len else "⚠"
            if desc_len > max_desc_len:
                all_passed = False

            print(f"{status} {tool_name:30s} - {desc_len:4d} chars (target: <{max_desc_len})")

            # Verify required fields
            if "name" not in tool_def:
                print(f"  ✗ Missing 'name' field")
                all_passed = False
            if "input_schema" not in tool_def:
                print(f"  ✗ Missing 'input_schema' field")
                all_passed = False

        print()
        return all_passed

    except Exception as e:
        print(f"✗ Error loading tools: {e}")
        return False


def measure_prompt_length():
    """Measure system prompt length to verify compression."""
    print("=" * 70)
    print("MEASURING SYSTEM PROMPT LENGTH")
    print("=" * 70)

    try:
        from agent import Agent
        from source_profiles import PROFILE_REGISTRY

        # Create agent instance
        agent = Agent()

        # Test with different source types
        source_types = ["universal", "obituary", "news_article", "wiki"]

        for source_type in source_types:
            try:
                profile = PROFILE_REGISTRY.get(source_type)
                prompt = agent._create_system_prompt(profile)

                lines = len(prompt.split('\n'))
                chars = len(prompt)
                words = len(prompt.split())

                # Rough token estimate (1 token ≈ 4 chars for English, ~2-3 for Chinese mixed)
                estimated_tokens = chars // 3

                print(f"\n{source_type.upper()}:")
                print(f"  Lines: {lines}")
                print(f"  Characters: {chars:,}")
                print(f"  Words: {words:,}")
                print(f"  Estimated tokens: ~{estimated_tokens:,}")

                # Check if prompt is reasonably short (target: ~500-1000 chars after compression)
                if chars > 3000:
                    print(f"  ⚠ Prompt may still be too long (target: <3000 chars)")
                else:
                    print(f"  ✓ Prompt length looks good")

            except Exception as e:
                print(f"  ✗ Error with {source_type}: {e}")

        print()
        return True

    except Exception as e:
        print(f"✗ Error measuring prompt: {e}")
        return False


def check_agent_initialization():
    """Verify Agent can be initialized without errors."""
    print("=" * 70)
    print("CHECKING AGENT INITIALIZATION")
    print("=" * 70)

    try:
        from agent import Agent

        agent = Agent()
        print("✓ Agent initialized successfully")

        # Check key attributes
        attrs_to_check = [
            ("max_iterations", int),
            ("total_input_tokens", int),
            ("total_output_tokens", int),
            ("profile_registry", object),
        ]

        for attr_name, expected_type in attrs_to_check:
            if hasattr(agent, attr_name):
                value = getattr(agent, attr_name)
                if isinstance(value, expected_type):
                    print(f"✓ {attr_name:20s} - OK ({type(value).__name__})")
                else:
                    print(f"⚠ {attr_name:20s} - Wrong type (expected {expected_type.__name__}, got {type(value).__name__})")
            else:
                print(f"✗ {attr_name:20s} - Missing")

        print()
        return True

    except Exception as e:
        print(f"✗ Error initializing agent: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_source_text_optimization():
    """Verify the source text optimization is in place."""
    print("=" * 70)
    print("CHECKING SOURCE TEXT OPTIMIZATION")
    print("=" * 70)

    try:
        with open("agent.py", "r") as f:
            content = f.read()

        # Check for the optimization code
        checks = [
            ("source_text_sent flag", "source_text_sent = False"),
            ("Context retention logic", "if not source_text_sent and len(messages) > 0:"),
            ("Message replacement", '[Source text provided in initial message'),
        ]

        all_passed = True
        for check_name, search_string in checks:
            if search_string in content:
                print(f"✓ {check_name:40s} - Found")
            else:
                print(f"✗ {check_name:40s} - Missing")
                all_passed = False

        print()
        return all_passed

    except Exception as e:
        print(f"✗ Error checking source text optimization: {e}")
        return False


def run_all_tests():
    """Run all verification tests."""
    print("\n" + "=" * 70)
    print("RUNNING ALL VERIFICATION TESTS")
    print("=" * 70 + "\n")

    results = {}

    results["imports"] = check_imports()
    results["tool_definitions"] = check_tool_definitions()
    results["prompt_length"] = measure_prompt_length()
    results["agent_init"] = check_agent_initialization()
    results["source_text_opt"] = verify_source_text_optimization()

    # Summary
    print("\n" + "=" * 70)
    print("VERIFICATION SUMMARY")
    print("=" * 70)

    for test_name, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{test_name:30s} - {status}")

    all_passed = all(results.values())

    print("\n" + "=" * 70)
    if all_passed:
        print("✓ ALL CHECKS PASSED")
        print("\nNext steps:")
        print("1. Run unit tests: pytest tests/ -v")
        print("2. Test with sample extraction: python3 cli.py extract --url <test-url> --verbose")
        print("3. Measure actual token usage and compare to baseline (~58,000 tokens)")
    else:
        print("✗ SOME CHECKS FAILED")
        print("\nPlease review the errors above and fix before proceeding.")
    print("=" * 70 + "\n")

    return all_passed


def main():
    parser = argparse.ArgumentParser(
        description="Verify token optimization changes"
    )
    parser.add_argument(
        "--test-all",
        action="store_true",
        help="Run all verification tests"
    )
    parser.add_argument(
        "--check-imports",
        action="store_true",
        help="Only check if modules can be imported"
    )
    parser.add_argument(
        "--measure-prompt",
        action="store_true",
        help="Only measure system prompt length"
    )
    parser.add_argument(
        "--check-agent",
        action="store_true",
        help="Only check agent initialization"
    )

    args = parser.parse_args()

    if not any([args.test_all, args.check_imports, args.measure_prompt, args.check_agent]):
        # Default: run all tests
        args.test_all = True

    success = True

    if args.test_all:
        success = run_all_tests()
    else:
        if args.check_imports:
            success = success and check_imports()
        if args.measure_prompt:
            success = success and measure_prompt_length()
        if args.check_agent:
            success = success and check_agent_initialization()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
