"""
AIO Verifier for AI Agents (Python)

This library is designed for AI agent developers to:
1. Detect AIO content in web pages
2. Extract the Markdown Shadow
3. Verify cryptographic signatures
4. Return clean, trusted content

Usage:
    from aio_verifier import AIOVerifier
    
    verifier = AIOVerifier()
    
    # From HTML string
    result = verifier.extract(html_content)
    
    # From URL
    result = verifier.fetch_and_extract('https://example.com/article')
    
    # Check verification status
    if result.is_verified:
        print("Content is authentic")
        print(result.markdown)
"""

import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime, timezone

# Optional dependencies
try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

try:
    from nacl.signing import VerifyKey
    from nacl.exceptions import BadSignatureError
    import base64
    NACL_AVAILABLE = True
except ImportError:
    NACL_AVAILABLE = False


class VerificationStatus(Enum):
    """Verification status codes"""
    VERIFIED = "VERIFIED"                    # Signature valid, content matches
    HASH_VALID = "HASH_VALID"               # No signature, but hash matches
    HASH_MISMATCH = "HASH_MISMATCH"         # Content modified
    SIGNATURE_INVALID = "SIGNATURE_INVALID"  # Signature check failed
    EXPIRED = "EXPIRED"                      # Timestamp too old
    NO_TRUST_LAYER = "NO_TRUST_LAYER"       # No verification data
    NO_AIO_CONTENT = "NO_AIO_CONTENT"       # No markdown shadow found
    ERROR = "ERROR"                          # Processing error


@dataclass
class TrustInfo:
    """Trust layer verification results"""
    status: VerificationStatus = VerificationStatus.NO_TRUST_LAYER
    hash_valid: bool = False
    signature_valid: Optional[bool] = None
    content_hash: Optional[str] = None
    provided_hash: Optional[str] = None
    timestamp: Optional[str] = None
    algorithm: Optional[str] = None
    public_key: Optional[str] = None
    message: str = ""


@dataclass
class AIOResult:
    """Complete AIO extraction result"""
    markdown: Optional[str] = None
    jsonld: List[Dict] = field(default_factory=list)
    trust: TrustInfo = field(default_factory=TrustInfo)
    meta: Dict[str, str] = field(default_factory=dict)
    url: Optional[str] = None
    fetched_at: Optional[str] = None
    error: Optional[str] = None
    
    @property
    def has_aio(self) -> bool:
        return self.markdown is not None
    
    @property
    def is_verified(self) -> bool:
        return self.trust.status == VerificationStatus.VERIFIED
    
    @property
    def is_trusted(self) -> bool:
        return self.trust.status in [VerificationStatus.VERIFIED, VerificationStatus.HASH_VALID]


