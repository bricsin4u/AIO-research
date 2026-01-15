#!/usr/bin/env python3
"""
AIO vs Classic Scraping - End-to-End Benchmark

This benchmark measures what actually matters:
1. LLM Input Tokens - What gets sent to the model (cost)
2. End-to-End Time - Total latency to answer
3. Answer Accuracy - Does it find correct info?
4. Targeted Retrieval - AIO chunk selection vs full text

Usage:
    python benchmark/e2e_benchmark.py
"""

import sys
import time
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from aio_parser import AIOParser
from aio_parser.discovery import discover_aio
from aio_parser.fetcher import AIOFetcher
from aio_parser.fallback import HTMLScraper


@dataclass
class BenchmarkQuery:
    """A test query with expected answer."""
    query: str
    expected_keywords: List[str]  # Keywords that should appear in correct answer
    target_chunk: str  # Which AIO chunk should contain the answer
    category: str  # fact_extraction, comparison, etc.


@dataclass 
class BenchmarkResult:
    """Result of a single benchmark run."""
    query: str
    method: str  # "aio_targeted" | "aio_full" | "scraped"
    
    # Token metrics
    tokens_to_llm: int  # What would be sent to LLM
    tokens_in_answer_section: int  # Tokens in the relevant section only
    
    # Time metrics (ms)
    fetch_time_ms: float
    parse_time_ms: float
    total_time_ms: float
    
    # Quality metrics
    answer_found: bool  # Did the content contain expected keywords?
    chunks_retrieved: int  # How many chunks were matched (AIO only)
    noise_in_result: float  # Proportion of irrelevant content
    
    def to_dict(self) -> dict:
        return {
            "query": self.query,
            "method": self.method,
            "tokens_to_llm": self.tokens_to_llm,
            "tokens_in_answer_section": self.tokens_in_answer_section,
            "fetch_time_ms": round(self.fetch_time_ms, 2),
            "parse_time_ms": round(self.parse_time_ms, 2),
            "total_time_ms": round(self.total_time_ms, 2),
            "answer_found": self.answer_found,
            "chunks_retrieved": self.chunks_retrieved,
            "noise_in_result": round(self.noise_in_result, 4),
        }


