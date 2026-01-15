"""
AIO Discovery - Protocol for detecting AIO availability on websites.

Implements the 4-priority discovery mechanism from AIO v2.1 spec:
1. HTTP Link header
2. HTML <link> tag
3. robots.txt directive
4. Direct URL attempt
"""

import re
from typing import Optional, Tuple
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup


class AIODiscovery:
    """
    Discovers AIO content availability for a given URL.
    
    Priority order (per spec):
    1. HTTP Link header - fastest, no extra request
    2. HTML <link> tag - fallback if headers stripped
    3. robots.txt directive - site-wide signal
    4. Direct URL attempt - /ai-content.aio at site root
    """
    
    def __init__(self, timeout: int = 10, user_agent: str = None):
        self.timeout = timeout
        self.user_agent = user_agent or "AIOParser/0.1 (ECR-Compatible)"
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.user_agent})
    
    def discover(self, url: str) -> Tuple[Optional[str], str]:
        """
        Attempt to discover AIO content for given URL.
        
        Args:
            url: The URL to check for AIO availability
            
        Returns:
            Tuple of (aio_url, discovery_method)
            aio_url is None if no AIO found
            discovery_method is one of: "link_header", "link_tag", "robots_txt", "direct", "none"
        """
        parsed = urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        
        # Priority 1: Check HTTP Link header
        aio_url = self._check_link_header(url)
        if aio_url:
            return urljoin(base_url, aio_url), "link_header"
        
        # Priority 2: Check HTML <link> tag
        aio_url = self._check_link_tag(url)
        if aio_url:
            return urljoin(base_url, aio_url), "link_tag"
        
        # Priority 3: Check robots.txt
        aio_url = self._check_robots_txt(base_url)
        if aio_url:
            return urljoin(base_url, aio_url), "robots_txt"
        
        # Priority 4: Direct URL attempt
        aio_url = self._check_direct(base_url)
        if aio_url:
            return aio_url, "direct"
        
        return None, "none"
    
    def _check_link_header(self, url: str) -> Optional[str]:
        """
        Check for AIO Link header in HTTP response.
        
        Expected format:
        Link: </ai-content.aio>; rel="alternate"; type="application/aio+json"
        """
        try:
            response = self.session.head(url, timeout=self.timeout, allow_redirects=True)
            link_header = response.headers.get("Link", "")
            
            # Parse Link header for AIO content
            # Pattern: </path>; rel="alternate"; type="application/aio+json"
            pattern = r'<([^>]+)>;\s*rel="alternate";\s*type="application/aio\+json"'
            match = re.search(pattern, link_header)
            
            if match:
                return match.group(1)
                
        except requests.RequestException:
            pass
        
        return None
    
    def _check_link_tag(self, url: str) -> Optional[str]:
        """
        Check for AIO <link> tag in HTML <head>.
        
        Expected format:
        <link rel="alternate" type="application/aio+json" href="/ai-content.aio">
        """
        try:
            response = self.session.get(url, timeout=self.timeout)
            if response.status_code != 200:
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find link tag with AIO type
            link = soup.find('link', {
                'rel': 'alternate',
                'type': 'application/aio+json'
            })
            
            if link and link.get('href'):
                return link['href']
                
        except requests.RequestException:
            pass
        
        return None
    
    def _check_robots_txt(self, base_url: str) -> Optional[str]:
        """
        Check for AIO-Content directive in robots.txt.
        
        Expected format:
        AIO-Content: /ai-content.aio
        """
        try:
            robots_url = urljoin(base_url, "/robots.txt")
            response = self.session.get(robots_url, timeout=self.timeout)
            
            if response.status_code != 200:
                return None
            
            # Parse robots.txt for AIO-Content directive
            for line in response.text.split('\n'):
                line = line.strip()
                if line.lower().startswith('aio-content:'):
                    path = line.split(':', 1)[1].strip()
                    return path
                    
        except requests.RequestException:
            pass
        
        return None
    
    def _check_direct(self, base_url: str) -> Optional[str]:
        """
        Try fetching /ai-content.aio directly.
        """
        try:
            aio_url = urljoin(base_url, "/ai-content.aio")
            response = self.session.head(aio_url, timeout=self.timeout)
            
            if response.status_code == 200:
                # Verify it's actually AIO content
                content_type = response.headers.get("Content-Type", "")
                if "aio+json" in content_type or "application/json" in content_type:
                    return aio_url
                    
                # If no content-type, try GET to verify structure
                response = self.session.get(aio_url, timeout=self.timeout)
                try:
                    data = response.json()
                    if "aio_version" in data:
                        return aio_url
                except:
                    pass
                    
        except requests.RequestException:
            pass
        
        return None


def discover_aio(url: str, timeout: int = 10) -> Tuple[Optional[str], str]:
    """
    Convenience function for AIO discovery.
    
    Args:
        url: URL to check for AIO availability
        timeout: Request timeout in seconds
        
    Returns:
        Tuple of (aio_url, discovery_method)
    """
    discovery = AIODiscovery(timeout=timeout)
    return discovery.discover(url)
