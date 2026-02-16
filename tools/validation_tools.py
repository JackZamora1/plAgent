"""Data validation tools."""
from typing import Dict, List, Any, Optional
from schema import ToolResult
import re

_SOURCE_CONTEXTS: Dict[str, str] = {}


def register_source_context(source_ref: str, source_text: str) -> None:
    """Register source text by reference for verification lookups."""
    _SOURCE_CONTEXTS[source_ref] = source_text


def clear_source_context(source_ref: str) -> None:
    """Clear source text for a completed extraction."""
    _SOURCE_CONTEXTS.pop(source_ref, None)


def resolve_source_context(source_ref: str) -> Optional[str]:
    """Resolve source text from a source reference."""
    return _SOURCE_CONTEXTS.get(source_ref)


def _parse_year(date_str: Optional[str]) -> Optional[int]:
    """
    Parse year from date string (YYYY or YYYY-MM-DD format).

    Args:
        date_str: Date string in YYYY or YYYY-MM-DD format

    Returns:
        Year as integer, or None if invalid/missing
    """
    if not date_str:
        return None

    try:
        # Extract first 4 digits (year)
        match = re.match(r'^(\d{4})', date_str)
        if match:
            return int(match.group(1))
    except (ValueError, AttributeError):
        pass

    return None


# Anthropic tool definition for date validation
VALIDATE_DATES_TOOL = {
    "name": "validate_dates",
    "description": "Verify dates are chronologically consistent (birth < enlistment < promotions < death).",
    "input_schema": {
        "type": "object",
        "properties": {
            "enlistment_date": {
                "type": "string",
                "description": "Date when officer joined the military (YYYY or YYYY-MM-DD)"
            },
            "party_membership_date": {
                "type": "string",
                "description": "Date when officer joined the CCP (YYYY or YYYY-MM-DD)"
            },
            "promotions": {
                "type": "array",
                "description": "List of military promotions with dates",
                "items": {
                    "type": "object",
                    "properties": {
                        "rank": {"type": "string"},
                        "date": {"type": "string"}
                    }
                }
            },
            "birth_date": {
                "type": "string",
                "description": "Birth date (YYYY or YYYY-MM-DD)"
            },
            "death_date": {
                "type": "string",
                "description": "Death date (YYYY or YYYY-MM-DD)"
            }
        }
    }
}


