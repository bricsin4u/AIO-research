"""
Noise Stripper - Core utility for removing environmental noise from HCA content.
Part of the Entropy-Controlled Retrieval (ECR) pipeline.
"""

import re
from typing import Tuple, Optional
from bs4 import BeautifulSoup, Comment

class NoiseStripper:
    """
    Implements deterministic noise stripping for HCA content.
    Removes navigation, ads, and boilerplate while preserving semantic structure.
    """
    
    NOISE_TAGS = [
        'nav', 'header', 'footer', 'aside', 'script', 'style', 'noscript',
        'iframe', 'form', 'button', 'input', 'select', 'textarea',
        'svg', 'canvas', 'video', 'audio', 'map', 'object', 'embed'
    ]
    
    NOISE_CLASSES = [
        'nav', 'navigation', 'menu', 'sidebar', 'footer', 'header',
        'cookie', 'banner', 'ad', 'advertisement', 'promo', 'popup',
        'modal', 'overlay', 'social', 'share', 'comment', 'related',
        'widget', 'newsletter', 'subscribe'
    ]
    
    NOISE_IDS = [
        'nav', 'menu', 'sidebar', 'footer', 'header', 'cookie',
        'banner', 'ad', 'popup', 'modal', 'overlay'
    ]

    def strip(self, html: str) -> str:
        """
        Transforms noisy HTML into clean narrative text.
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove comments
        for comment in soup.find_all(string=lambda t: isinstance(t, Comment)):
            comment.extract()
        
        # Remove noise tags
        for tag in self.NOISE_TAGS:
            for element in soup.find_all(tag):
                element.decompose()
        
        # Remove elements with noise classes/IDs
        for element in soup.find_all(lambda tag: self._is_noise(tag)):
            element.decompose()
        
        # Extract and clean text
        text = self._extract_clean_text(soup)
        return text

    def _is_noise(self, tag) -> bool:
        classes = tag.get('class', [])
        if isinstance(classes, str): classes = [classes]
        for cls in classes:
            if any(n in cls.lower() for n in self.NOISE_CLASSES): return True
        
        id_val = tag.get('id', '').lower()
        if any(n in id_val for n in self.NOISE_IDS): return True
        return False

    def _extract_clean_text(self, soup: BeautifulSoup) -> str:
        # Simplified text extraction logic for core utility
        return soup.get_text(separator='\n', strip=True)
