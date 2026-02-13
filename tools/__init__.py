"""Tools package for PLA Agent SDK."""
from typing import List, Dict, Any, Callable
import logging
from datetime import datetime

# Import all tools and executors
from .extraction_tools import (
    extract_text_from_url,
    extract_text_from_file,
    to_anthropic_tool,
    SAVE_OFFICER_BIO_TOOL,
    execute_save_officer_bio
)
from .validation_tools import (
    VALIDATE_DATES_TOOL,
    VERIFY_INFORMATION_TOOL,
    execute_validate_dates,
    execute_verify_information
)
from .database_tools import (
    save_officer_bio_to_database,
    LOOKUP_OFFICER_TOOL,
    LOOKUP_UNIT_TOOL,
    SAVE_TO_DATABASE_TOOL,
    execute_lookup_officer,
    execute_lookup_unit,
    execute_save_to_database
)

# Import ToolResult for type hints
from schema import ToolResult

# Set up logging
logger = logging.getLogger(__name__)


# Tool Registry: Maps tool names to their definitions
TOOL_REGISTRY: Dict[str, Dict[str, Any]] = {
    "save_officer_bio": SAVE_OFFICER_BIO_TOOL,
    "validate_dates": VALIDATE_DATES_TOOL,
    "verify_information_present": VERIFY_INFORMATION_TOOL,
    "lookup_existing_officer": LOOKUP_OFFICER_TOOL,
    "lookup_unit_by_name": LOOKUP_UNIT_TOOL,
    "save_to_database": SAVE_TO_DATABASE_TOOL,
}


# Tool Executors: Maps tool names to their executor functions
TOOL_EXECUTORS: Dict[str, Callable[[Dict[str, Any]], ToolResult]] = {
    "save_officer_bio": execute_save_officer_bio,
    "validate_dates": execute_validate_dates,
    "verify_information_present": execute_verify_information,
    "lookup_existing_officer": execute_lookup_officer,
    "lookup_unit_by_name": execute_lookup_unit,
    "save_to_database": execute_save_to_database,
}


def get_all_tools() -> List[Dict[str, Any]]:
    """
    Get all tool definitions for Anthropic API.

    Returns a list of all registered tool definitions that can be passed
    directly to the Anthropic messages.create() API call.

    Returns:
        List of tool definition dictionaries

    Example:
        >>> from tools import get_all_tools
        >>> tools = get_all_tools()
        >>> response = client.messages.create(
        ...     model="claude-sonnet-4-20250514",
        ...     max_tokens=4096,
        ...     tools=tools,  # All tools available
        ...     messages=[...]
        ... )
    """
    return list(TOOL_REGISTRY.values())


def execute_tool(tool_name: str, tool_input: Dict[str, Any]) -> ToolResult:
    """
    Execute a tool by name with the given input.

    Dispatches to the appropriate executor function based on tool name.
    Handles unknown tool names and logs all tool executions.

    Args:
        tool_name: Name of the tool to execute
        tool_input: Input dictionary for the tool

    Returns:
        ToolResult from the tool execution

    Raises:
        ValueError: If tool_name is not registered

    Example:
        >>> from tools import execute_tool
        >>> result = execute_tool(
        ...     "validate_dates",
        ...     {"enlistment_date": "1961", "promotions": [...]}
        ... )
        >>> if result.success:
        ...     print("Validation passed!")

    Notes:
        - Automatically logs tool execution start and end
        - Handles unknown tools gracefully
        - Returns ToolResult even on errors
    """
    # Log tool execution start
    logger.info(f"Executing tool: {tool_name}")
    logger.debug(f"Tool input: {tool_input}")

    start_time = datetime.now()

    # Check if tool is registered
    if tool_name not in TOOL_EXECUTORS:
        error_msg = f"Unknown tool: {tool_name}. Available tools: {list(TOOL_EXECUTORS.keys())}"
        logger.error(error_msg)

        # Return error ToolResult
        return ToolResult(
            tool_name=tool_name,
            success=False,
            data={"input": tool_input},
            error=error_msg
        )

    try:
        # Get executor function
        executor = TOOL_EXECUTORS[tool_name]

        # Execute tool
        result = executor(tool_input)

        # Log execution time
        execution_time = (datetime.now() - start_time).total_seconds()
        logger.info(
            f"Tool '{tool_name}' executed in {execution_time:.2f}s - "
            f"Success: {result.success}"
        )

        if not result.success:
            logger.warning(f"Tool '{tool_name}' failed: {result.error}")

        return result

    except Exception as e:
        # Log unexpected errors
        execution_time = (datetime.now() - start_time).total_seconds()
        logger.error(
            f"Tool '{tool_name}' raised exception after {execution_time:.2f}s: {e}",
            exc_info=True
        )

        # Return error ToolResult
        return ToolResult(
            tool_name=tool_name,
            success=False,
            data={"input": tool_input},
            error=f"Unexpected error during tool execution: {str(e)}"
        )


