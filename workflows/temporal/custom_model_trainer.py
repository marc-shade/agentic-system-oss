#!/usr/bin/env python3
"""
Custom Model Trainer - Train codebase-specific models for task execution

Training Approaches:
1. Quick Deploy: Ollama Modelfile with system prompts (immediate)
2. LoRA Fine-tuning: Adapter training on codebase patterns (hours)
3. Full Fine-tuning: Complete model training (days, requires GPU cluster)

Training Data Sources:
- Codebase patterns and conventions
- Successful task execution logs
- Test patterns and assertions
- Documentation styles

STATUS: Production Ready
"""

import asyncio
import json
import logging
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import sqlite3
import hashlib

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Paths
AGENTIC_BASE = Path("/Volumes/SSDRAID0/agentic-system")
TRAINING_DATA_DIR = AGENTIC_BASE / "training-data"
MODELS_DIR = AGENTIC_BASE / "models"
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")

# Ensure directories exist
TRAINING_DATA_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class TrainingExample:
    """Single training example for fine-tuning"""
    instruction: str
    input_context: str
    output: str
    category: str  # implement, test, research, plan, document
    source_file: Optional[str] = None
    quality_score: float = 1.0


@dataclass
class CodebasePattern:
    """Extracted pattern from codebase"""
    pattern_type: str  # import, class, function, test, config
    content: str
    file_path: str
    context: str
    frequency: int = 1


