# Kaggle Setup Command

Initialize Kaggle environment with modern kagglehub library and CLI.

## Task

1. **Install kagglehub** (recommended modern approach):
   ```bash
   pip install kagglehub

   # Optional: Install data adapters
   pip install kagglehub[pandas-datasets]  # Pandas DataFrames
   pip install kagglehub[polars-datasets]  # Polars (fastest)
   pip install kagglehub[hf-datasets]      # Hugging Face datasets
   ```

2. **Install kaggle CLI** (legacy, still widely used):
   ```bash
   pip install kaggle
   ```

3. **Verify kaggle.json credentials** at `~/.kaggle/kaggle.json`:
   - If missing, prompt user to:
     1. Go to https://www.kaggle.com/settings
     2. Click "Create New API Token"
     3. Save kaggle.json to ~/.kaggle/
   - Set permissions: `chmod 600 ~/.kaggle/kaggle.json`

4. **Test authentication with kagglehub**:
   ```python
   import kagglehub

   # Test with a small dataset download
   try:
       path = kagglehub.dataset_download('unsdsn/world-happiness', version=1)
       print(f"✓ Kagglehub authenticated successfully")
       print(f"  Test data downloaded to: {path}")
   except Exception as e:
       print(f"✗ Kagglehub authentication failed: {e}")
       print("  Run: kagglehub.login() for interactive setup")
   ```

5. **Test authentication with kaggle CLI**:
   ```bash
   kaggle competitions list --page 1
   ```

6. **Report versions and status**:
   ```python
   import kagglehub
   import subprocess

   print("Kaggle Environment Status:")
   print("=" * 60)
   print(f"Kagglehub version: {kagglehub.__version__}")

   # Get CLI version
   result = subprocess.run(['kaggle', '--version'], capture_output=True, text=True)
   print(f"Kaggle CLI version: {result.stdout.strip()}")

   # Get username from credentials
   import json
   from pathlib import Path

   creds_path = Path.home() / '.kaggle' / 'kaggle.json'
   if creds_path.exists():
       with open(creds_path) as f:
           creds = json.load(f)
           print(f"Authenticated as: {creds['username']}")
   ```

7. **Create working directory structure**:
   ```bash
   mkdir -p ~/kaggle-competitions
   ```

   Competition-specific structure (created on download):
   ```
   ~/kaggle-competitions/[competition-name]/
   ├── data/           # Downloaded datasets
   ├── notebooks/      # Jupyter notebooks
   ├── models/         # Trained models
   ├── submissions/    # Submission files
   └── README.md       # Competition notes
   ```

8. **Install recommended libraries**:
   ```bash
   pip install jupyter jupyterlab pandas numpy matplotlib seaborn scikit-learn xgboost lightgbm catboost
   ```

## Output

Report showing:
- ✓ Kagglehub installed and authenticated
- ✓ Kaggle CLI installed and authenticated
- ✓ Username from credentials
- ✓ Working directory created
- ✓ Recommended libraries installed

## Choosing Between kagglehub and CLI

**Use kagglehub (recommended)** for:
- ✅ Python-first workflows
- ✅ Direct DataFrame loading
- ✅ Better caching and performance
- ✅ Modern API with adapters
- ✅ Model and notebook output access

**Use kaggle CLI** for:
- ✅ Shell scripts and automation
- ✅ Quick downloads from terminal
- ✅ Legacy workflows and documentation
- ✅ Competition submissions (still required)
