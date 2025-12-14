# Kaggle EDA Command

Perform exploratory data analysis and generate insights notebook.

## Arguments

- `competition-name`: The Kaggle competition identifier
- `target-column` (optional): Name of target variable if known

## Task

1. Navigate to competition directory:
   ```bash
   cd ~/kaggle-competitions/$COMPETITION_NAME
   ```

2. Create EDA Jupyter notebook at `notebooks/01-eda.ipynb` with:

   **Cell 1: Setup and Data Loading**
   ```python
   import pandas as pd
   import numpy as np
   import matplotlib.pyplot as plt
   import seaborn as sns
   from pathlib import Path

   # Try kagglehub for direct DataFrame loading (faster, cached)
   try:
       import kagglehub
       from kagglehub import KaggleDatasetAdapter

       print("Loading data with kagglehub (cached, optimized)...")

       # Load train data directly as DataFrame
       train = kagglehub.competition_download('$COMPETITION_NAME')
       train = pd.read_csv(Path(train) / 'train.csv')
       test = pd.read_csv(Path(train) / 'test.csv')

       print("✓ Loaded via kagglehub")

   except (ImportError, Exception) as e:
       print(f"Kagglehub not available: {e}")
       print("Loading from local data directory...")
       train = pd.read_csv('../data/train.csv')
       test = pd.read_csv('../data/test.csv')

   # Set visualization style
   sns.set_style('whitegrid')
   plt.rcParams['figure.figsize'] = (12, 6)

   print(f"\nTrain shape: {train.shape}")
   print(f"Test shape: {test.shape}")
   print(f"Memory usage: {train.memory_usage(deep=True).sum() / 1024**2:.2f} MB")
   ```

   **Cell 2: Data Overview**
   ```python
   # Display first rows
   display(train.head())

   # Data types and missing values
   info_df = pd.DataFrame({
       'dtype': train.dtypes,
       'missing': train.isnull().sum(),
       'missing_pct': (train.isnull().sum() / len(train) * 100).round(2)
   })
   display(info_df[info_df['missing'] > 0].sort_values('missing', ascending=False))

   # Basic statistics
   display(train.describe())
   ```

   **Cell 3: Target Distribution** (if target specified)
   ```python
   if '$TARGET_COLUMN' in train.columns:
       plt.figure(figsize=(10, 6))
       train['$TARGET_COLUMN'].value_counts().plot(kind='bar')
       plt.title('Target Distribution')
       plt.xlabel('$TARGET_COLUMN')
       plt.ylabel('Count')
       plt.show()

       print(f"Target value counts:\n{train['$TARGET_COLUMN'].value_counts()}")
       print(f"Target balance: {train['$TARGET_COLUMN'].value_counts(normalize=True)}")
   ```

   **Cell 4: Numerical Features**
   ```python
   numerical_cols = train.select_dtypes(include=['int64', 'float64']).columns.tolist()
   if '$TARGET_COLUMN' in numerical_cols:
       numerical_cols.remove('$TARGET_COLUMN')

   # Distributions
   for col in numerical_cols[:6]:  # First 6 features
       plt.figure(figsize=(12, 4))

       plt.subplot(1, 2, 1)
       train[col].hist(bins=50)
       plt.title(f'{col} - Distribution')

       plt.subplot(1, 2, 2)
       train.boxplot(column=col)
       plt.title(f'{col} - Boxplot')

       plt.tight_layout()
       plt.show()
   ```

   **Cell 5: Categorical Features**
   ```python
   categorical_cols = train.select_dtypes(include=['object']).columns.tolist()

   for col in categorical_cols[:6]:  # First 6 features
       print(f"\n{col} value counts:")
       print(train[col].value_counts().head(10))

       plt.figure(figsize=(10, 6))
       train[col].value_counts().head(10).plot(kind='bar')
       plt.title(f'{col} - Top 10 Values')
       plt.xticks(rotation=45)
       plt.tight_layout()
       plt.show()
   ```

   **Cell 6: Correlation Analysis**
   ```python
   # Correlation matrix for numerical features
   if len(numerical_cols) > 0:
       plt.figure(figsize=(12, 10))
       correlation = train[numerical_cols].corr()
       sns.heatmap(correlation, annot=True, fmt='.2f', cmap='coolwarm', center=0)
       plt.title('Feature Correlation Matrix')
       plt.tight_layout()
       plt.show()

       # Features most correlated with target
       if '$TARGET_COLUMN' in train.columns and train['$TARGET_COLUMN'].dtype in ['int64', 'float64']:
           target_corr = train.corr()['$TARGET_COLUMN'].abs().sort_values(ascending=False)
           print("\nTop features correlated with target:")
           print(target_corr.head(10))
   ```

   **Cell 7: Missing Data Visualization**
   ```python
   import missingno as msno

   msno.matrix(train)
   plt.title('Missing Data Pattern')
   plt.show()
   ```

   **Cell 8: Key Insights**
   ```markdown
   ## Key Findings

   ### Data Quality
   - [ ] Missing values: [describe patterns]
   - [ ] Outliers: [describe significant outliers]
   - [ ] Data types: [any issues?]

   ### Feature Insights
   - [ ] Important numerical features: [list]
   - [ ] Important categorical features: [list]
   - [ ] Feature engineering opportunities: [list ideas]

   ### Modeling Approach
   - [ ] Problem type: [classification/regression]
   - [ ] Evaluation metric: [from competition]
   - [ ] Baseline strategy: [simple approach to beat]
   - [ ] Advanced strategies: [ideas to try]
   ```

3. Launch Jupyter Lab to view notebook:
   ```bash
   cd ~/kaggle-competitions/$COMPETITION_NAME
   jupyter lab notebooks/01-eda.ipynb
   ```

## Output

- Path to created EDA notebook
- Instructions to run and review analysis
- Key insights to inform feature engineering
