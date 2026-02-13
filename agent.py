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
        base_prompt = f"""You are an expert in extracting PLA officer biographies from {profile.source_description}

# Core Rules
- Extract ONLY explicitly stated information
- Generate pinyin_name (transliterate if not in source, e.g., 林炳尧 → Lín Bǐngyáo)
- Use YYYY or YYYY-MM-DD date format
- Verify rare fields ({', '.join(profile.rare_fields)}) with verify_information_present before setting null
- Extract ALL positions (junior to senior) - complete career progression is valuable
- Use extraction_notes for position-implied ranks (e.g., 班长→下士, 团长→上校), but only add explicit promotions to promotions array

# Workflow
1. lookup_existing_officer (check duplicates)
2. Extract bio (focus on {', '.join(profile.common_fields[:3])})
3. verify_information_present for rare fields
4. lookup_unit_by_name for unit references
5. validate_dates (chronological check)
6. save_officer_bio (once only)
7. save_to_database (if confidence >= {profile.min_confidence_threshold})

# {profile.display_name} Field Expectations
{self._format_field_expectations(profile)}

# Source Context
{profile.extraction_context}

# Confidence Scoring
- 0.9-1.0: Most expected fields, dates validated
- 0.7-0.8: Common fields present, minor gaps
- 0.5-0.6: Limited info, some missing fields
Threshold for DB save: {profile.min_confidence_threshold}

Common fields for {profile.display_name}: {', '.join(profile.common_fields[:5])}"""

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
