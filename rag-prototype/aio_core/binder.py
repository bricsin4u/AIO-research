"""
Structure Binder - Links extracted entities to narrative anchors.

This is the CRITICAL component that prevents fact-mixing errors.

The problem: I find a price ($49.99) in the structure layer and a product
name ("Basic Plan") in the narrative. Without explicit binding, I might
incorrectly associate them.

The solution: Every entity gets an anchor_ref that points to the exact
section of narrative it came from. This creates a verifiable link between
structured facts and their source context.
"""

from dataclasses import dataclass
from typing import Optional
from .structure_extractor import ExtractedEntity


@dataclass
class BoundEntity:
    """An entity with a verified link to its narrative source."""
    entity: ExtractedEntity
    anchor_ref: Optional[str]
    binding_confidence: float
    binding_method: str  # "line_match", "content_match", "proximity", "unbound"


class StructureBinder:
    """
    Binds extracted entities to narrative anchors.
    
    Binding strategies (in order of confidence):
    1. Line match: Entity's line_number falls within anchor's line range
    2. Content match: Entity's source_text appears in anchor's content
    3. Proximity: Entity is near an anchor (lower confidence)
    4. Unbound: No suitable anchor found (flagged for review)
    """
    
    def __init__(self, proximity_threshold: int = 5):
        """
        Initialize the binder.
        
        Args:
            proximity_threshold: Max lines away to consider for proximity binding
        """
        self.proximity_threshold = proximity_threshold
    
    def bind(
        self,
        entities: list[ExtractedEntity],
        anchors: dict[str, dict],
        narrative: str
    ) -> list[BoundEntity]:
        """
        Bind entities to their source anchors.
        
        Args:
            entities: Extracted entities with line numbers
            anchors: Anchor dictionary from AnchorGenerator
            narrative: Original markdown content
            
        Returns:
            List of bound entities with anchor references
        """
        bound_entities = []
        lines = narrative.split('\n')
        
        for entity in entities:
            bound = self._bind_entity(entity, anchors, lines)
            bound_entities.append(bound)
        
        return bound_entities
    
    def _bind_entity(
        self,
        entity: ExtractedEntity,
        anchors: dict[str, dict],
        lines: list[str]
    ) -> BoundEntity:
        """Bind a single entity to an anchor."""
        
        # Strategy 1: Direct line match
        for anchor_id, anchor_data in anchors.items():
            if anchor_data["line_start"] <= entity.line_number <= anchor_data["line_end"]:
                return BoundEntity(
                    entity=entity,
                    anchor_ref=f"#{anchor_id}",
                    binding_confidence=1.0,
                    binding_method="line_match"
                )
        
        # Strategy 2: Content match (source_text appears in anchor content)
        for anchor_id, anchor_data in anchors.items():
            anchor_content = '\n'.join(
                lines[anchor_data["line_start"]:anchor_data["line_end"] + 1]
            )
            if entity.source_text in anchor_content:
                return BoundEntity(
                    entity=entity,
                    anchor_ref=f"#{anchor_id}",
                    binding_confidence=0.9,
                    binding_method="content_match"
                )
        
        # Strategy 3: Proximity (find nearest anchor)
        nearest_anchor = self._find_nearest_anchor(entity.line_number, anchors)
        if nearest_anchor:
            anchor_id, distance = nearest_anchor
            if distance <= self.proximity_threshold:
                # Confidence decreases with distance
                confidence = max(0.5, 0.8 - (distance * 0.05))
                return BoundEntity(
                    entity=entity,
                    anchor_ref=f"#{anchor_id}",
                    binding_confidence=confidence,
                    binding_method="proximity"
                )
        
        # Strategy 4: Unbound (no suitable anchor)
        return BoundEntity(
            entity=entity,
            anchor_ref=None,
            binding_confidence=0.0,
            binding_method="unbound"
        )
    
    def _find_nearest_anchor(
        self,
        line_number: int,
        anchors: dict[str, dict]
    ) -> Optional[tuple[str, int]]:
        """Find the anchor nearest to a line number."""
        nearest = None
        min_distance = float('inf')
        
        for anchor_id, anchor_data in anchors.items():
            # Distance to anchor range
            if line_number < anchor_data["line_start"]:
                distance = anchor_data["line_start"] - line_number
            elif line_number > anchor_data["line_end"]:
                distance = line_number - anchor_data["line_end"]
            else:
                distance = 0  # Inside anchor
            
            if distance < min_distance:
                min_distance = distance
                nearest = (anchor_id, distance)
        
        return nearest
    
    def to_entity_list(self, bound_entities: list[BoundEntity]) -> list[dict]:
        """
        Convert bound entities to a list suitable for the envelope.
        
        Args:
            bound_entities: List of bound entities
            
        Returns:
            List of entity dictionaries with anchor_ref
        """
        result = []
        
        for bound in bound_entities:
            entity_dict = {
                "@type": bound.entity.type,
                **bound.entity.properties,
                "anchor_ref": bound.anchor_ref,
                "binding_confidence": bound.binding_confidence,
                "_source": {
                    "text": bound.entity.source_text,
                    "line": bound.entity.line_number,
                    "method": bound.binding_method
                }
            }
            result.append(entity_dict)
        
        return result
    
    def get_binding_report(self, bound_entities: list[BoundEntity]) -> dict:
        """
        Generate a report on binding quality.
        
        Args:
            bound_entities: List of bound entities
            
        Returns:
            Dictionary with binding statistics
        """
        total = len(bound_entities)
        if total == 0:
            return {"total": 0, "bound": 0, "unbound": 0, "avg_confidence": 0}
        
        methods = {}
        confidences = []
        unbound_count = 0
        
        for bound in bound_entities:
            method = bound.binding_method
            methods[method] = methods.get(method, 0) + 1
            confidences.append(bound.binding_confidence)
            
            if bound.anchor_ref is None:
                unbound_count += 1
        
        return {
            "total": total,
            "bound": total - unbound_count,
            "unbound": unbound_count,
            "avg_confidence": sum(confidences) / len(confidences),
            "by_method": methods,
            "unbound_entities": [
                {
                    "type": b.entity.type,
                    "source_text": b.entity.source_text,
                    "line": b.entity.line_number
                }
                for b in bound_entities if b.anchor_ref is None
            ]
        }


