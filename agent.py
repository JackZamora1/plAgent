"""Main agent for PLA leadership data extraction."""
import anthropic
from anthropic import Anthropic
from config import CONFIG
from schema import OfficerBio, AgentExtractionResult, ToolResult
from tools import get_all_tools, execute_tool
from source_profiles import SourceProfileRegistry, SourceProfile
from rich.console import Console
from rich.panel import Panel
from rich.json import JSON
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from pathlib import Path
from typing import Optional, List, Dict, Any
import json
import logging
import time

logger = logging.getLogger(__name__)

# Import learning system
try:
    from learning_system import ExtractionLearner
    LEARNING_AVAILABLE = True
except ImportError:
    LEARNING_AVAILABLE = False
    logger.warning("Learning system not available")

console = Console()


class ConversationPrinter:
    """Utility class for pretty-printing agent conversations and results."""

    @staticmethod
    def print_conversation(messages: List[dict]):
        """
        Pretty-print the conversation messages.

        Args:
            messages: List of conversation messages
        """
        console = Console()

        for i, msg in enumerate(messages):
            role = msg.get("role", "unknown")
            content = msg.get("content", "")

            # User messages
            if role == "user":
                if isinstance(content, str):
                    console.print(f"\n[bold blue]User (Turn {i+1}):[/bold blue]")
                    console.print(Panel(content, border_style="blue", padding=(1, 2)))
                elif isinstance(content, list):
                    # Tool results
                    console.print(f"\n[bold cyan]Tool Results (Turn {i+1}):[/bold cyan]")
                    for item in content:
                        if isinstance(item, dict) and item.get("type") == "tool_result":
                            tool_content = item.get("content", "")
                            console.print(f"  [cyan]└─ Tool result:[/cyan]")
                            if len(tool_content) > 200:
                                console.print(f"    {tool_content[:200]}...")
                            else:
                                console.print(f"    {tool_content}")

            # Assistant messages
            elif role == "assistant":
                console.print(f"\n[bold green]Assistant (Turn {i+1}):[/bold green]")

                if isinstance(content, list):
                    for block in content:
                        # Normalize API objects to dicts
                        if hasattr(block, 'type') and not isinstance(block, dict):
                            block = {"type": block.type,
                                     **({"text": block.text} if block.type == "text" else {}),
                                     **({"name": block.name, "input": block.input} if block.type == "tool_use" else {})}

                        if not isinstance(block, dict):
                            continue

                        block_type = block.get("type", "")

                        if block_type == "text":
                            text = block.get("text", "")
                            if text:
                                console.print(Panel(text, border_style="green", padding=(1, 2)))

                        elif block_type == "tool_use":
                            tool_name = block.get("name", "unknown")
                            tool_input = block.get("input", {})
                            console.print(f"  [yellow]Using tool: {tool_name}[/yellow]")
                            tool_input_str = json.dumps(tool_input, indent=2, ensure_ascii=False)
                            if len(tool_input_str) > 300:
                                console.print(f"    [dim]Input: {tool_input_str[:300]}...[/dim]")
                            else:
                                console.print(f"    [dim]Input: {tool_input_str}[/dim]")

                elif isinstance(content, str):
                    console.print(Panel(content, border_style="green", padding=(1, 2)))

    @staticmethod
    def print_extraction_summary(result: AgentExtractionResult):
        """
        Print extraction result summary.

        Args:
            result: AgentExtractionResult to summarize
        """
        console = Console()

        console.print("\n[bold magenta]═══ Extraction Summary ═══[/bold magenta]\n")

        # Success/failure status
        if result.success:
            console.print("[bold green]✓ Status: SUCCESS[/bold green]\n")
        else:
            console.print(f"[bold red]✗ Status: FAILED[/bold red]")
            console.print(f"[red]Error: {result.error_message}[/red]\n")
            return

        # Officer bio fields
        if result.officer_bio:
            officer = result.officer_bio

            console.print("[bold cyan]Extracted Fields:[/bold cyan]\n")

            # Create table for fields
            field_table = Table(show_header=True, header_style="bold magenta")
            field_table.add_column("Field", style="cyan", width=25)
            field_table.add_column("Value", style="white", width=50)
            field_table.add_column("Status", style="dim", width=10)

            # Helper to format value and status
            def add_field(name: str, value: Any):
                if value is None or value == "" or (isinstance(value, list) and len(value) == 0):
                    field_table.add_row(name, "[dim]null[/dim]", "[yellow]⚠[/yellow]")
                else:
                    if isinstance(value, list):
                        display = f"{len(value)} item(s)"
                    else:
                        display = str(value)
                        if len(display) > 50:
                            display = display[:47] + "..."
                    field_table.add_row(name, display, "[green]✓[/green]")

            # Add all fields
            add_field("name", officer.name)
            add_field("pinyin_name", officer.pinyin_name)
            add_field("hometown", officer.hometown)
            add_field("birth_date", officer.birth_date)
            add_field("death_date", officer.death_date)
            add_field("enlistment_date", officer.enlistment_date)
            add_field("party_membership_date", officer.party_membership_date)
            add_field("promotions", officer.promotions)
            add_field("notable_positions", officer.notable_positions)
            add_field("congress_participation", officer.congress_participation)
            add_field("cppcc_participation", officer.cppcc_participation)
            add_field("awards", officer.awards)
            add_field("wife_name", officer.wife_name)
            add_field("retirement_date", officer.retirement_date)

            console.print(field_table)

            # Confidence score
            console.print(f"\n[bold cyan]Confidence Score:[/bold cyan] [bold]{officer.confidence_score:.2f}[/bold]")

            if officer.extraction_notes:
                console.print(f"[bold cyan]Notes:[/bold cyan] {officer.extraction_notes}")

        # Performance metrics
        console.print(f"\n[bold cyan]Performance Metrics:[/bold cyan]\n")

        metrics_table = Table(show_header=False, box=None)
        metrics_table.add_column("Metric", style="cyan", width=25)
        metrics_table.add_column("Value", style="white")

        metrics_table.add_row("Conversation Turns", str(result.conversation_turns))
        metrics_table.add_row("Tool Calls", str(len(result.tool_calls)))
        metrics_table.add_row("Input Tokens", f"{result.total_input_tokens:,}")
        metrics_table.add_row("Output Tokens", f"{result.total_output_tokens:,}")
        metrics_table.add_row("Total Tokens", f"{result.get_total_tokens():,}")

        if result.tool_calls:
            metrics_table.add_row("Tool Success Rate", f"{result.get_success_rate():.1%}")

        console.print(metrics_table)

        # Tool usage breakdown
        if result.tool_calls:
            console.print(f"\n[bold cyan]Tool Usage:[/bold cyan]\n")

            tool_table = Table(show_header=True, header_style="bold magenta")
            tool_table.add_column("#", style="dim", width=5)
            tool_table.add_column("Tool", style="cyan", width=30)
            tool_table.add_column("Status", style="white", width=10)
            tool_table.add_column("Notes", style="dim", width=40)

            for idx, tool_call in enumerate(result.tool_calls, 1):
                status = "[green]✓[/green]" if tool_call.success else "[red]✗[/red]"

                notes = ""
                if not tool_call.success and tool_call.error:
                    notes = tool_call.error[:40] + "..." if len(tool_call.error) > 40 else tool_call.error
                elif tool_call.data:
                    # Extract interesting info from data
                    if tool_call.tool_name == "validate_dates":
                        notes = "Dates validated"
                    elif tool_call.tool_name == "verify_information_present":
                        if tool_call.data.get('found'):
                            notes = f"Found: {tool_call.data.get('field_name', 'unknown')}"
                        else:
                            notes = f"Not found: {tool_call.data.get('field_name', 'unknown')}"
                    elif tool_call.tool_name == "lookup_existing_officer":
                        if tool_call.data.get('found'):
                            notes = "Officer exists in DB"
                        else:
                            notes = "New officer"
                    elif tool_call.tool_name == "save_officer_bio":
                        notes = "Data saved"

                tool_table.add_row(str(idx), tool_call.tool_name, status, notes)

            console.print(tool_table)

        console.print("\n[bold magenta]═══════════════════════[/bold magenta]\n")


