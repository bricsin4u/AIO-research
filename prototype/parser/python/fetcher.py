"""
AIO Fetcher - Retrieves and validates AIO content.

Handles:
- Fetching AIO files from discovered URLs
- Signature verification (when implemented)
- Per-chunk hash verification
- Caching (future)
"""

import hashlib
import json
from typing import Optional, Dict, List, Any
from urllib.parse import urljoin
import requests


class AIOFetcher:
    """
    Fetches and validates AIO content files.
    """
    
    def __init__(self, timeout: int = 10, user_agent: str = None):
        self.timeout = timeout
        self.user_agent = user_agent or "AIOParser/0.1 (ECR-Compatible)"
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.user_agent})
    
    def fetch(self, aio_url: str) -> Optional[Dict]:
        """
        Fetch AIO content from URL.
        
        Args:
            aio_url: URL to the AIO file
            
        Returns:
            Parsed AIO JSON data, or None if fetch failed
        """
        try:
            response = self.session.get(aio_url, timeout=self.timeout)
            
            if response.status_code != 200:
                return None
            
            data = response.json()
            
            # Validate it's actually AIO content
            if "aio_version" not in data:
                return None
            
            return data
            
        except (requests.RequestException, json.JSONDecodeError):
            return None
    
    def fetch_manifest(self, manifest_url: str) -> Optional[Dict]:
        """
        Fetch AIO manifest for trust/policy information.
        """
        try:
            response = self.session.get(manifest_url, timeout=self.timeout)
            if response.status_code == 200:
                return response.json()
        except:
            pass
        return None
    
    def verify_chunk_hash(self, chunk: Dict) -> bool:
        """
        Verify a single chunk's content hash.
        
        Args:
            chunk: Chunk dict with 'content' and 'hash' fields
            
        Returns:
            True if hash matches, False otherwise
        """
        content = chunk.get("content", "")
        expected_hash = chunk.get("hash", "")
        
        if not expected_hash:
            return True  # No hash to verify
        
        # Parse hash format: "sha256:abcdef..."
        if ":" in expected_hash:
            algorithm, hash_value = expected_hash.split(":", 1)
        else:
            algorithm = "sha256"
            hash_value = expected_hash
        
        # Calculate hash
        if algorithm.lower() == "sha256":
            calculated = hashlib.sha256(content.encode()).hexdigest()
        else:
            return False  # Unsupported algorithm
        
        # Compare (case-insensitive, partial match for truncated hashes)
        return hash_value.lower() in calculated.lower() or calculated.lower().startswith(hash_value.lower())
    
    def get_matching_chunks(self, aio_data: Dict, keywords: List[str]) -> List[Dict]:
        """
        Find chunks matching given keywords.
        
        Args:
            aio_data: Full AIO data
            keywords: Keywords to match against chunk index
            
        Returns:
            List of matching content chunks
        """
        keywords_lower = [k.lower() for k in keywords]
        matching_ids = []
        
        # Search index for keyword matches
        for idx in aio_data.get("index", []):
            chunk_keywords = [k.lower() for k in idx.get("keywords", [])]
            title_lower = idx.get("title", "").lower()
            summary_lower = idx.get("summary", "").lower()
            
            # Check for any keyword match
            for kw in keywords_lower:
                if (kw in chunk_keywords or 
                    kw in title_lower or 
                    kw in summary_lower):
                    matching_ids.append(idx["id"])
                    break
        
        # Get matching content
        matching_chunks = []
        for content in aio_data.get("content", []):
            if content["id"] in matching_ids:
                matching_chunks.append(content)
        
        return matching_chunks
    
    def get_chunk_by_id(self, aio_data: Dict, chunk_id: str) -> Optional[Dict]:
        """
        Get a specific chunk by ID.
        """
        for content in aio_data.get("content", []):
            if content["id"] == chunk_id:
                return content
        return None


def fetch_aio(url: str, timeout: int = 10) -> Optional[Dict]:
    """Convenience function for fetching AIO content."""
    fetcher = AIOFetcher(timeout=timeout)
    return fetcher.fetch(url)