class TrainingDataCollector:
    """Collect and prepare training data from the codebase"""

    def __init__(self):
        self.patterns: List[CodebasePattern] = []
        self.examples: List[TrainingExample] = []
        self.db_path = TRAINING_DATA_DIR / "training_data.db"
        self._init_db()

    def _init_db(self):
        """Initialize SQLite database for training data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS patterns (
                id INTEGER PRIMARY KEY,
                pattern_type TEXT,
                content TEXT,
                file_path TEXT,
                context TEXT,
                frequency INTEGER DEFAULT 1,
                content_hash TEXT UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS training_examples (
                id INTEGER PRIMARY KEY,
                instruction TEXT,
                input_context TEXT,
                output TEXT,
                category TEXT,
                source_file TEXT,
                quality_score REAL DEFAULT 1.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_outcomes (
                id INTEGER PRIMARY KEY,
                task_id INTEGER,
                task_title TEXT,
                task_description TEXT,
                phase TEXT,
                provider TEXT,
                success INTEGER,
                output TEXT,
                error TEXT,
                execution_time REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()

    def collect_from_codebase(self, directories: List[str] = None) -> Dict:
        """Collect patterns from codebase directories"""
        if directories is None:
            directories = [
                str(AGENTIC_BASE / "mcp-servers"),
                str(AGENTIC_BASE / "intelligent-agents"),
                str(AGENTIC_BASE / "workflows"),
            ]

        stats = {"files_processed": 0, "patterns_found": 0, "examples_created": 0}

        for directory in directories:
            dir_path = Path(directory)
            if not dir_path.exists():
                logger.warning(f"Directory not found: {directory}")
                continue

            # Process Python files
            for py_file in dir_path.rglob("*.py"):
                if "__pycache__" in str(py_file) or ".pyc" in str(py_file):
                    continue

                try:
                    self._process_python_file(py_file)
                    stats["files_processed"] += 1
                except Exception as e:
                    logger.warning(f"Failed to process {py_file}: {e}")

        stats["patterns_found"] = len(self.patterns)
        stats["examples_created"] = len(self.examples)

        # Save to database
        self._save_patterns_to_db()
        self._save_examples_to_db()

        logger.info(f"Collection complete: {stats}")
        return stats

    def _process_python_file(self, file_path: Path):
        """Extract patterns from a Python file"""
        content = file_path.read_text(errors='ignore')
        lines = content.split('\n')

        # Extract imports
        imports = [line for line in lines if line.strip().startswith(('import ', 'from '))]
        if imports:
            self.patterns.append(CodebasePattern(
                pattern_type="import",
                content="\n".join(imports[:20]),  # First 20 imports
                file_path=str(file_path),
                context=f"Imports from {file_path.name}",
                frequency=len(imports)
            ))

        # Extract function definitions
        for i, line in enumerate(lines):
            if line.strip().startswith('def ') or line.strip().startswith('async def '):
                # Get function with docstring
                func_lines = [line]
                j = i + 1
                in_docstring = False
                while j < len(lines) and j < i + 30:  # Max 30 lines
                    func_lines.append(lines[j])
                    if '"""' in lines[j] or "'''" in lines[j]:
                        if in_docstring:
                            break
                        in_docstring = True
                    j += 1

                func_content = "\n".join(func_lines)
                self.patterns.append(CodebasePattern(
                    pattern_type="function",
                    content=func_content,
                    file_path=str(file_path),
                    context=f"Function from {file_path.name}"
                ))

                # Create training example from function
                if '"""' in func_content:
                    self._create_example_from_function(func_content, file_path)

        # Extract class definitions
        for i, line in enumerate(lines):
            if line.strip().startswith('class '):
                class_lines = [line]
                j = i + 1
                indent_level = len(line) - len(line.lstrip())
                while j < len(lines) and j < i + 50:
                    if lines[j].strip() and not lines[j].startswith(' ' * (indent_level + 1)):
                        if not lines[j].startswith(' ' * indent_level) or lines[j].strip().startswith('class '):
                            break
                    class_lines.append(lines[j])
                    j += 1

                self.patterns.append(CodebasePattern(
                    pattern_type="class",
                    content="\n".join(class_lines[:30]),
                    file_path=str(file_path),
                    context=f"Class from {file_path.name}"
                ))

    def _create_example_from_function(self, func_content: str, file_path: Path):
        """Create training example from function with docstring"""
        lines = func_content.split('\n')
        func_def = lines[0].strip()

        # Extract docstring
        docstring_lines = []
        in_docstring = False
        for line in lines[1:]:
            if '"""' in line or "'''" in line:
                if in_docstring:
                    docstring_lines.append(line)
                    break
                in_docstring = True
            if in_docstring:
                docstring_lines.append(line)

        if docstring_lines:
            docstring = "\n".join(docstring_lines).strip().strip('"""').strip("'''")

            # Determine category
            category = "implement"
            if "test" in file_path.name.lower() or func_def.startswith("def test"):
                category = "test"
            elif "doc" in docstring.lower():
                category = "document"

            self.examples.append(TrainingExample(
                instruction=f"Implement a function that: {docstring}",
                input_context=f"File: {file_path.name}",
                output=func_content,
                category=category,
                source_file=str(file_path)
            ))

    def _save_patterns_to_db(self):
        """Save patterns to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for pattern in self.patterns:
            content_hash = hashlib.md5(pattern.content.encode()).hexdigest()
            try:
                cursor.execute("""
                    INSERT OR IGNORE INTO patterns
                    (pattern_type, content, file_path, context, frequency, content_hash)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (pattern.pattern_type, pattern.content, pattern.file_path,
                      pattern.context, pattern.frequency, content_hash))
            except Exception as e:
                logger.warning(f"Failed to save pattern: {e}")

        conn.commit()
        conn.close()

    def _save_examples_to_db(self):
        """Save training examples to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for example in self.examples:
            try:
                cursor.execute("""
                    INSERT INTO training_examples
                    (instruction, input_context, output, category, source_file, quality_score)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (example.instruction, example.input_context, example.output,
                      example.category, example.source_file, example.quality_score))
            except Exception as e:
                logger.warning(f"Failed to save example: {e}")

        conn.commit()
        conn.close()

    def record_task_outcome(self, task_id: int, title: str, description: str,
                            phase: str, provider: str, success: bool,
                            output: str, error: str, execution_time: float):
        """Record task execution outcome for training"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO task_outcomes
            (task_id, task_title, task_description, phase, provider, success, output, error, execution_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (task_id, title, description, phase, provider, 1 if success else 0,
              output, error, execution_time))

        conn.commit()
        conn.close()

        # If successful, create training example
        if success and output:
            self.examples.append(TrainingExample(
                instruction=title,
                input_context=description,
                output=output[:5000],  # Limit size
                category=phase,
                quality_score=1.0 if success else 0.5
            ))
            self._save_examples_to_db()

    def export_training_data(self, format: str = "jsonl") -> Path:
        """Export training data for fine-tuning"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT instruction, input_context, output, category FROM training_examples")
        examples = cursor.fetchall()
        conn.close()

        output_file = TRAINING_DATA_DIR / f"training_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{format}"

        if format == "jsonl":
            with open(output_file, 'w') as f:
                for instruction, input_ctx, output, category in examples:
                    example = {
                        "instruction": instruction,
                        "input": input_ctx,
                        "output": output,
                        "category": category
                    }
                    f.write(json.dumps(example) + "\n")
        elif format == "json":
            data = [
                {"instruction": inst, "input": inp, "output": out, "category": cat}
                for inst, inp, out, cat in examples
            ]
            with open(output_file, 'w') as f:
                json.dump(data, f, indent=2)

        logger.info(f"Exported {len(examples)} examples to {output_file}")
        return output_file

    def get_stats(self) -> Dict:
        """Get training data statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM patterns")
        pattern_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM training_examples")
        example_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM task_outcomes WHERE success = 1")
        success_count = cursor.fetchone()[0]

        cursor.execute("SELECT category, COUNT(*) FROM training_examples GROUP BY category")
        category_counts = dict(cursor.fetchall())

        conn.close()

        return {
            "total_patterns": pattern_count,
            "total_examples": example_count,
            "successful_tasks": success_count,
            "examples_by_category": category_counts
        }


class OllamaModelBuilder:
    """Build and deploy custom Ollama models"""

    def __init__(self, base_model: str = "qwen2.5-coder:14b"):
        self.base_model = base_model
        self.model_name = "agentic-task-executor"

    def create_modelfile(self, system_prompt: str = None) -> Path:
        """Create Ollama Modelfile for custom model"""
        if system_prompt is None:
            system_prompt = self._generate_system_prompt()

        modelfile_content = f'''# Agentic Task Executor Model
# Based on {self.base_model} with codebase-specific training

FROM {self.base_model}

# Temperature for code generation (lower = more deterministic)
PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER top_k 40

# Context window
PARAMETER num_ctx 8192

# System prompt with codebase knowledge
SYSTEM """
{system_prompt}
"""

# License
LICENSE """
Custom model for 2 Acre Studios agentic system.
Based on {self.base_model}.
"""
'''

        modelfile_path = MODELS_DIR / "Modelfile.agentic-task-executor"
        modelfile_path.write_text(modelfile_content)
        logger.info(f"Created Modelfile at {modelfile_path}")
        return modelfile_path

    def _generate_system_prompt(self) -> str:
        """Generate system prompt from collected patterns"""
        collector = TrainingDataCollector()
        stats = collector.get_stats()

        # Load some patterns for context
        conn = sqlite3.connect(collector.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT content FROM patterns WHERE pattern_type = 'import' LIMIT 5")
        import_patterns = [row[0] for row in cursor.fetchall()]

        cursor.execute("SELECT content FROM patterns WHERE pattern_type = 'function' LIMIT 10")
        function_patterns = [row[0][:500] for row in cursor.fetchall()]

        conn.close()

        system_prompt = f'''You are an expert AI assistant specialized in the 2 Acre Studios agentic system codebase.

CODEBASE KNOWLEDGE:
- Total patterns learned: {stats['total_patterns']}
- Training examples: {stats['total_examples']}
- Categories: {stats.get('examples_by_category', {})}

CODING CONVENTIONS:
- Use Python 3.10+ with type hints
- Async/await for I/O operations
- Proper error handling with specific exceptions
- Logging with structured output
- Production-ready code only - no TODOs, placeholders, or mock data

COMMON IMPORTS:
{chr(10).join(import_patterns[:3]) if import_patterns else "# Standard library and framework imports"}

FUNCTION PATTERNS:
Follow these function patterns from the codebase:
{chr(10).join(f"# Example {i+1}:{chr(10)}{p[:300]}..." for i, p in enumerate(function_patterns[:3]))}

RESPONSE FORMAT:
1. For implementation tasks: Provide complete, runnable code
2. For research tasks: Structured analysis with sources
3. For testing tasks: Comprehensive test cases with assertions
4. For documentation: Clear, concise technical writing

Always prioritize:
- Code correctness and safety
- Following existing codebase patterns
- Production-ready implementations
- Proper error handling'''

        return system_prompt

    def build_model(self) -> Dict:
        """Build the custom model using Ollama"""
        modelfile_path = self.create_modelfile()

        logger.info(f"Building model {self.model_name} from {modelfile_path}")

        try:
            result = subprocess.run(
                ["ollama", "create", self.model_name, "-f", str(modelfile_path)],
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode == 0:
                logger.info(f"Model {self.model_name} created successfully")
                return {
                    "success": True,
                    "model_name": self.model_name,
                    "message": result.stdout
                }
            else:
                logger.error(f"Model creation failed: {result.stderr}")
                return {
                    "success": False,
                    "error": result.stderr
                }

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Model creation timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def test_model(self, test_prompt: str = None) -> Dict:
        """Test the custom model"""
        if test_prompt is None:
            test_prompt = "Write a Python function that checks if a port is available on localhost."

        try:
            result = subprocess.run(
                ["ollama", "run", self.model_name, test_prompt],
                capture_output=True,
                text=True,
                timeout=60
            )

            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr if result.returncode != 0 else None
            }

        except Exception as e:
            return {"success": False, "error": str(e)}


class LoRATrainer:
    """Fine-tune models using LoRA/QLoRA"""

    def __init__(self, base_model: str = "qwen2.5-coder:14b"):
        self.base_model = base_model
        self.training_dir = TRAINING_DATA_DIR / "lora_training"
        self.training_dir.mkdir(parents=True, exist_ok=True)

    def prepare_training_data(self) -> Path:
        """Prepare data in format suitable for LoRA training"""
        collector = TrainingDataCollector()

        # Export as JSONL
        data_file = collector.export_training_data("jsonl")

        # Convert to chat format for fine-tuning
        chat_data = []
        with open(data_file, 'r') as f:
            for line in f:
                example = json.loads(line)
                chat_data.append({
                    "messages": [
                        {"role": "system", "content": "You are an expert Python developer for the agentic system."},
                        {"role": "user", "content": f"{example['instruction']}\n\nContext: {example['input']}"},
                        {"role": "assistant", "content": example['output']}
                    ]
                })

        output_file = self.training_dir / "chat_training_data.jsonl"
        with open(output_file, 'w') as f:
            for item in chat_data:
                f.write(json.dumps(item) + "\n")

        logger.info(f"Prepared {len(chat_data)} examples for LoRA training")
        return output_file

    def create_training_config(self) -> Path:
        """Create LoRA training configuration"""
        config = {
            "model_name": self.base_model,
            "output_dir": str(self.training_dir / "output"),
            "lora_config": {
                "r": 16,
                "lora_alpha": 32,
                "lora_dropout": 0.05,
                "target_modules": ["q_proj", "v_proj", "k_proj", "o_proj"],
                "bias": "none",
                "task_type": "CAUSAL_LM"
            },
            "training_args": {
                "num_train_epochs": 3,
                "per_device_train_batch_size": 4,
                "gradient_accumulation_steps": 4,
                "learning_rate": 2e-4,
                "warmup_ratio": 0.03,
                "logging_steps": 10,
                "save_steps": 100,
                "fp16": True,
                "optim": "paged_adamw_8bit"
            }
        }

        config_path = self.training_dir / "lora_config.json"
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)

        return config_path

    def generate_training_script(self) -> Path:
        """Generate LoRA training script"""
        script = '''#!/usr/bin/env python3
"""
LoRA Fine-tuning Script for Agentic Task Executor

