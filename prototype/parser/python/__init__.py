"""
AIO Parser - AI Optimization Protocol Parser

A Python library for AIO-aware web content retrieval.
Implements the consumer-side ECR (Entropy-Controlled Retrieval) pipeline.

Usage:
    from aio_parser import parse
    
    # Parse with AIO detection
    envelope = parse("https://example.com/pricing", query="What is the price?")
    
    print(envelope.narrative)  # Clean markdown content
    print(envelope.tokens)     # Token count
    print(envelope.source_type)  # "aio" or "scraped"
"""

from .parser import parse, AIOParser
from .envelope import ContentEnvelope, ChunkIndex
from .discovery import discover_aio

__version__ = "0.1.0"
__all__ = ["parse", "AIOParser", "ContentEnvelope", "ChunkIndex", "discover_aio"]
