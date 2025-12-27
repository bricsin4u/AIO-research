import requests
import time
import sys
import tiktoken
from bs4 import BeautifulSoup
import json
import statistics
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler

# Configuration
PORT = 8001
BASE_URL = f"http://localhost:{PORT}"
ITERATIONS = 50

# Files to test (served from current directory)
PAGES = {
    "CLASSIC": "/test_classic.html",
    "HYBRID": "/test_hybrid.html",
    "PURE_AIO": "/test_pure_aio.html"
}

def start_server():
    server = HTTPServer(('localhost', PORT), SimpleHTTPRequestHandler)
    print(f"Starting local server on port {PORT}...")
    server.serve_forever()

def count_tokens(text):
    """Estimate token count using cl100k_base (GPT-4) encoding"""
    try:
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception:
        # Fallback approximation if tiktoken fails
        return len(text) // 4

def simulate_agent_crawl(url, strategy="standard"):
    """
    Simulates an AI agent crawling a page.
    strategy="standard": Parses full HTML DOM (Classic/Standard behavior)
    strategy="aio": Looks for Markdown Shadow (AIO behavior)
    """
    start_time = time.time()
    
    try:
        resp = requests.get(url)
        content_size = len(resp.content)
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        extracted_text = ""
        
        if strategy == "aio":
            # AIO Strategy: Target specific script tag
            md_block = soup.find('script', type='text/markdown')
            if md_block:
                extracted_text = md_block.string.strip()
            else:
                # Fallback to body if no AIO found (Simulation of failure)
                extracted_text = soup.body.get_text()
        else:
            # Standard Strategy: Parse everything, remove scripts/styles
            for script in soup(["script", "style", "nav", "footer", "aside"]):
                script.extract()
            extracted_text = soup.get_text(separator=' ', strip=True)
            
        duration = (time.time() - start_time) * 1000 # ms
        tokens = count_tokens(extracted_text)
        
        return {
            "duration_ms": duration,
            "tokens": tokens,
            "bytes_downloaded": content_size,
            "success": True
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def run_benchmark():
    # Start server in background
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    time.sleep(1) # Wait for server
    
    results = {
        "CLASSIC": [],
        "HYBRID": [],
        "PURE_AIO": []
    }
    
    print("\n--- BENCHMARK STARTING ---")
    print(f"Iterations per page: {ITERATIONS}")
    
    # 1. Test Classic Page (Standard Crawler)
    print("\n1. Testing CLASSIC SEO Page (Standard Crawler)...")
    for _ in range(ITERATIONS):
        res = simulate_agent_crawl(BASE_URL + PAGES["CLASSIC"], strategy="standard")
        if res["success"]: results["CLASSIC"].append(res)
        
    # 2. Test Hybrid Page (AIO Crawler)
    print("2. Testing HYBRID Page (AIO Crawler)...")
    for _ in range(ITERATIONS):
        res = simulate_agent_crawl(BASE_URL + PAGES["HYBRID"], strategy="aio")
        if res["success"]: results["HYBRID"].append(res)
        
    # 3. Test Pure AIO Page (AIO Crawler)
    print("3. Testing PURE AIO Page (AIO Crawler)...")
    for _ in range(ITERATIONS):
        res = simulate_agent_crawl(BASE_URL + PAGES["PURE_AIO"], strategy="aio")
        if res["success"]: results["PURE_AIO"].append(res)
        
    print("\n--- BENCHMARK COMPLETE ---")
    
    # Analysis
    report = {}
    
    # Calculate G-Index constants
    # G = D_eff / A
    # We assume A (Attention) is constant (1.0) for the same agent
    # D_eff (Effective Noise) = (Total Tokens - Signal Tokens) / Total Tokens
    # We take Pure AIO tokens as the "Signal" baseline (Ground Truth)
    
    baseline_signal_tokens = 0
    if results["PURE_AIO"]:
         baseline_signal_tokens = statistics.mean([d['tokens'] for d in results["PURE_AIO"]])
    
    for key, data in results.items():
        if not data:
            continue
            
        avg_dur = statistics.mean([d['duration_ms'] for d in data])
        avg_tokens = statistics.mean([d['tokens'] for d in data])
        avg_bytes = statistics.mean([d['bytes_downloaded'] for d in data])
        
        # Calculate Noise Ratio (D)
        # Noise = Total - Signal. If Total < Signal (unlikely but possible due to jitter), Noise = 0
        noise_tokens = max(0, avg_tokens - baseline_signal_tokens)
        
        if avg_tokens > 0:
            noise_ratio = noise_tokens / avg_tokens
        else:
            noise_ratio = 0
            
        # G-Index Calculation (Simplified: G ~ D)
        # In Petrenko's theory, D > 0.7 is Singularity.
        g_index = round(noise_ratio, 3)
        
        report[key] = {
            "avg_duration_ms": round(avg_dur, 2),
            "avg_tokens": round(avg_tokens, 1),
            "avg_bytes": round(avg_bytes, 1),
            "noise_ratio": round(noise_ratio, 3),
            "g_index": g_index
        }
        
    # Print Report
    print("\n--- FINAL REPORT ---")
    print(f"{'TYPE':<15} | {'TIME (ms)':<10} | {'TOKENS':<10} | {'NOISE (D)':<10} | {'G-INDEX':<10}")
    print("-" * 70)
    
    for key, metrics in report.items():
        print(f"{key:<15} | {metrics['avg_duration_ms']:<10} | {metrics['avg_tokens']:<10} | {metrics['noise_ratio']:<10} | {metrics['g_index']:<10}")
        
    # Save to JSON
    with open("benchmark_results.json", "w") as f:
        json.dump(report, f, indent=2)
    print("\nResults saved to benchmark_results.json")

if __name__ == "__main__":
    run_benchmark()
