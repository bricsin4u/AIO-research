"""
HTML Fallback Scraper - ECR pipeline for non-AIO sites.

When a site doesn't have AIO content, this module:
1. Fetches HTML content
2. Strips navigation, ads, boilerplate
3. Extracts main content
4. Calculates noise metrics
"""

import re
from typing import Tuple, Optional
import requests
from bs4 import BeautifulSoup, Comment


class HTMLScraper:
    """
    Fallback scraper for sites without AIO support.
    Implements basic noise stripping per ECR specification.
    """
    
    # Tags to remove completely (navigation, ads, etc.)
    NOISE_TAGS = [
        'nav', 'header', 'footer', 'aside', 'script', 'style', 'noscript',
        'iframe', 'form', 'button', 'input', 'select', 'textarea',
        'svg', 'canvas', 'video', 'audio', 'map', 'object', 'embed'
    ]
    
    # Class names that typically indicate noise
    NOISE_CLASSES = [
        'nav', 'navigation', 'menu', 'sidebar', 'footer', 'header',
        'cookie', 'banner', 'ad', 'advertisement', 'promo', 'popup',
        'modal', 'overlay', 'social', 'share', 'comment', 'related',
        'widget', 'newsletter', 'subscribe'
    ]
    
    # ID patterns that indicate noise
    NOISE_IDS = [
        'nav', 'menu', 'sidebar', 'footer', 'header', 'cookie',
        'banner', 'ad', 'popup', 'modal', 'overlay'
    ]
    
    def __init__(self, timeout: int = 10, user_agent: str = None):
        self.timeout = timeout
        self.user_agent = user_agent or "AIOParser/0.1 (ECR-Compatible)"
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.user_agent})
    
    def scrape(self, url: str) -> Tuple[str, int, int]:
        """
        Scrape and clean HTML content.
        
        Args:
            url: URL to scrape
            
        Returns:
            Tuple of (cleaned_content, original_size, cleaned_size)
        """
        try:
            response = self.session.get(url, timeout=self.timeout)
            if response.status_code != 200:
                return "", 0, 0
            
            html = response.text
            original_size = len(html)
            
            # Clean and extract content
            cleaned = self._clean_html(html)
            cleaned_size = len(cleaned)
            
            return cleaned, original_size, cleaned_size
            
        except requests.RequestException:
            return "", 0, 0
    
    def _clean_html(self, html: str) -> str:
        """
        Remove noise and extract main content.
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove comments
        for comment in soup.find_all(string=lambda t: isinstance(t, Comment)):
            comment.extract()
        
        # Remove noise tags
        for tag in self.NOISE_TAGS:
            for element in soup.find_all(tag):
                element.decompose()
        
        # Remove elements with noise classes
        for element in soup.find_all(class_=self._is_noise_class):
            element.decompose()
        
        # Remove elements with noise IDs
        for element in soup.find_all(id=self._is_noise_id):
            element.decompose()
        
        # Try to find main content area
        main_content = self._find_main_content(soup)
        
        if main_content:
            text = self._extract_text(main_content)
        else:
            # Fallback to body
            body = soup.find('body')
            text = self._extract_text(body) if body else ""
        
        # Clean up whitespace
        text = self._clean_whitespace(text)
        
        return text
    
    def _is_noise_class(self, class_list):
        """Check if any class indicates noise."""
        if not class_list:
            return False
        if isinstance(class_list, str):
            class_list = [class_list]
        for cls in class_list:
            cls_lower = cls.lower()
            for noise in self.NOISE_CLASSES:
                if noise in cls_lower:
                    return True
        return False
    
    def _is_noise_id(self, id_value):
        """Check if ID indicates noise."""
        if not id_value:
            return False
        id_lower = id_value.lower()
        for noise in self.NOISE_IDS:
            if noise in id_lower:
                return True
        return False
    
    def _find_main_content(self, soup: BeautifulSoup) -> Optional[BeautifulSoup]:
        """
        Try to identify the main content area.
        """
        # Priority order for main content detection
        selectors = [
            ('main', {}),
            ('article', {}),
            ('div', {'role': 'main'}),
            ('div', {'id': re.compile(r'main|content|article', re.I)}),
            ('div', {'class': re.compile(r'main|content|article|post', re.I)}),
        ]
        
        for tag, attrs in selectors:
            element = soup.find(tag, attrs)
            if element:
                return element
        
        return None
    
    def _extract_text(self, element: BeautifulSoup) -> str:
        """
        Extract text with basic formatting preserved.
        """
        if not element:
            return ""
        
        lines = []
        
        for child in element.descendants:
            if child.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                level = int(child.name[1])
                prefix = '#' * level
                lines.append(f"\n{prefix} {child.get_text(strip=True)}\n")
            elif child.name == 'p':
                text = child.get_text(strip=True)
                if text:
                    lines.append(f"\n{text}\n")
            elif child.name == 'li':
                text = child.get_text(strip=True)
                if text:
                    lines.append(f"- {text}")
            elif child.name == 'br':
                lines.append("\n")
            elif child.name == 'table':
                lines.append(self._extract_table(child))
        
        return '\n'.join(lines)
    
    def _extract_table(self, table: BeautifulSoup) -> str:
        """Extract table as markdown."""
        rows = []
        for tr in table.find_all('tr'):
            cells = []
            for td in tr.find_all(['td', 'th']):
                cells.append(td.get_text(strip=True))
            if cells:
                rows.append('| ' + ' | '.join(cells) + ' |')
        
        if len(rows) >= 1:
            # Add header separator
            header = rows[0]
            cols = header.count('|') - 1
            separator = '|' + '---|' * cols
            rows.insert(1, separator)
        
        return '\n'.join(rows)
    
    def _clean_whitespace(self, text: str) -> str:
        """Normalize whitespace."""
        # Remove multiple blank lines
        text = re.sub(r'\n{3,}', '\n\n', text)
        # Remove leading/trailing whitespace per line
        lines = [line.strip() for line in text.split('\n')]
        # Remove empty lines at start/end
        while lines and not lines[0]:
            lines.pop(0)
        while lines and not lines[-1]:
            lines.pop()
        return '\n'.join(lines)


def scrape_html(url: str, timeout: int = 10) -> Tuple[str, int, int]:
    """Convenience function for HTML scraping."""
    scraper = HTMLScraper(timeout=timeout)
    return scraper.scrape(url)
