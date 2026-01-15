"""
Content Envelope - Unified output format for AIO Parser.

The Content Envelope provides a standardized representation of web content,
regardless of whether it came from an AIO file or was scraped from HTML.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
import json


@dataclass
class ChunkIndex:
    """Index entry for a content chunk."""
    id: str
    path: str
    title: str
    keywords: List[str]
    summary: str
    content_type: str = "article"
    token_estimate: int = 0
    priority: float = 0.5
    related: List[str] = field(default_factory=list)


@dataclass
class Entity:
    """Structured entity extracted from content."""
    type: str  # e.g., "PriceSpecification", "Product", "Organization"
    properties: Dict[str, Any] = field(default_factory=dict)
    anchor_ref: Optional[str] = None  # Link to narrative section
    binding_confidence: float = 1.0


@dataclass
class IntegrityInfo:
    """Cryptographic integrity information."""
    narrative_hash: Optional[str] = None
    verified: bool = False
    signature_valid: Optional[bool] = None
    verified_at: Optional[datetime] = None


@dataclass
class ContentEnvelope:
    """
    Unified content envelope - the output of AIO parsing.
    
    This structure represents clean, structured content ready for LLM consumption.
    It may come from an AIO file (ideal case) or be generated from HTML scraping (fallback).
    """
    # Identification
    id: str
    source_url: str
    source_type: str  # "aio" | "scraped" | "hybrid"
    
    # Narrative layer (clean text for embeddings/context)
    narrative: str
    format: str = "markdown"
    
    # Metrics
    tokens: int = 0
    noise_score: float = 0.0  # 0.0 = no noise, 1.0 = all noise
    relevance_ratio: float = 1.0  # Inverse of attention tax
    
    # Index layer (for targeted retrieval)
    chunks: List[ChunkIndex] = field(default_factory=list)
    
    # Structure layer (typed entities)
    entities: List[Entity] = field(default_factory=list)
    
    # Integrity layer
    integrity: IntegrityInfo = field(default_factory=IntegrityInfo)
    
    # Metadata
    fetched_at: datetime = field(default_factory=datetime.utcnow)
    aio_version: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert envelope to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "source_url": self.source_url,
            "source_type": self.source_type,
            "narrative": self.narrative,
            "format": self.format,
            "tokens": self.tokens,
            "noise_score": self.noise_score,
            "relevance_ratio": self.relevance_ratio,
            "chunks": [
                {
                    "id": c.id,
                    "path": c.path,
                    "title": c.title,
                    "keywords": c.keywords,
                    "summary": c.summary,
                    "token_estimate": c.token_estimate,
                }
                for c in self.chunks
            ],
            "entities": [
                {
                    "type": e.type,
                    "properties": e.properties,
                    "anchor_ref": e.anchor_ref,
                }
                for e in self.entities
            ],
            "integrity": {
                "verified": self.integrity.verified,
                "signature_valid": self.integrity.signature_valid,
            },
            "fetched_at": self.fetched_at.isoformat(),
            "aio_version": self.aio_version,
        }
    
    def to_json(self, indent: int = 2) -> str:
        """Serialize envelope to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)
    
    @classmethod
    def from_aio(cls, aio_data: dict, source_url: str, chunk_id: Optional[str] = None) -> "ContentEnvelope":
        """
        Create envelope from AIO file data.
        
        Args:
            aio_data: Parsed AIO JSON content
            source_url: Original URL requested
            chunk_id: Optional specific chunk to extract (if None, returns all)
        """
        # Build chunk index
        chunks = []
        for idx in aio_data.get("index", []):
            chunks.append(ChunkIndex(
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
        
        # Extract narrative content
        content_items = aio_data.get("content", [])
        
        if chunk_id:
            # Get specific chunk
            matching = [c for c in content_items if c["id"] == chunk_id]
            if matching:
                narrative = matching[0].get("content", "")
            else:
                narrative = ""
        else:
            # Combine all content
            narrative = "\n\n---\n\n".join(
                c.get("content", "") for c in content_items
            )
        
        # Calculate token estimate (rough: ~4 chars per token)
        token_estimate = len(narrative) // 4
        
        return cls(
            id=f"aio-{hash(source_url) % 100000:05d}",
            source_url=source_url,
            source_type="aio",
            narrative=narrative,
            format="markdown",
            tokens=token_estimate,
            noise_score=0.0,  # AIO content has no noise
            relevance_ratio=1.0,
            chunks=chunks,
            aio_version=aio_data.get("aio_version"),
            integrity=IntegrityInfo(verified=True),
        )
    
    @classmethod
    def from_scraped(cls, content: str, source_url: str, 
                     original_size: int, cleaned_size: int) -> "ContentEnvelope":
        """
        Create envelope from scraped and cleaned HTML content.
        
        Args:
            content: Cleaned text content
            source_url: Original URL
            original_size: Size before cleaning (for noise calculation)
            cleaned_size: Size after cleaning
        """
        # Calculate noise score
        if original_size > 0:
            noise_score = 1.0 - (cleaned_size / original_size)
        else:
            noise_score = 0.0
        
        relevance_ratio = 1.0 - noise_score
        token_estimate = len(content) // 4
        
        return cls(
            id=f"scraped-{hash(source_url) % 100000:05d}",
            source_url=source_url,
            source_type="scraped",
            narrative=content,
            format="plain",
            tokens=token_estimate,
            noise_score=noise_score,
            relevance_ratio=relevance_ratio,
            chunks=[],
            integrity=IntegrityInfo(verified=False),
        )