class AIOVerifier:
    """AIO content extractor and verifier for AI agents"""
    
    def __init__(self, user_agent: str = "AIO-Verifier/1.0"):
        self.user_agent = user_agent
    
    def extract(self, html: str, max_age_hours: Optional[int] = None) -> AIOResult:
        """
        Extract and verify AIO content from HTML.
        
        Args:
            html: HTML content string
            max_age_hours: Maximum age of content in hours (optional)
        
        Returns:
            AIOResult with extracted content and verification status
        """
        try:
            parsed = self._parse_html(html)
            trust = self._verify_trust(
                parsed['markdown'], 
                parsed['trust'],
                max_age_hours
            )
            
            return AIOResult(
                markdown=parsed['markdown'],
                jsonld=parsed['jsonld'],
                trust=trust,
                meta=parsed['meta']
            )
        except Exception as e:
            return AIOResult(
                trust=TrustInfo(
                    status=VerificationStatus.ERROR,
                    message=str(e)
                ),
                error=str(e)
            )
    
    def fetch_and_extract(self, url: str, max_age_hours: Optional[int] = None) -> AIOResult:
        """
        Fetch URL and extract AIO content.
        
        Args:
            url: URL to fetch
            max_age_hours: Maximum age of content in hours (optional)
        
        Returns:
            AIOResult with extracted content and verification status
        """
        if not REQUESTS_AVAILABLE:
            raise ImportError("requests library required: pip install requests")
        
        response = requests.get(url, headers={
            'User-Agent': self.user_agent,
            'Accept': 'text/html'
        })
        response.raise_for_status()
        
        result = self.extract(response.text, max_age_hours)
        result.url = url
        result.fetched_at = datetime.now(timezone.utc).isoformat()
        
        return result
    
    def fetch_ai_instructions(self, base_url: str) -> Optional[Dict]:
        """
        Fetch AI instructions from well-known location.
        
        Args:
            base_url: Base URL of the site
        
        Returns:
            Parsed JSON or None if not found
        """
        if not REQUESTS_AVAILABLE:
            raise ImportError("requests library required: pip install requests")
        
        url = base_url.rstrip('/') + '/.well-known/ai-instructions.json'
        
        try:
            response = requests.get(url, headers={
                'User-Agent': self.user_agent,
                'Accept': 'application/json'
            })
            if response.ok:
                return response.json()
        except:
            pass
        
        return None
    
    def _parse_html(self, html: str) -> Dict:
        """Parse HTML and extract AIO components"""
        if BS4_AVAILABLE:
            return self._parse_with_bs4(html)
        return self._parse_with_regex(html)
    
    def _parse_with_bs4(self, html: str) -> Dict:
        """Parse with BeautifulSoup"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract Markdown Shadow
        md_script = soup.find('script', type='text/markdown')
        markdown = md_script.string.strip() if md_script and md_script.string else None
        
        # Extract JSON-LD
        jsonld = []
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                if script.string:
                    jsonld.append(json.loads(script.string))
            except json.JSONDecodeError:
                pass
        
        # Extract Trust Layer
        trust = {
            'signature': self._get_meta(soup, 'aio-truth-signature'),
            'content_hash': self._get_meta(soup, 'aio-content-hash'),
            'public_key': self._get_meta(soup, 'aio-public-key'),
            'timestamp': self._get_meta(soup, 'aio-last-verified'),
            'algorithm': self._get_meta(soup, 'aio-signature-algorithm')
        }
        
        # Extract page metadata
        meta = {
            'title': soup.title.string if soup.title else None,
            'description': self._get_meta(soup, 'description'),
            'canonical': soup.find('link', rel='canonical')['href'] if soup.find('link', rel='canonical') else None
        }
        
        return {'markdown': markdown, 'jsonld': jsonld, 'trust': trust, 'meta': meta}
    
    def _get_meta(self, soup, name: str) -> Optional[str]:
        """Get meta tag content"""
        tag = soup.find('meta', attrs={'name': name})
        return tag.get('content') if tag else None
    
    def _parse_with_regex(self, html: str) -> Dict:
        """Parse with regex (fallback)"""
        # Extract Markdown Shadow
        md_match = re.search(
            r'<script[^>]*type=["\']text/markdown["\'][^>]*>(.*?)</script>',
            html, re.DOTALL | re.IGNORECASE
        )
        markdown = md_match.group(1).strip() if md_match else None
        
        # Extract JSON-LD
        jsonld = []
        for match in re.finditer(
            r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
            html, re.DOTALL | re.IGNORECASE
        ):
            try:
                jsonld.append(json.loads(match.group(1)))
            except json.JSONDecodeError:
                pass
        
        # Extract Trust Layer
        trust = {
            'signature': self._extract_meta_regex(html, 'aio-truth-signature'),
            'content_hash': self._extract_meta_regex(html, 'aio-content-hash'),
            'public_key': self._extract_meta_regex(html, 'aio-public-key'),
            'timestamp': self._extract_meta_regex(html, 'aio-last-verified'),
            'algorithm': self._extract_meta_regex(html, 'aio-signature-algorithm')
        }
        
        # Extract page metadata
        title_match = re.search(r'<title[^>]*>([^<]*)</title>', html, re.IGNORECASE)
        meta = {
            'title': title_match.group(1) if title_match else None,
            'description': self._extract_meta_regex(html, 'description'),
            'canonical': None
        }
        
        return {'markdown': markdown, 'jsonld': jsonld, 'trust': trust, 'meta': meta}
    
    def _extract_meta_regex(self, html: str, name: str) -> Optional[str]:
        """Extract meta tag content with regex"""
        pattern = rf'<meta[^>]*name=["\']{ name}["\'][^>]*content=["\']([^"\']+)["\']'
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            return match.group(1)
        
        # Try reverse order
        pattern2 = rf'<meta[^>]*content=["\']([^"\']+)["\'][^>]*name=["\']{ name}["\']'
        match2 = re.search(pattern2, html, re.IGNORECASE)
        return match2.group(1) if match2 else None
    
    def _sha256(self, content: str) -> str:
        """Compute SHA-256 hash"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def _verify_trust(self, markdown: Optional[str], trust: Dict, max_age_hours: Optional[int]) -> TrustInfo:
        """Verify the Trust Layer"""
        result = TrustInfo()
        
        if not markdown:
            result.status = VerificationStatus.NO_AIO_CONTENT
            result.message = "No markdown shadow found"
            return result
        
        # Compute actual hash
        result.content_hash = self._sha256(markdown.strip())
        result.provided_hash = trust.get('content_hash')
        result.timestamp = trust.get('timestamp')
        result.algorithm = trust.get('algorithm')
        result.public_key = trust.get('public_key')
        
        # Check if any trust data exists
        if not trust.get('content_hash') and not trust.get('signature'):
            result.message = "No trust layer metadata found"
            return result
        
        # Verify hash
        if trust.get('content_hash'):
            result.hash_valid = result.content_hash == trust['content_hash']
            
            if not result.hash_valid:
                result.status = VerificationStatus.HASH_MISMATCH
                result.message = "Content hash does not match - content may have been modified"
                return result
        
        # Check timestamp
        if trust.get('timestamp') and max_age_hours:
            try:
                ts = datetime.fromisoformat(trust['timestamp'].replace('Z', '+00:00'))
                age_hours = (datetime.now(timezone.utc) - ts).total_seconds() / 3600
                if age_hours > max_age_hours:
                    result.status = VerificationStatus.EXPIRED
                    result.message = f"Content timestamp is {age_hours:.1f} hours old"
                    return result
            except:
                pass
        
        # Verify signature
        signature = trust.get('signature')
        if signature and signature != 'UNSIGNED':
            algorithm = trust.get('algorithm', 'Ed25519')
            
            if algorithm == 'Ed25519' and trust.get('public_key'):
                result.signature_valid = self._verify_ed25519(
                    markdown.strip(),
                    signature,
                    trust['public_key'],
                    trust.get('timestamp', ''),
                    algorithm
                )
                
                if result.signature_valid is True:
                    result.status = VerificationStatus.VERIFIED
                    result.message = "Content verified - signature valid"
                elif result.signature_valid is False:
                    result.status = VerificationStatus.SIGNATURE_INVALID
                    result.message = "Signature verification failed"
                else:
                    result.status = VerificationStatus.HASH_VALID if result.hash_valid else VerificationStatus.NO_TRUST_LAYER
                    result.message = "Could not verify signature (nacl library not available)"
            
            elif algorithm == 'SHA256-HASH':
                result.status = VerificationStatus.HASH_VALID if result.hash_valid else VerificationStatus.HASH_MISMATCH
                result.message = "Content hash verified" if result.hash_valid else "Hash mismatch"
            
            else:
                result.status = VerificationStatus.HASH_VALID if result.hash_valid else VerificationStatus.NO_TRUST_LAYER
                result.message = f"Unknown algorithm: {algorithm}"
        
        elif result.hash_valid:
            result.status = VerificationStatus.HASH_VALID
            result.message = "Content hash verified (no signature)"
        
        return result
    
    def _verify_ed25519(self, markdown: str, signature: str, public_key: str, 
                        timestamp: str, algorithm: str) -> Optional[bool]:
        """Verify Ed25519 signature"""
        if not NACL_AVAILABLE:
            return None
        
        try:
            # Build canonical payload
            content_hash = self._sha256(markdown)
            payload = json.dumps({
                'algorithm': algorithm,
                'content_hash': content_hash,
                'timestamp': timestamp
            }, separators=(',', ':'), sort_keys=True)
            
            # Verify
            verify_key = VerifyKey(base64.b64decode(public_key))
            sig_bytes = base64.b64decode(signature)
            verify_key.verify(payload.encode('utf-8'), sig_bytes)
            return True
        
        except BadSignatureError:
            return False
        except Exception:
            return False


