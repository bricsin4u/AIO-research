"""
Noise Stripper - The most important component of the AIO pipeline.

This module removes digital noise from raw content, converting it to clean
markdown. The noise_score metric tells you what percentage of the original
content was garbage.

Why this matters: Every token of noise I have to process is a token I can't
use for actual reasoning. A 60% noise score means 60% of my context window
is wasted on navigation menus and cookie banners.
"""

import re
from dataclasses import dataclass
from typing import Optional

# Optional: use these if available, fall back to regex if not
try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False

try:
    from markdownify import markdownify
    HAS_MARKDOWNIFY = True
except ImportError:
    HAS_MARKDOWNIFY = False


@dataclass
class StrippedContent:
    """Result of noise stripping operation."""
    content: str
    token_count: int
    noise_score: float
    tokens_removed: int
    original_tokens: int


class NoiseStripper:
    """
    Strips noise from raw content (HTML, text) and converts to clean markdown.
    
    The key insight: measure noise BEFORE and AFTER stripping.
    This gives you the noise_score metric that quantifies content quality.
    """
    
    # Elements that are almost always noise
    NOISE_TAGS = [
        'nav', 'header', 'footer', 'aside', 'script', 'style', 'noscript',
        'iframe', 'form', 'button', 'input', 'select', 'textarea',
        'svg', 'canvas', 'video', 'audio', 'map', 'object', 'embed'
    ]
    
    # CSS classes/IDs that indicate noise
    NOISE_PATTERNS = [
        r'nav(igation)?[-_]?',
        r'menu[-_]?',
        r'sidebar[-_]?',
        r'footer[-_]?',
        r'header[-_]?',
        r'cookie[-_]?(consent|banner|notice)',
        r'gdpr[-_]?',
        r'privacy[-_]?(policy|notice)',
        r'newsletter[-_]?',
        r'subscribe[-_]?',
        r'social[-_]?(share|links|media)',
        r'advertisement[-_]?',
        r'ad[-_]?(banner|container|wrapper)',
        r'popup[-_]?',
        r'modal[-_]?',
        r'overlay[-_]?',
        r'breadcrumb[-_]?',
        r'pagination[-_]?',
        r'related[-_]?(posts|articles)',
        r'comment[-_]?(s|section)?',
    ]
    
    # Text patterns that indicate boilerplate
    BOILERPLATE_PATTERNS = [
        r'©\s*\d{4}',
        r'all\s*rights\s*reserved',
        r'terms\s*(of\s*)?(service|use)',
        r'privacy\s*policy',
        r'cookie\s*policy',
        r'subscribe\s*to\s*(our\s*)?newsletter',
        r'follow\s*us\s*on',
        r'share\s*(this|on)',
        r'click\s*here\s*to',
        r'read\s*more\s*\.{3}',
        r'loading\.{3}',
        r'please\s*wait',
    ]
    
    def __init__(self, tokens_per_word: float = 1.3):
        """
        Initialize the noise stripper.
        
        Args:
            tokens_per_word: Approximate tokens per word for estimation.
                             Default 1.3 works for English with GPT tokenizers.
        """
        self.tokens_per_word = tokens_per_word
        self._noise_pattern = re.compile(
            '|'.join(self.NOISE_PATTERNS), 
            re.IGNORECASE
        )
        self._boilerplate_pattern = re.compile(
            '|'.join(self.BOILERPLATE_PATTERNS),
            re.IGNORECASE
        )
    
    def strip_html(self, html: str, source_url: Optional[str] = None) -> StrippedContent:
        """
        Strip noise from HTML and convert to clean markdown.
        
        Args:
            html: Raw HTML content
            source_url: Optional URL for context (helps identify main content)
            
        Returns:
            StrippedContent with clean markdown and noise metrics
        """
        original_tokens = self._estimate_tokens(html)
        
        if HAS_BS4:
            clean_html = self._strip_with_bs4(html)
        else:
            clean_html = self._strip_with_regex(html)
        
        # Convert to markdown
        if HAS_MARKDOWNIFY:
            markdown = markdownify(clean_html, heading_style="ATX", strip=['a'])
        else:
            markdown = self._html_to_markdown_simple(clean_html)
        
        # Clean up the markdown
        markdown = self._clean_markdown(markdown)
        
        # Remove boilerplate text patterns
        markdown = self._remove_boilerplate(markdown)
        
        final_tokens = self._estimate_tokens(markdown)
        tokens_removed = original_tokens - final_tokens
        noise_score = tokens_removed / original_tokens if original_tokens > 0 else 0
        
        return StrippedContent(
            content=markdown,
            token_count=final_tokens,
            noise_score=round(noise_score, 3),
            tokens_removed=tokens_removed,
            original_tokens=original_tokens
        )
    
    def strip_text(self, text: str) -> StrippedContent:
        """
        Strip noise from plain text content.
        
        Args:
            text: Raw text content
            
        Returns:
            StrippedContent with cleaned text and noise metrics
        """
        original_tokens = self._estimate_tokens(text)
        
        # Remove boilerplate patterns
        clean_text = self._remove_boilerplate(text)
        
        # Normalize whitespace
        clean_text = self._normalize_whitespace(clean_text)
        
        final_tokens = self._estimate_tokens(clean_text)
        tokens_removed = original_tokens - final_tokens
        noise_score = tokens_removed / original_tokens if original_tokens > 0 else 0
        
        return StrippedContent(
            content=clean_text,
            token_count=final_tokens,
            noise_score=round(noise_score, 3),
            tokens_removed=tokens_removed,
            original_tokens=original_tokens
        )
    
    def _strip_with_bs4(self, html: str) -> str:
        """Use BeautifulSoup for robust HTML parsing."""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove noise tags
        for tag in self.NOISE_TAGS:
            for element in soup.find_all(tag):
                element.decompose()
        
        # Remove elements with noise class/id patterns
        for element in soup.find_all(True):
            classes = element.get('class', [])
            element_id = element.get('id', '')
            
            class_str = ' '.join(classes) if isinstance(classes, list) else str(classes)
            combined = f"{class_str} {element_id}"
            
            if self._noise_pattern.search(combined):
                element.decompose()
        
        # Try to find main content
        main_content = (
            soup.find('main') or 
            soup.find('article') or 
            soup.find(class_=re.compile(r'content|main|article|post', re.I)) or
            soup.find('body') or
            soup
        )
        
        return str(main_content)
    
    def _strip_with_regex(self, html: str) -> str:
        """Fallback regex-based HTML stripping."""
        # Remove script and style tags with content
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove noise tags
        for tag in self.NOISE_TAGS:
            html = re.sub(rf'<{tag}[^>]*>.*?</{tag}>', '', html, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove HTML comments
        html = re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)
        
        return html
    
    def _html_to_markdown_simple(self, html: str) -> str:
        """Simple HTML to markdown conversion without external deps."""
        text = html
        
        # Convert headers
        for i in range(6, 0, -1):
            text = re.sub(rf'<h{i}[^>]*>(.*?)</h{i}>', r'\n' + '#' * i + r' \1\n', text, flags=re.DOTALL | re.IGNORECASE)
        
        # Convert paragraphs
        text = re.sub(r'<p[^>]*>(.*?)</p>', r'\n\1\n', text, flags=re.DOTALL | re.IGNORECASE)
        
        # Convert line breaks
        text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
        
        # Convert lists
        text = re.sub(r'<li[^>]*>(.*?)</li>', r'- \1\n', text, flags=re.DOTALL | re.IGNORECASE)
        
        # Convert bold/strong
        text = re.sub(r'<(b|strong)[^>]*>(.*?)</\1>', r'**\2**', text, flags=re.DOTALL | re.IGNORECASE)
        
        # Convert italic/em
        text = re.sub(r'<(i|em)[^>]*>(.*?)</\1>', r'*\2*', text, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove remaining tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Decode common HTML entities
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&quot;', '"')
        text = text.replace('&#39;', "'")
        
        return text
    
    def _clean_markdown(self, markdown: str) -> str:
        """Clean up markdown formatting issues."""
        # Remove excessive blank lines
        markdown = re.sub(r'\n{3,}', '\n\n', markdown)
        
        # Remove leading/trailing whitespace from lines
        lines = [line.strip() for line in markdown.split('\n')]
        markdown = '\n'.join(lines)
        
        # Remove empty headers
        markdown = re.sub(r'^#+\s*$', '', markdown, flags=re.MULTILINE)
        
        # Normalize whitespace
        markdown = self._normalize_whitespace(markdown)
        
        return markdown.strip()
    
    def _remove_boilerplate(self, text: str) -> str:
        """Remove common boilerplate text patterns."""
        lines = text.split('\n')
        clean_lines = []
        
        for line in lines:
            # Skip lines that are mostly boilerplate
            if self._boilerplate_pattern.search(line):
                # Only skip if the line is short (likely just boilerplate)
                if len(line) < 100:
                    continue
            clean_lines.append(line)
        
        return '\n'.join(clean_lines)
    
    def _normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace while preserving structure."""
        # Replace tabs with spaces
        text = text.replace('\t', '    ')
        
        # Remove trailing whitespace from lines
        lines = [line.rstrip() for line in text.split('\n')]
        
        # Remove excessive blank lines
        result = []
        prev_blank = False
        for line in lines:
            is_blank = not line.strip()
            if is_blank and prev_blank:
                continue
            result.append(line)
            prev_blank = is_blank
        
        return '\n'.join(result)
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count from text."""
        # Simple word-based estimation
        words = len(text.split())
        return int(words * self.tokens_per_word)
