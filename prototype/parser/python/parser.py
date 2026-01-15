"""
AIO Parser - Main entry point for AIO-aware web parsing.

This is the primary interface for the library. It:
1. Checks if URL has AIO content available
2. If yes: fetches clean AIO content directly
3. If no: falls back to HTML scraping with noise removal
4. Returns a unified ContentEnvelope
"""

from typing import Optional, List
from urllib.parse import urlparse

from .discovery import AIODiscovery, discover_aio
from .fetcher import AIOFetcher
from .fallback import HTMLScraper
from .envelope import ContentEnvelope, ChunkIndex


class AIOParser:
    """
    Main parser class for AIO-aware web content retrieval.
    
    Usage:
        parser = AIOParser()
        envelope = parser.parse("https://example.com", query="pricing")
        print(envelope.narrative)
    """
    
    def __init__(self, timeout: int = 10, user_agent: str = None):
        """
        Initialize the parser.
        
        Args:
            timeout: Request timeout in seconds
            user_agent: Custom user agent string
        """
        self.timeout = timeout
        self.user_agent = user_agent or "AIOParser/0.1 (ECR-Compatible)"
        
        # Initialize components
        self.discovery = AIODiscovery(timeout=timeout, user_agent=user_agent)
        self.fetcher = AIOFetcher(timeout=timeout, user_agent=user_agent)
        self.scraper = HTMLScraper(timeout=timeout, user_agent=user_agent)
    
    def parse(self, url: str, query: Optional[str] = None) -> ContentEnvelope:
        """
        Parse content from URL using AIO-aware retrieval.
        
        Args:
            url: URL to parse
            query: Optional query for targeted chunk retrieval
            
        Returns:
            ContentEnvelope with parsed content
        """
        # Step 1: Check for AIO availability
        aio_url, discovery_method = self.discovery.discover(url)
        
        if aio_url:
            # Step 2a: AIO path - fetch clean content
            return self._parse_aio(url, aio_url, query, discovery_method)
        else:
            # Step 2b: Fallback path - scrape and clean HTML
            return self._parse_html(url)
    
    def _parse_aio(self, original_url: str, aio_url: str, 
                   query: Optional[str], discovery_method: str) -> ContentEnvelope:
        """
        Parse content from AIO file.
        """
        # Fetch AIO data
        aio_data = self.fetcher.fetch(aio_url)
        
        if not aio_data:
            # AIO fetch failed, fallback to HTML
            return self._parse_html(original_url)
        
        # Build chunk index for all chunks
        all_chunks = []
        for idx in aio_data.get("index", []):
            all_chunks.append(ChunkIndex(
                id=idx["id"],
                path=idx.get("path", ""),
                title=idx.get("title", ""),
                keywords=idx.get("keywords", []),
                summary=idx.get("summary", ""),
                content_type=idx.get("content_type", "article"),
                token_estimate=idx.get("token_estimate", 0),
                priority=idx.get("priority", 0.5),
                related=idx.get("related", []),
            ))
        
        # If query provided, find matching chunks
        if query:
            keywords = self._extract_keywords(query)
            matching_chunks = self.fetcher.get_matching_chunks(aio_data, keywords)
            
            if matching_chunks:
                # Combine matching chunk content ONLY
                narrative = "\n\n---\n\n".join(
                    chunk.get("content", "") for chunk in matching_chunks
                )
                
                # Verify chunk hashes
                for chunk in matching_chunks:
                    self.fetcher.verify_chunk_hash(chunk)
                
                # Filter chunks to only matched ones
                matched_ids = [c["id"] for c in matching_chunks]
                chunks = [c for c in all_chunks if c.id in matched_ids]
                token_estimate = sum(c.token_estimate for c in chunks)
            else:
                # No matches, return all content
                narrative = "\n\n---\n\n".join(
                    c.get("content", "") for c in aio_data.get("content", [])
                )
                chunks = all_chunks
                token_estimate = sum(c.token_estimate for c in chunks)
        else:
            # No query, return all content
            narrative = "\n\n---\n\n".join(
                c.get("content", "") for c in aio_data.get("content", [])
            )
            chunks = all_chunks
            token_estimate = sum(c.token_estimate for c in chunks)
        
        # Build envelope with correct narrative and token count
        return ContentEnvelope(
            id=f"aio-{hash(original_url) % 100000:05d}",
            source_url=original_url,
            source_type="aio",
            narrative=narrative,
            format="markdown",
            tokens=token_estimate if token_estimate > 0 else len(narrative) // 4,
            noise_score=0.0,
            relevance_ratio=1.0,
            chunks=chunks,
            aio_version=aio_data.get("aio_version"),
        )
    
    def _parse_html(self, url: str) -> ContentEnvelope:
        """
        Parse content by scraping HTML (fallback path).
        """
        content, original_size, cleaned_size = self.scraper.scrape(url)
        return ContentEnvelope.from_scraped(content, url, original_size, cleaned_size)
    
    def _extract_keywords(self, query: str) -> List[str]:
        """
        Extract keywords from a query string.
        Simple implementation - can be enhanced with NLP.
        """
        # Remove common stop words
        stop_words = {
            'a', 'an', 'the', 'is', 'are', 'was', 'were', 'be', 'been',
            'what', 'how', 'when', 'where', 'who', 'which', 'why',
            'do', 'does', 'did', 'can', 'could', 'would', 'should',
            'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her',
            'of', 'in', 'on', 'at', 'to', 'for', 'with', 'by', 'from',
            'and', 'or', 'but', 'if', 'then', 'so', 'as'
        }
        
        # Tokenize and filter
        words = query.lower().split()
        keywords = [w.strip('?.,!') for w in words if w.strip('?.,!') not in stop_words]
        
        return keywords
    
    def check_aio_support(self, url: str) -> dict:
        """
        Check if a URL has AIO support without fetching content.
        
        Returns:
            Dict with 'supported', 'aio_url', 'discovery_method' keys
        """
        aio_url, method = self.discovery.discover(url)
        return {
            "supported": aio_url is not None,
            "aio_url": aio_url,
            "discovery_method": method
        }


def parse(url: str, query: Optional[str] = None, timeout: int = 10) -> ContentEnvelope:
    """
    Convenience function for parsing a URL.
    
    Args:
        url: URL to parse
        query: Optional query for targeted retrieval
        timeout: Request timeout
        
    Returns:
        ContentEnvelope with parsed content
        
    Example:
        >>> from aio_parser import parse
        >>> envelope = parse("https://example.com/pricing", query="subscription cost")
        >>> print(envelope.narrative)
        >>> print(f"Tokens: {envelope.tokens}, Noise: {envelope.noise_score}")
    """
    parser = AIOParser(timeout=timeout)
    return parser.parse(url, query)