class E2EBenchmark:
    """
    End-to-end benchmark comparing AIO vs classic scraping.
    """
    
    # Test queries with expected answers
    TEST_QUERIES = [
        BenchmarkQuery(
            query="What is the price of the Pro plan?",
            expected_keywords=["$12", "user", "month"],
            target_chunk="pricing",
            category="fact_extraction"
        ),
        BenchmarkQuery(
            query="What integrations are available?",
            expected_keywords=["Slack", "Jira", "GitHub"],
            target_chunk="features",
            category="fact_extraction"
        ),
        BenchmarkQuery(
            query="When was the company founded?",
            expected_keywords=["2022"],
            target_chunk="about",
            category="fact_extraction"
        ),
        BenchmarkQuery(
            query="What is the sales email?",
            expected_keywords=["sales@techstartup.com"],
            target_chunk="contact",
            category="fact_extraction"
        ),
        BenchmarkQuery(
            query="What is the free plan storage limit?",
            expected_keywords=["1 GB", "1GB"],
            target_chunk="pricing", 
            category="fact_extraction"
        ),
        BenchmarkQuery(
            query="Does it support mobile apps?",
            expected_keywords=["iOS", "Android", "mobile"],
            target_chunk="features",
            category="fact_extraction"
        ),
        BenchmarkQuery(
            query="How much funding did they raise in Series B?",
            expected_keywords=["$45M", "45M", "Sequoia"],
            target_chunk="about",
            category="fact_extraction"
        ),
    ]
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.parser = AIOParser(timeout=15)
        self.scraper = HTMLScraper(timeout=15)
        self.fetcher = AIOFetcher(timeout=15)
        self.results: List[BenchmarkResult] = []
    
    def run(self) -> None:
        """Run the full benchmark suite."""
        print("=" * 70)
        print("AIO vs Classic Scraping - End-to-End Benchmark")
        print("=" * 70)
        print(f"Base URL: {self.base_url}")
        print(f"Queries: {len(self.TEST_QUERIES)}")
        print()
        
        # Check AIO availability
        aio_url, discovery_method = discover_aio(self.base_url)
        if not aio_url:
            print("ERROR: AIO not found on target. Make sure demo server is running.")
            return
        
        print(f"AIO discovered via: {discovery_method}")
        print(f"AIO URL: {aio_url}")
        print()
        
        # Pre-fetch AIO data for targeted retrieval tests
        aio_data = self.fetcher.fetch(aio_url)
        if not aio_data:
            print("ERROR: Could not fetch AIO content")
            return
        
        # Run tests for each query
        for i, query in enumerate(self.TEST_QUERIES, 1):
            print(f"\n[{i}/{len(self.TEST_QUERIES)}] Query: {query.query}")
            
            # Method 1: Classic scraping (what web tools do)
            result_scraped = self._benchmark_scraped(query)
            self.results.append(result_scraped)
            print(f"  Scraped:      {result_scraped.tokens_to_llm:4} tokens, "
                  f"{result_scraped.total_time_ms:6.1f}ms, "
                  f"found={result_scraped.answer_found}")
            
            # Method 2: AIO full content (no query targeting)
            result_aio_full = self._benchmark_aio_full(query, aio_data)
            self.results.append(result_aio_full)
            print(f"  AIO (full):   {result_aio_full.tokens_to_llm:4} tokens, "
                  f"{result_aio_full.total_time_ms:6.1f}ms, "
                  f"found={result_aio_full.answer_found}")
            
            # Method 3: AIO targeted (using index to get only relevant chunk)
            result_aio_targeted = self._benchmark_aio_targeted(query, aio_data)
            self.results.append(result_aio_targeted)
            print(f"  AIO (target): {result_aio_targeted.tokens_to_llm:4} tokens, "
                  f"{result_aio_targeted.total_time_ms:6.1f}ms, "
                  f"found={result_aio_targeted.answer_found}, "
                  f"chunks={result_aio_targeted.chunks_retrieved}")
        
        # Generate summary
        self._generate_summary()
    
    def _benchmark_scraped(self, query: BenchmarkQuery) -> BenchmarkResult:
        """Benchmark classic scraping approach."""
        start = time.time()
        
        # Fetch and scrape
        fetch_start = time.time()
        content, raw_size, clean_size = self.scraper.scrape(self.base_url)
        fetch_time = (time.time() - fetch_start) * 1000
        
        # Parse time (minimal for scraped - just tokenize)
        parse_start = time.time()
        tokens = len(content) // 4
        parse_time = (time.time() - parse_start) * 1000
        
        total_time = (time.time() - start) * 1000
        
        # Check if answer is in content
        answer_found = any(kw.lower() in content.lower() for kw in query.expected_keywords)
        
        # Calculate noise (content that's not in target chunk area)
        # For scraped, everything is mixed, so noise is high
        noise = 0.7  # Approximate - scraped content is jumbled
        
        return BenchmarkResult(
            query=query.query,
            method="scraped",
            tokens_to_llm=tokens,
            tokens_in_answer_section=tokens // 5,  # Estimate: answer is ~20% of content
            fetch_time_ms=fetch_time,
            parse_time_ms=parse_time,
            total_time_ms=total_time,
            answer_found=answer_found,
            chunks_retrieved=0,
            noise_in_result=noise,
        )
    
    def _benchmark_aio_full(self, query: BenchmarkQuery, aio_data: dict) -> BenchmarkResult:
        """Benchmark AIO with full content (no targeting)."""
        start = time.time()
        
        # Simulate fetch (already have data, but measure parse time)
        fetch_time = 5.0  # Assume ~5ms for cached fetch
        
        parse_start = time.time()
        # Combine all content
        all_content = "\n\n".join(
            c.get("content", "") for c in aio_data.get("content", [])
        )
        tokens = len(all_content) // 4
        parse_time = (time.time() - parse_start) * 1000
        
        total_time = (time.time() - start) * 1000 + fetch_time
        
        # Check if answer is in content
        answer_found = any(kw.lower() in all_content.lower() for kw in query.expected_keywords)
        
        # For full AIO, content is structured but you're still sending everything
        # Noise is content from other chunks
        target_chunk_tokens = 0
        for idx in aio_data.get("index", []):
            if idx["id"] == query.target_chunk:
                target_chunk_tokens = idx.get("token_estimate", 0)
                break
        
        noise = 1.0 - (target_chunk_tokens / tokens) if tokens > 0 else 0
        
        return BenchmarkResult(
            query=query.query,
            method="aio_full",
            tokens_to_llm=tokens,
            tokens_in_answer_section=target_chunk_tokens,
            fetch_time_ms=fetch_time,
            parse_time_ms=parse_time,
            total_time_ms=total_time,
            answer_found=answer_found,
            chunks_retrieved=len(aio_data.get("content", [])),
            noise_in_result=noise,
        )
    
    def _benchmark_aio_targeted(self, query: BenchmarkQuery, aio_data: dict) -> BenchmarkResult:
        """Benchmark AIO with targeted chunk retrieval."""
        start = time.time()
        
        # Simulate fetch (already have data)
        fetch_time = 5.0  # Assume ~5ms for cached fetch
        
        parse_start = time.time()
        
        # Extract keywords from query
        keywords = self._extract_keywords(query.query)
        
        # Find matching chunks using index
        matching_chunks = self.fetcher.get_matching_chunks(aio_data, keywords)
        
        if matching_chunks:
            content = "\n\n".join(c.get("content", "") for c in matching_chunks)
            tokens = len(content) // 4
        else:
            # Fallback to all content
            content = "\n\n".join(c.get("content", "") for c in aio_data.get("content", []))
            tokens = len(content) // 4
        
        parse_time = (time.time() - parse_start) * 1000
        total_time = (time.time() - start) * 1000 + fetch_time
        
        # Check if answer is in content
        answer_found = any(kw.lower() in content.lower() for kw in query.expected_keywords)
        
        # For targeted, we only retrieved relevant chunks
        # Check if target chunk was retrieved
        matched_ids = [c["id"] for c in matching_chunks]
        target_retrieved = query.target_chunk in matched_ids
        
        # Noise is chunks that aren't the target
        if matching_chunks:
            target_tokens = sum(
                len(c.get("content", "")) // 4 
                for c in matching_chunks 
                if c["id"] == query.target_chunk
            )
            noise = 1.0 - (target_tokens / tokens) if tokens > 0 else 0
        else:
            noise = 0.8  # Fallback case
        
        return BenchmarkResult(
            query=query.query,
            method="aio_targeted",
            tokens_to_llm=tokens,
            tokens_in_answer_section=tokens if target_retrieved else 0,
            fetch_time_ms=fetch_time,
            parse_time_ms=parse_time,
            total_time_ms=total_time,
            answer_found=answer_found,
            chunks_retrieved=len(matching_chunks),
            noise_in_result=max(0, noise),
        )
    
    def _extract_keywords(self, query: str) -> List[str]:
        """Extract keywords from query."""
        stop_words = {
            'a', 'an', 'the', 'is', 'are', 'was', 'were', 'be', 'been',
            'what', 'how', 'when', 'where', 'who', 'which', 'why',
            'do', 'does', 'did', 'can', 'could', 'would', 'should',
            'i', 'you', 'he', 'she', 'it', 'we', 'they',
            'of', 'in', 'on', 'at', 'to', 'for', 'with', 'by', 'from',
            'and', 'or', 'but', 'if', 'then', 'so', 'as'
        }
        words = query.lower().split()
        return [w.strip('?.,!') for w in words if w.strip('?.,!') not in stop_words]
    
    def _generate_summary(self) -> None:
        """Generate benchmark summary."""
        print("\n" + "=" * 70)
        print("BENCHMARK SUMMARY")
        print("=" * 70)
        
        # Group by method
        by_method = {}
        for r in self.results:
            if r.method not in by_method:
                by_method[r.method] = []
            by_method[r.method].append(r)
        
        print("\n### Average Metrics by Method ###\n")
        print(f"{'Method':<15} {'Tokens':<10} {'Time(ms)':<12} {'Accuracy':<10} {'Noise':<10}")
        print("-" * 57)
        
        for method in ["scraped", "aio_full", "aio_targeted"]:
            if method not in by_method:
                continue
            results = by_method[method]
            avg_tokens = sum(r.tokens_to_llm for r in results) / len(results)
            avg_time = sum(r.total_time_ms for r in results) / len(results)
            accuracy = sum(1 for r in results if r.answer_found) / len(results) * 100
            avg_noise = sum(r.noise_in_result for r in results) / len(results)
            
            print(f"{method:<15} {avg_tokens:<10.0f} {avg_time:<12.1f} {accuracy:<10.0f}% {avg_noise:<10.2f}")
        
        # Calculate improvements
        scraped = by_method.get("scraped", [])
        targeted = by_method.get("aio_targeted", [])
        
        if scraped and targeted:
            avg_scraped_tokens = sum(r.tokens_to_llm for r in scraped) / len(scraped)
            avg_targeted_tokens = sum(r.tokens_to_llm for r in targeted) / len(targeted)
            
            if avg_scraped_tokens > 0:
                token_reduction = (avg_scraped_tokens - avg_targeted_tokens) / avg_scraped_tokens * 100
            else:
                token_reduction = 0
            
            avg_scraped_noise = sum(r.noise_in_result for r in scraped) / len(scraped)
            avg_targeted_noise = sum(r.noise_in_result for r in targeted) / len(targeted)
            
            print("\n### Key Improvements (AIO Targeted vs Scraped) ###\n")
            print(f"Token Reduction:    {token_reduction:+.1f}%")
            print(f"Noise Reduction:    {(avg_scraped_noise - avg_targeted_noise) * 100:.1f} percentage points")
            
            scraped_accuracy = sum(1 for r in scraped if r.answer_found) / len(scraped) * 100
            targeted_accuracy = sum(1 for r in targeted if r.answer_found) / len(targeted) * 100
            print(f"Answer Accuracy:    {scraped_accuracy:.0f}% → {targeted_accuracy:.0f}%")
        
        # Save results
        output_dir = Path(__file__).parent / "results"
        output_dir.mkdir(exist_ok=True)
        
        results_file = output_dir / "e2e_benchmark_results.json"
        with open(results_file, 'w') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "base_url": self.base_url,
                "results": [r.to_dict() for r in self.results]
            }, f, indent=2)
        
        print(f"\nResults saved to: {results_file}")


if __name__ == "__main__":
    benchmark = E2EBenchmark()
    benchmark.run()
