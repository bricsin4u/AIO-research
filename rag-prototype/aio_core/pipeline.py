"""
AIO Pipeline - The complete ingestion pipeline.

This module ties together all components to create AIO envelopes from raw content.

Usage:
    pipeline = AIOPipeline()
    envelope = pipeline.process_html(html_content, source_url)
    # or
    envelope = pipeline.process_markdown(markdown_content, source_uri)
"""

from typing import Optional
from .envelope import Envelope, EnvelopeBuilder
from .noise_stripper import NoiseStripper, StrippedContent
from .anchor_generator import AnchorGenerator
from .structure_extractor import StructureExtractor
from .binder import StructureBinder, CrossLayerValidator


class AIOPipeline:
    """
    Complete AIO ingestion pipeline.
    
    Processes raw content through:
    1. Noise stripping (HTML → clean markdown)
    2. Anchor generation (stable section IDs)
    3. Structure extraction (typed entities)
    4. Structure-narrative binding (link facts to context)
    5. Envelope creation (unified output)
    """
    
    def __init__(
        self,
        include_paragraph_anchors: bool = False,
        validate_bindings: bool = True
    ):
        """
        Initialize the pipeline.
        
        Args:
            include_paragraph_anchors: Generate anchors for paragraphs (more granular)
            validate_bindings: Run cross-layer validation after binding
        """
        self.noise_stripper = NoiseStripper()
        self.anchor_generator = AnchorGenerator(include_paragraphs=include_paragraph_anchors)
        self.structure_extractor = StructureExtractor()
        self.binder = StructureBinder()
        self.validator = CrossLayerValidator() if validate_bindings else None
    
    def process_html(
        self,
        html: str,
        source_url: str,
        source_type: str = "web"
    ) -> Envelope:
        """
        Process HTML content into an AIO envelope.
        
        Args:
            html: Raw HTML content
            source_url: URL or URI of the source
            source_type: Type of source (web, pdf, etc.)
            
        Returns:
            Complete AIO envelope
        """
        # Step 1: Strip noise
        stripped = self.noise_stripper.strip_html(html, source_url)
        
        # Continue with clean markdown
        return self._process_markdown(
            stripped.content,
            source_url,
            source_type,
            stripped.token_count,
            stripped.noise_score
        )
    
    def process_markdown(
        self,
        markdown: str,
        source_uri: str,
        source_type: str = "markdown"
    ) -> Envelope:
        """
        Process markdown content into an AIO envelope.
        
        Args:
            markdown: Markdown content
            source_uri: URI or path of the source
            source_type: Type of source
            
        Returns:
            Complete AIO envelope
        """
        # For markdown, we still run through noise stripper for cleanup
        stripped = self.noise_stripper.strip_text(markdown)
        
        return self._process_markdown(
            stripped.content,
            source_uri,
            source_type,
            stripped.token_count,
            stripped.noise_score
        )
    
    def _process_markdown(
        self,
        markdown: str,
        source_uri: str,
        source_type: str,
        token_count: int,
        noise_score: float
    ) -> Envelope:
        """Internal processing of clean markdown."""
        
        # Step 2: Generate anchors
        anchors = self.anchor_generator.generate(markdown)
        
        # Step 3: Extract structured entities
        entities = self.structure_extractor.extract(markdown)
        
        # Step 4: Bind entities to anchors
        bound_entities = self.binder.bind(entities, anchors, markdown)
        
        # Step 5: Validate bindings (optional)
        validation_result = None
        if self.validator:
            validation_result = self.validator.validate(bound_entities, anchors, markdown)
        
        # Step 6: Build envelope
        entity_list = self.binder.to_entity_list(bound_entities)
        
        envelope = (EnvelopeBuilder()
            .with_source(source_uri, source_type)
            .with_narrative(markdown, token_count, noise_score)
            .with_anchors(anchors)
            .with_entities(entity_list)
            .build())
        
        return envelope
    
    def process_with_report(
        self,
        html: str,
        source_url: str,
        source_type: str = "web"
    ) -> dict:
        """
        Process HTML and return envelope with detailed processing report.
        
        Useful for debugging and quality assessment.
        
        Returns:
            Dictionary with envelope and processing metrics
        """
        # Step 1: Strip noise
        stripped = self.noise_stripper.strip_html(html, source_url)
        
        # Step 2: Generate anchors
        anchors = self.anchor_generator.generate(stripped.content)
        
        # Step 3: Extract entities
        entities = self.structure_extractor.extract(stripped.content)
        
        # Step 4: Bind entities
        bound_entities = self.binder.bind(entities, anchors, stripped.content)
        binding_report = self.binder.get_binding_report(bound_entities)
        
        # Step 5: Validate
        validation_result = None
        if self.validator:
            validation_result = self.validator.validate(
                bound_entities, anchors, stripped.content
            )
        
        # Step 6: Build envelope
        entity_list = self.binder.to_entity_list(bound_entities)
        
        envelope = (EnvelopeBuilder()
            .with_source(source_url, source_type)
            .with_narrative(stripped.content, stripped.token_count, stripped.noise_score)
            .with_anchors(anchors)
            .with_entities(entity_list)
            .build())
        
        return {
            "envelope": envelope,
            "report": {
                "noise_stripping": {
                    "original_tokens": stripped.original_tokens,
                    "final_tokens": stripped.token_count,
                    "tokens_removed": stripped.tokens_removed,
                    "noise_score": stripped.noise_score
                },
                "anchors": {
                    "total": len(anchors),
                    "by_type": self._count_by_type(anchors, "type")
                },
                "entities": {
                    "total": len(entities),
                    "by_type": self._count_entity_types(entities)
                },
                "binding": binding_report,
                "validation": validation_result
            }
        }
    
    def _count_by_type(self, items: dict, type_key: str) -> dict:
        """Count items by type."""
        counts = {}
        for item in items.values():
            t = item.get(type_key, "unknown")
            counts[t] = counts.get(t, 0) + 1
        return counts
    
    def _count_entity_types(self, entities: list) -> dict:
        """Count entities by type."""
        counts = {}
        for entity in entities:
            t = entity.type
            counts[t] = counts.get(t, 0) + 1
        return counts


# Convenience function for quick processing
def create_envelope(
    content: str,
    source_uri: str,
    content_type: str = "html"
) -> Envelope:
    """
    Quick function to create an AIO envelope from content.
    
    Args:
        content: Raw content (HTML or markdown)
        source_uri: Source URI
        content_type: "html" or "markdown"
        
    Returns:
        AIO Envelope
    """
    pipeline = AIOPipeline()
    
    if content_type == "html":
        return pipeline.process_html(content, source_uri)
    else:
        return pipeline.process_markdown(content, source_uri)
