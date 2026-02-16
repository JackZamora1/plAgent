#!/usr/bin/env python3
"""
Generic source content fetching utilities.

This module provides unified content fetching across different source types:
- Xinhua news articles (obituaries, news)
- Wikipedia articles
- Generic HTML pages

Consolidates earlier source-specific fetch logic into one module.
"""
import sys
import logging
import requests
from bs4 import BeautifulSoup
from pathlib import Path
from rich.console import Console
from typing import Optional

console = Console()
logger = logging.getLogger(__name__)


def detect_source_type(url: str) -> str:
    """
    Automatically detect source type from URL.

    Args:
        url: Source URL

    Returns:
        Detected source type: "obituary", "news_article", or "wiki"

    Examples:
        >>> detect_source_type("https://zh.wikipedia.org/wiki/林炳尧")
        "wiki"
        >>> detect_source_type("https://news.cn/mil/2025/obituary.htm")
        "obituary"
        >>> detect_source_type("https://news.cn/mil/2025/appointment.htm")
        "news_article"
    """
    url_lower = url.lower()

    # Wikipedia detection (highest priority - most specific)
    if "wikipedia.org" in url_lower:
        return "wiki"

    # Obituary keywords in URL
    obituary_keywords = ["obituary", "逝世", "讣告", "悼念"]
    if any(keyword in url_lower for keyword in obituary_keywords):
        return "obituary"

    # Default to news_article for news domains
    news_domains = ["news.cn", "xinhuanet.com", "81.cn", "chinamil.cn", "mod.gov.cn"]
    if any(domain in url_lower for domain in news_domains):
        return "news_article"

    # Default fallback
    return "news_article"


def fetch_source_content(url: str) -> str:
    """
    Fetch content from URL with source-aware parsing.

    This is the main entry point for fetching biographical source text.
    Automatically detects the source domain and applies appropriate extraction.

    Args:
        url: Source URL
    Returns:
        Cleaned text content

    Raises:
        requests.RequestException: If request fails
        ValueError: If content cannot be extracted
    """
    logger.debug(f"fetch_source_content called with URL: {url}")
    detected_source_type = detect_source_type(url)

    logger.debug(f"Detected source type: {detected_source_type}")
    console.print(f"[bold cyan]Fetching {detected_source_type} from:[/bold cyan] {url}")

    # Detect domain and route to appropriate fetcher
    if "news.cn" in url or "xinhuanet.com" in url or "81.cn" in url:
        logger.debug("Routing to fetch_xinhua_article()")
        content = fetch_xinhua_article(url)
    elif "wikipedia.org" in url:
        logger.debug("Routing to fetch_wikipedia_article()")
        content = fetch_wikipedia_article(url)
    else:
        # Generic fallback for other sources
        logger.debug("Routing to fetch_generic_html()")
        content = fetch_generic_html(url)

    logger.debug(f"Fetched content length: {len(content)} chars")
    logger.debug(f"First 100 chars: {content[:100]}...")

    return content


def fetch_xinhua_article(url: str) -> str:
    """
    Fetch and extract article text from Xinhua-style news sources.

    Works with:
    - news.cn (Xinhua News Agency)
    - xinhuanet.com (Xinhua Net)
    - 81.cn (PLA Daily)

    Args:
        url: Xinhua news article URL

    Returns:
        Extracted article text

    Raises:
        requests.RequestException: If request fails
        ValueError: If article content cannot be found
    """
    # Set headers to mimic a browser
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        logger.debug(f"Sending GET request to: {url}")

        # Fetch the webpage
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        # Auto-detect encoding if needed
        response.encoding = response.apparent_encoding

        logger.debug(f"Response status: {response.status_code}")
        logger.debug(f"Response encoding: {response.encoding}")
        logger.debug(f"Response content length: {len(response.text)} chars")

        console.print("[bold green]✓ Page fetched successfully[/bold green]")

        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')

        # Try common Xinhua/Chinese news article content selectors
        article_text = None

        selectors = [
            '#detail',                      # Common detail div
            '.article',                     # Article class
            '.content',                     # Content class
            'article',                      # HTML5 article tag
            '#content',                     # Content ID
            '.detail-content',              # Detail content class
            'div[class*="article"]',        # Any div with "article" in class
            'div[class*="content"]',        # Any div with "content" in class
        ]

        for selector in selectors:
            content = soup.select_one(selector)
            if content:
                console.print(f"[bold green]✓ Found content using selector:[/bold green] {selector}")

                # Extract all paragraphs
                paragraphs = content.find_all(['p', 'div'], recursive=True)

                # Filter and clean paragraphs
                text_parts = []
                for p in paragraphs:
                    text = p.get_text(strip=True)
                    # Skip empty paragraphs and navigation/metadata
                    if (text and len(text) > 10 and
                        not text.startswith('来源:') and
                        not text.startswith('编辑:') and
                        not text.startswith('责任编辑:')):
                        text_parts.append(text)

                article_text = '\n\n'.join(text_parts)
                break

        # Fallback: If no specific selector works, try getting all paragraphs
        if not article_text:
            console.print("[yellow]⚠ Using fallback extraction method[/yellow]")
            paragraphs = soup.find_all('p')
            text_parts = []
            for p in paragraphs:
                text = p.get_text(strip=True)
                if text and len(text) > 20:
                    text_parts.append(text)
            article_text = '\n\n'.join(text_parts)

        if not article_text:
            raise ValueError("Could not extract article content from the page")

        console.print(f"[bold green]✓ Extracted {len(article_text)} characters[/bold green]")
        return article_text

    except requests.Timeout:
        console.print("[bold red]✗ Request timed out[/bold red]")
        raise
    except requests.ConnectionError:
        console.print("[bold red]✗ Connection error - check your internet connection[/bold red]")
        raise
    except requests.HTTPError as e:
        console.print(f"[bold red]✗ HTTP error: {e.response.status_code}[/bold red]")
        raise
    except Exception as e:
        console.print(f"[bold red]✗ Error: {e}[/bold red]")
        raise


