# AIO v2.1: Entropy-Controlled Information Architecture

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.18251778.svg)](https://doi.org/10.5281/zenodo.18251778)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

This repository contains the core implementation and benchmark suite for **AI Optimization (AIO)** and **Entropy-Controlled Retrieval (ECR)**, as described in the flagship paper *"Entropy-Controlled Information Architecture: A Unified Framework for Machine-Optimized Content Delivery and Retrieval"*.

## 🔬 Theoretical Foundation

This framework is the first to operationalize the **Theory of Stupidity** (Petrenko, 2025) for machine systems. By treating information delivery as a cybernetic control problem, AIO minimizes environmental entropy ($D$) to protect machine attention ($A$), preventing the "Stupidity Singularity" predicted by the G-formula:

$$ G \propto \frac{D_{eff}}{A} $$

## 🚀 Key Results (Benchmarks)

Our end-to-end benchmark suite (`research/benchmarks/e2e_benchmark.py`) demonstrates:
- **100% Answer Accuracy**: Eliminating information loss inherent in traditional scraping.
- **6x Faster Retrieval**: Latency reduced from 29ms to 5ms (average).
- **27% Token Efficiency**: Significant cost reduction per correct answer.

## 📂 Repository Structure

- `/aio_core`: Reference implementation of the Content Envelope schema and AIO Parser.
- `/research/benchmarks`: Reproducible scripts for accuracy and latency testing.
- `/prototype`: Demo server and client implementations.
- `/specs`: Technical definitions of the `.aio` indexing protocol.

## 🛠 Installation & Usage

```bash
pip install -r requirements.txt
python research/benchmarks/run_benchmark.py
```

## 📜 Citation

If you use this work in your research, please cite:

```bibtex
@article{petrenko2026unified,
  title={Entropy-Controlled Information Architecture: A Unified Framework for Machine-Optimized Content Delivery and Retrieval},
  author={Petrenko, Igor Sergeevich},
  year={2026},
  doi={10.5281/zenodo.18251778}
}
```

---
© 2026 Igor Sergeevich Petrenko | AIFUSION Research
