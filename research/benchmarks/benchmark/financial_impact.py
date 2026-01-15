#!/usr/bin/env python3
"""
Financial Impact Calculator - Real-world savings from AIO adoption.

Calculates cost savings at scale for:
1. AI Search companies (Perplexity, Google AI Overviews)
2. Enterprise RAG deployments
3. Autonomous agents

Based on benchmark data:
- 100% accuracy (AIO) vs 57% (scraped) 
- 6x speed improvement
- Token efficiency per correct answer: 27% better
"""

import json
from dataclasses import dataclass
from typing import Dict


@dataclass
class ScaleScenario:
    """A usage scenario at scale."""
    name: str
    queries_per_day: int
    avg_pages_per_query: int  # How many web pages retrieved per query
    description: str


# Real-world scale scenarios
SCENARIOS = [
    ScaleScenario(
        name="Perplexity-scale",
        queries_per_day=10_000_000,  # ~10M queries/day estimated
        avg_pages_per_query=5,
        description="AI search engine processing millions of queries daily"
    ),
    ScaleScenario(
        name="Google AI Overviews",
        queries_per_day=500_000_000,  # Fraction of Google's 8.5B daily searches
        avg_pages_per_query=3,
        description="Google's AI-powered search summaries"
    ),
    ScaleScenario(
        name="Enterprise RAG",
        queries_per_day=100_000,
        avg_pages_per_query=10,
        description="Large enterprise with internal knowledge base"
    ),
    ScaleScenario(
        name="AI Agent Platform",
        queries_per_day=1_000_000,
        avg_pages_per_query=8,
        description="Platform running autonomous AI agents (browsing, research)"
    ),
]

# LLM pricing (per 1M tokens, input)
LLM_PRICING = {
    "GPT-4o": 2.50,      # $2.50 per 1M input tokens
    "GPT-4-turbo": 10.00,
    "Claude-3.5-Sonnet": 3.00,
    "Claude-3-Opus": 15.00,
    "Gemini-1.5-Pro": 1.25,
}

# Benchmark results (from our tests)
BENCHMARK_DATA = {
    "scraped": {
        "avg_tokens_per_page": 317,
        "accuracy": 0.57,  # 57% - answer found
        "avg_time_ms": 29,
    },
    "aio_targeted": {
        "avg_tokens_per_page": 405,  # When answer IS found (higher quality)
        "accuracy": 1.00,  # 100% - answer found
        "avg_time_ms": 5,
    }
}

# But wait - for FAILED queries, scraping wastes tokens
# Effective tokens per CORRECT answer:
TOKENS_PER_CORRECT_ANSWER = {
    "scraped": 555,  # 317 tokens / 0.57 accuracy
    "aio_targeted": 405,  # 405 tokens / 1.0 accuracy  
}


def calculate_savings(scenario: ScaleScenario, llm_model: str = "GPT-4o") -> Dict:
    """Calculate annual savings for a scenario."""
    
    price_per_million = LLM_PRICING[llm_model]
    
    # Daily page retrievals
    pages_per_day = scenario.queries_per_day * scenario.avg_pages_per_query
    
    # Annual volume
    pages_per_year = pages_per_day * 365
    
    # === SCRAPING APPROACH ===
    # Tokens used (many wasted on failed extractions)
    scraped_tokens_year = pages_per_year * TOKENS_PER_CORRECT_ANSWER["scraped"]
    scraped_cost_year = (scraped_tokens_year / 1_000_000) * price_per_million
    
    # Failures (need re-query, human review, or bad answers)
    failure_rate = 1 - BENCHMARK_DATA["scraped"]["accuracy"]
    failed_queries_year = scenario.queries_per_day * 365 * failure_rate
    
    # Cost of failures (conservative: $0.10 per failed query for re-processing)
    failure_cost = failed_queries_year * 0.10
    
    scraped_total_cost = scraped_cost_year + failure_cost
    
    # === AIO APPROACH ===
    aio_tokens_year = pages_per_year * TOKENS_PER_CORRECT_ANSWER["aio_targeted"]
    aio_cost_year = (aio_tokens_year / 1_000_000) * price_per_million
    
    # No failures to account for
    aio_total_cost = aio_cost_year
    
    # === SAVINGS ===
    annual_savings = scraped_total_cost - aio_total_cost
    savings_percent = (annual_savings / scraped_total_cost) * 100 if scraped_total_cost > 0 else 0
    
    # === SPEED BENEFITS ===
    # Time saved per page
    time_saved_per_page_ms = BENCHMARK_DATA["scraped"]["avg_time_ms"] - BENCHMARK_DATA["aio_targeted"]["avg_time_ms"]
    time_saved_year_hours = (pages_per_year * time_saved_per_page_ms) / 1000 / 3600
    
    # Infrastructure cost (servers for processing) - rough estimate
    # Assume $0.10 per CPU-hour
    infra_savings = time_saved_year_hours * 0.10
    
    return {
        "scenario": scenario.name,
        "description": scenario.description,
        "llm_model": llm_model,
        "pages_per_year": pages_per_year,
        
        # Token comparison
        "scraped_tokens_per_page_effective": TOKENS_PER_CORRECT_ANSWER["scraped"],
        "aio_tokens_per_page_effective": TOKENS_PER_CORRECT_ANSWER["aio_targeted"],
        "token_efficiency_gain_percent": round(
            (1 - TOKENS_PER_CORRECT_ANSWER["aio_targeted"] / TOKENS_PER_CORRECT_ANSWER["scraped"]) * 100, 1
        ),
        
        # Accuracy
        "scraped_accuracy": f"{BENCHMARK_DATA['scraped']['accuracy'] * 100:.0f}%",
        "aio_accuracy": f"{BENCHMARK_DATA['aio_targeted']['accuracy'] * 100:.0f}%",
        "failed_queries_avoided_per_year": int(failed_queries_year),
        
        # Financial
        "scraped_llm_cost_year": round(scraped_cost_year, 0),
        "scraped_failure_cost_year": round(failure_cost, 0),
        "scraped_total_cost_year": round(scraped_total_cost, 0),
        "aio_total_cost_year": round(aio_total_cost, 0),
        "annual_savings": round(annual_savings, 0),
        "savings_percent": round(savings_percent, 1),
        
        # Speed
        "time_saved_per_page_ms": time_saved_per_page_ms,
        "processing_hours_saved_year": round(time_saved_year_hours, 0),
        "infra_savings_year": round(infra_savings, 0),
        
        # Total value
        "total_annual_value": round(annual_savings + infra_savings, 0),
    }


