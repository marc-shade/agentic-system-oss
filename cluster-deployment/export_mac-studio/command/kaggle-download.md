# Kaggle Download Command

Download competition data using modern kagglehub or CLI.

## Arguments

- `competition-name`: The Kaggle competition identifier (e.g., "titanic")
- `method` (optional): "kagglehub" (default) or "cli"

## Task

1. **Create competition directory structure**:
   ```bash
   mkdir -p ~/kaggle-competitions/$COMPETITION_NAME/{data,notebooks,models,submissions}
   cd ~/kaggle-competitions/$COMPETITION_NAME
   ```

2. **Download competition files**:

   **Method 1: Using kagglehub (recommended)**:
   ```python
   import kagglehub
   from pathlib import Path
   import shutil

   # Download competition data
   print(f"Downloading {competition_name} competition data with kagglehub...")

   try:
       # Download to kagglehub cache
       cache_path = kagglehub.competition_download(competition_name)
       print(f"Downloaded to cache: {cache_path}")

       # Copy files to our data directory
       data_dir = Path("data")
       data_dir.mkdir(exist_ok=True)

       for file in Path(cache_path).glob("*"):
           shutil.copy2(file, data_dir / file.name)
           print(f"  ✓ {file.name}")

       print(f"\n✓ All files copied to: {data_dir.absolute()}")

   except Exception as e:
       print(f"✗ Kagglehub download failed: {e}")
       print("Falling back to kaggle CLI...")
       # Fall back to CLI method below
   ```

   **Method 2: Using kaggle CLI (fallback)**:
   ```bash
   kaggle competitions download -c $COMPETITION_NAME -p data/

   # Extract downloaded files
   cd data/
   unzip -o "*.zip"
   rm *.zip
   cd ..
   ```

3. **List downloaded files with sizes**:
   ```bash
   ls -lh data/
   ```

4. **Analyze data files**:
   ```python
   import pandas as pd
   from pathlib import Path

   data_dir = Path("data")
   csv_files = list(data_dir.glob("*.csv"))

   print("\nData File Summary:")
   print("=" * 60)

   for csv_file in csv_files:
       try:
           df = pd.read_csv(csv_file)
           print(f"\n{csv_file.name}:")
           print(f"  Rows: {len(df):,}")
           print(f"  Columns: {len(df.columns)}")
           print(f"  Size: {csv_file.stat().st_size / 1024 / 1024:.2f} MB")
           print(f"  Columns: {', '.join(df.columns.tolist()[:5])}" +
                 ("..." if len(df.columns) > 5 else ""))
       except Exception as e:
           print(f"\n{csv_file.name}: Unable to read - {e}")

   # Try to identify train/test splits
   train_files = [f for f in csv_files if 'train' in f.name.lower()]
   test_files = [f for f in csv_files if 'test' in f.name.lower()]

   if train_files:
       print(f"\n✓ Training data: {train_files[0].name}")
   if test_files:
       print(f"✓ Test data: {test_files[0].name}")
   ```

5. **Create initial README.md**:
   ```python
   import pandas as pd
   from pathlib import Path
   from datetime import datetime

   # Get data files info
   data_dir = Path("data")
   csv_files = list(data_dir.glob("*.csv"))

   readme_content = f"""# {competition_name.title()} Competition

   Competition URL: https://www.kaggle.com/c/{competition_name}

   Downloaded: {datetime.now().strftime('%Y-%m-%d %H:%M')}

   ## Data Files

   """

   for csv_file in csv_files:
       try:
           df = pd.read_csv(csv_file)
           readme_content += f"- **{csv_file.name}**: {len(df):,} rows, {len(df.columns)} columns\n"
       except:
           readme_content += f"- **{csv_file.name}**: [Unable to read]\n"

   readme_content += """
   ## Approach

   ### Phase 1: EDA
   - [ ] Analyze data distributions
   - [ ] Identify missing values
   - [ ] Check correlations
   - [ ] Feature engineering ideas

   ### Phase 2: Baseline
   - [ ] Simple model baseline
   - [ ] Cross-validation setup
   - [ ] Initial submission

   ### Phase 3: Iteration
   - [ ] Feature engineering
   - [ ] Model tuning
   - [ ] Ensemble methods

   ## Results

   | Date | Model | CV Score | LB Score | Notes |
   |------|-------|----------|----------|-------|
   | | | | | |
   """

   with open("README.md", "w") as f:
       f.write(readme_content)

   print(f"\n✓ Created README.md")
   ```

6. **Quick data preview**:
   ```python
   # Load and preview the most likely training file
   train_candidates = [f for f in csv_files if 'train' in f.name.lower()]

   if train_candidates:
       train_file = train_candidates[0]
       print(f"\nPreview of {train_file.name}:")
       print("=" * 60)
       df = pd.read_csv(train_file)
       print(df.head())
       print(f"\nData types:\n{df.dtypes}")
       print(f"\nMissing values:\n{df.isnull().sum()[df.isnull().sum() > 0]}")
   ```

## Output

- ✓ Competition data downloaded (via kagglehub or CLI)
- ✓ Files organized in data/ directory
- ✓ Data file summaries (rows, columns, size)
- ✓ README.md created with competition structure
- ✓ Quick data preview displayed
- Path to competition working directory

## Performance Note

Kagglehub uses intelligent caching - if you've previously downloaded the data, it will be served from cache instantly instead of re-downloading.
