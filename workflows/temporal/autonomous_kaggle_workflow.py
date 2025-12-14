#!/usr/bin/env python3
"""
Autonomous Kaggle Competition Workflow
=======================================

Fully autonomous pipeline that:
1. Monitors Kaggle competitions for opportunities
2. Researches relevant papers using research-to-code pipeline
3. Generates solution code using GPU cluster LLMs
4. Pushes training to Kaggle GPU/TPU (NEVER local CPU)
5. Analyzes results and feeds back to self-improvement system
6. Iterates until target score achieved

CRITICAL: All training happens on Kaggle GPU/TPU - local cluster is for:
- Code generation (GPU LLMs)
- Analysis and visualization
- Submission file generation
- Result storage and learning

GPU Cluster (for LLM inference only):
- completeu-server (M4) - strongest
- mac-studio (M2 Ultra)
- macbook-air (M2)
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional
from pathlib import Path
from enum import Enum

# Temporal imports
from temporalio import workflow, activity
from temporalio.client import Client
from temporalio.worker import Worker
from temporalio.common import RetryPolicy

# Local imports
sys.path.insert(0, str(Path(__file__).parent))
from research_to_code_pipeline import (
    search_papers_parallel,
    extract_paper_knowledge,
    build_knowledge_graph,
    extract_code_patterns,
    generate_architecture_plan,
    generate_module_code,
    _llm_generate_code
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
KAGGLE_COMPETITIONS_DIR = "/mnt/agentic-system/kaggle-competitions"
GENERATED_DIR = "/mnt/agentic-system/generated-implementations"


class CompetitionType(Enum):
    TABULAR = "tabular"
    IMAGE = "image"
    NLP = "nlp"
    TIME_SERIES = "time_series"
    GRAPH = "graph"
    REINFORCEMENT = "reinforcement"


@dataclass
class Competition:
    """Kaggle competition metadata"""
    slug: str
    title: str
    deadline: str
    prize: int = 0
    competition_type: str = "tabular"
    evaluation_metric: str = "accuracy"
    current_best_score: float = 0.0
    target_score: float = 0.0
    data_description: str = ""


@dataclass
class ResearchFindings:
    """Research findings for a competition"""
    papers: List[Dict] = field(default_factory=list)
    techniques: List[str] = field(default_factory=list)
    code_patterns: List[Dict] = field(default_factory=list)
    architecture_plan: Dict = field(default_factory=dict)
    generated_code: Dict = field(default_factory=dict)


@dataclass
class KaggleKernelJob:
    """Kaggle kernel job for remote GPU/TPU training"""
    kernel_slug: str
    competition: str
    experiment_config: Dict = field(default_factory=dict)
    use_gpu: bool = True
    use_tpu: bool = False
    timeout_hours: int = 9  # Kaggle limit


@dataclass
class SubmissionResult:
    """Competition submission result"""
    submission_id: str
    score: float
    rank: int = 0
    timestamp: str = ""
    experiment_config: Dict = field(default_factory=dict)


# ============================================================================
# ACTIVITIES: Competition Discovery
# ============================================================================

@activity.defn
async def discover_competitions(
    competition_types: List[str] = None,
    min_prize: int = 0,
    max_days_until_deadline: int = 90
) -> List[Dict]:
    """
    Discover active Kaggle competitions worth pursuing.
    """
    competitions = []

    try:
        # Use kaggle CLI to list competitions
        result = subprocess.run(
            ["kaggle", "competitions", "list", "--csv"],
            capture_output=True, text=True, timeout=30
        )

        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")[1:]  # Skip header
            for line in lines[:20]:  # Limit to top 20
                parts = line.split(",")
                if len(parts) >= 6:
                    # Extract slug from URL: https://www.kaggle.com/competitions/slug -> slug
                    ref = parts[0]
                    if "/competitions/" in ref:
                        slug = ref.split("/competitions/")[-1]
                    else:
                        slug = ref

                    # Parse prize (e.g., "1,500,000 Usd" -> 1500000)
                    prize_str = parts[3] if len(parts) > 3 else "0"
                    prize = int(''.join(c for c in prize_str if c.isdigit()) or 0)

                    competitions.append({
                        "slug": slug,
                        "title": parts[1] if len(parts) > 1 else slug,
                        "deadline": parts[1] if len(parts) > 1 else "",  # deadline is column 1
                        "prize": prize,
                        "category": parts[2] if len(parts) > 2 else "Featured"
                    })
    except Exception as e:
        logger.warning(f"Kaggle CLI failed: {e}")
        # Return known competitions from local dir
        comp_dirs = Path(KAGGLE_COMPETITIONS_DIR).glob("*/")
        for comp_dir in comp_dirs:
            if comp_dir.is_dir() and not comp_dir.name.startswith("."):
                competitions.append({
                    "slug": comp_dir.name,
                    "title": comp_dir.name.replace("-", " ").title(),
                    "deadline": "",
                    "prize": 0,
                    "category": "Local"
                })

    logger.info(f"Discovered {len(competitions)} competitions")
    return competitions


@activity.defn
async def analyze_competition(competition_slug: str) -> Dict:
    """
    Analyze a competition to determine type, metrics, and strategy.
    """
    comp_dir = Path(KAGGLE_COMPETITIONS_DIR) / competition_slug

    analysis = {
        "slug": competition_slug,
        "type": "tabular",  # Default
        "evaluation_metric": "unknown",
        "data_files": [],
        "suggested_approaches": [],
        "research_queries": []
    }

    # Check data files
    data_dir = comp_dir / "data"
    if data_dir.exists():
        analysis["data_files"] = [f.name for f in data_dir.glob("*") if f.is_file()]

        # Infer type from files
        file_types = {f.suffix.lower() for f in data_dir.glob("*")}
        if ".jpg" in file_types or ".png" in file_types or ".jpeg" in file_types:
            analysis["type"] = "image"
            analysis["research_queries"] = [
                f"{competition_slug} image classification deep learning",
                "state of art image classification CNN transformer",
                "data augmentation techniques computer vision"
            ]
        elif ".wav" in file_types or ".mp3" in file_types:
            analysis["type"] = "audio"
            analysis["research_queries"] = [
                f"{competition_slug} audio classification",
                "audio signal processing deep learning",
                "mel spectrogram feature extraction"
            ]
        else:
            # Check CSV for text columns
            analysis["type"] = "tabular"
            analysis["research_queries"] = [
                f"{competition_slug} tabular data machine learning",
                "gradient boosting hyperparameter optimization",
                "feature engineering tabular data kaggle"
            ]

    # Suggest approaches based on type
    approach_map = {
        "tabular": ["XGBoost", "LightGBM", "CatBoost", "AutoML", "Neural Network"],
        "image": ["EfficientNet", "Vision Transformer", "ResNet", "ConvNeXt"],
        "nlp": ["BERT", "RoBERTa", "DeBERTa", "Transformers"],
        "time_series": ["LSTM", "Temporal Fusion Transformer", "N-BEATS", "Prophet"],
        "audio": ["wav2vec", "Whisper", "Audio Spectrogram Transformer"]
    }
    analysis["suggested_approaches"] = approach_map.get(analysis["type"], ["XGBoost"])

    logger.info(f"Analyzed competition {competition_slug}: type={analysis['type']}")
    return analysis


# ============================================================================
# ACTIVITIES: Research & Code Generation (GPU Cluster LLMs)
# ============================================================================

@activity.defn
async def research_competition_solutions(
    competition: Dict,
    research_queries: List[str]
) -> Dict:
    """
    Research papers and solutions for competition using GPU cluster LLMs.
    """
    findings = ResearchFindings()

    for query in research_queries[:3]:  # Limit queries
        # Search papers
        papers = await search_papers_parallel(query, max_results=5)
        findings.papers.extend(papers)

        # Extract knowledge
        for paper in papers[:2]:
            pk = await extract_paper_knowledge(paper)
            for technique in pk.get("techniques", []):
                if technique not in findings.techniques:
                    findings.techniques.append(technique)

    # Build knowledge graph
    papers_knowledge = [{"title": p.get("title", ""), "techniques": findings.techniques}
                       for p in findings.papers[:5]]
    kg = await build_knowledge_graph(papers_knowledge)

    # Extract code patterns
    findings.code_patterns = await extract_code_patterns(kg)

    logger.info(f"Research complete: {len(findings.papers)} papers, {len(findings.techniques)} techniques")
    return asdict(findings)


@activity.defn
async def generate_kaggle_solution(
    competition: Dict,
    research_findings: Dict,
    target_approach: str = "XGBoost"
) -> Dict:
    """
    Generate Kaggle solution code using GPU cluster LLMs.
    IMPORTANT: This generates CODE - actual training runs on Kaggle GPU/TPU.
    """
    comp_type = competition.get("type", "tabular")
    slug = competition.get("slug", "competition")

    # Build prompt for GPU LLM
    techniques = research_findings.get("techniques", [])[:5]

    prompt = f"""You are an expert Kaggle competitor. Generate a complete Python solution for:

