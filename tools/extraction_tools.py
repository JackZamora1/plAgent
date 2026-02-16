"""Text extraction tools for various sources."""
import requests
from bs4 import BeautifulSoup
from pathlib import Path
from typing import Optional, Dict, Any, Type
from pydantic import BaseModel, ValidationError
from schema import OfficerBio, ToolResult, Promotion
from safeguards import validate_real_source_url


def extract_text_from_url(url: str) -> str:
    """
    Extract text content from a URL.

    Args:
        url: URL to extract text from

    Returns:
        Extracted text content

    Raises:
        requests.RequestException: If the request fails
    """
    response = requests.get(url, timeout=10)
    response.raise_for_status()

    soup = BeautifulSoup(response.content, 'html.parser')

    # Remove script and style elements
    for script in soup(["script", "style"]):
        script.decompose()

    # Get text
    text = soup.get_text()

    # Clean up whitespace
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = '\n'.join(chunk for chunk in chunks if chunk)

    return text


def extract_text_from_file(file_path: str) -> str:
    """
    Extract text content from a file.

    Args:
        file_path: Path to the file

    Returns:
        File content as text

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file encoding is incompatible
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    # Try UTF-8 first, fall back to other encodings if needed
    encodings = ['utf-8', 'gb2312', 'gbk', 'big5']

    for encoding in encodings:
        try:
            with open(path, 'r', encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue

    raise ValueError(
        f"Could not decode file {file_path} with any of the attempted encodings: {encodings}"
    )


def to_anthropic_tool(pydantic_model: Type[BaseModel]) -> Dict[str, Any]:
    """
    Convert a Pydantic model to Anthropic tool schema format.

    This function generates a tool schema compatible with the Anthropic API
    from a Pydantic model. It handles nested models, proper type mapping,
    descriptions, and required fields.

    Args:
        pydantic_model: A Pydantic BaseModel class to convert

    Returns:
        Dictionary containing the Anthropic tool schema with:
        - type: "object"
        - properties: Mapped field definitions
        - required: List of required field names

    Example:
        >>> schema = to_anthropic_tool(OfficerBio)
        >>> print(schema['properties']['name'])
        {'type': 'string', 'description': 'Chinese name of the officer'}

    Note:
        - Handles nested Pydantic models recursively
        - Maps Pydantic types to JSON schema types
        - Preserves field descriptions from Field(description=...)
        - Identifies required vs optional fields
    """
    schema = pydantic_model.model_json_schema()

    def resolve_ref(ref: str, defs: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve a $ref to its definition."""
        ref_name = ref.split('/')[-1]
        if ref_name in defs:
            return clean_schema(defs[ref_name], defs)
        return {}

    def clean_schema(schema_obj: Dict[str, Any], defs: Dict[str, Any] = None) -> Dict[str, Any]:
        """Recursively clean and resolve schema."""
        if defs is None:
            defs = {}

        # Create a copy to avoid modifying original
        result = {}

        # Handle $ref
        if '$ref' in schema_obj:
            return resolve_ref(schema_obj['$ref'], defs)

        # Copy basic fields
        for key in ['type', 'description', 'minimum', 'maximum']:
            if key in schema_obj:
                result[key] = schema_obj[key]

        # Handle anyOf (for Optional fields)
        if 'anyOf' in schema_obj:
            # Find the non-null option
            for option in schema_obj['anyOf']:
                if option.get('type') != 'null':
                    return clean_schema(option, defs)

        # Handle properties (for objects)
        if 'properties' in schema_obj:
            result['properties'] = {}
            for prop_name, prop_schema in schema_obj['properties'].items():
                result['properties'][prop_name] = clean_schema(prop_schema, defs)

        # Handle required fields
        if 'required' in schema_obj:
            result['required'] = schema_obj['required']

        # Handle arrays
        if schema_obj.get('type') == 'array':
            result['type'] = 'array'
            if 'items' in schema_obj:
                result['items'] = clean_schema(schema_obj['items'], defs)

        # Handle default values (but remove them - they're optional)
        if 'default' in schema_obj and 'type' in result:
            # Don't include default in final schema
            pass

        # Remove Pydantic-specific fields
        result.pop('title', None)

        return result

    # Get definitions
    defs = schema.pop('$defs', {})

    # Clean the main schema
    converted = clean_schema(schema, defs)

    return {
        "type": "object",
        "properties": converted.get('properties', {}),
        "required": converted.get('required', [])
    }


