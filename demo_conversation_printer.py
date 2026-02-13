#!/usr/bin/env python3
"""Demo script showing ConversationPrinter usage."""
from agent import PLAgentSDK, ConversationPrinter
from tools.extraction_tools import extract_text_from_file
from pathlib import Path
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


def main():
    """Demonstrate ConversationPrinter features."""
    print("=" * 80)
    print("ConversationPrinter Demo")
    print("=" * 80)

    # Initialize SDK
    sdk = PLAgentSDK(require_db=False)

    # Load test obituary
    test_file = Path(__file__).parent / "data" / "test_obituary.txt"
    if not test_file.exists():
        print(f"Error: Test file not found: {test_file}")
        return 1

    source_text = extract_text_from_file(str(test_file))

    # Extract biography
    result = sdk.extract_bio_agentic(
        source_text=source_text,
        source_url="https://www.news.cn/test/obituary.html",
        source_type="universal"
    )

    # Print extraction summary (replaces the demo_agentic_extraction.py display logic)
    ConversationPrinter.print_extraction_summary(result)

    # Demonstrate conversation printing
    print("\n" + "=" * 80)
    print("Conversation History (for debugging)")
    print("=" * 80)

    # Create a simplified conversation for demo
    # In real usage, you'd use the actual messages from sdk.extract_bio_agentic
    demo_messages = [
        {
            "role": "user",
            "content": "Extract biographical information from this source..."
        },
        {
            "role": "assistant",
            "content": [
                {"type": "text", "text": "I'll extract the officer's information using the available tools."},
                {
                    "type": "tool_use",
                    "name": "lookup_existing_officer",
                    "input": {"name": "林炳尧"}
                }
            ]
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "content": '{"success": true, "found": false, "message": "Officer not found in database"}'
                }
            ]
        },
        {
            "role": "assistant",
            "content": [
                {
                    "type": "tool_use",
                    "name": "save_officer_bio",
                    "input": {
                        "name": "林炳尧",
                        "hometown": "福建晋江",
                        "enlistment_date": "1961",
                        "confidence_score": 0.85
                    }
                }
            ]
        }
    ]

    ConversationPrinter.print_conversation(demo_messages)

    print("\n" + "=" * 80)
    print("Demo complete!")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    exit(main())
