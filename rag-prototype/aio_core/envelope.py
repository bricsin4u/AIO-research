"""
AIO Envelope - The core data structure for AI-optimized content.

The envelope contains synchronized views of the same content:
- narrative: clean markdown for context
- structure: typed entities for fact extraction  
- anchors: stable IDs for citations
- integrity: hashes for verification
"""

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Source:
    """Origin information for the content."""
    uri: str
    type: str  # web, pdf, database, api, etc.
    fetched_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


@dataclass
class Narrative:
    """Clean, noise-free content representation."""
    format: str  # markdown, plaintext
    content: str
    token_count: int = 0
    noise_score: float = 0.0  # 0 = no noise removed, 1 = all noise


@dataclass
class Anchor:
    """Stable reference point within the narrative."""
    line_start: int
    line_end: int
    type: str  # section, paragraph, list, table
    title: Optional[str] = None


@dataclass 
class Entity:
    """Structured fact extracted from content."""
    type: str  # Product, Person, Organization, Price, Date, etc.
    properties: dict
    anchor_ref: Optional[str] = None  # Link to narrative anchor
    binding_confidence: float = 1.0


@dataclass
class Integrity:
    """Verification metadata."""
    narrative_hash: str
    structure_hash: Optional[str] = None
    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


@dataclass
class Envelope:
    """
    The complete AIO envelope containing all synchronized views.
    
    This is what gets stored and retrieved. Each view serves a purpose:
    - narrative: for embeddings and context
    - structure: for fact queries and filtering
    - anchors: for stable citations
    - integrity: for verification
    """
    id: str
    source: Source
    narrative: Narrative
    anchors: dict[str, Anchor]
    entities: list[Entity]
    integrity: Integrity
    version: str = "1.0"
    
    def to_dict(self) -> dict:
        """Serialize to dictionary for storage."""
        return {
            "envelope_version": self.version,
            "id": self.id,
            "source": {
                "uri": self.source.uri,
                "type": self.source.type,
                "fetched_at": self.source.fetched_at
            },
            "narrative": {
                "format": self.narrative.format,
                "content": self.narrative.content,
                "token_count": self.narrative.token_count,
                "noise_score": self.narrative.noise_score
            },
            "anchors": {
                k: {
                    "line_start": v.line_start,
                    "line_end": v.line_end,
                    "type": v.type,
                    "title": v.title
                } for k, v in self.anchors.items()
            },
            "structure": {
                "entities": [
                    {
                        "@type": e.type,
                        **e.properties,
                        "anchor_ref": e.anchor_ref,
                        "binding_confidence": e.binding_confidence
                    } for e in self.entities
                ]
            },
            "integrity": {
                "narrative_hash": self.integrity.narrative_hash,
                "structure_hash": self.integrity.structure_hash,
                "generated_at": self.integrity.generated_at
            }
        }
    
    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)
    
    def get_section_by_anchor(self, anchor_id: str) -> Optional[str]:
        """Extract narrative section by anchor ID."""
        anchor_id = anchor_id.lstrip('#')
        if anchor_id not in self.anchors:
            return None
        
        anchor = self.anchors[anchor_id]
        lines = self.narrative.content.split('\n')
        section_lines = lines[anchor.line_start:anchor.line_end + 1]
        return '\n'.join(section_lines)
    
    def get_entities_by_anchor(self, anchor_id: str) -> list[Entity]:
        """Get all entities linked to a specific anchor."""
        anchor_id = f"#{anchor_id}" if not anchor_id.startswith('#') else anchor_id
        return [e for e in self.entities if e.anchor_ref == anchor_id]
    
    def verify_integrity(self) -> bool:
        """Verify the narrative hash matches content."""
        computed_hash = f"sha256:{hashlib.sha256(self.narrative.content.encode()).hexdigest()}"
        return computed_hash == self.integrity.narrative_hash


class EnvelopeBuilder:
    """
    Fluent builder for creating AIO envelopes.
    
    Usage:
        envelope = (EnvelopeBuilder()
            .with_source("https://example.com", "web")
            .with_narrative(clean_markdown, token_count, noise_score)
            .with_anchors(anchors_dict)
            .with_entities(entities_list)
            .build())
    """
    
    def __init__(self):
        self._source: Optional[Source] = None
        self._narrative: Optional[Narrative] = None
        self._anchors: dict[str, Anchor] = {}
        self._entities: list[Entity] = []
    
    def with_source(self, uri: str, source_type: str) -> "EnvelopeBuilder":
        self._source = Source(uri=uri, type=source_type)
        return self
    
    def with_narrative(
        self, 
        content: str, 
        token_count: int = 0,
        noise_score: float = 0.0,
        format: str = "markdown"
    ) -> "EnvelopeBuilder":
        self._narrative = Narrative(
            format=format,
            content=content,
            token_count=token_count,
            noise_score=noise_score
        )
        return self
    
    def with_anchors(self, anchors: dict) -> "EnvelopeBuilder":
        for anchor_id, data in anchors.items():
            self._anchors[anchor_id] = Anchor(
                line_start=data["line_start"],
                line_end=data["line_end"],
                type=data.get("type", "section"),
                title=data.get("title")
            )
        return self
    
    def with_entities(self, entities: list[dict]) -> "EnvelopeBuilder":
        for e in entities:
            entity_type = e.pop("@type", e.pop("type", "Thing"))
            anchor_ref = e.pop("anchor_ref", None)
            confidence = e.pop("binding_confidence", 1.0)
            
            self._entities.append(Entity(
                type=entity_type,
                properties=e,
                anchor_ref=anchor_ref,
                binding_confidence=confidence
            ))
        return self
    
    def build(self) -> Envelope:
        if not self._source:
            raise ValueError("Source is required")
        if not self._narrative:
            raise ValueError("Narrative is required")
        
        # Generate ID from content hash
        content_hash = hashlib.sha256(self._narrative.content.encode()).hexdigest()[:8]
        envelope_id = f"doc-{content_hash}"
        
        # Generate integrity hashes
        narrative_hash = f"sha256:{hashlib.sha256(self._narrative.content.encode()).hexdigest()}"
        
        structure_content = json.dumps([e.properties for e in self._entities], sort_keys=True)
        structure_hash = f"sha256:{hashlib.sha256(structure_content.encode()).hexdigest()}"
        
        integrity = Integrity(
            narrative_hash=narrative_hash,
            structure_hash=structure_hash
        )
        
        return Envelope(
            id=envelope_id,
            source=self._source,
            narrative=self._narrative,
            anchors=self._anchors,
            entities=self._entities,
            integrity=integrity
        )
