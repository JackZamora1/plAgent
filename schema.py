"""Pydantic models for PLA leadership data extraction."""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator, model_validator
import re


class Promotion(BaseModel):
    """Model for military rank promotions."""

    rank: str = Field(..., description="Military rank (e.g., '少将', '中将', '上将')")
    date: Optional[str] = Field(
        None,
        description="Promotion date in YYYY or YYYY-MM-DD format"
    )
    unit: Optional[str] = Field(
        None,
        description="Military unit or organization at time of promotion"
    )

    @field_validator('date')
    @classmethod
    def validate_date_format(cls, v: Optional[str]) -> Optional[str]:
        """Validate date is in YYYY or YYYY-MM-DD format."""
        if v is None:
            return v

        # Check YYYY format
        if re.match(r'^\d{4}$', v):
            return v

        # Check YYYY-MM-DD format
        if re.match(r'^\d{4}-\d{2}-\d{2}$', v):
            # Validate it's a real date
            try:
                datetime.strptime(v, '%Y-%m-%d')
                return v
            except ValueError:
                raise ValueError(f"Invalid date: {v}")

        raise ValueError(f"Date must be in YYYY or YYYY-MM-DD format, got: {v}")

    @field_validator('rank')
    @classmethod
    def validate_rank_not_empty(cls, v: str) -> str:
        """Ensure rank is not empty."""
        if not v or not v.strip():
            raise ValueError("Rank cannot be empty")
        return v.strip()

    class Config:
        json_schema_extra = {
            "example": {
                "rank": "少将",
                "date": "1995",
                "unit": "南京军区"
            }
        }


