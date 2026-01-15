"""
Intent Classifier - Determines the optimal retrieval strategy for a query.

Why this matters: A "what is the price?" query should hit the structure index
directly. An "explain how X works" query should use vector search on narrative.
Using the wrong strategy wastes tokens and reduces accuracy.

This is the "Attention Control" (A) optimization from the G-model.
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class QueryIntent(Enum):
    """Types of query intents that determine retrieval strategy."""
    
    FACT_EXTRACTION = "fact_extraction"
    # Single fact lookup: "What is X?", "How much does Y cost?"
    # Strategy: Structure-first, validate with narrative
    
    EXPLANATION = "explanation"
    # Conceptual understanding: "Explain X", "How does Y work?"
    # Strategy: Narrative-first with vector search
    
    COMPARISON = "comparison"
    # Multi-entity analysis: "Compare X and Y", "Difference between A and B"
    # Strategy: Hybrid parallel - need both entities with equal depth
    
    ENUMERATION = "enumeration"
    # Collection queries: "List all X", "What are the features?"
    # Strategy: Structure aggregate, then narrative for context
    
    VERIFICATION = "verification"
    # Fact checking: "Is it true that X?", "Does Y support Z?"
    # Strategy: Structure-first, verify against narrative
    
    PROCEDURAL = "procedural"
    # How-to queries: "How do I X?", "Steps to Y"
    # Strategy: Narrative-first, look for ordered content
    
    UNKNOWN = "unknown"
    # Fallback: Use balanced hybrid approach


@dataclass
class ClassifiedQuery:
    """Result of query classification."""
    query: str
    intent: QueryIntent
    strategy: str
    confidence: float
    extracted_entities: list[str]  # Entities mentioned in query
    constraints: dict  # Extracted constraints (dates, numbers, etc.)


class IntentClassifier:
    """
    Classifies queries to determine optimal retrieval strategy.
    
    Uses pattern matching and keyword analysis. For production,
    consider using a small classifier model for better accuracy.
    """
    
    # Intent patterns: (pattern, intent, confidence_boost)
    INTENT_PATTERNS = [
        # Fact extraction
        (r'\b(what is|what\'s|what are)\b', QueryIntent.FACT_EXTRACTION, 0.3),
        (r'\b(how much|how many|price|cost)\b', QueryIntent.FACT_EXTRACTION, 0.4),
        (r'\b(when did|when was|when is)\b', QueryIntent.FACT_EXTRACTION, 0.3),
        (r'\b(who is|who was|who are)\b', QueryIntent.FACT_EXTRACTION, 0.3),
        (r'\b(where is|where are)\b', QueryIntent.FACT_EXTRACTION, 0.3),
        
        # Explanation
        (r'\b(explain|describe|tell me about)\b', QueryIntent.EXPLANATION, 0.4),
        (r'\b(why does|why is|why do)\b', QueryIntent.EXPLANATION, 0.3),
        (r'\b(how does|how do)\b', QueryIntent.EXPLANATION, 0.3),
        (r'\b(what does .+ mean)\b', QueryIntent.EXPLANATION, 0.3),
        
        # Comparison
        (r'\b(compare|comparison|versus|vs\.?)\b', QueryIntent.COMPARISON, 0.5),
        (r'\b(difference between|differ from)\b', QueryIntent.COMPARISON, 0.5),
        (r'\b(better|worse|faster|slower) than\b', QueryIntent.COMPARISON, 0.4),
        (r'\b(which is|which one)\b', QueryIntent.COMPARISON, 0.3),
        
        # Enumeration
        (r'\b(list|enumerate|show all)\b', QueryIntent.ENUMERATION, 0.5),
        (r'\b(what are the|what are all)\b', QueryIntent.ENUMERATION, 0.4),
        (r'\b(how many .+ are there)\b', QueryIntent.ENUMERATION, 0.4),
        (r'\b(all the|every)\b', QueryIntent.ENUMERATION, 0.3),
        
        # Verification
        (r'\b(is it true|is it correct)\b', QueryIntent.VERIFICATION, 0.5),
        (r'\b(does .+ (support|have|include))\b', QueryIntent.VERIFICATION, 0.4),
        (r'\b(can .+ (do|be|have))\b', QueryIntent.VERIFICATION, 0.3),
        (r'\b(verify|confirm|check if)\b', QueryIntent.VERIFICATION, 0.5),
        
        # Procedural
        (r'\b(how (do|can|to) I)\b', QueryIntent.PROCEDURAL, 0.5),
        (r'\b(steps to|guide to|tutorial)\b', QueryIntent.PROCEDURAL, 0.5),
        (r'\b(instructions for|how to)\b', QueryIntent.PROCEDURAL, 0.4),
    ]
    
    # Strategy mapping
    STRATEGIES = {
        QueryIntent.FACT_EXTRACTION: "structure_first",
        QueryIntent.EXPLANATION: "narrative_first",
        QueryIntent.COMPARISON: "hybrid_parallel",
        QueryIntent.ENUMERATION: "structure_aggregate",
        QueryIntent.VERIFICATION: "structure_verify",
        QueryIntent.PROCEDURAL: "narrative_ordered",
        QueryIntent.UNKNOWN: "hybrid_balanced",
    }
    
    def __init__(self):
        self._compiled_patterns = [
            (re.compile(pattern, re.IGNORECASE), intent, boost)
            for pattern, intent, boost in self.INTENT_PATTERNS
        ]
    
    def classify(self, query: str) -> ClassifiedQuery:
        """
        Classify a query to determine retrieval strategy.
        
        Args:
            query: User's query string
            
        Returns:
            ClassifiedQuery with intent, strategy, and extracted info
        """
        query_lower = query.lower()
        
        # Score each intent
        intent_scores = {intent: 0.0 for intent in QueryIntent}
        
        for pattern, intent, boost in self._compiled_patterns:
            if pattern.search(query_lower):
                intent_scores[intent] += boost
        
        # Find best intent
        best_intent = max(intent_scores, key=intent_scores.get)
        best_score = intent_scores[best_intent]
        
        # If no strong signal, default to UNKNOWN
        if best_score < 0.2:
            best_intent = QueryIntent.UNKNOWN
            confidence = 0.3
        else:
            # Normalize confidence
            confidence = min(0.95, 0.5 + best_score)
        
        # Extract entities and constraints
        entities = self._extract_entities(query)
        constraints = self._extract_constraints(query)
        
        return ClassifiedQuery(
            query=query,
            intent=best_intent,
            strategy=self.STRATEGIES[best_intent],
            confidence=confidence,
            extracted_entities=entities,
            constraints=constraints
        )
    
    def _extract_entities(self, query: str) -> list[str]:
        """Extract potential entity names from query."""
        entities = []
        
        # Look for quoted strings
        quoted = re.findall(r'"([^"]+)"', query)
        entities.extend(quoted)
        
        # Look for capitalized words (potential proper nouns)
        # Skip common words at start of sentences
        words = query.split()
        for i, word in enumerate(words):
            if i > 0 and word[0].isupper() and len(word) > 2:
                # Clean punctuation
                clean_word = re.sub(r'[^\w]', '', word)
                if clean_word:
                    entities.append(clean_word)
        
        return entities
    
    def _extract_constraints(self, query: str) -> dict:
        """Extract constraints like dates, numbers, specific values."""
        constraints = {}
        
        # Extract dates
        date_patterns = [
            r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})',
            r'((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4})',
        ]
        for pattern in date_patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            if matches:
                constraints["dates"] = matches
        
        # Extract numbers/prices
        price_matches = re.findall(r'\$(\d+(?:\.\d{2})?)', query)
        if price_matches:
            constraints["prices"] = [float(p) for p in price_matches]
        
        number_matches = re.findall(r'\b(\d+)\b', query)
        if number_matches:
            constraints["numbers"] = [int(n) for n in number_matches]
        
        # Extract version numbers
        version_matches = re.findall(r'v?(\d+\.\d+(?:\.\d+)?)', query)
        if version_matches:
            constraints["versions"] = version_matches
        
        return constraints
    
    def get_strategy_description(self, intent: QueryIntent) -> str:
        """Get human-readable description of the retrieval strategy."""
        descriptions = {
            QueryIntent.FACT_EXTRACTION: 
                "Query structured index first, fetch narrative anchor for context",
            QueryIntent.EXPLANATION:
                "Vector search on narrative, expand to full sections",
            QueryIntent.COMPARISON:
                "Retrieve both entities in parallel with equal context depth",
            QueryIntent.ENUMERATION:
                "Aggregate from structure index, add narrative context",
            QueryIntent.VERIFICATION:
                "Check structure for fact, verify against narrative source",
            QueryIntent.PROCEDURAL:
                "Search narrative for ordered/sequential content",
            QueryIntent.UNKNOWN:
                "Balanced hybrid: structure + narrative with equal weight",
        }
        return descriptions.get(intent, "Unknown strategy")