# Convenience functions
def extract(html: str, **kwargs) -> AIOResult:
    """Extract AIO content from HTML"""
    return AIOVerifier().extract(html, **kwargs)


def fetch_and_extract(url: str, **kwargs) -> AIOResult:
    """Fetch URL and extract AIO content"""
    return AIOVerifier().fetch_and_extract(url, **kwargs)


def has_aio_content(url: str) -> bool:
    """Check if URL has AIO content"""
    return AIOVerifier().fetch_and_extract(url).has_aio


# CLI
if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python aio_verifier.py <url>")
        print("       python aio_verifier.py --file <path>")
        sys.exit(1)
    
    verifier = AIOVerifier()
    
    if sys.argv[1] == '--file':
        with open(sys.argv[2], 'r', encoding='utf-8') as f:
            result = verifier.extract(f.read())
    else:
        result = verifier.fetch_and_extract(sys.argv[1])
    
    print(f"\n{'='*60}")
    print(f"URL: {result.url or 'N/A'}")
    print(f"Has AIO: {result.has_aio}")
    print(f"Verification: {result.trust.status.value}")
    print(f"Message: {result.trust.message}")
    print(f"{'='*60}")
    
    if result.markdown:
        print(f"\nMarkdown Preview (first 500 chars):")
        print("-" * 40)
        print(result.markdown[:500])
        if len(result.markdown) > 500:
            print("...")
    
    if result.jsonld:
        print(f"\nJSON-LD: {len(result.jsonld)} block(s) found")
