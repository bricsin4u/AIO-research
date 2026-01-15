"""
Structure Extractor - Extracts typed entities from content.

This module identifies and extracts structured facts (Products, Prices, 
People, Organizations, Dates, etc.) from narrative content.

Why this matters: When you ask "What is the price of X?", I shouldn't have
to parse prose. I should be able to query structured data directly:
{"@type": "Product", "name": "X", "price": 49.99}

The extractor creates JSON-LD compatible entities that can be:
1. Queried directly for fact extraction
2. Linked to narrative anchors for context
3. Verified against the source text
"""

import re
from dataclasses import dataclass
from typing import Optional, Any
from datetime import datetime


@dataclass
class ExtractedEntity:
    """A structured entity extracted from content."""
    type: str  # Schema.org type: Product, Person, Organization, etc.
    properties: dict[str, Any]
    source_text: str  # The original text this was extracted from
    line_number: int  # Where in the document this was found
    confidence: float = 1.0  # Extraction confidence


class StructureExtractor:
    """
    Extracts structured entities from markdown content.
    
    Supports extraction of:
    - Products (with prices, features)
    - Prices (currency, amount, period)
    - People (names, roles)
    - Organizations
    - Dates and time periods
    - Technical specifications
    - Contact information
    """
    
    # Price patterns
    PRICE_PATTERNS = [
        # $49.99, $49, $49.99/month
        r'\$(\d+(?:,\d{3})*(?:\.\d{2})?)\s*(?:\/\s*(month|year|mo|yr|week|day))?',
        # 49.99 USD, 49 EUR
        r'(\d+(?:,\d{3})*(?:\.\d{2})?)\s*(USD|EUR|GBP|CAD|AUD|JPY|CNY)',
        # €49.99, £49.99
        r'[€£](\d+(?:,\d{3})*(?:\.\d{2})?)',
    ]
    
    # Date patterns
    DATE_PATTERNS = [
        # 2025-12-28, 2025/12/28
        r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})',
        # December 28, 2025
        r'((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4})',
        # 28 December 2025
        r'(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})',
    ]
    
    # Email pattern
    EMAIL_PATTERN = r'[\w.+-]+@[\w-]+\.[\w.-]+'
    
    # URL pattern
    URL_PATTERN = r'https?://[^\s<>\[\]()"\']+'
    
    # Version pattern
    VERSION_PATTERN = r'v?(\d+\.\d+(?:\.\d+)?(?:-[\w.]+)?)'
    
    def __init__(self):
        self._price_patterns = [re.compile(p, re.IGNORECASE) for p in self.PRICE_PATTERNS]
        self._date_patterns = [re.compile(p, re.IGNORECASE) for p in self.DATE_PATTERNS]
        self._email_pattern = re.compile(self.EMAIL_PATTERN)
        self._url_pattern = re.compile(self.URL_PATTERN)
        self._version_pattern = re.compile(self.VERSION_PATTERN)
    
    def extract(self, markdown: str) -> list[ExtractedEntity]:
        """
        Extract all structured entities from markdown content.
        
        Args:
            markdown: Clean markdown content
            
        Returns:
            List of extracted entities with source references
        """
        entities = []
        lines = markdown.split('\n')
        
        for i, line in enumerate(lines):
            # Extract prices
            entities.extend(self._extract_prices(line, i))
            
            # Extract dates
            entities.extend(self._extract_dates(line, i))
            
            # Extract emails
            entities.extend(self._extract_emails(line, i))
            
            # Extract URLs
            entities.extend(self._extract_urls(line, i))
            
            # Extract versions
            entities.extend(self._extract_versions(line, i))
        
        # Extract products (multi-line analysis)
        entities.extend(self._extract_products(markdown, lines))
        
        return entities
    
    def _extract_prices(self, line: str, line_num: int) -> list[ExtractedEntity]:
        """Extract price entities from a line."""
        entities = []
        
        for pattern in self._price_patterns:
            for match in pattern.finditer(line):
                amount_str = match.group(1).replace(',', '')
                amount = float(amount_str)
                
                # Determine currency
                full_match = match.group(0)
                if '$' in full_match:
                    currency = 'USD'
                elif '€' in full_match:
                    currency = 'EUR'
                elif '£' in full_match:
                    currency = 'GBP'
                elif len(match.groups()) > 1 and match.group(2):
                    currency = match.group(2).upper()
                else:
                    currency = 'USD'
                
                # Check for period (month, year, etc.)
                period = None
                period_match = re.search(r'/(month|year|mo|yr|week|day)', full_match, re.I)
                if period_match:
                    period_raw = period_match.group(1).lower()
                    period_map = {'mo': 'month', 'yr': 'year'}
                    period = period_map.get(period_raw, period_raw)
                
                properties = {
                    "value": amount,
                    "currency": currency
                }
                if period:
                    properties["period"] = period
                
                entities.append(ExtractedEntity(
                    type="PriceSpecification",
                    properties=properties,
                    source_text=full_match,
                    line_number=line_num
                ))
        
        return entities
    
    def _extract_dates(self, line: str, line_num: int) -> list[ExtractedEntity]:
        """Extract date entities from a line."""
        entities = []
        
        for pattern in self._date_patterns:
            for match in pattern.finditer(line):
                date_str = match.group(1)
                
                # Try to parse the date
                parsed_date = self._parse_date(date_str)
                
                entities.append(ExtractedEntity(
                    type="Date",
                    properties={
                        "value": date_str,
                        "iso": parsed_date.isoformat() if parsed_date else None
                    },
                    source_text=date_str,
                    line_number=line_num
                ))
        
        return entities
    
    def _extract_emails(self, line: str, line_num: int) -> list[ExtractedEntity]:
        """Extract email entities from a line."""
        entities = []
        
        for match in self._email_pattern.finditer(line):
            email = match.group(0)
            entities.append(ExtractedEntity(
                type="ContactPoint",
                properties={
                    "contactType": "email",
                    "email": email
                },
                source_text=email,
                line_number=line_num
            ))
        
        return entities
    
    def _extract_urls(self, line: str, line_num: int) -> list[ExtractedEntity]:
        """Extract URL entities from a line."""
        entities = []
        
        for match in self._url_pattern.finditer(line):
            url = match.group(0)
            entities.append(ExtractedEntity(
                type="URL",
                properties={
                    "url": url
                },
                source_text=url,
                line_number=line_num
            ))
        
        return entities
    
    def _extract_versions(self, line: str, line_num: int) -> list[ExtractedEntity]:
        """Extract version entities from a line."""
        entities = []
        
        # Only extract if it looks like a version context
        version_contexts = ['version', 'v.', 'release', 'update']
        line_lower = line.lower()
        
        if any(ctx in line_lower for ctx in version_contexts):
            for match in self._version_pattern.finditer(line):
                version = match.group(1)
                entities.append(ExtractedEntity(
                    type="SoftwareVersion",
                    properties={
                        "version": version
                    },
                    source_text=match.group(0),
                    line_number=line_num
                ))
        
        return entities
    
    def _extract_products(self, markdown: str, lines: list[str]) -> list[ExtractedEntity]:
        """
        Extract product entities by analyzing content structure.
        
        Products are identified by:
        - Headers followed by price mentions
        - "Plan" or "Tier" naming patterns
        - Feature lists with pricing
        """
        entities = []
        
        # Look for product patterns in headers
        for i, line in enumerate(lines):
            header_match = re.match(r'^#{1,3}\s+(.+)$', line)
            if header_match:
                title = header_match.group(1)
                
                # Check if this looks like a product/plan
                product_indicators = ['plan', 'tier', 'package', 'edition', 'version', 'pricing']
                if any(ind in title.lower() for ind in product_indicators):
                    # Look for price in nearby lines
                    search_range = lines[i:min(i+10, len(lines))]
                    search_text = '\n'.join(search_range)
                    
                    price_entity = None
                    for pattern in self._price_patterns:
                        price_match = pattern.search(search_text)
                        if price_match:
                            amount = float(price_match.group(1).replace(',', ''))
                            price_entity = {
                                "value": amount,
                                "currency": "USD"  # Default
                            }
                            break
                    
                    properties = {"name": title}
                    if price_entity:
                        properties["price"] = price_entity
                    
                    entities.append(ExtractedEntity(
                        type="Product",
                        properties=properties,
                        source_text=title,
                        line_number=i
                    ))
        
        return entities
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Try to parse a date string into a datetime object."""
        formats = [
            '%Y-%m-%d',
            '%Y/%m/%d',
            '%B %d, %Y',
            '%B %d %Y',
            '%d %B %Y',
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        return None
    
    def to_jsonld(self, entities: list[ExtractedEntity]) -> list[dict]:
        """
        Convert extracted entities to JSON-LD format.
        
        Args:
            entities: List of extracted entities
            
        Returns:
            List of JSON-LD compatible dictionaries
        """
        jsonld_entities = []
        
        for entity in entities:
            jsonld = {
                "@type": entity.type,
                **entity.properties,
                "_extraction": {
                    "source_text": entity.source_text,
                    "line_number": entity.line_number,
                    "confidence": entity.confidence
                }
            }
            jsonld_entities.append(jsonld)
        
        return jsonld_entities