def get_tool_names() -> List[str]:
    """
    Get list of all registered tool names.

    Returns:
        List of tool name strings

    Example:
        >>> from tools import get_tool_names
        >>> print(get_tool_names())
        ['save_officer_bio', 'validate_dates', ...]
    """
    return list(TOOL_REGISTRY.keys())


def get_tool_definition(tool_name: str) -> Dict[str, Any]:
    """
    Get the definition for a specific tool.

    Args:
        tool_name: Name of the tool

    Returns:
        Tool definition dictionary

    Raises:
        KeyError: If tool_name is not registered

    Example:
        >>> from tools import get_tool_definition
        >>> tool_def = get_tool_definition("validate_dates")
        >>> print(tool_def['description'])
    """
    return TOOL_REGISTRY[tool_name]


# Organize tools by category for easy selection
EXTRACTION_TOOLS = ["save_officer_bio"]
VALIDATION_TOOLS = ["validate_dates", "verify_information_present"]
DATABASE_TOOLS = ["lookup_existing_officer", "lookup_unit_by_name", "save_to_database"]


def get_tools_by_category(category: str) -> List[Dict[str, Any]]:
    """
    Get tool definitions for a specific category.

    Args:
        category: Tool category ("extraction", "validation", or "database")

    Returns:
        List of tool definitions in that category

    Raises:
        ValueError: If category is unknown

    Example:
        >>> from tools import get_tools_by_category
        >>> validation_tools = get_tools_by_category("validation")
        >>> # Use only validation tools
        >>> response = client.messages.create(
        ...     tools=validation_tools,
        ...     messages=[...]
        ... )
    """
    category_map = {
        "extraction": EXTRACTION_TOOLS,
        "validation": VALIDATION_TOOLS,
        "database": DATABASE_TOOLS,
    }

    if category not in category_map:
        raise ValueError(
            f"Unknown category: {category}. "
            f"Available: {list(category_map.keys())}"
        )

    tool_names = category_map[category]
    return [TOOL_REGISTRY[name] for name in tool_names]


__all__ = [
    # Text extraction utilities
    'extract_text_from_url',
    'extract_text_from_file',
    'to_anthropic_tool',

    # Tool definitions
    'SAVE_OFFICER_BIO_TOOL',
    'VALIDATE_DATES_TOOL',
    'VERIFY_INFORMATION_TOOL',
    'LOOKUP_OFFICER_TOOL',
    'LOOKUP_UNIT_TOOL',
    'SAVE_TO_DATABASE_TOOL',

    # Tool executors
    'execute_save_officer_bio',
    'execute_validate_dates',
    'execute_verify_information',
    'execute_lookup_officer',
    'execute_lookup_unit',
    'execute_save_to_database',

    # Tool registry
    'TOOL_REGISTRY',
    'TOOL_EXECUTORS',
    'get_all_tools',
    'execute_tool',
    'get_tool_names',
    'get_tool_definition',
    'get_tools_by_category',

    # Tool categories
    'EXTRACTION_TOOLS',
    'VALIDATION_TOOLS',
    'DATABASE_TOOLS',

    # Database utilities
    'save_officer_bio_to_database',
]
