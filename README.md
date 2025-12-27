# AIO: AI Optimization Protocol

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Spec Version](https://img.shields.io/badge/Spec-v1.0.0-blue.svg)](spec/AIO-SPECIFICATION-v1.0.md)

**The web was built for human eyes. AIO makes it readable for AI minds.**

---

## What is AIO?

AI Optimization (AIO) is a four-layer protocol that creates parallel data channels optimized for AI consumption. Instead of forcing LLMs to parse noisy HTML, AIO provides clean, verified, token-efficient content.

| Layer | Purpose | Implementation |
|-------|---------|----------------|
| **1. Structural** | Entity recognition | JSON-LD (Schema.org) |
| **2. Narrative** | Clean content | Markdown Shadow |
| **3. Discovery** | Efficient crawling | `/.well-known/ai-instructions.json` |
| **4. Trust** | Verification | SHA-256 / Ed25519 signatures |

## Why AIO?

- **65% fewer tokens** — Same information, less compute
- **Zero noise** — No nav menus, ads, or cookie banners in AI context
- **Verified content** — Cryptographic signatures prevent hallucination from tampered sources
- **Drop-in integration** — Works with existing sites, no rebuild required

## Quick Start

```bash
# Install
pip install -r requirements.txt

# Sign a page
python aio_cli.py sign --input page.html --output page-signed.html

# Verify a page
python aio_cli.py verify --url https://example.com/page
```

## Platform Adapters

Ready-to-use integrations:

| Platform | Location | Status |
|----------|----------|--------|
| WordPress | `adapters/wordpress/` | ✅ Ready |
| React/Next.js | `adapters/react/` | ✅ Ready |
| Laravel | `adapters/laravel/` | ✅ Ready |
| Drupal | `adapters/drupal/` | ✅ Ready |
| Shopify | `adapters/shopify/` | ✅ Ready |
| Ghost | `adapters/ghost/` | ✅ Ready |
| Strapi | `adapters/strapi/` | ✅ Ready |
| Contentful | `adapters/contentful/` | ✅ Ready |

## Research

This implementation accompanies the academic paper:

> **"AI Optimization (AIO): A Technical Methodology for Cognitive Security and Entropy Reduction in LLM-Based Search"**
> 
> Igor Sergeevich Petrenko, AIFUSION Research, 2025

Based on the **Theory of Stupidity** — a formal model showing that AI hallucinations arise from information overload, not intelligence deficits.

**Citation:**
```bibtex
@article{petrenko2025aio,
  title={AI Optimization (AIO): A Technical Methodology for Cognitive Security and Entropy Reduction in LLM-Based Search},
  author={Petrenko, Igor Sergeevich},
  journal={AIFUSION Research},
  year={2025}
}
```

## Benchmarks

Run the benchmark suite to reproduce our results:

```bash
cd research/benchmarks
python benchmark_suite.py
```

Results: [benchmark_results.json](research/benchmarks/benchmark_results.json)

## Specification

Full technical specification: [AIO-SPECIFICATION-v1.0.md](spec/AIO-SPECIFICATION-v1.0.md)

## Repository Structure

```
AIO/
├── adapters/           # Platform integrations
│   ├── wordpress/      # WordPress plugin
│   ├── react/          # React/Next.js components
│   ├── laravel/        # Laravel package
│   ├── drupal/         # Drupal module
│   ├── shopify/        # Shopify integration
│   ├── ghost/          # Ghost adapter
│   ├── strapi/         # Strapi plugin
│   └── contentful/     # Contentful integration
├── spec/               # Formal specification
├── research/           # Benchmarks and data
├── examples/           # Demo implementations
├── docs/               # Documentation
├── aio_cli.py          # Command-line tool
├── aio_signing.py      # Signing library (Python)
└── requirements.txt    # Python dependencies
```

## License

MIT — Free for commercial use.

## Author

**Igor Sergeevich Petrenko**  
Founder, AIFUSION Research & IN4U (BRICS Platform)  
Contact: research@aifusion.ru

---

*Making the web AI-native, one page at a time.*
