"""
Metrics - Token counting and relevance calculations for benchmarking.

Implements the metrics defined in the ECIA paper:
- Token Count
- Relevance Ratio
- Noise Score  
- Attention Tax
- Machine-Hostility Index
"""

import re
from typing import Tuple, Optional
from dataclasses import dataclass


@dataclass
class ContentMetrics:
    """Metrics for a single content retrieval."""
    url: str
    method: str  # "aio" | "scraped"
    
    # Size metrics
    raw_size: int  # Original HTML/raw size
    clean_size: int  # After cleaning
    
    # Token metrics (estimated)
    tokens_retrieved: int
    tokens_relevant: int  # Estimated relevant tokens
    
    # Derived metrics
    noise_score: float  # 1 - (clean/raw)
    relevance_ratio: float  # relevant/retrieved
    attention_tax: float  # 1 / (1 - noise_score)
    hostility_index: float  # 1 - (semantic/total)
    
    # Timing
    response_time_ms: float = 0.0
    
    def __post_init__(self):
        # Calculate derived metrics if not set
        if self.raw_size > 0 and self.noise_score == 0:
            self.noise_score = 1.0 - (self.clean_size / self.raw_size)
        
        if self.tokens_retrieved > 0 and self.relevance_ratio == 0:
            self.relevance_ratio = self.tokens_relevant / self.tokens_retrieved
        
        if self.noise_score < 1.0 and self.attention_tax == 0:
            self.attention_tax = 1.0 / (1.0 - self.noise_score)
    
    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "method": self.method,
            "raw_size": self.raw_size,
            "clean_size": self.clean_size,
            "tokens_retrieved": self.tokens_retrieved,
            "tokens_relevant": self.tokens_relevant,
            "noise_score": round(self.noise_score, 4),
            "relevance_ratio": round(self.relevance_ratio, 4),
            "attention_tax": round(self.attention_tax, 4),
            "hostility_index": round(self.hostility_index, 4),
            "response_time_ms": round(self.response_time_ms, 2),
        }


def estimate_tokens(text: str) -> int:
    """
    Estimate token count using character-based heuristic.
    
    GPT-4 tokenizer averages ~4 characters per token for English.
    This is a rough estimate - for exact counts, use tiktoken.
    """
    if not text:
        return 0
    
    # Remove excessive whitespace for more accurate estimate
    text = re.sub(r'\s+', ' ', text)
    
    # Rough estimate: 4 chars per token
    return len(text) // 4


def calculate_noise_score(original_size: int, clean_size: int) -> float:
    """
    Calculate noise score as defined in paper.
    
    noise_score = 1 - (clean_size / original_size)
    
    Returns value in [0, 1] where:
    - 0 = no noise (all content is useful)
    - 1 = all noise (no useful content)
    """
    if original_size <= 0:
        return 0.0
    
    ratio = clean_size / original_size
    return max(0.0, min(1.0, 1.0 - ratio))


def calculate_relevance_ratio(relevant_tokens: int, total_tokens: int) -> float:
    """
    Calculate relevance ratio as defined in paper.
    
    R = T_relevant / T_retrieved
    
    Returns value in [0, 1] where:
    - 0 = no relevant tokens
    - 1 = all tokens are relevant
    """
    if total_tokens <= 0:
        return 0.0
    
    return min(1.0, relevant_tokens / total_tokens)


def calculate_attention_tax(noise_score: float) -> float:
    """
    Calculate attention tax as defined in paper.
    
    τ = 1 / (1 - D)
    
    Where D is noise_score (digital noise).
    
    Returns overhead multiplier:
    - 1.0 = no overhead
    - 2.0 = 100% overhead
    - 10.0 = 900% overhead
    """
    if noise_score >= 1.0:
        return float('inf')
    
    return 1.0 / (1.0 - noise_score)


def calculate_hostility_index(semantic_payload: int, total_data: int) -> float:
    """
    Calculate Machine-Hostility Index as defined in paper.
    
    H_index = 1 - (|P_semantic| / |D_total|)
    
    Interpretation:
    - 0.0-0.3: Machine-friendly
    - 0.3-0.6: Moderate hostility
    - 0.6-0.9: High hostility
    - 0.9-1.0: Severe hostility
    """
    if total_data <= 0:
        return 0.0
    
    return max(0.0, min(1.0, 1.0 - (semantic_payload / total_data)))


def calculate_g_model_prediction(
    noise_score: float,
    intelligence: float = 1.0,
    base_error_rate: float = 0.05,
    attention_max: float = 1.0,
    alpha1: float = 0.3,
    alpha2: float = 0.7,
    d_threshold: float = 0.7
) -> float:
    """
    Calculate G (Stupidity Index) from the Machine-G Model.
    
    G_machine = α₁(B_err/I) + α₂(D_eff(D)/A)
    
    Where D_eff(D) = D * e^(max(0, D - D_thresh))
    
    Args:
        noise_score: D value (digital noise)
        intelligence: I value (model capability, normalized)
        base_error_rate: B_err (baseline error rate)
        attention_max: Maximum attention value
        alpha1, alpha2: Component weights
        d_threshold: Threshold for exponential noise growth
        
    Returns:
        G value in [0, 1] representing probability of error
    """
    import math
    
    # Calculate D_eff (effective noise with exponential growth)
    if noise_score > d_threshold:
        d_eff = noise_score * math.exp(noise_score - d_threshold)
    else:
        d_eff = noise_score
    
    # Calculate attention degradation
    # A = A_max / (1 + β * tokens * D)
    # Simplified: assume attention degrades linearly with noise
    attention = attention_max * (1.0 - noise_score * 0.5)
    attention = max(0.1, attention)  # Minimum attention
    
    # Calculate G components
    error_component = base_error_rate / intelligence if intelligence > 0 else 1.0
    noise_component = d_eff / attention if attention > 0 else 1.0
    
    # Combine
    g = alpha1 * error_component + alpha2 * noise_component
    
    return min(1.0, max(0.0, g))


def compare_methods(
    aio_tokens: int,
    scraped_tokens: int,
    aio_relevant: int,
    scraped_relevant: int
) -> dict:
    """
    Compare AIO vs scraped retrieval methods.
    
    Returns dict with:
    - token_reduction_percent
    - relevance_improvement_factor
    """
    # Token reduction
    if scraped_tokens > 0:
        token_reduction = ((scraped_tokens - aio_tokens) / scraped_tokens) * 100
    else:
        token_reduction = 0.0
    
    # Relevance improvement
    aio_ratio = aio_relevant / aio_tokens if aio_tokens > 0 else 0
    scraped_ratio = scraped_relevant / scraped_tokens if scraped_tokens > 0 else 0
    
    if scraped_ratio > 0:
        relevance_improvement = aio_ratio / scraped_ratio
    else:
        relevance_improvement = float('inf') if aio_ratio > 0 else 1.0
    
    return {
        "token_reduction_percent": round(token_reduction, 1),
        "aio_tokens": aio_tokens,
        "scraped_tokens": scraped_tokens,
        "aio_relevance_ratio": round(aio_ratio, 4),
        "scraped_relevance_ratio": round(scraped_ratio, 4),
        "relevance_improvement_factor": round(relevance_improvement, 1),
    }