class OfficerBio(BaseModel):
    """Comprehensive biographical model for PLA officers."""

    # Required fields
    name: str = Field(..., description="Chinese name of the officer")
    source_url: str = Field(..., description="Source URL of the biographical information")

    # Source metadata
    source_type: Optional[str] = Field(
        default="obituary",
        description="Type of source (obituary, news_article, wiki, etc.)"
    )

    # Optional identity fields
    pinyin_name: Optional[str] = Field(None, description="Romanized/Pinyin name")
    hometown: Optional[str] = Field(None, description="Hometown or birthplace")
    birth_date: Optional[str] = Field(None, description="Birth date (YYYY-MM-DD or YYYY)")

    # Military service dates
    enlistment_date: Optional[str] = Field(None, description="Date joined military")
    party_membership_date: Optional[str] = Field(
        None,
        description="Date joined Chinese Communist Party"
    )
    retirement_date: Optional[str] = Field(None, description="Retirement date (control variable)")
    death_date: Optional[str] = Field(None, description="Date of death if applicable")

    # Political participation
    congress_participation: Optional[List[str]] = Field(
        default=None,
        description="List of CCP National Congress participations (e.g., '第十五次全国代表大会')"
    )
    cppcc_participation: Optional[List[str]] = Field(
        default=None,
        description="List of CPPCC participations (e.g., '第十一届全国委员会委员')"
    )

    # Career information
    promotions: Optional[List[Promotion]] = Field(
        default=None,
        description="List of military rank promotions"
    )
    notable_positions: Optional[List[str]] = Field(
        default=None,
        description="List of notable military positions held"
    )
    awards: Optional[List[str]] = Field(
        default=None,
        description="Military awards and honors received"
    )

    # Control variables
    wife_name: Optional[str] = Field(
        None,
        description="Spouse name (control variable for family connections)"
    )

    # Extraction metadata
    confidence_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confidence score of extraction (0.0-1.0)"
    )
    extraction_notes: Optional[str] = Field(
        None,
        description="Agent's reasoning and notes about the extraction"
    )
    extracted_at: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp when data was extracted"
    )

    @field_validator('name')
    @classmethod
    def validate_name_not_empty(cls, v: str) -> str:
        """Ensure name is not empty."""
        if not v or not v.strip():
            raise ValueError("Name cannot be empty")
        return v.strip()

    @field_validator('source_url')
    @classmethod
    def validate_url_format(cls, v: str) -> str:
        """Basic URL validation."""
        if not v or not v.strip():
            raise ValueError("Source URL cannot be empty")
        if not (v.startswith('http://') or v.startswith('https://')):
            raise ValueError("Source URL must start with http:// or https://")
        return v.strip()

    @field_validator('birth_date', 'enlistment_date', 'party_membership_date',
                     'retirement_date', 'death_date')
    @classmethod
    def validate_date_fields(cls, v: Optional[str]) -> Optional[str]:
        """Validate date fields are in correct format."""
        if v is None:
            return v

        # Check YYYY format
        if re.match(r'^\d{4}$', v):
            return v

        # Check YYYY-MM-DD format
        if re.match(r'^\d{4}-\d{2}-\d{2}$', v):
            try:
                datetime.strptime(v, '%Y-%m-%d')
                return v
            except ValueError:
                raise ValueError(f"Invalid date: {v}")

        raise ValueError(f"Date must be in YYYY or YYYY-MM-DD format, got: {v}")

    @model_validator(mode='after')
    def validate_date_logic(self) -> 'OfficerBio':
        """Validate logical relationships between dates."""
        dates = {}

        # Parse dates for comparison
        for field_name in ['birth_date', 'enlistment_date', 'party_membership_date',
                          'retirement_date', 'death_date']:
            date_str = getattr(self, field_name)
            if date_str:
                # Extract year for comparison
                year = int(date_str[:4])
                dates[field_name] = year

        # Logical checks
        if 'birth_date' in dates and 'death_date' in dates:
            if dates['death_date'] < dates['birth_date']:
                raise ValueError("Death date cannot be before birth date")

        if 'birth_date' in dates and 'enlistment_date' in dates:
            if dates['enlistment_date'] < dates['birth_date']:
                raise ValueError("Enlistment date cannot be before birth date")

        if 'enlistment_date' in dates and 'party_membership_date' in dates:
            # Usually join party after enlisting, but not always strict
            pass

        if 'enlistment_date' in dates and 'retirement_date' in dates:
            if dates['retirement_date'] < dates['enlistment_date']:
                raise ValueError("Retirement date cannot be before enlistment date")

        return self

    def to_dict(self, exclude_none: bool = False) -> Dict[str, Any]:
        """
        Convert model to dictionary.

        Args:
            exclude_none: If True, exclude None values

        Returns:
            Dictionary representation
        """
        return self.model_dump(
            exclude_none=exclude_none,
            mode='json'
        )

    def to_json(self, exclude_none: bool = False, indent: int = 2) -> str:
        """
        Convert model to JSON string.

        Args:
            exclude_none: If True, exclude None values
            indent: JSON indentation level

        Returns:
            JSON string
        """
        import json
        return json.dumps(
            self.to_dict(exclude_none=exclude_none),
            ensure_ascii=False,
            indent=indent
        )

    class Config:
        json_schema_extra = {
            "example": {
                "name": "林炳尧",
                "pinyin_name": "Lin Bingyao",
                "hometown": "福建晋江",
                "birth_date": "1943",
                "enlistment_date": "1961",
                "party_membership_date": "1964",
                "death_date": "2025-08-18",
                "congress_participation": ["第十五次全国代表大会"],
                "cppcc_participation": ["第十一届全国委员会委员"],
                "promotions": [
                    {"rank": "少将", "date": "1995"},
                    {"rank": "中将", "date": "2002"}
                ],
                "notable_positions": ["原南京军区副司令员"],
                "source_url": "https://www.news.cn/20250901/example/c.html",
                "confidence_score": 0.95
            }
        }


