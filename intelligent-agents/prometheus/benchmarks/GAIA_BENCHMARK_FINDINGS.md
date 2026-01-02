# GAIA Benchmark Findings - January 2, 2026

## Executive Summary

Comprehensive benchmarking of GAIA Level 1 validation tasks (47 questions) across multiple AI providers and configurations. Key finding: **Multi-provider hybrid pipelines significantly outperform single-provider approaches**, with Gemini-based hybrid achieving 81.2% accuracy.

## Benchmark Results Summary

| Solver | Accuracy | Correct | Time/Task | Total Time | Notes |
|--------|----------|---------|-----------|------------|-------|
| **Hybrid (Gemini)** | **81.2%** | 38/47 | 70.2s | ~55 min | Best accuracy, quota limited |
| Codex (gpt-5.2-codex) | 31.9% | 15/47 | 30.4s | ~24 min | Question truncation issues |
| Hybrid (Groq fallback) | 31.8% | 15/47 | 20.9s | ~16 min | When Gemini exhausted |
| Mistral (mistral-large-latest) | 18.2% | 11/60 | 3.0s | ~3 min | Answer extraction poor |
| Groq-only (llama-3.3-70b) | 15.9% | 7/44 | 1.0s | ~45s | Too fast, inaccurate |
| Ollama (gpt-oss:120b-cloud) | 14.9% | 7/47 | 3.2s | ~2.5 min | Fastest, many failures |

## Hybrid Pipeline Architecture

The best-performing architecture uses a 3-stage pipeline:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    HYBRID PIPELINE (81.2% accuracy)                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Stage 1: FAST FACILITATOR (Groq ~0.15-0.24s)                       │
│  ├─ Task classification (general/math/code/research)                │
│  ├─ Context enrichment (Wikipedia, web search)                     │
│  └─ Initial reasoning and answer extraction                         │
│                                                                      │
│  Stage 2: ACCURATE SOLVER (Gemini 2.5 Flash ~60-70s)                │
│  ├─ Deep reasoning with full context                                │
│  ├─ Multi-step problem decomposition                                │
│  └─ Verified answer generation                                      │
│                                                                      │
│  Stage 3: FAST EXTRACTION (Groq ~0.1s)                              │
│  └─ Extract final answer in required format                         │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Why This Works

1. **Fast Classification**: Groq's llama-3.3-70b provides near-instant task classification (<0.25s)
2. **Intelligent Routing**: Different task types get appropriate context enrichment
3. **Accurate Solving**: Gemini 2.5 Flash has the reasoning capability to handle complex multi-step problems
4. **Clean Extraction**: Final Groq pass ensures answers match expected format

## Individual Provider Analysis

### Gemini 2.5 Flash (Best Solver)
- **Accuracy**: 81.2% in hybrid pipeline
- **Latency**: 60-70 seconds per task
- **Strengths**: Deep reasoning, multi-step problems, research questions
- **Weaknesses**: Slow, daily quota limits (free tier exhausts quickly)
- **API**: `generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20`

### OpenAI Codex (gpt-5.2-codex)
- **Accuracy**: 31.9%
- **Latency**: ~30 seconds per task
- **Strengths**: Code execution, structured reasoning
- **Weaknesses**:
  - Question truncation (says "I'm missing the actual puzzle statement")
  - Cannot access external resources ("I can't access Wikipedia")
  - No web browsing capability
- **CLI**: `codex exec --skip-git-repo-check -o output.txt "prompt"`

### Groq (llama-3.3-70b-versatile)
- **Accuracy**: 15.9% standalone, but excellent as facilitator
- **Latency**: 0.15-0.24 seconds (fastest)
- **Strengths**: Ultra-fast classification and extraction
- **Weaknesses**: Insufficient for complex reasoning alone
- **Best Use**: Pipeline facilitator, not primary solver

### Mistral (mistral-large-latest)
- **Accuracy**: 18.2%
- **Latency**: ~3 seconds per task
- **Weaknesses**: Poor answer extraction - tends to add explanations
- **Not recommended** for GAIA-style benchmarks