def fetch_wikipedia_article(url: str) -> str:
    """
    Fetch and extract article text from Wikipedia.

    Extracts both the main content and infobox data from Wikipedia articles.
    Works with both Chinese and English Wikipedia.

    Args:
        url: Wikipedia article URL

    Returns:
        Extracted article text including infobox data

    Raises:
        requests.RequestException: If request fails
        ValueError: If article content cannot be found
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        response.encoding = response.apparent_encoding

        console.print("[bold green]✓ Wikipedia page fetched[/bold green]")

        soup = BeautifulSoup(response.text, 'html.parser')

        text_parts = []

        # Extract infobox first (structured data)
        infobox = soup.select_one('.infobox')
        if infobox:
            console.print("[bold green]✓ Found infobox[/bold green]")
            infobox_text = infobox.get_text(separator='\n', strip=True)
            text_parts.append("=== Infobox ===")
            text_parts.append(infobox_text)
            text_parts.append("")

        # Extract main content
        content = soup.select_one('#mw-content-text')
        if content:
            console.print("[bold green]✓ Found main content[/bold green]")

            # Remove navigation boxes, references, etc.
            for unwanted in content.select('.navbox, .reflist, .reference, .mw-editsection'):
                unwanted.decompose()

            # Extract paragraphs
            paragraphs = content.find_all(['p', 'li'])
            for p in paragraphs:
                text = p.get_text(strip=True)
                if text and len(text) > 20:
                    text_parts.append(text)

        if not text_parts:
            raise ValueError("Could not extract Wikipedia content")

        article_text = '\n\n'.join(text_parts)
        console.print(f"[bold green]✓ Extracted {len(article_text)} characters[/bold green]")
        return article_text

    except Exception as e:
        console.print(f"[bold red]✗ Error fetching Wikipedia: {e}[/bold red]")
        raise


def fetch_generic_html(url: str) -> str:
    """
    Generic HTML text extraction as fallback.

    Uses simple heuristics to extract main content from any HTML page.
    Less reliable than domain-specific extractors but works as fallback.

    Args:
        url: URL to fetch

    Returns:
        Extracted text content

    Raises:
        requests.RequestException: If request fails
        ValueError: If no content could be extracted
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        console.print("[yellow]⚠ Using generic HTML extractor[/yellow]")

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        response.encoding = response.apparent_encoding

        soup = BeautifulSoup(response.text, 'html.parser')

        # Remove script, style, nav, footer
        for element in soup(['script', 'style', 'nav', 'footer', 'header']):
            element.decompose()

        # Try to find main content area
        main_content = soup.find('main') or soup.find('article') or soup.find('body')

        if main_content:
            # Extract all text blocks
            paragraphs = main_content.find_all(['p', 'div', 'li', 'span'])
            text_parts = []

            for p in paragraphs:
                text = p.get_text(strip=True)
                if text and len(text) > 30:  # Higher threshold for generic extraction
                    text_parts.append(text)

            if text_parts:
                article_text = '\n\n'.join(text_parts)
                console.print(f"[bold green]✓ Extracted {len(article_text)} characters[/bold green]")
                return article_text

        raise ValueError("Could not extract meaningful content from page")

    except Exception as e:
        console.print(f"[bold red]✗ Generic extraction failed: {e}[/bold red]")
        raise


def save_to_file(text: str, output_path: Path) -> None:
    """
    Save text to file with UTF-8 encoding.

    Args:
        text: Text to save
        output_path: Path to output file
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(text)

    console.print(f"[bold green]✓ Saved to:[/bold green] {output_path}")


def main():
    """Main function for CLI usage."""
    if len(sys.argv) < 2:
        console.print("[bold red]Usage: python fetch_source.py <url>[/bold red]")
        console.print("\nExample:")
        console.print("  python fetch_source.py https://www.news.cn/...")
        console.print("  python fetch_source.py https://zh.wikipedia.org/...")
        sys.exit(1)

    url = sys.argv[1]

    # Output file path
    script_dir = Path(__file__).parent
    output_file = script_dir / 'data' / f"test_{detect_source_type(url)}.txt"

    try:
        # Fetch content
        content = fetch_source_content(url)

        # Save to file
        save_to_file(content, output_file)

        # Print preview
        preview = content[:200]
        console.print("\n[bold cyan]Preview (first 200 characters):[/bold cyan]")
        console.print(f"[dim]{preview}[/dim]")

        console.print(f"\n[bold green]✓ Complete! Total characters: {len(content)}[/bold green]")

    except KeyboardInterrupt:
        console.print("\n[bold yellow]⚠ Interrupted by user[/bold yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[bold red]✗ Failed to fetch content: {e}[/bold red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
