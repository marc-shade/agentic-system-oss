# GAIA Benchmark Framework

This directory contains the **official GAIA benchmark** framework for testing our agentic system against the [GAIA General AI Assistants benchmark](https://arxiv.org/abs/2311.12983).

## What is GAIA?

GAIA (General AI Assistants) is a benchmark with 466 real-world questions requiring:
- Multi-step reasoning
- Tool usage (code execution, web browsing, file handling)
- Multi-modal understanding (PDFs, images, spreadsheets)
- Long-horizon planning

**Performance Reference:**
| System | Accuracy |
|--------|----------|
| Human | 92% |
| H2O Agent (SOTA as of 2025) | 75% |
| GPT-4 + plugins (original paper) | 15% |

## Setup

### 1. Install Dependencies

```bash
pip install datasets huggingface_hub
```

### 2. Get HuggingFace Access

The GAIA dataset is gated to prevent training data contamination:

1. Create account at https://huggingface.co
2. Request access at https://huggingface.co/datasets/gaia-benchmark/GAIA
3. Agree to terms (no resharing in crawlable format)
4. Create token at https://huggingface.co/settings/tokens

### 3. Set Environment Variable

```bash
export HF_TOKEN="hf_your_token_here"
```

## Running Benchmarks

### Quick Test (10 tasks)

```bash
cd /Volumes/SSDRAID0/agentic-system/intelligent-agents/prometheus/benchmarks
python3 gaia_official_benchmark.py
```

### Full Assessment

```python
from gaia_official_benchmark import GAIABenchmarkRunner
import asyncio

async def run_full_assessment():
    runner = GAIABenchmarkRunner()

    # Check access first
    has_access, msg = runner.check_access()
    if not has_access:
        print(msg)
        return

    # Run Level 1 (easiest)
    results = await runner.run_benchmark(level=1, split="validation")
    runner.print_results(results)
    runner.save_results(results, "level1_results.json")

    # Run all levels
    results = await runner.run_benchmark(level=None, split="validation")
    runner.print_results(results)

asyncio.run(run_full_assessment())
```

## Submitting to Leaderboard

The official leaderboards:
- **HuggingFace**: https://huggingface.co/spaces/gaia-benchmark/leaderboard
- **HAL**: https://hal.cs.princeton.edu/gaia

To submit:

1. Run assessment on the **test** split (not validation)
2. Format results according to leaderboard requirements
3. Submit through the official interface

**Important**: The validation set (165 questions) has known data contamination issues. For true benchmarking, use the test set (300 questions with private answers).

## File Structure

```
benchmarks/
├── gaia_official_benchmark.py    # Official GAIA framework (USE THIS)
├── gaia_results/                 # Saved assessment results
├── README.md                     # This file
└── _deprecated_fake_gaia_benchmarks.py  # OLD - Do not use
```

## Deprecated Files

- `_deprecated_fake_gaia_benchmarks.py`: This was a **fake benchmark** that created custom questions instead of using the official GAIA dataset. It has been deprecated and renamed. Do not use it for any legitimate assessment.

## References

- Paper: https://arxiv.org/abs/2311.12983
- Dataset: https://huggingface.co/datasets/gaia-benchmark/GAIA
- Leaderboard: https://huggingface.co/spaces/gaia-benchmark/leaderboard
- HAL Leaderboard: https://hal.cs.princeton.edu/gaia