class CrossLayerValidator:
    """
    Validates that structure and narrative layers are properly synchronized.
    
    This catches errors like:
    - Entities referencing non-existent anchors
    - Anchors with no linked entities (potential extraction gaps)
    - Mismatched content between layers
    """
    
    def validate(
        self,
        bound_entities: list[BoundEntity],
        anchors: dict[str, dict],
        narrative: str
    ) -> dict:
        """
        Validate cross-layer consistency.
        
        Returns:
            Validation report with issues found
        """
        issues = []
        lines = narrative.split('\n')
        
        # Check 1: All anchor_refs point to valid anchors
        for bound in bound_entities:
            if bound.anchor_ref:
                anchor_id = bound.anchor_ref.lstrip('#')
                if anchor_id not in anchors:
                    issues.append({
                        "type": "invalid_anchor_ref",
                        "entity_type": bound.entity.type,
                        "anchor_ref": bound.anchor_ref,
                        "message": f"Entity references non-existent anchor: {bound.anchor_ref}"
                    })
        
        # Check 2: Verify source_text appears in referenced anchor
        for bound in bound_entities:
            if bound.anchor_ref and bound.binding_method != "proximity":
                anchor_id = bound.anchor_ref.lstrip('#')
                if anchor_id in anchors:
                    anchor_data = anchors[anchor_id]
                    anchor_content = '\n'.join(
                        lines[anchor_data["line_start"]:anchor_data["line_end"] + 1]
                    )
                    if bound.entity.source_text not in anchor_content:
                        issues.append({
                            "type": "content_mismatch",
                            "entity_type": bound.entity.type,
                            "source_text": bound.entity.source_text,
                            "anchor_ref": bound.anchor_ref,
                            "message": "Entity source_text not found in referenced anchor"
                        })
        
        # Check 3: Identify anchors with no linked entities (informational)
        linked_anchors = set()
        for bound in bound_entities:
            if bound.anchor_ref:
                linked_anchors.add(bound.anchor_ref.lstrip('#'))
        
        unlinked_anchors = set(anchors.keys()) - linked_anchors
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "stats": {
                "total_entities": len(bound_entities),
                "total_anchors": len(anchors),
                "linked_anchors": len(linked_anchors),
                "unlinked_anchors": list(unlinked_anchors)
            }
        }
