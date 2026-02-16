"""Main agent for PLA leadership data extraction."""
import anthropic
from anthropic import Anthropic
from config import CONFIG
from schema import OfficerBio, AgentExtractionResult, ToolResult
from tools import get_all_tools, execute_tool
from tools.validation_tools import (
    register_source_context,
    clear_source_context,
    execute_validate_dates,
    execute_verify_information,
)
from source_profiles import SourceProfileRegistry, SourceProfile
from safeguards import validate_source_text_not_fixture
from rich.console import Console
from rich.panel import Panel
from rich.json import JSON
from rich.table import Table
from pathlib import Path
from typing import Optional, List, Dict, Any
import json
import logging
import time
from uuid import uuid4
import re

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
    - Single-pass extraction with selective verification
    - Comprehensive logging
    - Token usage tracking
    - Error handling with retries
    - Confidence scoring
    """

    def __init__(
        self,
        require_db: bool = False,
        use_few_shot: bool = True
    ):
        """
        Initialize the PLAgentSDK.

        Args:
            require_db: If True, require database credentials during validation
            use_few_shot: If True, use few-shot learning from past extractions
        """
        # Validate configuration
        CONFIG.validate_db_credentials(require_db=require_db)

        # Initialize Anthropic client
        if not CONFIG.ANTHROPIC_API_KEY:
            raise ValueError(
                "ANTHROPIC_API_KEY is required but not set.\n"
                "Please add it to your .env file:\n"
                "  ANTHROPIC_API_KEY=your_api_key_here"
            )
        self.client = Anthropic(api_key=CONFIG.ANTHROPIC_API_KEY)
        self.model = CONFIG.MODEL_NAME

        # Configure whether DB tools should be available.
        has_db_creds = bool(CONFIG.DATABASE_URL or (CONFIG.DB_USER and CONFIG.DB_PASSWORD))
        self.db_tools_enabled = require_db or has_db_creds

        # Load tools; remove DB tools when DB is not configured.
        all_tools = get_all_tools()
        if self.db_tools_enabled:
            self.tools = all_tools
        else:
            db_tool_names = {"lookup_existing_officer", "lookup_unit_by_name", "save_to_database"}
            self.tools = [tool for tool in all_tools if tool.get("name") not in db_tool_names]
            logger.info("DB tools disabled (no DB configuration detected)")

        logger.info(f"Loaded {len(self.tools)} tools for agent")

        # Initialize source profile registry
        self.profile_registry = SourceProfileRegistry()
        logger.info(f"Loaded {len(self.profile_registry.list_sources())} source profiles")

        # Configuration
        self.max_retries = 3
        self.retry_delay = 2  # seconds
        self.extraction_mode = "single_pass"
        self.max_verify_calls_per_extraction = max(0, CONFIG.MAX_VERIFY_CALLS_PER_EXTRACTION)

        # Tracking
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.conversation_turns = 0
        self._last_messages: List[Dict[str, Any]] = []

        # Initialize learning system
        if not CONFIG.ENABLE_FEW_SHOT_SINGLE_PASS:
            use_few_shot = False
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

        logger.info(f"PLAgentSDK initialized successfully (mode={self.extraction_mode})")

    def _create_single_pass_system_prompt(self, profile: SourceProfile) -> str:
        """Create compact system prompt for single-pass extraction."""
        del profile  # Universal prompt for now.
        return (
            "Extract PLA officer biography fields with high precision.\n"
            "Rules:\n"
            "- Use only explicitly supported information from source text.\n"
            "- pinyin_name may be transliterated when not explicit.\n"
            "- Dates must be YYYY or YYYY-MM-DD.\n"
            "- Return a single JSON object matching OfficerBio fields.\n"
            "- Use null for unknown fields.\n"
            "- Keep lists as arrays; no prose outside JSON.\n"
        )

    def _create_single_pass_user_prompt(self, source_text: str, source_url: str) -> str:
        """Create compact user prompt for single-pass extraction."""
        return (
            "Extract officer biography into JSON with these keys:\n"
            "name, source_url, source_type, pinyin_name, hometown, birth_date, enlistment_date,\n"
            "party_membership_date, retirement_date, death_date, congress_participation,\n"
            "cppcc_participation, promotions, notable_positions, awards, wife_name,\n"
            "confidence_score, extraction_notes.\n\n"
            f"source_url: {source_url}\n"
            "source_type: infer from content (obituary/news_article/wiki/social_media/other).\n\n"
            f"Source text:\n{source_text}\n\n"
            "Return JSON only."
        )

    def extract_bio_agentic(
        self,
        source_text: str,
        source_url: str
    ) -> AgentExtractionResult:
        """Extract officer biography using single-pass mode."""
        return self._extract_single_pass(source_text=source_text, source_url=source_url)

    def _extract_single_pass(self, source_text: str, source_url: str) -> AgentExtractionResult:
        """Single-pass extraction with local validation and gated verification."""
        logger.info("Starting single-pass bio extraction")
        logger.debug(f"Source text length: {len(source_text)} chars")
        validate_source_text_not_fixture(source_text, source_url, Path(__file__).parent)

        profile = self.profile_registry.get("universal")
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.conversation_turns = 0

        source_ref = f"src_{uuid4().hex[:12]}"
        register_source_context(source_ref, source_text)

        system_prompt = self._create_single_pass_system_prompt(profile)
        user_prompt = self._create_single_pass_user_prompt(source_text, source_url)
        messages = [{"role": "user", "content": user_prompt}]
        self._last_messages = list(messages)
        tool_call_history: List[ToolResult] = []

        try:
            self.conversation_turns += 1
            response = self._call_api_with_retry(
                messages=messages,
                system_prompt=system_prompt,
                tools_override=[]
            )
            self._last_messages.append({"role": "assistant", "content": response.content})
            self.total_input_tokens += response.usage.input_tokens
            self.total_output_tokens += response.usage.output_tokens

            payload = self._extract_json_payload(response.content)
            if not payload:
                return AgentExtractionResult(
                    officer_bio=None,
                    tool_calls=tool_call_history,
                    conversation_turns=self.conversation_turns,
                    total_input_tokens=self.total_input_tokens,
                    total_output_tokens=self.total_output_tokens,
                    success=False,
                    error_message="Single-pass extraction returned no parseable JSON payload"
                )

            payload["source_url"] = source_url
            payload.setdefault("source_type", "universal")
            payload.setdefault("confidence_score", 0.0)

            save_result = execute_tool("save_officer_bio", payload)
            tool_call_history.append(save_result)

            if not save_result.success:
                repaired = self._repair_single_pass_payload(
                    source_text=source_text,
                    source_url=source_url,
                    prior_payload=payload,
                    validation_error=save_result.error or "schema validation failed"
                )
                if repaired:
                    repaired["source_url"] = source_url
                    repaired.setdefault("source_type", "universal")
                    repaired.setdefault("confidence_score", 0.0)
                    save_result = execute_tool("save_officer_bio", repaired)
                    tool_call_history.append(save_result)

            if not save_result.success:
                return AgentExtractionResult(
                    officer_bio=None,
                    tool_calls=tool_call_history,
                    conversation_turns=self.conversation_turns,
                    total_input_tokens=self.total_input_tokens,
                    total_output_tokens=self.total_output_tokens,
                    success=False,
                    error_message=save_result.error or "Failed to validate extracted payload"
                )

            officer_bio = OfficerBio(**save_result.data["officer_bio"])

            verify_calls = 0
            for field_name in profile.rare_fields:
                field_value = getattr(officer_bio, field_name, None)
                if field_value is None:
                    continue
                if verify_calls >= self.max_verify_calls_per_extraction:
                    break

                terms = profile.get_search_terms(field_name) or [str(field_value)]
                verify_result = execute_verify_information({
                    "field_name": field_name,
                    "search_terms": terms,
                    "source_ref": source_ref
                })
                tool_call_history.append(verify_result)
                verify_calls += 1

                if verify_result.success and not verify_result.data.get("found"):
                    setattr(officer_bio, field_name, None)
                    note = f"{field_name} removed after verification check."
                    if officer_bio.extraction_notes:
                        officer_bio.extraction_notes = f"{officer_bio.extraction_notes} {note}"
                    else:
                        officer_bio.extraction_notes = note

            date_validation = execute_validate_dates(officer_bio.to_dict(exclude_none=True))
            tool_call_history.append(date_validation)

            if not date_validation.success:
                return AgentExtractionResult(
                    officer_bio=None,
                    tool_calls=tool_call_history,
                    conversation_turns=self.conversation_turns,
                    total_input_tokens=self.total_input_tokens,
                    total_output_tokens=self.total_output_tokens,
                    success=False,
                    error_message=date_validation.error or "Date validation failed"
                )

            self._normalize_position_order(officer_bio, source_text)
            self._annotate_inferred_fields(officer_bio, source_text)
            confidence = self._calculate_confidence(officer_bio, tool_call_history)
            officer_bio.confidence_score = confidence

            return AgentExtractionResult(
                officer_bio=officer_bio,
                tool_calls=tool_call_history,
                conversation_turns=self.conversation_turns,
                total_input_tokens=self.total_input_tokens,
                total_output_tokens=self.total_output_tokens,
                success=True
            )
        finally:
            clear_source_context(source_ref)

    def _extract_json_payload(self, response_content: Any) -> Optional[Dict[str, Any]]:
        """Parse first JSON object found in response text blocks."""
        text_chunks: List[str] = []
        for block in response_content:
            block_type = getattr(block, "type", None)
            if block_type == "text":
                text_chunks.append(getattr(block, "text", ""))

        if not text_chunks:
            return None

        raw_text = "\n".join(text_chunks).strip()
        if not raw_text:
            return None

        if raw_text.startswith("```"):
            raw_text = raw_text.strip("`")
            raw_text = raw_text.replace("json\n", "", 1).strip()

        try:
            return json.loads(raw_text)
        except json.JSONDecodeError:
            pass

        start = raw_text.find("{")
        end = raw_text.rfind("}")
        if start == -1 or end == -1 or start >= end:
            return None

        candidate = raw_text[start:end + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            return None

    def _repair_single_pass_payload(
        self,
        source_text: str,
        source_url: str,
        prior_payload: Dict[str, Any],
        validation_error: str
    ) -> Optional[Dict[str, Any]]:
        """Run a compact repair call when initial single-pass payload is invalid."""
        self.conversation_turns += 1
        system_prompt = (
            "Repair invalid OfficerBio JSON. Return ONLY corrected JSON with valid date formats "
            "(YYYY or YYYY-MM-DD), proper field types, and no extra text."
        )
        user_prompt = (
            f"Source URL: {source_url}\n"
            f"Validation error:\n{validation_error}\n\n"
            f"Previous JSON:\n{json.dumps(prior_payload, ensure_ascii=False, indent=2)}\n\n"
            f"Source text:\n{source_text}\n\n"
            "Return corrected JSON only."
        )
        self._last_messages.append({"role": "user", "content": user_prompt})
        response = self._call_api_with_retry(
            messages=[{"role": "user", "content": user_prompt}],
            system_prompt=system_prompt,
            tools_override=[]
        )
        self._last_messages.append({"role": "assistant", "content": response.content})
        self.total_input_tokens += response.usage.input_tokens
        self.total_output_tokens += response.usage.output_tokens
        return self._extract_json_payload(response.content)

    def _call_api_with_retry(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: str,
        tools_override: Optional[List[Dict[str, Any]]] = None,
        max_tokens: int = 4096
    ) -> Any:
        """
        Call Anthropic API with retry logic for error handling.

        Args:
            messages: Conversation messages
            system_prompt: System prompt
            tools_override: Optional explicit tool set for this call
            max_tokens: Max output tokens for this call

        Returns:
            API response

        Raises:
            RuntimeError: If all retries fail
        """
        for attempt in range(self.max_retries):
            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    system=system_prompt,
                    tools=self.tools if tools_override is None else tools_override,
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

    def _normalize_position_order(self, officer_bio: OfficerBio, source_text: str) -> None:
        """Normalize notable_positions to source appearance order."""
        if not officer_bio.notable_positions:
            return

        indexed_positions = []
        for i, position in enumerate(officer_bio.notable_positions):
            idx = source_text.find(position)
            # Keep stable ordering for non-matches by placing them at the end.
            order_key = idx if idx >= 0 else len(source_text) + i
            indexed_positions.append((order_key, i, position))

        indexed_positions.sort(key=lambda x: (x[0], x[1]))
        officer_bio.notable_positions = [p for _, _, p in indexed_positions]

    def _is_date_explicit_in_source(self, date_value: str, source_text: str) -> bool:
        """Check whether a date appears explicitly in source text."""
        if not date_value:
            return False
        if date_value in source_text:
            return True

        if re.match(r"^\d{4}$", date_value):
            return date_value in source_text

        if re.match(r"^\d{4}-\d{2}-\d{2}$", date_value):
            year = int(date_value[:4])
            month = int(date_value[5:7])
            day = int(date_value[8:10])

            cn_date_patterns = [
                f"{year}年{month}月{day}日",
                f"{year}年{month}月{day}号",
                f"{year}年{month}月{day}",
            ]
            if any(p in source_text for p in cn_date_patterns):
                return True

            en_patterns = [
                f"{year}-{month:02d}-{day:02d}",
                f"{year}/{month}/{day}",
                f"{year}/{month:02d}/{day:02d}",
            ]
            if any(p in source_text for p in en_patterns):
                return True

        return False

    def _annotate_inferred_fields(self, officer_bio: OfficerBio, source_text: str) -> None:
        """Add extraction note for likely inferred fields."""
        inferred_fields: List[str] = []
        for field_name in ("birth_date", "death_date", "retirement_date"):
            value = getattr(officer_bio, field_name, None)
            if not value:
                continue
            if not self._is_date_explicit_in_source(str(value), source_text):
                inferred_fields.append(field_name)

        if inferred_fields:
            note = f"Inferred fields (not explicitly stated verbatim): {', '.join(inferred_fields)}."
            if officer_bio.extraction_notes:
                if note not in officer_bio.extraction_notes:
                    officer_bio.extraction_notes = f"{officer_bio.extraction_notes} {note}"
            else:
                officer_bio.extraction_notes = note

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
        # Deterministic score from extraction completeness and tool outcomes.
        bio_dict = officer_bio.to_dict(exclude_none=True)
        key_fields = [
            'pinyin_name', 'hometown', 'birth_date', 'enlistment_date',
            'party_membership_date', 'promotions', 'notable_positions'
        ]
        populated = sum(1 for field in key_fields if field in bio_dict)
        completeness_score = populated / len(key_fields) if key_fields else 0.0

        date_validation_score = 1.0 if any(
            tc.tool_name == "validate_dates" and tc.success for tc in tool_calls
        ) else 0.0

        verify_calls = [tc for tc in tool_calls if tc.tool_name == "verify_information_present"]
        if verify_calls:
            verification_score = sum(1 for tc in verify_calls if tc.success) / len(verify_calls)
        else:
            verification_score = 0.5

        if tool_calls:
            tool_success_ratio = sum(1 for tc in tool_calls if tc.success) / len(tool_calls)
        else:
            tool_success_ratio = 0.0

        final_score = (
            completeness_score * 0.55
            + date_validation_score * 0.25
            + verification_score * 0.10
            + tool_success_ratio * 0.10
        )

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