def execute_validate_dates(tool_input: Dict[str, Any]) -> ToolResult:
    """
    Execute date validation tool to check chronological consistency.

    This function validates that dates are in logical chronological order:
    - Birth date before all other dates
    - Enlistment date before party membership and promotions
    - Promotions in chronological order
    - Death date after all other dates

    Args:
        tool_input: Dictionary containing dates to validate:
            - enlistment_date: Optional[str]
            - party_membership_date: Optional[str]
            - promotions: Optional[List[dict]] with 'rank' and 'date'
            - birth_date: Optional[str]
            - death_date: Optional[str]

    Returns:
        ToolResult with:
        - success=True if all dates are consistent
        - success=False if inconsistencies found, with detailed errors

    Example:
        >>> tool_input = {
        ...     "enlistment_date": "1990",
        ...     "promotions": [
        ...         {"rank": "少将", "date": "1985"},  # Before enlistment!
        ...         {"rank": "中将", "date": "1995"}
        ...     ]
        ... }
        >>> result = execute_validate_dates(tool_input)
        >>> print(result.error)
        "Date inconsistencies found:
         - Enlistment date 1990 is after promotion date 1985"

    Notes:
        - All dates are converted to years for comparison
        - Missing/None dates are skipped in validation
        - Returns detailed error messages for each inconsistency found
    """
    try:
        errors = []
        warnings = []

        # Parse dates
        birth_year = _parse_year(tool_input.get('birth_date'))
        enlist_year = _parse_year(tool_input.get('enlistment_date'))
        party_year = _parse_year(tool_input.get('party_membership_date'))
        death_year = _parse_year(tool_input.get('death_date'))

        # Parse promotions in original order
        promotions = tool_input.get('promotions', [])
        promotion_years = []
        for promo in promotions:
            if isinstance(promo, dict) and 'date' in promo:
                year = _parse_year(promo['date'])
                if year:
                    promotion_years.append({
                        'rank': promo.get('rank', 'Unknown'),
                        'year': year
                    })

        # Validation checks
        # 1. Birth date checks
        if birth_year:
            if enlist_year and birth_year > enlist_year:
                errors.append(
                    f"Birth date {birth_year} is after enlistment date {enlist_year}"
                )

            if party_year and birth_year > party_year:
                errors.append(
                    f"Birth date {birth_year} is after party membership date {party_year}"
                )

            for promo in promotion_years:
                if birth_year > promo['year']:
                    errors.append(
                        f"Birth date {birth_year} is after promotion to {promo['rank']} in {promo['year']}"
                    )

        # 2. Death date checks
        if death_year:
            if birth_year and death_year < birth_year:
                errors.append(
                    f"Death date {death_year} is before birth date {birth_year}"
                )

            if enlist_year and death_year < enlist_year:
                errors.append(
                    f"Death date {death_year} is before enlistment date {enlist_year}"
                )

        # 3. Enlistment date checks
        if enlist_year:
            # Usually join party after enlisting (but not always strict)
            if party_year and enlist_year > party_year:
                warnings.append(
                    f"Enlistment date {enlist_year} is after party membership date {party_year} "
                    "(unusual but possible)"
                )

            # Promotions should be after enlistment
            for promo in promotion_years:
                if enlist_year > promo['year']:
                    errors.append(
                        f"Enlistment date {enlist_year} is after promotion to {promo['rank']} in {promo['year']}"
                    )

        # 4. Check promotions are in chronological order as provided
        for i in range(len(promotion_years) - 1):
            current = promotion_years[i]
            next_promo = promotion_years[i + 1]

            if current['year'] > next_promo['year']:
                errors.append(
                    f"Promotion to {current['rank']} in {current['year']} "
                    f"is after promotion to {next_promo['rank']} in {next_promo['year']}"
                )

        # Build result
        if errors:
            error_msg = "Date inconsistencies found:\n"
            for error in errors:
                error_msg += f" - {error}\n"

            if warnings:
                error_msg += "\nWarnings:\n"
                for warning in warnings:
                    error_msg += f" - {warning}\n"

            return ToolResult(
                tool_name="validate_dates",
                success=False,
                data={
                    "errors": errors,
                    "warnings": warnings,
                    "input": tool_input
                },
                error=error_msg.strip()
            )

        # Success!
        success_msg = "All dates are chronologically consistent."
        if warnings:
            success_msg += "\n\nWarnings:\n"
            for warning in warnings:
                success_msg += f" - {warning}\n"

        return ToolResult(
            tool_name="validate_dates",
            success=True,
            data={
                "message": "Dates validated successfully",
                "warnings": warnings,
                "checked": {
                    "birth_year": birth_year,
                    "enlistment_year": enlist_year,
                    "party_year": party_year,
                    "death_year": death_year,
                    "promotion_count": len(promotion_years)
                }
            }
        )

    except Exception as e:
        return ToolResult(
            tool_name="validate_dates",
            success=False,
            data={"input": tool_input},
            error=f"Unexpected error during date validation: {str(e)}"
        )


# Anthropic tool definition for information verification
VERIFY_INFORMATION_TOOL = {
    "name": "verify_information_present",
    "description": "Search source text to confirm if biographical details (wife, retirement date, awards, etc.) are mentioned. Returns matching excerpts or confirms absence. Prevents hallucination.",
    "input_schema": {
        "type": "object",
        "properties": {
            "field_name": {
                "type": "string",
                "description": "Name of the field being verified (e.g., 'wife_name', 'retirement_date', 'death_date')"
            },
            "search_terms": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of Chinese terms to search for (e.g., ['妻子', '夫人', '配偶'] for wife)"
            },
            "source_ref": {
                "type": "string",
                "description": "Opaque source reference registered by SDK for current extraction"
            }
        },
        "required": ["field_name", "search_terms", "source_ref"]
    }
}