# Anthropic tool definition for saving officer biographical data
SAVE_OFFICER_BIO_TOOL = {
    "name": "save_officer_bio",
    "description": "Save extracted officer bio. Set null for missing fields. Use confidence_score (0-1) and extraction_notes for uncertainties. Call once after extraction.",
    "input_schema": to_anthropic_tool(OfficerBio)
}


def _sanitize_tool_input(tool_input: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize tool input to handle common LLM output quirks."""
    cleaned = {}
    list_fields = {
        'congress_participation', 'cppcc_participation',
        'promotions', 'notable_positions', 'awards'
    }
    for key, value in tool_input.items():
        # Convert string "null"/"None" OR empty strings to actual None
        if isinstance(value, str) and (value.lower() in ('null', 'none') or value.strip() == ''):
            cleaned[key] = None
        # Coerce bare strings to lists for list fields
        elif key in list_fields and isinstance(value, str):
            cleaned[key] = [value]
        else:
            cleaned[key] = value
    return cleaned


def execute_save_officer_bio(tool_input: Dict[str, Any]) -> ToolResult:
    """
    Execute the save_officer_bio tool by validating and processing input.

    This function validates the tool input against the OfficerBio schema
    and returns a ToolResult containing the validated data or error information.

    Args:
        tool_input: Dictionary containing officer biographical data.
                   Should match the OfficerBio model structure.

    Returns:
        ToolResult object with:
        - success=True and validated OfficerBio in data field if validation succeeds
        - success=False and error message if validation fails

    Example:
        >>> tool_input = {
        ...     "name": "林炳尧",
        ...     "source_url": "https://example.com",
        ...     "promotions": [{"rank": "少将", "date": "1995"}]
        ... }
        >>> result = execute_save_officer_bio(tool_input)
        >>> if result.success:
        ...     officer = result.data['officer_bio']
        ...     print(f"Saved: {officer.name}")

    Notes:
        - Validates all field types and constraints
        - Checks date formats and logical consistency
        - Handles nested Promotion objects
        - Returns detailed validation errors if input is invalid
        - The validated OfficerBio object is included in result.data['officer_bio']
    """
    tool_input = _sanitize_tool_input(tool_input)

    source_url = tool_input.get('source_url', '')
    source_url_valid, source_url_msg = validate_real_source_url(source_url)
    if not source_url_valid:
        return ToolResult(
            tool_name="save_officer_bio",
            success=False,
            data={
                "validation": "failed",
                "errors": [
                    source_url_msg,
                    "Please provide the actual source URL (e.g., https://www.news.cn/...)"
                ],
                "input": tool_input
            },
            error=(
                f"WARNING: Placeholder URL detected: {source_url}\n"
                "This suggests the extraction may be using incorrect source data.\n"
                "Please verify the source URL is correct before saving."
            )
        )

    try:
        # Validate input against OfficerBio schema
        officer_bio = OfficerBio(**tool_input)

        # Return success with the validated data
        # DB persistence is handled separately via the save_to_database tool
        return ToolResult(
            tool_name="save_officer_bio",
            success=True,
            data={
                "officer_bio": officer_bio.to_dict(exclude_none=True),
                "validation": "passed",
                "confidence_score": officer_bio.confidence_score
            }
        )

    except ValidationError as e:
        # Validation failed - return detailed error
        error_messages = []
        for error in e.errors():
            field = '.'.join(str(x) for x in error['loc'])
            message = error['msg']
            error_messages.append(f"{field}: {message}")

        error_str = "Validation failed:\n" + "\n".join(error_messages)

        return ToolResult(
            tool_name="save_officer_bio",
            success=False,
            data={
                "validation": "failed",
                "errors": error_messages,
                "input": tool_input
            },
            error=error_str
        )

    except Exception as e:
        # Unexpected error
        return ToolResult(
            tool_name="save_officer_bio",
            success=False,
            data={"input": tool_input},
            error=f"Unexpected error: {str(e)}"
        )
