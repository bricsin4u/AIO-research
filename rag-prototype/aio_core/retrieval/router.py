"""
Retrieval Router - Routes queries to the optimal retrieval path.

This is where the magic happens. Instead of blindly vector-searching everything,
we route queries based on intent:

- Fact queries → Structure index (fast, precise)
- Explanation queries → Vector search on narrative (semantic)
- Comparison queries → Parallel retrieval of both entities

The router is designed to work with any backend (Pinecone, Milvus, Weaviate, etc.)
through abstract index interfaces.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Any
from .intent_classifier import IntentClassifier, ClassifiedQuery, QueryIntent


@dataclass
class RetrievalResult:
    """A single retrieval result with metadata."""
    content: str
    anchor_id: Optional[str]
    source_id: str  # Envelope ID
    score: float
    result_type: str  # "structured", "narrative", "hybrid"
    entities: list[dict]  # Related structured entities
    metadata: dict


class IndexInterface(ABC):
    """Abstract interface for index backends."""
    
    @abstractmethod
    def query_structure(self, query: str, filters: dict = None, limit: int = 10) -> list[dict]:
        """Query the structured entity index."""
        pass
    
    @abstractmethod
    def query_narrative(self, query: str, limit: int = 10) -> list[dict]:
        """Vector search on narrative content."""
        pass
    
    @abstractmethod
    def get_by_anchor(self, envelope_id: str, anchor_id: str) -> Optional[dict]:
        """Get narrative section by anchor ID."""
        pass
    
    @abstractmethod
    def get_entities_by_anchor(self, envelope_id: str, anchor_id: str) -> list[dict]:
        """Get entities linked to an anchor."""
        pass


class RetrievalRouter:
    """
    Routes queries to optimal retrieval paths based on intent.
    
    This is the "Attention Control" (A) mechanism - it ensures I only
    process relevant content for each query type.
    """
    
    def __init__(self, index: IndexInterface):
        """
        Initialize the router.
        
        Args:
            index: Backend index implementing IndexInterface
        """
        self.index = index
        self.classifier = IntentClassifier()
    
    def retrieve(
        self,
        query: str,
        limit: int = 5,
        expand_sections: bool = True
    ) -> list[RetrievalResult]:
        """
        Retrieve relevant content for a query.
        
        Args:
            query: User's query
            limit: Maximum results to return
            expand_sections: If True, expand chunks to full sections
            
        Returns:
            List of retrieval results with content and metadata
        """
        # Classify the query
        classified = self.classifier.classify(query)
        
        # Route to appropriate strategy
        strategy = classified.strategy
        
        if strategy == "structure_first":
            return self._structure_first(classified, limit, expand_sections)
        elif strategy == "narrative_first":
            return self._narrative_first(classified, limit, expand_sections)
        elif strategy == "hybrid_parallel":
            return self._hybrid_parallel(classified, limit, expand_sections)
        elif strategy == "structure_aggregate":
            return self._structure_aggregate(classified, limit, expand_sections)
        elif strategy == "structure_verify":
            return self._structure_verify(classified, limit, expand_sections)
        elif strategy == "narrative_ordered":
            return self._narrative_ordered(classified, limit, expand_sections)
        else:
            return self._hybrid_balanced(classified, limit, expand_sections)
    
    def _structure_first(
        self,
        classified: ClassifiedQuery,
        limit: int,
        expand_sections: bool
    ) -> list[RetrievalResult]:
        """
        Structure-first retrieval for fact extraction.
        
        1. Query structured index for matching entities
        2. Get narrative context via anchor_ref
        3. Return structured fact + narrative context
        """
        results = []
        
        # Build filters from constraints
        filters = self._build_filters(classified.constraints)
        
        # Query structure index
        entities = self.index.query_structure(classified.query, filters, limit)
        
        for entity in entities:
            result = RetrievalResult(
                content="",  # Will be filled with narrative
                anchor_id=entity.get("anchor_ref"),
                source_id=entity.get("_envelope_id", "unknown"),
                score=entity.get("_score", 1.0),
                result_type="structured",
                entities=[entity],
                metadata={"strategy": "structure_first"}
            )
            
            # Fetch narrative context if anchor exists
            if entity.get("anchor_ref") and expand_sections:
                anchor_id = entity["anchor_ref"].lstrip('#')
                narrative = self.index.get_by_anchor(
                    entity.get("_envelope_id"),
                    anchor_id
                )
                if narrative:
                    result.content = narrative.get("content", "")
            
            results.append(result)
        
        return results
    
    def _narrative_first(
        self,
        classified: ClassifiedQuery,
        limit: int,
        expand_sections: bool
    ) -> list[RetrievalResult]:
        """
        Narrative-first retrieval for explanations.
        
        1. Vector search on narrative content
        2. Expand to full sections (no fragments!)
        3. Attach related structured entities
        """
        results = []
        
        # Vector search
        chunks = self.index.query_narrative(classified.query, limit * 2)
        
        # Deduplicate by anchor (expand to sections)
        seen_anchors = set()
        
        for chunk in chunks:
            anchor_id = chunk.get("anchor_id")
            envelope_id = chunk.get("_envelope_id")
            
            # Skip if we've already included this section
            key = f"{envelope_id}:{anchor_id}"
            if key in seen_anchors:
                continue
            seen_anchors.add(key)
            
            # Get full section content
            content = chunk.get("content", "")
            if expand_sections and anchor_id:
                section = self.index.get_by_anchor(envelope_id, anchor_id)
                if section:
                    content = section.get("content", content)
            
            # Get related entities
            entities = []
            if anchor_id:
                entities = self.index.get_entities_by_anchor(envelope_id, anchor_id)
            
            results.append(RetrievalResult(
                content=content,
                anchor_id=anchor_id,
                source_id=envelope_id,
                score=chunk.get("_score", 0.5),
                result_type="narrative",
                entities=entities,
                metadata={"strategy": "narrative_first"}
            ))
            
            if len(results) >= limit:
                break
        
        return results
    
    def _hybrid_parallel(
        self,
        classified: ClassifiedQuery,
        limit: int,
        expand_sections: bool
    ) -> list[RetrievalResult]:
        """
        Hybrid parallel retrieval for comparisons.
        
        1. Identify comparison targets from query
        2. Retrieve both targets with equal depth
        3. Ensure balanced context for fair comparison
        """
        results = []
        
        # Extract comparison targets
        targets = classified.extracted_entities
        if len(targets) < 2:
            # Fall back to balanced hybrid
            return self._hybrid_balanced(classified, limit, expand_sections)
        
        # Retrieve each target
        per_target_limit = max(2, limit // len(targets))
        
        for target in targets[:2]:  # Compare first two targets
            # Query structure for this target
            target_entities = self.index.query_structure(
                target, 
                filters=None, 
                limit=per_target_limit
            )
            
            for entity in target_entities:
                content = ""
                if entity.get("anchor_ref") and expand_sections:
                    anchor_id = entity["anchor_ref"].lstrip('#')
                    narrative = self.index.get_by_anchor(
                        entity.get("_envelope_id"),
                        anchor_id
                    )
                    if narrative:
                        content = narrative.get("content", "")
                
                results.append(RetrievalResult(
                    content=content,
                    anchor_id=entity.get("anchor_ref"),
                    source_id=entity.get("_envelope_id", "unknown"),
                    score=entity.get("_score", 1.0),
                    result_type="hybrid",
                    entities=[entity],
                    metadata={
                        "strategy": "hybrid_parallel",
                        "comparison_target": target
                    }
                ))
        
        return results[:limit]
    
    def _structure_aggregate(
        self,
        classified: ClassifiedQuery,
        limit: int,
        expand_sections: bool
    ) -> list[RetrievalResult]:
        """
        Structure aggregate for enumeration queries.
        
        1. Query structure index for all matching entities
        2. Group by type
        3. Add narrative context for each group
        """
        # Query for more entities since we're aggregating
        entities = self.index.query_structure(classified.query, limit=limit * 3)
        
        # Group by type
        by_type = {}
        for entity in entities:
            entity_type = entity.get("@type", "Thing")
            if entity_type not in by_type:
                by_type[entity_type] = []
            by_type[entity_type].append(entity)
        
        results = []
        for entity_type, type_entities in by_type.items():
            # Create aggregate result
            content_parts = []
            all_entities = []
            
            for entity in type_entities[:limit]:
                all_entities.append(entity)
                
                if entity.get("anchor_ref") and expand_sections:
                    anchor_id = entity["anchor_ref"].lstrip('#')
                    narrative = self.index.get_by_anchor(
                        entity.get("_envelope_id"),
                        anchor_id
                    )
                    if narrative:
                        content_parts.append(narrative.get("content", ""))
            
            results.append(RetrievalResult(
                content="\n\n---\n\n".join(content_parts),
                anchor_id=None,  # Aggregate, no single anchor
                source_id="aggregate",
                score=1.0,
                result_type="aggregate",
                entities=all_entities,
                metadata={
                    "strategy": "structure_aggregate",
                    "entity_type": entity_type,
                    "count": len(type_entities)
                }
            ))
        
        return results[:limit]
    
    def _structure_verify(
        self,
        classified: ClassifiedQuery,
        limit: int,
        expand_sections: bool
    ) -> list[RetrievalResult]:
        """
        Structure-verify for fact checking.
        
        1. Query structure for the claimed fact
        2. Fetch narrative source for verification
        3. Include verification metadata
        """
        # Similar to structure_first but with verification emphasis
        results = self._structure_first(classified, limit, expand_sections)
        
        # Add verification metadata
        for result in results:
            result.metadata["strategy"] = "structure_verify"
            result.metadata["verification_required"] = True
        
        return results
    
    def _narrative_ordered(
        self,
        classified: ClassifiedQuery,
        limit: int,
        expand_sections: bool
    ) -> list[RetrievalResult]:
        """
        Narrative-ordered for procedural queries.
        
        1. Search for procedural content (steps, instructions)
        2. Preserve document order
        3. Look for numbered/ordered sections
        """
        # Search narrative with procedural bias
        chunks = self.index.query_narrative(classified.query, limit * 2)
        
        # Sort by document position to preserve order
        chunks.sort(key=lambda x: (
            x.get("_envelope_id", ""),
            x.get("_line_start", 0)
        ))
        
        results = []
        seen_anchors = set()
        
        for chunk in chunks:
            anchor_id = chunk.get("anchor_id")
            envelope_id = chunk.get("_envelope_id")
            
            key = f"{envelope_id}:{anchor_id}"
            if key in seen_anchors:
                continue
            seen_anchors.add(key)
            
            content = chunk.get("content", "")
            if expand_sections and anchor_id:
                section = self.index.get_by_anchor(envelope_id, anchor_id)
                if section:
                    content = section.get("content", content)
            
            results.append(RetrievalResult(
                content=content,
                anchor_id=anchor_id,
                source_id=envelope_id,
                score=chunk.get("_score", 0.5),
                result_type="narrative",
                entities=[],
                metadata={
                    "strategy": "narrative_ordered",
                    "position": chunk.get("_line_start", 0)
                }
            ))
            
            if len(results) >= limit:
                break
        
        return results
    
    def _hybrid_balanced(
        self,
        classified: ClassifiedQuery,
        limit: int,
        expand_sections: bool
    ) -> list[RetrievalResult]:
        """
        Balanced hybrid for unknown intent.
        
        1. Query both structure and narrative
        2. Merge results with equal weight
        3. Deduplicate by anchor
        """
        results = []
        
        # Get structure results
        structure_results = self._structure_first(
            classified, 
            limit // 2, 
            expand_sections
        )
        
        # Get narrative results
        narrative_results = self._narrative_first(
            classified,
            limit // 2,
            expand_sections
        )
        
        # Interleave results
        seen_anchors = set()
        
        for s_result, n_result in zip(structure_results, narrative_results):
            for result in [s_result, n_result]:
                key = f"{result.source_id}:{result.anchor_id}"
                if key not in seen_anchors:
                    seen_anchors.add(key)
                    result.metadata["strategy"] = "hybrid_balanced"
                    results.append(result)
        
        # Add remaining results
        for result in structure_results + narrative_results:
            key = f"{result.source_id}:{result.anchor_id}"
            if key not in seen_anchors:
                seen_anchors.add(key)
                result.metadata["strategy"] = "hybrid_balanced"
                results.append(result)
        
        return results[:limit]
    
    def _build_filters(self, constraints: dict) -> dict:
        """Build index filters from query constraints."""
        filters = {}
        
        if "prices" in constraints:
            filters["price_range"] = {
                "min": min(constraints["prices"]) * 0.8,
                "max": max(constraints["prices"]) * 1.2
            }
        
        if "dates" in constraints:
            filters["dates"] = constraints["dates"]
        
        if "versions" in constraints:
            filters["versions"] = constraints["versions"]
        
        return filters if filters else None
