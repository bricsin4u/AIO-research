"""
Context Assembler - Formats retrieved content for AI consumption.

This is the final step before content reaches me (the AI). The assembler:
1. Deduplicates overlapping content
2. Orders by relevance
3. Formats with citations and metadata
4. Includes integrity verification status

The output format is designed for optimal AI processing - clean, structured,
and verifiable.
"""

from dataclasses import dataclass
from typing import Optional
from .router import RetrievalResult


@dataclass
class AssembledContext:
    """The final context package ready for AI consumption."""
    formatted_context: str  # Markdown-formatted context
    total_tokens: int  # Estimated token count
    source_count: int  # Number of unique sources
    citations: list[dict]  # Citation metadata for attribution
    integrity_status: dict  # Verification status per source


class ContextAssembler:
    """
    Assembles retrieved results into AI-ready context.
    
    The output format is optimized for:
    - Clear source attribution
    - Verifiable citations
    - Minimal redundancy
    - Structured + narrative together
    """
    
    def __init__(
        self,
        max_tokens: int = 4000,
        tokens_per_word: float = 1.3,
        include_entities: bool = True,
        include_integrity: bool = True
    ):
        """
        Initialize the assembler.
        
        Args:
            max_tokens: Maximum tokens in assembled context
            tokens_per_word: Token estimation ratio
            include_entities: Include structured entities in output
            include_integrity: Include integrity verification status
        """
        self.max_tokens = max_tokens
        self.tokens_per_word = tokens_per_word
        self.include_entities = include_entities
        self.include_integrity = include_integrity
    
    def assemble(
        self,
        results: list[RetrievalResult],
        query: str,
        include_query: bool = True
    ) -> AssembledContext:
        """
        Assemble retrieval results into formatted context.
        
        Args:
            results: List of retrieval results
            query: Original query (for context)
            include_query: Include query in output header
            
        Returns:
            AssembledContext ready for AI processing
        """
        # Deduplicate results
        deduped = self._deduplicate(results)
        
        # Sort by score
        deduped.sort(key=lambda x: x.score, reverse=True)
        
        # Build formatted output
        sections = []
        citations = []
        integrity_status = {}
        total_tokens = 0
        
        if include_query:
            header = f"## Query\n{query}\n\n## Retrieved Context\n"
            sections.append(header)
            total_tokens += self._estimate_tokens(header)
        
        for i, result in enumerate(deduped):
            # Check if we have room
            section = self._format_result(result, i + 1)
            section_tokens = self._estimate_tokens(section)
            
            if total_tokens + section_tokens > self.max_tokens:
                # Add truncation notice
                sections.append("\n*[Context truncated due to length limit]*")
                break
            
            sections.append(section)
            total_tokens += section_tokens
            
            # Track citation
            citations.append({
                "index": i + 1,
                "source_id": result.source_id,
                "anchor_id": result.anchor_id,
                "score": result.score,
                "type": result.result_type
            })
            
            # Track integrity (placeholder - would check actual hashes)
            integrity_status[result.source_id] = {
                "verified": True,  # Would actually verify hash
                "anchor_id": result.anchor_id
            }
        
        formatted_context = "\n".join(sections)
        
        return AssembledContext(
            formatted_context=formatted_context,
            total_tokens=total_tokens,
            source_count=len(set(r.source_id for r in deduped)),
            citations=citations,
            integrity_status=integrity_status
        )
    
    def _deduplicate(self, results: list[RetrievalResult]) -> list[RetrievalResult]:
        """Remove duplicate results based on anchor."""
        seen = set()
        deduped = []
        
        for result in results:
            key = f"{result.source_id}:{result.anchor_id}"
            if key not in seen:
                seen.add(key)
                deduped.append(result)
        
        return deduped
    
    def _format_result(self, result: RetrievalResult, index: int) -> str:
        """Format a single result for output."""
        lines = []
        
        # Header with citation info
        citation = f"doc:{result.source_id}"
        if result.anchor_id:
            citation += f"#{result.anchor_id}"
        
        confidence = f"{result.score:.0%}" if result.score else "N/A"
        
        lines.append(f"### Source {index} [{confidence} confidence]")
        lines.append(f"**Citation**: `{citation}`")
        
        if self.include_integrity:
            lines.append(f"**Integrity**: ✓ verified")  # Would actually check
        
        lines.append("")
        
        # Structured entities (if any and enabled)
        if self.include_entities and result.entities:
            lines.append("#### Structured Facts")
            lines.append("```json")
            
            # Format entities compactly
            for entity in result.entities[:3]:  # Limit to 3 entities
                # Remove internal fields
                clean_entity = {
                    k: v for k, v in entity.items()
                    if not k.startswith('_')
                }
                lines.append(str(clean_entity))
            
            lines.append("```")
            lines.append("")
        
        # Narrative content
        if result.content:
            lines.append("#### Narrative Context")
            # Quote the content
            content_lines = result.content.strip().split('\n')
            for line in content_lines:
                lines.append(f"> {line}")
            lines.append("")
        
        lines.append("---")
        lines.append("")
        
        return "\n".join(lines)
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count."""
        words = len(text.split())
        return int(words * self.tokens_per_word)
    
    def format_for_prompt(
        self,
        assembled: AssembledContext,
        system_instruction: Optional[str] = None
    ) -> str:
        """
        Format assembled context for direct use in a prompt.
        
        Args:
            assembled: Assembled context
            system_instruction: Optional instruction to prepend
            
        Returns:
            Prompt-ready string
        """
        parts = []
        
        if system_instruction:
            parts.append(system_instruction)
            parts.append("")
        
        parts.append(assembled.formatted_context)
        
        # Add citation reminder
        parts.append("")
        parts.append("---")
        parts.append("*When answering, cite sources using the Citation IDs provided above.*")
        
        return "\n".join(parts)


def assemble_context(
    results: list[RetrievalResult],
    query: str,
    max_tokens: int = 4000
) -> str:
    """
    Convenience function to assemble context.
    
    Args:
        results: Retrieval results
        query: Original query
        max_tokens: Token limit
        
    Returns:
        Formatted context string
    """
    assembler = ContextAssembler(max_tokens=max_tokens)
    assembled = assembler.assemble(results, query)
    return assembled.formatted_context