class ToolResult(BaseModel):
    """Model for tracking individual tool execution results."""

    tool_name: str = Field(..., description="Name of the tool that was called")
    success: bool = Field(..., description="Whether the tool call succeeded")
    data: Optional[Dict[str, Any]] = Field(
        None,
        description="Data returned by the tool"
    )
    error: Optional[str] = Field(
        None,
        description="Error message if tool call failed"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="When the tool was called"
    )

    @model_validator(mode='after')
    def validate_error_on_failure(self) -> 'ToolResult':
        """Ensure error is provided when success is False."""
        if not self.success and not self.error:
            raise ValueError("Error message must be provided when success is False")
        return self

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return self.model_dump(mode='json')

    class Config:
        json_schema_extra = {
            "example": {
                "tool_name": "extract_text_from_url",
                "success": True,
                "data": {"text_length": 1234, "encoding": "utf-8"},
                "error": None,
                "timestamp": "2025-02-09T10:30:00"
            }
        }


class AgentExtractionResult(BaseModel):
    """Model for tracking overall agent extraction process and results."""

    # Extraction result
    officer_bio: Optional[OfficerBio] = Field(
        None,
        description="Extracted officer biography (None if extraction failed)"
    )

    # Tool usage tracking
    tool_calls: List[ToolResult] = Field(
        default_factory=list,
        description="List of all tool calls made during extraction"
    )

    # Performance metrics
    conversation_turns: int = Field(
        default=0,
        ge=0,
        description="Number of conversation turns with Claude"
    )
    total_input_tokens: int = Field(
        default=0,
        ge=0,
        description="Total input tokens used"
    )
    total_output_tokens: int = Field(
        default=0,
        ge=0,
        description="Total output tokens used"
    )

    # Overall status
    success: bool = Field(..., description="Whether extraction succeeded overall")
    error_message: Optional[str] = Field(
        None,
        description="Error message if extraction failed"
    )

    # Timestamp
    completed_at: datetime = Field(
        default_factory=datetime.now,
        description="When extraction was completed"
    )

    @model_validator(mode='after')
    def validate_success_consistency(self) -> 'AgentExtractionResult':
        """Validate consistency between success flag and data."""
        if self.success and not self.officer_bio:
            raise ValueError("Success is True but no officer_bio provided")
        if not self.success and not self.error_message:
            raise ValueError("Error message must be provided when success is False")
        return self

    def get_total_tokens(self) -> int:
        """Get total tokens used."""
        return self.total_input_tokens + self.total_output_tokens

    def get_success_rate(self) -> float:
        """Get success rate of tool calls."""
        if not self.tool_calls:
            return 0.0
        successful = sum(1 for tool in self.tool_calls if tool.success)
        return successful / len(self.tool_calls)

    def to_dict(self, exclude_none: bool = False) -> Dict[str, Any]:
        """
        Convert to dictionary.

        Args:
            exclude_none: If True, exclude None values

        Returns:
            Dictionary representation
        """
        return self.model_dump(
            exclude_none=exclude_none,
            mode='json'
        )

    def to_json(self, exclude_none: bool = False, indent: int = 2) -> str:
        """
        Convert to JSON string.

        Args:
            exclude_none: If True, exclude None values
            indent: JSON indentation level

        Returns:
            JSON string
        """
        import json
        return json.dumps(
            self.to_dict(exclude_none=exclude_none),
            ensure_ascii=False,
            indent=indent
        )

    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary statistics.

        Returns:
            Summary dictionary
        """
        return {
            "success": self.success,
            "officer_name": self.officer_bio.name if self.officer_bio else None,
            "total_tokens": self.get_total_tokens(),
            "conversation_turns": self.conversation_turns,
            "tool_calls_count": len(self.tool_calls),
            "tool_success_rate": self.get_success_rate(),
            "completed_at": self.completed_at.isoformat(),
        }

    class Config:
        json_schema_extra = {
            "example": {
                "officer_bio": {
                    "name": "林炳尧",
                    "source_url": "https://example.com",
                    "confidence_score": 0.95
                },
                "tool_calls": [
                    {
                        "tool_name": "extract_text_from_url",
                        "success": True,
                        "data": {"text_length": 1234}
                    }
                ],
                "conversation_turns": 3,
                "total_input_tokens": 1500,
                "total_output_tokens": 800,
                "success": True,
                "error_message": None
            }
        }