Requirements:
pip install transformers peft bitsandbytes accelerate datasets trl

Run:
python train_lora.py
"""

import json
import torch
from datasets import load_dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments,
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from trl import SFTTrainer

# Load config
with open("lora_config.json", "r") as f:
    config = json.load(f)

# Quantization config for QLoRA
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16,
    bnb_4bit_use_double_quant=True,
)

# Load model and tokenizer
model = AutoModelForCausalLM.from_pretrained(
    config["model_name"],
    quantization_config=bnb_config,
    device_map="auto",
    trust_remote_code=True,
)
model = prepare_model_for_kbit_training(model)

tokenizer = AutoTokenizer.from_pretrained(config["model_name"], trust_remote_code=True)
tokenizer.pad_token = tokenizer.eos_token

# LoRA config
peft_config = LoraConfig(**config["lora_config"])
model = get_peft_model(model, peft_config)

# Load dataset
dataset = load_dataset("json", data_files="chat_training_data.jsonl", split="train")

# Training arguments
training_args = TrainingArguments(
    output_dir=config["output_dir"],
    **config["training_args"]
)

# Trainer
trainer = SFTTrainer(
    model=model,
    train_dataset=dataset,
    peft_config=peft_config,
    tokenizer=tokenizer,
    args=training_args,
    max_seq_length=2048,
)

# Train
trainer.train()

# Save
trainer.save_model(config["output_dir"])
print(f"Model saved to {config['output_dir']}")
'''

        script_path = self.training_dir / "train_lora.py"
        script_path.write_text(script)
        script_path.chmod(0o755)

        return script_path


async def main():
    """Main training pipeline"""
    print("=" * 60)
    print("Custom Model Training Pipeline")
    print("=" * 60)

    # Step 1: Collect training data
    print("\n1. Collecting training data from codebase...")
    collector = TrainingDataCollector()
    stats = collector.collect_from_codebase()
    print(f"   Collected: {stats}")

    # Step 2: Build quick Ollama model
    print("\n2. Building Ollama model with system prompt...")
    builder = OllamaModelBuilder()
    result = builder.build_model()
    print(f"   Result: {result}")

    # Step 3: Test the model
    if result.get("success"):
        print("\n3. Testing custom model...")
        test_result = builder.test_model()
        print(f"   Test success: {test_result.get('success')}")
        if test_result.get('output'):
            print(f"   Output preview: {test_result['output'][:200]}...")

    # Step 4: Prepare LoRA training (for deeper fine-tuning)
    print("\n4. Preparing LoRA training infrastructure...")
    lora_trainer = LoRATrainer()
    data_file = lora_trainer.prepare_training_data()
    config_file = lora_trainer.create_training_config()
    script_file = lora_trainer.generate_training_script()
    print(f"   Training data: {data_file}")
    print(f"   Config: {config_file}")
    print(f"   Script: {script_file}")

    # Summary
    print("\n" + "=" * 60)
    print("Training Setup Complete!")
    print("=" * 60)
    final_stats = collector.get_stats()
    print(f"\nTraining Data Statistics:")
    print(f"  - Patterns: {final_stats['total_patterns']}")
    print(f"  - Examples: {final_stats['total_examples']}")
    print(f"  - By Category: {final_stats.get('examples_by_category', {})}")
    print(f"\nQuick Deploy Model: agentic-task-executor")
    print(f"LoRA Training Dir: {lora_trainer.training_dir}")
    print(f"\nTo run LoRA training:")
    print(f"  cd {lora_trainer.training_dir}")
    print(f"  pip install transformers peft bitsandbytes accelerate datasets trl")
    print(f"  python train_lora.py")


if __name__ == "__main__":
    asyncio.run(main())
