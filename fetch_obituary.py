#!/usr/bin/env python3
"""
Fetch obituary text from Xinhua news articles.

DEPRECATED: This module is deprecated. Use fetch_source.py instead for
generic source fetching that works with multiple source types.

This module is kept for backward compatibility but will be removed in a future version.
"""
import sys
import warnings
import requests
from bs4 import BeautifulSoup
from pathlib import Path
from rich.console import Console
from rich.panel import Panel

# Issue deprecation warning
warnings.warn(
    "fetch_obituary module is deprecated. Use fetch_source.fetch_xinhua_article() instead.",
    DeprecationWarning,
    stacklevel=2
)

console = Console()


def fetch_xinhua_article(url: str) -> str:
    """
    Fetch and extract article text from Xinhua news URL.

    Args:
        url: Xinhua news article URL

    Returns:
        Extracted article text

    Raises:
        requests.RequestException: If request fails
        ValueError: If article content cannot be found
    """
    console.print(f"[bold cyan]Fetching article from:[/bold cyan] {url}")

    # Set headers to mimic a browser
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        # Fetch the webpage
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        # Auto-detect encoding if needed
        response.encoding = response.apparent_encoding

        console.print("[bold green]✓ Page fetched successfully[/bold green]")

        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')

        # Xinhua articles typically use these structures
        # Try multiple selectors to find the main content
        article_text = None

        # Try common Xinhua article content selectors
        selectors = [
            '#detail',  # Common detail div
            '.article',  # Article class
            '.content',  # Content class
            'article',  # HTML5 article tag
            '#content',  # Content ID
            '.detail-content',  # Detail content class
            'div[class*="article"]',  # Any div with "article" in class
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
                    if text and len(text) > 10 and not text.startswith('来源:') and not text.startswith('编辑:'):
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
    """Main function."""
    if len(sys.argv) < 2:
        console.print("[bold red]Usage: python fetch_obituary.py <url>[/bold red]")
        console.print("\nExample:")
        console.print("  python fetch_obituary.py https://www.news.cn/20250901/45e0f3a29d2e4b1ba12bbff08c5aec82/c.html")
        sys.exit(1)

    url = sys.argv[1]

    # Output file path
    script_dir = Path(__file__).parent
    output_file = script_dir / 'data' / 'test_obituary.txt'

    try:
        # Fetch article
        article_text = fetch_xinhua_article(url)

        # Save to file
        save_to_file(article_text, output_file)

        # Print preview
        preview = article_text[:200]
        console.print("\n[bold cyan]Preview (first 200 characters):[/bold cyan]")
        console.print(Panel(preview, title="Article Preview", border_style="cyan"))

        console.print(f"\n[bold green]✓ Complete! Total characters: {len(article_text)}[/bold green]")

    except KeyboardInterrupt:
        console.print("\n[bold yellow]⚠ Interrupted by user[/bold yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[bold red]✗ Failed to fetch obituary: {e}[/bold red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