class PLAgentSDK:
    """
    Advanced agentic PLA officer biography extraction using Anthropic's tool use pattern.

    This agent uses Claude with multiple tools to:
    - Look up existing officers in database
    - Verify uncertain information in source text
    - Validate date chronology
    - Save extracted biographical data

    Features:
    - Agentic loop with tool use
    - Comprehensive logging
    - Token usage tracking
    - Error handling with retries
    - Confidence scoring
    """

    def __init__(self, require_db: bool = False, use_few_shot: bool = True):
        """
        Initialize the PLAgentSDK.

        Args:
            require_db: If True, require database credentials during validation
            use_few_shot: If True, use few-shot learning from past extractions
        """
        # Validate configuration
        CONFIG.validate_db_credentials(require_db=require_db)

        # Initialize Anthropic client
        self.client = Anthropic(api_key=CONFIG.ANTHROPIC_API_KEY)
        self.model = CONFIG.MODEL_NAME

        # Load all tools from registry
        self.tools = get_all_tools()
        logger.info(f"Loaded {len(self.tools)} tools for agent")

        # Initialize source profile registry
        self.profile_registry = SourceProfileRegistry()
        logger.info(f"Loaded {len(self.profile_registry.list_sources())} source profiles")

        # Configuration
        self.max_iterations = CONFIG.MAX_ITERATIONS
        self.max_retries = 3
        self.retry_delay = 2  # seconds

        # Tracking
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.conversation_turns = 0

        # Initialize learning system
        self.use_few_shot = use_few_shot and LEARNING_AVAILABLE
        self.learner = None

        if self.use_few_shot:
            try:
                self.learner = ExtractionLearner()
                stats = self.learner.get_statistics()
                if stats['total_examples'] >= 5:
                    logger.info(
                        f"Few-shot learning enabled: {stats['total_examples']} examples "
                        f"(avg confidence: {stats['avg_confidence']:.2f})"
                    )
                else:
                    logger.info(
                        f"Few-shot learning: insufficient examples ({stats['total_examples']}/5)"
                    )
                    self.use_few_shot = False
            except Exception as e:
                logger.warning(f"Failed to initialize learning system: {e}")
                self.use_few_shot = False
                self.learner = None

        logger.info("PLAgentSDK initialized successfully")

    def _create_system_prompt(self, profile: SourceProfile) -> str:
        """
        Create comprehensive system prompt for Claude customized for source type.

        Optionally includes few-shot examples from past successful extractions.

        Args:
            profile: SourceProfile for the source type being processed

        Returns:
            System prompt string
        """
        base_prompt = f"""You are an expert in extracting biographical information about PLA (People's Liberation Army) officers from {profile.source_description}

Your task is to extract structured biographical data using the tools provided to you.

# Source Context

{profile.extraction_context}

# Available Tools

You have access to these tools:
1. **lookup_existing_officer** - Check if this officer already exists in our database
2. **lookup_unit_by_name** - Look up PLA units by name to get unit IDs
3. **verify_information_present** - Double-check if specific information is actually mentioned in the source text
4. **validate_dates** - Validate that extracted dates are chronologically consistent
5. **save_officer_bio** - Save the final extracted biographical data
6. **save_to_database** - Persist the validated officer bio to the PostgreSQL database for long-term storage

# Extraction Guidelines

## What to Extract

Extract the following information when explicitly stated:
- **Name** (Chinese characters) - REQUIRED
- **Pinyin name** (romanization) - if explicitly provided in the text, use that. If NOT provided, transliterate the Chinese name to pinyin yourself (e.g., 林炳尧 → Lín Bǐngyáo). Always populate this field.
- **Hometown/birthplace** - if mentioned
- **Birth date** - if mentioned (use YYYY or YYYY-MM-DD format)
- **Death date** - if mentioned
- **Enlistment date** - when joined military
- **Party membership date** - when joined CCP
- **Promotions** - military rank promotions with dates (only explicitly stated promotions)
- **Notable positions** - ALL military positions held. Extract every position mentioned in the text, including junior/enlisted ranks (战士, 班长, 排长, etc.) through senior command roles. The complete career progression is analytically valuable.
- **Congress participation** - CCP National Congress memberships
- **CPPCC participation** - Political consultative conference memberships
- **Awards** - military honors and medals

## Field Expectations for {profile.display_name}

{self._format_field_expectations(profile)}

## Implicit Rank Inference (Optional Enrichment)

Chinese military positions often imply specific ranks. When a position progression is listed, you may note implied ranks in `extraction_notes`, but ONLY add to the `promotions` array ranks that are **explicitly stated** with dates.

Common position-to-rank mappings for reference:
- 班长 (Squad Leader) → typically 下士/中士
- 排长 (Platoon Leader) → 少尉/中尉
- 连长 (Company Commander) → 上尉
- 营长 (Battalion Commander) → 少校/中校
- 团长 (Regiment Commander) → 上校
- 师参谋长 (Division Chief of Staff) → 大校
- 军参谋长 (Corps Chief of Staff) → 少将

Include these as observations in `extraction_notes` (e.g., "Position progression suggests intermediate promotions through 上校 before explicit 少将 promotion in 1995"), but do NOT fabricate promotion entries without explicit textual evidence.

## Important Constraints

- **Only extract explicitly stated information** - do not infer or guess
- **Always generate pinyin_name** - even if not in the source text, transliterate the Chinese name yourself using standard pinyin with tone marks
- **Before setting rare fields to null, call `verify_information_present`** to confirm the information is truly absent from the text. For {profile.display_name}, these rare fields require verification: {', '.join(profile.rare_fields)}. Do not skip verification — even if a field seems obviously absent, the tool catches edge cases you might miss.
- **Extract ALL positions, not just senior roles** - the full career arc from enlistment (战士) through senior command is important for analysis. "历任" (successively held) lists should be captured in their entirety.
- **Use YYYY or YYYY-MM-DD format for dates** - be consistent

## RECOMMENDED WORKFLOW

⚠️ IMPORTANT: Follow this tool sequence for optimal extraction quality.

**Step 1: Check for existing officer**
- First, call `lookup_existing_officer` to check if this officer is already in our database
- If found, note the existing data for comparison
- If the call fails (database not initialized), that's expected — continue normally

**Step 2: Extract biographical information**
- Read the obituary carefully
- Extract ALL explicitly stated information
- Self-transliterate pinyin_name if not provided in text (e.g., 林炳尧 → Lín Bǐngyáo)
- Extract ALL positions from career progression, not just senior roles

**Step 3: Verify uncertain/missing fields**
- For ANY optional field you plan to set to null, call `verify_information_present` to confirm absence
- REQUIRED verification for: wife_name, retirement_date, congress_participation, cppcc_participation
- This is MANDATORY — prevents missing buried information and hallucination
- Example: verify_information_present(field_name="wife_name", search_terms=["妻子", "夫人", "配偶", "爱人"])

**Step 4: Look up unit references (optional but recommended)**
- For ANY unit reference in positions (集团军, 军区, 战区, 军, 师, 旅, etc.), call `lookup_unit_by_name`
- Even vague references like "某集团军" should be looked up
- Do this BEFORE save_officer_bio to enrich the data

**Step 5: Validate chronological consistency**
- Call `validate_dates` to ensure dates are chronologically consistent
- Checks: birth < enlistment < promotions < death, etc.
- This catches data entry errors and logical inconsistencies

**Step 6: Save extracted data (ONLY ONCE)**
- Only after validation passes, call `save_officer_bio` with all extracted information
- Include confidence_score (0.0-1.0) based on completeness and certainty
- Add extraction_notes explaining reasoning, uncertainties, and implicit rank observations
- DO NOT call save_officer_bio multiple times

**Step 7: Persist to database (OPTIONAL)**
- If confident and no validation errors (confidence_score >= {profile.min_confidence_threshold}), optionally call `save_to_database`
- This enables long-term storage and cross-referencing
- Skip this step if confidence is low or validation failed

**You may deviate from this sequence if the situation requires it, but this is the recommended approach for consistent, high-quality extractions.**

## Confidence Scoring for {profile.display_name}

When setting confidence_score, consider the expectations for this source type:
- 0.9-1.0: Most expected fields present, dates validated, all rare fields verified, no uncertainties
- 0.7-0.8: Common fields present, dates consistent, minor uncertainties
- 0.5-0.6: Limited information, some missing common fields, moderate uncertainties
- Below 0.5: Very limited information, significant uncertainties

Minimum confidence threshold for automatic database save: {profile.min_confidence_threshold}

Remember: For {profile.display_name}, these fields are COMMON and their absence may lower confidence:
{', '.join(profile.common_fields[:5])}

## Example Good Behavior

For a source mentioning "林炳尧，福建晋江人，1961年入伍，1964年加入中国共产党...":
1. ✓ Transliterate pinyin: 林炳尧 → Lín Bǐngyáo
2. ✓ Call verify_information_present for rare fields from profile ({', '.join(profile.rare_fields[:3])}, etc.)
3. ✓ Call lookup_unit_by_name for "某集团军" and "某军区"
4. ✓ Call validate_dates with enlistment_date="1961", party_membership_date="1964"
5. ✓ Call save_officer_bio with extracted data and appropriate confidence_score
6. ✓ Include source-specific observations in extraction_notes

## Example Bad Behavior

- ✗ Guessing wife_name based on common patterns
- ✗ Inferring retirement_date from death_date
- ✗ Making up personal background details not explicitly stated
- ✗ Calling save_officer_bio multiple times
- ✗ Skipping date validation
- ✗ Setting rare fields to null without calling verify_information_present first
- ✗ Leaving pinyin_name null when the Chinese name is available for transliteration
- ✗ Ignoring unit references without attempting lookup_unit_by_name
- ✗ Expecting {profile.display_name} to have the same completeness as other source types

Remember: Quality over quantity. It's better to have accurate, verified data with some null fields than to guess and hallucinate information.
For {profile.display_name}, adjust your expectations: {', '.join(profile.rare_fields[:2])} are rarely present in this source type."""

        # Optionally enhance with few-shot examples
        if self.use_few_shot and self.learner:
            try:
                examples = self.learner.get_few_shot_examples(n=2, min_confidence=0.8)
                if examples:
                    logger.info(f"Adding {len(examples)} few-shot examples to system prompt")
                    base_prompt = self.learner.add_to_system_prompt(base_prompt, examples)
                else:
                    logger.debug("No few-shot examples available")
            except Exception as e:
                logger.warning(f"Failed to add few-shot examples: {e}")

        return base_prompt

    def _format_field_expectations(self, profile: SourceProfile) -> str:
        """
        Format field expectations from profile into readable text.

        Args:
            profile: SourceProfile to format

        Returns:
            Formatted field expectations string
        """
        if not profile.field_expectations:
            return "No specific field expectations for this source type."

        lines = []
        for field_name, expectation in profile.field_expectations.items():
            lines.append(f"- **{field_name}**: {expectation}")

        return "\n".join(lines)

    def _create_user_prompt(self, source_text: str, source_url: str,
                           profile: SourceProfile) -> str:
        """
        Create user prompt customized for source type.

        Args:
            source_text: The biographical source text
            source_url: URL of the source
            profile: SourceProfile for this source type

        Returns:
            Formatted user prompt
        """
        return f"""Extract biographical information from this {profile.display_name}.

Source URL: {source_url}
Source Type: {profile.source_type}

{profile.display_name} text:
{source_text}

IMPORTANT: Follow the RECOMMENDED WORKFLOW:
1. lookup_existing_officer (check for duplicates)
2. Extract biographical information (focus on common fields: {', '.join(profile.common_fields[:3])})
3. verify_information_present for ALL rare fields ({', '.join(profile.rare_fields[:3])}, etc.)
4. validate_dates (ensure chronological consistency)
5. save_officer_bio (only once, after validation)
6. save_to_database (optional, if confidence >= {profile.min_confidence_threshold})

Use the tools systematically to ensure high-quality extraction."""

    def extract_bio_agentic(
        self,
        source_text: str,
        source_url: str,
        source_type: str = "universal"
    ) -> AgentExtractionResult:
        """
        Extract officer biography using agentic tool use pattern.

        This method implements an agentic loop where Claude can use tools iteratively
        to extract, validate, and save officer biographical data. Works with ANY
        biographical source - Claude intelligently adapts to the source type.

        Args:
            source_text: Full text of the biographical source
            source_url: URL where the source was found
            source_type: Type of source (default: "universal" for automatic adaptation).
                        Legacy options: "obituary", "news_article", "wiki"

        Returns:
            AgentExtractionResult with extraction data and metadata

        Raises:
            RuntimeError: If max iterations reached or critical error occurs
            ValueError: If source_type is invalid
        """
        logger.info(f"Starting agentic bio extraction (source_type={source_type})")
        logger.debug(f"Source text length: {len(source_text)} chars")

        # Load source profile (defaults to universal)
        try:
            profile = self.profile_registry.get(source_type)
            logger.info(f"Using profile: {profile.display_name}")
        except ValueError:
            # Fallback to universal if invalid type specified
            logger.warning(f"Unknown source type '{source_type}', falling back to universal")
            profile = self.profile_registry.get("universal")
            logger.info(f"Using profile: {profile.display_name}")

        # Reset tracking
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.conversation_turns = 0

        # Initialize conversation with source-specific prompts
        system_prompt = self._create_system_prompt(profile)
        user_prompt = self._create_user_prompt(source_text, source_url, profile)

        messages = [{
            "role": "user",
            "content": user_prompt
        }]

        # Track tool calls
        tool_call_history: List[ToolResult] = []

        # Track whether source text has been sent (for token optimization)
        source_text_sent = False

        # Agentic loop
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("[cyan]Extracting biography...", total=None)

            for iteration in range(self.max_iterations):
                self.conversation_turns += 1
                logger.info(f"Iteration {iteration + 1}/{self.max_iterations}")

                # Call Claude API with retries
                response = self._call_api_with_retry(
                    messages=messages,
                    system_prompt=system_prompt
                )

                # Track tokens
                self.total_input_tokens += response.usage.input_tokens
                self.total_output_tokens += response.usage.output_tokens

                # OPTIMIZATION: After first turn, replace source text with reference to save tokens
                # This prevents sending the full source text in every subsequent API call
                if not source_text_sent and len(messages) > 0:
                    source_text_sent = True
                    # Replace the full source text in the first message with a compact reference
                    # Claude retains the context from the first call
                    original_content = messages[0]["content"]
                    # Keep a short reference instead of full text
                    messages[0]["content"] = "[Source text provided in initial message - context retained]"
                    logger.debug(f"Source text optimization: reduced first message from {len(original_content)} to {len(messages[0]['content'])} chars")

                logger.info(
                    f"Response: stop_reason={response.stop_reason}, "
                    f"tokens={response.usage.input_tokens}/{response.usage.output_tokens}"
                )

                # Handle different stop reasons
                if response.stop_reason == "tool_use":
                    # Extract tool use blocks
                    tool_uses = [
                        block for block in response.content
                        if block.type == "tool_use"
                    ]

                    logger.info(f"Claude wants to use {len(tool_uses)} tool(s)")

                    # Execute tools
                    tool_results = []
                    for tool_use in tool_uses:
                        progress.update(
                            task,
                            description=f"[cyan]Executing {tool_use.name}..."
                        )

                        logger.info(f"Executing tool: {tool_use.name}")

                        # Execute tool using registry
                        result = execute_tool(tool_use.name, tool_use.input)

                        # Track tool call
                        tool_call_history.append(result)

                        # Prepare tool result for Claude
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_use.id,
                            "content": result.model_dump_json()
                        })

                    # Append to conversation
                    messages.append({"role": "assistant", "content": response.content})
                    messages.append({"role": "user", "content": tool_results})

                elif response.stop_reason == "end_turn":
                    # Claude is done
                    logger.info("Claude finished extraction")
                    progress.update(task, description="[green]✓ Extraction complete")
                    break

                elif response.stop_reason == "max_tokens":
                    # Response too long
                    logger.error("Response exceeded max tokens")
                    return AgentExtractionResult(
                        officer_bio=None,
                        tool_calls=tool_call_history,
                        conversation_turns=self.conversation_turns,
                        total_input_tokens=self.total_input_tokens,
                        total_output_tokens=self.total_output_tokens,
                        success=False,
                        error_message="Response exceeded maximum token limit"
                    )

                else:
                    logger.warning(f"Unexpected stop reason: {response.stop_reason}")
                    break

            else:
                # Max iterations reached
                logger.error(f"Max iterations ({self.max_iterations}) reached")
                return AgentExtractionResult(
                    officer_bio=None,
                    tool_calls=tool_call_history,
                    conversation_turns=self.conversation_turns,
                    total_input_tokens=self.total_input_tokens,
                    total_output_tokens=self.total_output_tokens,
                    success=False,
                    error_message=f"Maximum iterations ({self.max_iterations}) reached without completion"
                )

        # Store conversation for verbose/replay access
        self._last_messages = messages

        # Extract officer bio from tool call history
        officer_bio = self._extract_officer_bio_from_history(tool_call_history)

        if officer_bio:
            # Calculate enhanced confidence score
            confidence = self._calculate_confidence(officer_bio, tool_call_history)
            officer_bio.confidence_score = confidence

            logger.info(f"Extraction successful: {officer_bio.name}")
            logger.info(f"Confidence: {confidence:.2f}")

            return AgentExtractionResult(
                officer_bio=officer_bio,
                tool_calls=tool_call_history,
                conversation_turns=self.conversation_turns,
                total_input_tokens=self.total_input_tokens,
                total_output_tokens=self.total_output_tokens,
                success=True
            )
        else:
            logger.error("No officer bio was saved during extraction")
            return AgentExtractionResult(
                officer_bio=None,
                tool_calls=tool_call_history,
                conversation_turns=self.conversation_turns,
                total_input_tokens=self.total_input_tokens,
                total_output_tokens=self.total_output_tokens,
                success=False,
                error_message="Officer bio was not saved - save_officer_bio was never called or failed"
            )

    def _call_api_with_retry(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: str
    ) -> Any:
        """
        Call Anthropic API with retry logic for error handling.

        Args:
            messages: Conversation messages
            system_prompt: System prompt

        Returns:
            API response

        Raises:
            RuntimeError: If all retries fail
        """
        for attempt in range(self.max_retries):
            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=4096,
                    system=system_prompt,
                    tools=self.tools,
                    messages=messages
                )
                return response

            except anthropic.RateLimitError as e:
                logger.warning(f"Rate limit hit (attempt {attempt + 1}/{self.max_retries})")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                else:
                    raise RuntimeError(f"Rate limit error after {self.max_retries} retries: {e}")

            except anthropic.APIConnectionError as e:
                logger.warning(f"Connection error (attempt {attempt + 1}/{self.max_retries})")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                else:
                    raise RuntimeError(f"Connection error after {self.max_retries} retries: {e}")

            except anthropic.APIError as e:
                logger.error(f"API error: {e}")
                raise RuntimeError(f"Anthropic API error: {e}")

    def _extract_officer_bio_from_history(
        self,
        tool_calls: List[ToolResult]
    ) -> Optional[OfficerBio]:
        """
        Extract OfficerBio from tool call history.

        Searches for the save_officer_bio tool call and extracts the officer data.

        Args:
            tool_calls: List of all tool results from the conversation

        Returns:
            OfficerBio if found, None otherwise
        """
        # Find save_officer_bio tool call
        for tool_result in reversed(tool_calls):  # Start from most recent
            if tool_result.tool_name == "save_officer_bio" and tool_result.success:
                try:
                    officer_data = tool_result.data.get('officer_bio')
                    if officer_data:
                        # Reconstruct OfficerBio from dict
                        return OfficerBio(**officer_data)
                except Exception as e:
                    logger.error(f"Error reconstructing OfficerBio: {e}")
                    continue

        return None

    def _calculate_confidence(
        self,
        officer_bio: OfficerBio,
        tool_calls: List[ToolResult]
    ) -> float:
        """
        Calculate confidence score based on extraction quality.

        Factors:
        - Number of fields populated
        - Whether dates were validated
        - Number of verification checks
        - Success rate of tool calls

        Args:
            officer_bio: Extracted officer biography
            tool_calls: List of tool results

        Returns:
            Confidence score (0.0-1.0)
        """
        base_score = officer_bio.confidence_score

        # Bonus for date validation
        date_validated = any(
            tc.tool_name == "validate_dates" and tc.success
            for tc in tool_calls
        )
        if date_validated:
            base_score = min(1.0, base_score + 0.05)

        # Bonus for information verification
        verification_count = sum(
            1 for tc in tool_calls
            if tc.tool_name == "verify_information_present"
        )
        if verification_count > 0:
            base_score = min(1.0, base_score + 0.03)

        # Check field completeness
        bio_dict = officer_bio.to_dict(exclude_none=True)
        key_fields = [
            'pinyin_name', 'hometown', 'birth_date', 'enlistment_date',
            'party_membership_date', 'promotions', 'notable_positions'
        ]
        populated = sum(1 for field in key_fields if field in bio_dict)
        completeness_score = populated / len(key_fields)

        # Weighted average
        final_score = (base_score * 0.7) + (completeness_score * 0.3)

        return round(final_score, 2)

    def save_result_to_file(
        self,
        result: AgentExtractionResult,
        filename: Optional[str] = None
    ) -> Path:
        """
        Save extraction result to JSON file.

        Args:
            result: Extraction result to save
            filename: Optional filename (defaults to officer name + timestamp)

        Returns:
            Path to saved file
        """
        # Create output directory
        output_dir = Path(__file__).parent / "output"
        output_dir.mkdir(exist_ok=True)

        # Generate filename
        if filename is None:
            if result.officer_bio:
                base_name = result.officer_bio.name
            else:
                base_name = "failed_extraction"

            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"{base_name}_{timestamp}.json"

        output_file = output_dir / filename

        # Save with proper UTF-8 encoding
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(
                result.to_dict(exclude_none=True),
                f,
                ensure_ascii=False,
                indent=2
            )

        logger.info(f"Result saved to {output_file}")
        console.print(f"[green]✓ Result saved to {output_file}[/green]")

        return output_file


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    sdk = PLAgentSDK()
    console.print("[bold green]PLAgentSDK initialized successfully![/bold green]")