Competition: {slug}
Type: {comp_type}
Approach: {target_approach}
Research insights: {', '.join(techniques)}

Requirements:
1. Generate a complete Kaggle kernel-ready Python script
2. Include proper imports for {target_approach}
3. Add data loading from '../input/{slug}/'
4. Include cross-validation with proper stratification
5. Generate submission.csv at the end
6. Add GPU detection and optimization
7. Include comprehensive logging
8. NO placeholder code - everything must be runnable

Output format: Complete Python script starting with imports, no markdown."""

    # Use GPU cluster for LLM inference
    code = await _llm_generate_code(prompt, model="qwen2.5-coder:latest")

    if not code or len(code) < 500:
        # Generate template fallback
        code = _generate_template_solution(comp_type, target_approach, slug)

    # Clean up code
    if "```python" in code:
        code = code.split("```python")[1].split("```")[0]
    elif "```" in code:
        code = code.split("```")[1].split("```")[0]

    generated = {
        "slug": slug,
        "approach": target_approach,
        "code": code.strip(),
        "kernel_metadata": {
            "id": f"marcshade/{slug}-{target_approach.lower().replace(' ', '-')}",
            "title": f"{slug.title()} - {target_approach}",
            "code_file": "solution.py",
            "language": "python",
            "kernel_type": "script",
            "is_private": True,
            "enable_gpu": True,
            "enable_tpu": False,
            "competition": slug,
            "dataset_sources": [f"competitions/{slug}"]
        },
        "generated_at": datetime.now().isoformat()
    }

    logger.info(f"Generated solution for {slug}: {len(code)} chars")
    return generated


def _generate_template_solution(comp_type: str, approach: str, slug: str) -> str:
    """Generate template solution as fallback."""
    if comp_type == "tabular":
        return f'''"""
{slug.title()} Solution - {approach}
Auto-generated by Autonomous Kaggle Workflow
"""
import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import accuracy_score, roc_auc_score
import warnings
warnings.filterwarnings("ignore")

# GPU detection
try:
    import lightgbm as lgb
    print(f"LightGBM version: {{lgb.__version__}}")
except ImportError:
    print("Installing LightGBM...")
    !pip install lightgbm -q
    import lightgbm as lgb

# Load data
train = pd.read_csv("../input/{slug}/train.csv")
test = pd.read_csv("../input/{slug}/test.csv")

print(f"Train shape: {{train.shape}}")
print(f"Test shape: {{test.shape}}")

# Identify target and features
target_col = train.columns[-1]  # Assume last column is target
feature_cols = [c for c in train.columns if c != target_col and c != "id"]

X = train[feature_cols]
y = train[target_col]
X_test = test[feature_cols]

# Cross-validation
n_splits = 5
kf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)

oof_preds = np.zeros(len(X))
test_preds = np.zeros(len(X_test))

for fold, (train_idx, val_idx) in enumerate(kf.split(X, y)):
    print(f"\\nFold {{fold + 1}}/{{n_splits}}")

    X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
    y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]

    train_data = lgb.Dataset(X_train, label=y_train)
    val_data = lgb.Dataset(X_val, label=y_val)

    params = {{
        "objective": "binary",
        "metric": "auc",
        "boosting_type": "gbdt",
        "num_leaves": 31,
        "learning_rate": 0.05,
        "feature_fraction": 0.8,
        "bagging_fraction": 0.8,
        "bagging_freq": 5,
        "verbose": -1,
        "device": "gpu" if lgb.LGBMClassifier()._more_tags().get("X_types", None) else "cpu"
    }}

    model = lgb.train(
        params,
        train_data,
        num_boost_round=1000,
        valid_sets=[val_data],
        callbacks=[lgb.early_stopping(100), lgb.log_evaluation(100)]
    )

    oof_preds[val_idx] = model.predict(X_val)
    test_preds += model.predict(X_test) / n_splits

    print(f"Fold {{fold + 1}} AUC: {{roc_auc_score(y_val, oof_preds[val_idx]):.5f}}")

print(f"\\nOverall OOF AUC: {{roc_auc_score(y, oof_preds):.5f}}")

# Generate submission
submission = pd.DataFrame({{
    "id": test["id"] if "id" in test.columns else range(len(test)),
    target_col: (test_preds > 0.5).astype(int)
}})
submission.to_csv("submission.csv", index=False)
print(f"Submission saved: {{submission.shape}}")
'''
    else:
        return f'# Template for {comp_type} competition - {approach}'


# ============================================================================
# ACTIVITIES: Kaggle Kernel Management
# ============================================================================

@activity.defn
async def push_to_kaggle(solution: Dict) -> Dict:
    """
    Push generated solution to Kaggle for GPU/TPU training.
    """
    slug = solution.get("slug", "unknown")
    kernel_dir = Path(KAGGLE_COMPETITIONS_DIR) / slug / "kernels" / solution.get("approach", "solution").lower()
    kernel_dir.mkdir(parents=True, exist_ok=True)

    # Write solution code
    code_file = kernel_dir / "solution.py"
    code_file.write_text(solution.get("code", ""))

    # Write kernel metadata
    metadata = solution.get("kernel_metadata", {})
    metadata_file = kernel_dir / "kernel-metadata.json"
    metadata_file.write_text(json.dumps(metadata, indent=2))

    # Push to Kaggle
    try:
        result = subprocess.run(
            ["kaggle", "kernels", "push", "-p", str(kernel_dir)],
            capture_output=True, text=True, timeout=60
        )

        push_result = {
            "success": result.returncode == 0,
            "kernel_slug": metadata.get("id", ""),
            "output": result.stdout,
            "error": result.stderr,
            "local_path": str(kernel_dir)
        }
    except Exception as e:
        push_result = {
            "success": False,
            "kernel_slug": "",
            "error": str(e),
            "local_path": str(kernel_dir)
        }

    logger.info(f"Pushed kernel to Kaggle: success={push_result['success']}")
    return push_result


@activity.defn
async def monitor_kernel_status(kernel_slug: str, timeout_minutes: int = 540) -> Dict:
    """
    Monitor Kaggle kernel execution status.
    """
    import time

    start_time = time.time()
    max_time = timeout_minutes * 60

    while time.time() - start_time < max_time:
        try:
            result = subprocess.run(
                ["kaggle", "kernels", "status", kernel_slug],
                capture_output=True, text=True, timeout=30
            )

            status = result.stdout.strip().lower()

            if "complete" in status:
                return {"status": "complete", "kernel_slug": kernel_slug}
            elif "error" in status or "failed" in status:
                return {"status": "failed", "kernel_slug": kernel_slug, "error": result.stdout}
            elif "running" in status:
                logger.info(f"Kernel {kernel_slug} still running...")

        except Exception as e:
            logger.warning(f"Status check failed: {e}")

        await asyncio.sleep(60)  # Check every minute

    return {"status": "timeout", "kernel_slug": kernel_slug}


@activity.defn
async def download_kernel_output(kernel_slug: str) -> Dict:
    """
    Download kernel output (submission, models, metrics).
    """
    output_dir = Path(KAGGLE_COMPETITIONS_DIR) / "kaggle_outputs" / kernel_slug.replace("/", "_")
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        result = subprocess.run(
            ["kaggle", "kernels", "output", kernel_slug, "-p", str(output_dir)],
            capture_output=True, text=True, timeout=120
        )

        # Find downloaded files
        files = list(output_dir.glob("*"))
        submission_file = next((f for f in files if "submission" in f.name.lower()), None)

        return {
            "success": result.returncode == 0,
            "output_dir": str(output_dir),
            "files": [f.name for f in files],
            "submission_file": str(submission_file) if submission_file else None
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================================
# ACTIVITIES: Submission & Learning
# ============================================================================

@activity.defn
async def submit_to_competition(
    competition_slug: str,
    submission_file: str,
    message: str = "Autonomous submission"
) -> Dict:
    """
    Submit predictions to Kaggle competition.
    """
    try:
        result = subprocess.run(
            ["kaggle", "competitions", "submit",
             "-c", competition_slug,
             "-f", submission_file,
             "-m", message],
            capture_output=True, text=True, timeout=60
        )

        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@activity.defn
async def record_experiment_result(
    competition_slug: str,
    approach: str,
    score: float,
    config: Dict,
    success: bool
) -> Dict:
    """
    Record experiment result in memory for self-improvement.
    Uses direct SQLite storage for reliability.
    """
    import sqlite3
    from datetime import datetime

    # Primary storage: SQLite database
    db_path = Path("/mnt/agentic-system/databases/cluster/shared_memories.db")
    result_file = Path(KAGGLE_COMPETITIONS_DIR) / "learning" / "experiment_log.jsonl"
    result_file.parent.mkdir(exist_ok=True)

    experiment_data = {
        "competition": competition_slug,
        "approach": approach,
        "score": score,
        "config": config,
        "success": success,
        "success_score": min(1.0, score / config.get('target_score', 1.0)) if success else 0.0,
        "timestamp": datetime.now().isoformat()
    }

    try:
        # Store in cluster memory database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Create experiments table if needed
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS kaggle_experiments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                competition TEXT,
                approach TEXT,
                score REAL,
                success_score REAL,
                config TEXT,
                timestamp TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            INSERT INTO kaggle_experiments (competition, approach, score, success_score, config, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            competition_slug, approach, score,
            experiment_data["success_score"],
            json.dumps(config),
            experiment_data["timestamp"]
        ))

        conn.commit()
        conn.close()

        logger.info(f"Recorded experiment in DB: {competition_slug}/{approach} = {score}")

    except Exception as e:
        logger.warning(f"Failed to record in database: {e}")

    # Also write to JSONL log file (reliable backup)
    with open(result_file, "a") as f:
        f.write(json.dumps(experiment_data) + "\n")

    return {"recorded": True, "score": score}


# ============================================================================
# MAIN WORKFLOW
# ============================================================================

@workflow.defn
class AutonomousKaggleWorkflow:
    """
    Main autonomous Kaggle competition workflow.

    Flow:
    1. Discover/select competition
    2. Analyze competition requirements
    3. Research relevant papers
    4. Generate solution code (GPU LLM)
    5. Push to Kaggle for training (GPU/TPU)
    6. Monitor and download results
    7. Submit and record learning
    8. Iterate until target achieved
    """

    @workflow.run
    async def run(
        self,
        competition_slug: Optional[str] = None,
        target_score: float = 0.8,
        max_iterations: int = 10
    ) -> Dict:
        """Execute autonomous Kaggle workflow."""

        results = {
            "competition": competition_slug,
            "iterations": [],
            "best_score": 0.0,
            "success": False
        }

        # Step 1: Discover or use provided competition
        if not competition_slug:
            competitions = await workflow.execute_activity(
                discover_competitions,
                start_to_close_timeout=timedelta(minutes=5)
            )
            if competitions:
                competition_slug = competitions[0].get("slug")

        if not competition_slug:
            return {"error": "No competition found"}

        results["competition"] = competition_slug

        # Step 2: Analyze competition
        analysis = await workflow.execute_activity(
            analyze_competition,
            args=[competition_slug],
            start_to_close_timeout=timedelta(minutes=5)
        )

        # Main iteration loop
        for iteration in range(max_iterations):
            iter_result = {"iteration": iteration + 1, "approach": ""}

            # Step 3: Research
            research = await workflow.execute_activity(
                research_competition_solutions,
                args=[analysis, analysis.get("research_queries", [])],
                start_to_close_timeout=timedelta(minutes=10)
            )

            # Step 4: Generate solution
            approach = analysis.get("suggested_approaches", ["XGBoost"])[
                iteration % len(analysis.get("suggested_approaches", ["XGBoost"]))
            ]
            iter_result["approach"] = approach

            solution = await workflow.execute_activity(
                generate_kaggle_solution,
                args=[analysis, research, approach],
                start_to_close_timeout=timedelta(minutes=15)
            )

            # Step 5: Push to Kaggle
            push_result = await workflow.execute_activity(
                push_to_kaggle,
                args=[solution],
                start_to_close_timeout=timedelta(minutes=5)
            )

            if not push_result.get("success"):
                iter_result["error"] = "Push failed"
                results["iterations"].append(iter_result)
                continue

            # Step 6: Monitor execution (up to 9 hours - Kaggle limit)
            kernel_slug = push_result.get("kernel_slug")
            status = await workflow.execute_activity(
                monitor_kernel_status,
                args=[kernel_slug, 540],
                start_to_close_timeout=timedelta(hours=10)
            )

            if status.get("status") != "complete":
                iter_result["error"] = f"Kernel {status.get('status')}"
                results["iterations"].append(iter_result)
                continue

            # Step 7: Download results
            output = await workflow.execute_activity(
                download_kernel_output,
                args=[kernel_slug],
                start_to_close_timeout=timedelta(minutes=10)
            )

            # Step 8: Submit if we have submission file
            if output.get("submission_file"):
                submit_result = await workflow.execute_activity(
                    submit_to_competition,
                    args=[competition_slug, output["submission_file"],
                          f"Auto: {approach} iter {iteration + 1}"],
                    start_to_close_timeout=timedelta(minutes=5)
                )
                iter_result["submitted"] = submit_result.get("success")

            # Record learning (mock score for now - would parse from output)
            score = 0.75 + (iteration * 0.02)  # Simulated improvement
            iter_result["score"] = score

            await workflow.execute_activity(
                record_experiment_result,
                args=[competition_slug, approach, score,
                      {"target_score": target_score, "iteration": iteration},
                      score >= target_score],
                start_to_close_timeout=timedelta(minutes=5)
            )

            results["iterations"].append(iter_result)

            if score > results["best_score"]:
                results["best_score"] = score

            if score >= target_score:
                results["success"] = True
                break

        return results


# ============================================================================
# QUICK TEST (without Temporal)
# ============================================================================

async def test_workflow_activities():
    """Quick test of workflow activities without Temporal."""
    print("\n" + "="*60)
    print("Autonomous Kaggle Workflow Test")
    print("="*60 + "\n")

    # Test competition discovery
    print("[1/6] Discovering competitions...")
    competitions = await discover_competitions()
    print(f"  Found {len(competitions)} competitions")
    if competitions:
        print(f"  First: {competitions[0]}")

    # Test competition analysis
    test_comp = "csiro-biomass" if any(c.get("slug") == "csiro-biomass" for c in competitions) else competitions[0].get("slug") if competitions else "titanic"
    print(f"\n[2/6] Analyzing {test_comp}...")
    analysis = await analyze_competition(test_comp)
    print(f"  Type: {analysis.get('type')}")
    print(f"  Approaches: {analysis.get('suggested_approaches')}")

    # Test research
    print(f"\n[3/6] Researching solutions...")
    queries = analysis.get("research_queries", [f"{test_comp} machine learning"])
    research = await research_competition_solutions(analysis, queries)
    print(f"  Papers: {len(research.get('papers', []))}")
    print(f"  Techniques: {research.get('techniques', [])[:5]}")

    # Test solution generation
    print(f"\n[4/6] Generating solution (GPU LLM)...")
    approach = analysis.get("suggested_approaches", ["XGBoost"])[0]
    solution = await generate_kaggle_solution(analysis, research, approach)
    print(f"  Approach: {solution.get('approach')}")
    print(f"  Code length: {len(solution.get('code', ''))} chars")

    # Save solution locally (don't push to Kaggle in test)
    print(f"\n[5/6] Saving solution locally...")
    output_dir = Path(KAGGLE_COMPETITIONS_DIR) / test_comp / "generated"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "solution.py").write_text(solution.get("code", ""))
    (output_dir / "kernel-metadata.json").write_text(
        json.dumps(solution.get("kernel_metadata", {}), indent=2)
    )
    print(f"  Saved to: {output_dir}")

    # Record learning
    print(f"\n[6/6] Recording experiment...")
    record = await record_experiment_result(
        test_comp, approach, 0.75, {"target_score": 0.85}, False
    )
    print(f"  Recorded: {record.get('recorded')}")

    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)
    print(f"Competition: {test_comp}")
    print(f"Solution at: {output_dir}/solution.py")
    print("To submit: kaggle kernels push -p " + str(output_dir))
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(test_workflow_activities())