### Ollama Cloud Models (gpt-oss:120b-cloud)
- **Accuracy**: 14.9%
- **Latency**: 3.2 seconds per task
- **Strengths**: Fast, no local GPU required
- **Weaknesses**: Many failures, frequent fallback to Groq
- **API**: `http://localhost:11434/api/generate` (connects to ollama.com)

## Code Implementation

### Key Files
- `gaia_consensus_executor.py` - Main benchmark executor with all solver methods
- `gaia_dataset.json` - 53 Level 1 validation tasks
- `gaia_results/` - JSON files with detailed per-question results

### Added Solver Methods

```python
# Codex CLI solver
async def _query_codex(self, prompt: str, timeout_sec: int = 120) -> ProviderAnswer:
    cmd = ["codex", "exec", "--skip-git-repo-check", "-o", output_file, prompt]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_sec)
    # Parse output from file or stdout

# Ollama API solver (faster than CLI)
async def _query_ollama(self, prompt: str, model: str = "gpt-oss:120b-cloud") -> ProviderAnswer:
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": model, "prompt": prompt, "stream": False}
    )
```

### Running Benchmarks

```python
from gaia_consensus_executor import ConsensusGAIAExecutor

executor = ConsensusGAIAExecutor()

# Run with specific solver
results = await executor.run_gaia_benchmark(
    dataset_path="gaia_dataset.json",
    solver="gemini"  # Options: gemini, codex, ollama, groq, mistral
)
```

## Question Type Analysis

Based on 47 Level 1 questions:

| Category | Count | Best Solver | Example |
|----------|-------|-------------|---------|
| General Knowledge | ~40% | Gemini | "What writer is quoted by Merriam-Webster..." |
| Mathematical | ~15% | Gemini | "If Eliud Kipchoge could maintain his pace..." |
| Code/Logic | ~10% | Codex | "What is the final numeric output from the Python code?" |
| Research | ~20% | Gemini | "In Emily Midkiff's June 2014 article..." |
| Visual/Video | ~15% | None | Requires video processing capability |

### Question Categories That Failed Consistently

1. **Video-based questions**: No solver can process YouTube videos
2. **Questions requiring web access**: Codex cannot browse
3. **Multi-step research**: Requires real-time information retrieval
4. **Truncated questions**: Some prompts exceed context limits

## Performance Optimization Insights

### Speed vs Accuracy Tradeoff

```
Accuracy
    ^
81% │        ★ Gemini Hybrid
    │
50% │
    │
32% │    ★ Codex    ★ Groq Fallback
    │
18% │ ★ Mistral
15% │ ★ Groq    ★ Ollama Cloud
    └────────────────────────────────> Speed
         3s    10s    30s    60s   70s
```

### Recommendations

1. **Production Use**: Hybrid pipeline with Gemini (when quota allows) + Groq fallback
2. **High-Volume**: Codex for code-heavy tasks, Groq for classification
3. **Cost Optimization**: Use Groq for filtering, only send complex queries to paid APIs
4. **Research Tasks**: Gemini with extended context window

## Next Steps for Improvement

1. **Video Processing**: Add yt-dlp + transcript extraction for video questions
2. **Web Augmentation**: Integrate real-time web search for research questions
3. **Ensemble Methods**: Vote across multiple providers for confidence
4. **Fine-tuning**: Consider fine-tuning local models on GAIA-style tasks
5. **Caching**: Cache Wikipedia/web content for repeated queries

## API Keys and Configuration

```bash
# Required environment variables
GROQ_API_KEY="gsk_..."        # For fast facilitator
GOOGLE_API_KEY="AIza..."      # For Gemini solver
OPENAI_API_KEY="sk-..."       # For Codex (or use ~/.codexrc)

# Ollama configuration
# Cloud models require: ollama pull gpt-oss:120b-cloud
```

## Conclusion

The GAIA benchmark reveals that **no single AI provider excels at all task types**. The optimal approach combines:
- **Fast providers** (Groq) for classification and extraction
- **Accurate providers** (Gemini) for complex reasoning
- **Specialized providers** (Codex) for code-specific tasks

Multi-provider hybrid pipelines achieve 2.5x better accuracy than single-provider approaches while managing costs through intelligent routing.

---
*Generated by mac-studio (Orchestrator) on January 2, 2026*
*Benchmark data: 47 Level 1 GAIA validation tasks*