def main():
    print("=" * 80)
    print("FINANCIAL IMPACT ANALYSIS: AIO vs Traditional Web Scraping")
    print("=" * 80)
    print()
    print("Based on benchmark data:")
    print(f"  - Scraped accuracy: {BENCHMARK_DATA['scraped']['accuracy']*100:.0f}%")
    print(f"  - AIO accuracy: {BENCHMARK_DATA['aio_targeted']['accuracy']*100:.0f}%")
    print(f"  - Speed improvement: {BENCHMARK_DATA['scraped']['avg_time_ms']/BENCHMARK_DATA['aio_targeted']['avg_time_ms']:.1f}x")
    print(f"  - Token efficiency gain: 27% per correct answer")
    print()
    
    all_results = []
    
    for scenario in SCENARIOS:
        print("-" * 80)
        print(f"\n### {scenario.name}")
        print(f"    {scenario.description}")
        print(f"    Scale: {scenario.queries_per_day:,} queries/day × {scenario.avg_pages_per_query} pages")
        print()
        
        result = calculate_savings(scenario)
        all_results.append(result)
        
        print(f"  Pages processed/year:     {result['pages_per_year']:>20,}")
        print()
        print(f"  ACCURACY IMPROVEMENT:")
        print(f"    Scraped accuracy:       {result['scraped_accuracy']:>20}")
        print(f"    AIO accuracy:           {result['aio_accuracy']:>20}")
        print(f"    Failed queries avoided: {result['failed_queries_avoided_per_year']:>20,}/year")
        print()
        print(f"  TOKEN EFFICIENCY:")
        print(f"    Tokens per correct answer (scraped): {result['scraped_tokens_per_page_effective']:>8}")
        print(f"    Tokens per correct answer (AIO):     {result['aio_tokens_per_page_effective']:>8}")
        print(f"    Efficiency gain:                     {result['token_efficiency_gain_percent']:>7}%")
        print()
        print(f"  COST COMPARISON ({result['llm_model']}):")
        print(f"    Scraped LLM cost:       ${result['scraped_llm_cost_year']:>18,}/year")
        print(f"    Scraped failure cost:   ${result['scraped_failure_cost_year']:>18,}/year")
        print(f"    Scraped TOTAL:          ${result['scraped_total_cost_year']:>18,}/year")
        print(f"    AIO TOTAL:              ${result['aio_total_cost_year']:>18,}/year")
        print()
        print(f"  💰 ANNUAL SAVINGS:         ${result['annual_savings']:>18,}")
        print(f"     ({result['savings_percent']}% reduction)")
        print()
        print(f"  SPEED BENEFITS:")
        print(f"    Processing hours saved: {result['processing_hours_saved_year']:>19,}/year")
        print(f"    Infrastructure savings: ${result['infra_savings_year']:>18,}/year")
        print()
        print(f"  🎯 TOTAL ANNUAL VALUE:    ${result['total_annual_value']:>18,}")
    
    # Summary table
    print("\n" + "=" * 80)
    print("SUMMARY TABLE (for paper)")
    print("=" * 80)
    print()
    print(f"{'Scenario':<25} {'Queries/Day':>15} {'Annual Savings':>18} {'Savings %':>12}")
    print("-" * 70)
    for r in all_results:
        print(f"{r['scenario']:<25} {SCENARIOS[all_results.index(r)].queries_per_day:>15,} ${r['annual_savings']:>17,} {r['savings_percent']:>11}%")
    
    print()
    print("Key metrics for paper:")
    print(f"  - Token efficiency improvement: 27% per correct answer")
    print(f"  - Accuracy improvement: 57% → 100% (+75% relative)")
    print(f"  - Speed improvement: 6x faster retrieval")
    print(f"  - At Perplexity scale: ${all_results[0]['annual_savings']:,}/year savings")
    print(f"  - At Google scale: ${all_results[1]['annual_savings']:,}/year savings")
    
    # Save results
    with open("benchmark/results/financial_impact.json", "w") as f:
        json.dump(all_results, f, indent=2)
    
    print("\nResults saved to benchmark/results/financial_impact.json")


if __name__ == "__main__":
    main()
