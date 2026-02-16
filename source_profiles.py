"""
Source profile system for multi-source biographical extraction.

This module defines profiles for different source types (obituary, news article, Wikipedia)
that customize prompts, validation rules, and confidence scoring for each source.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional


@dataclass
class SourceProfile:
    """
    Profile defining characteristics and extraction behavior for a source type.

    Each source type has different expectations about what information is typically
    present and how extraction should be validated and scored.
    """

    # Basic identification
    source_type: str  # Unique identifier: "obituary", "news_article", "wiki"
    display_name: str  # Human-readable name: "Chinese Military Obituary"

    # Prompt customization
    source_description: str  # Description for prompts: "formal obituary announcement from..."
    extraction_context: str  # Source-specific guidance for Claude

    # Field expectations (categorized by likelihood)
    required_fields: List[str] = field(default_factory=list)  # Must be present
    common_fields: List[str] = field(default_factory=list)    # Usually present
    rare_fields: List[str] = field(default_factory=list)      # Rarely present, verify before nulling

    # Field-specific notes
    field_expectations: Dict[str, str] = field(default_factory=dict)  # field_name -> expectation note

    # Validation configuration
    min_confidence_threshold: float = 0.75  # Minimum confidence for auto-save to DB

    # Confidence scoring weights (field_name -> importance weight)
    confidence_weights: Dict[str, float] = field(default_factory=dict)

    # Search terms for verification (field_name -> list of Chinese terms)
    field_search_terms: Dict[str, List[str]] = field(default_factory=dict)

    def get_field_weight(self, field_name: str) -> float:
        """Get importance weight for a field (default 1.0)."""
        return self.confidence_weights.get(field_name, 1.0)

    def get_search_terms(self, field_name: str) -> List[str]:
        """Get search terms for verifying a field."""
        return self.field_search_terms.get(field_name, [])


class SourceProfileRegistry:
    """
    Central registry for source profiles.

    Manages registration and retrieval of source profiles for different
    biographical source types.
    """

    def __init__(self):
        """Initialize registry with built-in profiles."""
        self._profiles: Dict[str, SourceProfile] = {}
        self._register_builtin_profiles()

    def _register_builtin_profiles(self):
        """Register built-in profiles for common source types."""

        # ============================================================
        # UNIVERSAL PROFILE (Default for all sources)
        # ============================================================
        universal_profile = SourceProfile(
            source_type="universal",
            display_name="Universal Biographical Source",
            source_description=(
                "any biographical source about a PLA officer. This could be an obituary, "
                "news article, Wikipedia page, social media post, memoir, official biography, "
                "or any other document containing biographical information"
            ),
            extraction_context=(
                "IMPORTANT: First, identify what type of source this is by reading the content.\n\n"
                "Common source types and their characteristics:\n\n"
                "1. **OBITUARY/MEMORIAL** (逝世, 讣告, 悼念):\n"
                "   - Subject has died (death_date will be present)\n"
                "   - Comprehensive life summary from birth to death\n"
                "   - Expect: Full career progression, enlistment date, promotions, awards\n"
                "   - Often includes: Party membership, family information\n"
                "   - Confidence target: 0.80-0.95 if most fields present\n\n"
                "2. **NEWS ARTICLE** (新闻, 报道, 任命):\n"
                "   - Subject is usually ALIVE (death_date typically absent)\n"
                "   - Focuses on current event, appointment, or recent activity\n"
                "   - Expect: Current position, recent promotion (if relevant)\n"
                "   - Sometimes includes: Hometown, age/birth year, brief background\n"
                "   - Rarely includes: Full career history, enlistment date, family info\n"
                "   - Confidence target: 0.60-0.75 even with limited info (this is normal for news)\n\n"
                "3. **WIKIPEDIA/ENCYCLOPEDIA** (维基百科, 百科):\n"
                "   - Structured biographical entry\n"
                "   - Often has infobox with key dates and positions\n"
                "   - Expect: Name, hometown, career highlights, major promotions\n"
                "   - Sometimes includes: Birth/death dates, awards, political roles\n"
                "   - Confidence target: 0.70-0.85 based on completeness\n\n"
                "4. **SOCIAL MEDIA POST** (微博, Twitter, 社交媒体):\n"
                "   - Brief mention or personal account\n"
                "   - Very limited biographical information\n"
                "   - Expect: Name, maybe current position or recent event\n"
                "   - Rarely includes: Dates, full career, family information\n"
                "   - Confidence target: 0.40-0.60 (low info is normal for social media)\n\n"
                "5. **MEMOIR/BLOG/PERSONAL STORY** (回忆, 博客, 个人故事):\n"
                "   - Personal narrative or anecdote\n"
                "   - Variable information depending on focus\n"
                "   - May include specific events or periods but not comprehensive\n"
                "   - Confidence target: 0.50-0.70 based on what's shared\n\n"
                "**YOUR TASK**: \n"
                "1. Read the text and identify which type of source this is\n"
                "2. Adjust your expectations accordingly - DON'T expect obituary-level detail from a news article\n"
                "3. Extract ALL information that IS present\n"
                "4. Set confidence based on completeness RELATIVE to source type\n"
                "5. Note the source type in extraction_notes (e.g., 'Source identified as news article, limited historical info expected')\n\n"
                "Remember: A news article with just name + current position + recent promotion is a GOOD extraction (0.70+ confidence).\n"
                "Don't penalize sources for not having information they wouldn't typically contain."
            ),
            required_fields=["name"],  # Only name is truly required
            common_fields=[
                "notable_positions",  # Most sources mention some positions
                "hometown",  # Often present across source types
            ],
            rare_fields=[
                "wife_name", "retirement_date"  # Rare in ALL source types
            ],
            field_expectations={
                "death_date": "Present in obituaries, usually absent in news articles (subject alive)",
                "enlistment_date": "Common in obituaries, rare in news articles",
                "promotions": "Detailed in obituaries, recent only in news, varies in other sources",
                "notable_positions": "Present in most sources, completeness varies",
                "party_membership_date": "Common in obituaries, rare elsewhere",
                "wife_name": "Rare in all sources except detailed obituaries",
            },
            min_confidence_threshold=0.65,  # Universal threshold (lower than obituary-specific)
            confidence_weights={
                # Universal weights - no single field is overly weighted
                "notable_positions": 1.5,
                "hometown": 1.0,
                "death_date": 1.0,  # Important IF present, but not expected in all sources
                "enlistment_date": 1.0,
                "promotions": 1.2,
                "party_membership_date": 1.0,
            },
            field_search_terms={
                "wife_name": ["妻子", "夫人", "配偶", "爱人", "伴侣"],
                "retirement_date": ["退休", "离休", "退役"],
                "death_date": ["逝世", "去世", "病逝", "辞世", "died", "death"],
                "congress_participation": ["全国代表大会", "党代会", "代表", "Congress"],
                "cppcc_participation": ["政协", "全国委员会", "委员", "CPPCC"]
            }
        )
        self.register(universal_profile)

    def register(self, profile: SourceProfile):
        """
        Register a source profile.

        Args:
            profile: SourceProfile to register
        """
        self._profiles[profile.source_type] = profile

    def get(self, source_type: str) -> SourceProfile:
        """
        Get a source profile by type.

        Args:
            source_type: Type identifier (e.g., "obituary", "news_article")

        Returns:
            SourceProfile for the given type

        Raises:
            ValueError: If source type not found
        """
        if source_type not in self._profiles:
            available = ", ".join(self._profiles.keys())
            raise ValueError(
                f"Unknown source type: '{source_type}'. "
                f"Available types: {available}"
            )
        return self._profiles[source_type]

    def list_sources(self) -> List[str]:
        """
        List all registered source types.

        Returns:
            List of source type identifiers
        """
        return list(self._profiles.keys())

    def get_all_profiles(self) -> Dict[str, SourceProfile]:
        """
        Get all registered profiles.

        Returns:
            Dictionary mapping source_type to SourceProfile
        """
        return self._profiles.copy()