def execute_verify_information(tool_input: Dict[str, Any]) -> ToolResult:
    """
    Execute information verification tool to check if data exists in source text.

    This function searches the source text for mentions of specific information,
    helping to avoid hallucination by confirming details are actually present
    in the source material.

    Args:
        tool_input: Dictionary containing:
            - field_name: str - Name of field being verified
            - search_terms: List[str] - Chinese terms to search for
            - source_ref: str - Source reference for SDK-registered source text

    Returns:
        ToolResult with:
        - success=True if information found, with relevant excerpt in data
        - success=False if not found (but this is still useful information!)

    Example:
        >>> tool_input = {
        ...     "field_name": "wife_name",
        ...     "search_terms": ["妻子", "夫人", "配偶"],
        ...     "source_ref": "src_abc123"
        ... }
        >>> result = execute_verify_information(tool_input)
        >>> print(result.data['excerpt'])
        "...夫人是张三..."

    Notes:
        - Case-insensitive search
        - Returns up to 3 matching excerpts
        - Each excerpt shows context (50 chars before/after match)
        - success=False doesn't mean error - it means info wasn't found
    """
    try:
        field_name = tool_input.get('field_name', 'unknown')
        search_terms = tool_input.get('search_terms', [])
        source_ref = tool_input.get('source_ref')
        source_text = ""
        if source_ref:
            source_text = resolve_source_context(source_ref) or ""

        if not source_text:
            return ToolResult(
                tool_name="verify_information_present",
                success=False,
                data={"field_name": field_name, "source_ref": source_ref},
                error="No source text available for verification (missing or invalid source_ref)"
            )

        if not search_terms:
            return ToolResult(
                tool_name="verify_information_present",
                success=False,
                data={"field_name": field_name},
                error="No search terms provided"
            )

        # Search for each term
        found_excerpts = []
        found_terms = []

        for term in search_terms:
            # Find all occurrences of this term
            pattern = re.escape(term)
            matches = list(re.finditer(pattern, source_text, re.IGNORECASE))

            for match in matches:
                start = match.start()
                end = match.end()

                # Get context (50 chars before and after)
                context_start = max(0, start - 50)
                context_end = min(len(source_text), end + 50)

                excerpt = source_text[context_start:context_end]

                # Add ellipsis if truncated
                if context_start > 0:
                    excerpt = "..." + excerpt
                if context_end < len(source_text):
                    excerpt = excerpt + "..."

                found_excerpts.append({
                    "term": term,
                    "excerpt": excerpt,
                    "position": start
                })
                found_terms.append(term)

        # Remove duplicates and limit to 3 excerpts
        unique_excerpts = []
        seen_positions = set()

        for excerpt_data in found_excerpts:
            pos = excerpt_data['position']
            if pos not in seen_positions:
                unique_excerpts.append(excerpt_data)
                seen_positions.add(pos)

            if len(unique_excerpts) >= 3:
                break

        # Build result
        if found_excerpts:
            # Information found!
            return ToolResult(
                tool_name="verify_information_present",
                success=True,
                data={
                    "field_name": field_name,
                    "found": True,
                    "matched_terms": list(set(found_terms)),
                    "excerpt_count": len(unique_excerpts),
                    "excerpts": [e['excerpt'] for e in unique_excerpts],
                    "message": f"Found {len(unique_excerpts)} mention(s) of {field_name} in the text."
                }
            )
        else:
            # Information not found (not an error - just confirms absence)
            return ToolResult(
                tool_name="verify_information_present",
                success=True,  # Success means search completed, even if not found
                data={
                    "field_name": field_name,
                    "found": False,
                    "searched_terms": search_terms,
                    "message": f"No mention of {field_name} found in the text. "
                               f"Searched for: {', '.join(search_terms)}"
                }
            )

    except Exception as e:
        return ToolResult(
            tool_name="verify_information_present",
            success=False,
            data={"field_name": tool_input.get('field_name', 'unknown')},
            error=f"Unexpected error during verification: {str(e)}"
        )
