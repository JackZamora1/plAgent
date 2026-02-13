#!/usr/bin/env python3
"""
Learning system for PLA Agent SDK.

Implements few-shot learning by using previous successful extractions
as examples to improve consistency and quality.
"""
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from collections import defaultdict

from schema import AgentExtractionResult, OfficerBio

logger = logging.getLogger(__name__)


class ExtractionLearner:
    """
    Learns from previous extractions to improve future performance.

    Uses few-shot learning by selecting high-confidence past extractions
    and including them as examples in the system prompt.
    """

    def __init__(self, examples_dir: str = "output/"):
        """
        Initialize the learning system.

        Args:
            examples_dir: Directory containing past extraction results
        """
        self.examples_dir = Path(examples_dir)
        self.examples_cache = []
        self.load_successful_extractions()

    def load_successful_extractions(self):
        """
        Load successful extractions from the examples directory.

        Filters for:
        - Successful extractions only
        - Confidence >= 0.7
        - Valid officer bio data
        """
        logger.info(f"Loading examples from {self.examples_dir}")

        if not self.examples_dir.exists():
            logger.warning(f"Examples directory not found: {self.examples_dir}")
            return

        # Find all JSON files (exclude review and batch reports)
        json_files = list(self.examples_dir.glob("*.json"))
        json_files = [
            f for f in json_files
            if not f.name.startswith("REVIEW_")
            and not f.name.startswith("batch_report")
        ]

        logger.debug(f"Found {len(json_files)} potential example files")

        # Load and filter examples
        successful_examples = []

        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Check if it's a valid extraction result
                if not data.get('success'):
                    continue

                # Check if officer_bio exists
                if 'officer_bio' not in data:
                    continue

                officer_bio = data['officer_bio']

                # Check confidence threshold
                confidence = officer_bio.get('confidence_score', 0.0)
                if confidence < 0.7:
                    continue

                # Parse into AgentExtractionResult
                result = AgentExtractionResult(**data)

                # Store as example
                example = {
                    'file': json_file.name,
                    'officer_bio': result.officer_bio,
                    'confidence': confidence,
                    'tool_calls': len(result.tool_calls),
                    'tokens': result.get_total_tokens(),
                    'result': result
                }

                successful_examples.append(example)

            except Exception as e:
                logger.debug(f"Skipping {json_file.name}: {e}")
                continue

        # Sort by confidence (highest first)
        successful_examples.sort(key=lambda x: x['confidence'], reverse=True)

        self.examples_cache = successful_examples

        logger.info(f"Loaded {len(self.examples_cache)} successful examples")

        if self.examples_cache:
            logger.debug(
                f"Confidence range: {self.examples_cache[-1]['confidence']:.2f} - "
                f"{self.examples_cache[0]['confidence']:.2f}"
            )

    def get_few_shot_examples(
        self,
        n: int = 3,
        min_confidence: float = 0.8,
        diversity: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Select n high-confidence extractions as few-shot examples.

        Args:
            n: Number of examples to select
            min_confidence: Minimum confidence threshold
            diversity: If True, select diverse examples (different officers)

        Returns:
            List of example dictionaries with 'input' and 'output' keys
        """
        if not self.examples_cache:
            logger.warning("No examples available for few-shot learning")
            return []

        # Filter by confidence
        candidates = [
            ex for ex in self.examples_cache
            if ex['confidence'] >= min_confidence
        ]

        if not candidates:
            logger.warning(
                f"No examples with confidence >= {min_confidence}. "
                f"Lowering threshold to 0.7"
            )
            candidates = [ex for ex in self.examples_cache if ex['confidence'] >= 0.7]

        if not candidates:
            logger.warning("No examples meet criteria")
            return []

        # Select examples
        if diversity:
            # Try to select diverse examples (different names, different confidence levels)
            selected = self._select_diverse_examples(candidates, n)
        else:
            # Just take top n by confidence
            selected = candidates[:n]

        # Format as few-shot examples
        few_shot_examples = []

        for ex in selected:
            officer = ex['officer_bio']

            # Create a concise example
            example = {
                'name': officer.name,
                'confidence': ex['confidence'],
                'input': self._format_example_input(officer),
                'output': self._format_example_output(officer)
            }

            few_shot_examples.append(example)

        logger.info(f"Selected {len(few_shot_examples)} few-shot examples")

        return few_shot_examples

    def _select_diverse_examples(
        self,
        candidates: List[Dict[str, Any]],
        n: int
    ) -> List[Dict[str, Any]]:
        """
        Select diverse examples to cover different scenarios.

        Args:
            candidates: List of candidate examples
            n: Number to select

        Returns:
            List of selected examples
        """
        if len(candidates) <= n:
            return candidates

        selected = []
        used_names = set()

        # Group by confidence range
        confidence_groups = defaultdict(list)
        for ex in candidates:
            conf = ex['confidence']
            if conf >= 0.9:
                group = 'excellent'
            elif conf >= 0.8:
                group = 'good'
            else:
                group = 'acceptable'
            confidence_groups[group].append(ex)

        # Try to get examples from different confidence levels
        for group in ['excellent', 'good', 'acceptable']:
            group_examples = confidence_groups[group]

            for ex in group_examples:
                if len(selected) >= n:
                    break

                # Skip if we already have this officer
                officer_name = ex['officer_bio'].name
                if officer_name in used_names:
                    continue

                selected.append(ex)
                used_names.add(officer_name)

        # If we still need more, add remaining high-confidence ones
        if len(selected) < n:
            for ex in candidates:
                if len(selected) >= n:
                    break
                if ex not in selected:
                    selected.append(ex)

        return selected[:n]

    def _format_example_input(self, officer: OfficerBio) -> str:
        """
        Format example input (obituary excerpt).

        Since we don't store the original obituary text,
        we reconstruct a sample obituary from the extracted data.

        Args:
            officer: OfficerBio object

        Returns:
            Formatted example input
        """
        # Create a sample obituary from extracted data
        parts = [f"{officer.name}同志逝世"]

        if officer.hometown:
            parts.append(f"{officer.name}是{officer.hometown}人")

        if officer.birth_date and officer.death_date:
            parts.append(f"生于{officer.birth_date}年，于{officer.death_date}逝世")

        if officer.enlistment_date:
            parts.append(f"{officer.enlistment_date}年入伍")

        if officer.party_membership_date:
            parts.append(f"{officer.party_membership_date}年加入中国共产党")

        if officer.promotions:
            for promo in officer.promotions:
                if promo.date:
                    parts.append(f"{promo.date}年晋升{promo.rank}军衔")

        if officer.notable_positions:
            parts.append(f"历任{', '.join(officer.notable_positions[:3])}")

        return "。".join(parts) + "。（示例摘录）"

    def _format_example_output(self, officer: OfficerBio) -> Dict[str, Any]:
        """
        Format example output (extracted data).

        Args:
            officer: OfficerBio object

        Returns:
            Dictionary of extracted fields
        """
        # Return a concise version of the extraction
        output = {
            'name': officer.name,
            'pinyin_name': officer.pinyin_name,
            'hometown': officer.hometown,
            'birth_date': officer.birth_date,
            'death_date': officer.death_date,
            'enlistment_date': officer.enlistment_date,
            'party_membership_date': officer.party_membership_date,
            'confidence_score': officer.confidence_score
        }

        # Include promotions if present
        if officer.promotions:
            output['promotions'] = [
                {'rank': p.rank, 'date': p.date}
                for p in officer.promotions
            ]

        # Include positions if present
        if officer.notable_positions:
            output['notable_positions'] = officer.notable_positions[:3]  # First 3

        # Remove None values for clarity
        output = {k: v for k, v in output.items() if v is not None}

        return output

    def add_to_system_prompt(
        self,
        base_prompt: str,
        examples: List[Dict[str, Any]]
    ) -> str:
        """
        Append few-shot examples to system prompt.

        Args:
            base_prompt: Original system prompt
            examples: List of example dictionaries

        Returns:
            Enhanced system prompt with examples
        """
        if not examples:
            return base_prompt

        # Build examples section
        examples_section = "\n\n# Few-Shot Learning Examples\n\n"
        examples_section += "Here are examples of successful extractions from our database. "
        examples_section += "Use these as reference for quality and format:\n\n"

        for i, example in enumerate(examples, 1):
            examples_section += f"## Example {i}: {example['name']} (Confidence: {example['confidence']:.2f})\n\n"

            # Input (sample source text)
            examples_section += "**Input (Source Excerpt):**\n"
            examples_section += f"```\n{example['input']}\n```\n\n"

            # Output (extracted data)
            examples_section += "**Output (Extracted Data):**\n"
            examples_section += "```json\n"
            examples_section += json.dumps(example['output'], ensure_ascii=False, indent=2)
            examples_section += "\n```\n\n"

        examples_section += "Follow this level of detail and accuracy in your extractions.\n"

        # Append to base prompt
        enhanced_prompt = base_prompt + examples_section

        return enhanced_prompt

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about available examples.

        Returns:
            Dictionary with statistics
        """
        if not self.examples_cache:
            return {
                'total_examples': 0,
                'avg_confidence': 0.0,
                'min_confidence': 0.0,
                'max_confidence': 0.0
            }

        confidences = [ex['confidence'] for ex in self.examples_cache]

        return {
            'total_examples': len(self.examples_cache),
            'avg_confidence': sum(confidences) / len(confidences),
            'min_confidence': min(confidences),
            'max_confidence': max(confidences),
            'examples_above_0.8': sum(1 for c in confidences if c >= 0.8),
            'examples_above_0.9': sum(1 for c in confidences if c >= 0.9),
        }

    def should_use_few_shot(self, min_examples: int = 5) -> bool:
        """
        Determine if few-shot learning should be used.

        Args:
            min_examples: Minimum number of examples needed

        Returns:
            True if few-shot should be used
        """
        return len(self.examples_cache) >= min_examples


def main():
    """Demo/test function for ExtractionLearner."""
    from rich.console import Console
    from rich.table import Table
    from rich import box

    console = Console()

    console.print("\n[bold cyan]ExtractionLearner Demo[/bold cyan]\n")

    # Initialize learner
    learner = ExtractionLearner()

    # Get statistics
    stats = learner.get_statistics()

    console.print("[bold]Statistics:[/bold]")
    stats_table = Table(show_header=True, header_style="bold cyan", box=box.ROUNDED)
    stats_table.add_column("Metric", style="cyan", width=30)
    stats_table.add_column("Value", style="white", width=20)

    stats_table.add_row("Total Examples", str(stats['total_examples']))
    stats_table.add_row("Average Confidence", f"{stats['avg_confidence']:.3f}")
    stats_table.add_row("Min Confidence", f"{stats['min_confidence']:.3f}")
    stats_table.add_row("Max Confidence", f"{stats['max_confidence']:.3f}")
    stats_table.add_row("Examples ≥ 0.8", str(stats['examples_above_0.8']))
    stats_table.add_row("Examples ≥ 0.9", str(stats['examples_above_0.9']))

    console.print(stats_table)

    # Check if few-shot should be used
    should_use = learner.should_use_few_shot(min_examples=5)
    console.print(f"\n[bold]Should use few-shot:[/bold] {should_use}")

    if should_use:
        # Get few-shot examples
        console.print("\n[bold cyan]Few-Shot Examples:[/bold cyan]\n")

        examples = learner.get_few_shot_examples(n=3)

        for i, example in enumerate(examples, 1):
            console.print(f"[bold]Example {i}:[/bold] {example['name']} (Confidence: {example['confidence']:.2f})")
            console.print(f"[dim]Input:[/dim] {example['input'][:100]}...")
            console.print(f"[dim]Output fields:[/dim] {', '.join(example['output'].keys())}\n")

        # Show enhanced prompt preview
        console.print("[bold cyan]Enhanced Prompt Preview:[/bold cyan]\n")
        base_prompt = "Extract biographical information..."
        enhanced = learner.add_to_system_prompt(base_prompt, examples[:1])

        console.print(enhanced[:500] + "...\n")
        console.print(f"[dim]Full prompt length: {len(enhanced)} characters[/dim]")

    else:
        console.print("\n[yellow]Not enough examples for few-shot learning[/yellow]")
        console.print(f"[yellow]Need at least 5 successful extractions (have {stats['total_examples']})[/yellow]")


if __name__ == "__main__":
    main()
