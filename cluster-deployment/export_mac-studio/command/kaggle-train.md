# Kaggle Train Command

Train machine learning model with cross-validation.

## Arguments

- `competition-name`: The Kaggle competition identifier
- `model-type`: Model type (xgboost, lightgbm, catboost, random-forest, neural-net)
- `target-column`: Name of target variable

## Task

1. Navigate to competition directory:
   ```bash
   cd ~/kaggle-competitions/$COMPETITION_NAME
   ```

2. Create training notebook at `notebooks/02-train-$MODEL_TYPE.ipynb`:

   **Cell 1: Setup and Data Loading**
   ```python
   import pandas as pd
   import numpy as np
   from sklearn.model_selection import cross_val_score, StratifiedKFold, KFold
   from sklearn.metrics import *
   import joblib
   from pathlib import Path

   # Load processed data (or raw if feature engineering not done yet)
   train = pd.read_csv('../data/train.csv')
   test = pd.read_csv('../data/test.csv')

   # Separate features and target
   target_col = '$TARGET_COLUMN'
   X = train.drop(columns=[target_col])
   y = train[target_col]
   X_test = test.copy()

   print(f"Training data: {X.shape}")
   print(f"Test data: {X_test.shape}")
   ```

   **Cell 2: Feature Preprocessing**
   ```python
   from sklearn.preprocessing import LabelEncoder, StandardScaler
   from sklearn.impute import SimpleImputer

   # Identify categorical and numerical columns
   categorical_cols = X.select_dtypes(include=['object']).columns.tolist()
   numerical_cols = X.select_dtypes(include=['int64', 'float64']).columns.tolist()

   # Handle missing values
   num_imputer = SimpleImputer(strategy='median')
   cat_imputer = SimpleImputer(strategy='most_frequent')

   X[numerical_cols] = num_imputer.fit_transform(X[numerical_cols])
   X_test[numerical_cols] = num_imputer.transform(X_test[numerical_cols])

   if len(categorical_cols) > 0:
       X[categorical_cols] = cat_imputer.fit_transform(X[categorical_cols])
       X_test[categorical_cols] = cat_imputer.transform(X_test[categorical_cols])

       # Label encode categorical features
       label_encoders = {}
       for col in categorical_cols:
           le = LabelEncoder()
           X[col] = le.fit_transform(X[col].astype(str))
           X_test[col] = le.transform(X_test[col].astype(str))
           label_encoders[col] = le

   print(f"Processed features: {X.shape[1]}")
   ```

   **Cell 3: Model Configuration**
   ```python
   # Model-specific imports and configuration
   if '$MODEL_TYPE' == 'xgboost':
       import xgboost as xgb
       model = xgb.XGBClassifier(
           n_estimators=1000,
           learning_rate=0.01,
           max_depth=6,
           subsample=0.8,
           colsample_bytree=0.8,
           random_state=42,
           n_jobs=-1
       )

   elif '$MODEL_TYPE' == 'lightgbm':
       import lightgbm as lgb
       model = lgb.LGBMClassifier(
           n_estimators=1000,
           learning_rate=0.01,
           max_depth=6,
           num_leaves=31,
           subsample=0.8,
           colsample_bytree=0.8,
           random_state=42,
           n_jobs=-1
       )

   elif '$MODEL_TYPE' == 'catboost':
       from catboost import CatBoostClassifier
       model = CatBoostClassifier(
           iterations=1000,
           learning_rate=0.01,
           depth=6,
           random_state=42,
           verbose=100
       )

   elif '$MODEL_TYPE' == 'random-forest':
       from sklearn.ensemble import RandomForestClassifier
       model = RandomForestClassifier(
           n_estimators=500,
           max_depth=10,
           min_samples_split=5,
           random_state=42,
           n_jobs=-1
       )

   elif '$MODEL_TYPE' == 'neural-net':
       from sklearn.neural_network import MLPClassifier
       from sklearn.preprocessing import StandardScaler

       scaler = StandardScaler()
       X = scaler.fit_transform(X)
       X_test = scaler.transform(X_test)

       model = MLPClassifier(
           hidden_layer_sizes=(100, 50),
           max_iter=1000,
           random_state=42
       )
   ```

   **Cell 4: Cross-Validation**
   ```python
   # Determine if classification or regression
   is_classification = y.dtype == 'object' or len(y.unique()) < 20

   if is_classification:
       cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
       scoring = 'accuracy'
   else:
       cv = KFold(n_splits=5, shuffle=True, random_state=42)
       scoring = 'neg_mean_squared_error'

   # Perform cross-validation
   cv_scores = cross_val_score(model, X, y, cv=cv, scoring=scoring, n_jobs=-1)

   print(f"\nCross-Validation Results:")
   print(f"Mean Score: {cv_scores.mean():.4f}")
   print(f"Std Score: {cv_scores.std():.4f}")
   print(f"Individual Folds: {cv_scores}")
   ```

   **Cell 5: Train Final Model**
   ```python
   # Train on full dataset
   model.fit(X, y)

   # Feature importance
   if hasattr(model, 'feature_importances_'):
       feature_importance = pd.DataFrame({
           'feature': X.columns,
           'importance': model.feature_importances_
       }).sort_values('importance', ascending=False)

       print("\nTop 10 Important Features:")
       print(feature_importance.head(10))

       # Plot feature importance
       import matplotlib.pyplot as plt
       plt.figure(figsize=(10, 8))
       feature_importance.head(20).plot(x='feature', y='importance', kind='barh')
       plt.title('Top 20 Feature Importances')
       plt.xlabel('Importance')
       plt.tight_layout()
       plt.show()
   ```

   **Cell 6: Generate Predictions**
   ```python
   # Make predictions on test set
   if is_classification:
       predictions = model.predict(X_test)
       prediction_proba = model.predict_proba(X_test)
   else:
       predictions = model.predict(X_test)

   print(f"\nPredictions generated: {len(predictions)}")
   print(f"Unique predictions: {len(np.unique(predictions))}")
   ```

   **Cell 7: Save Model and Predictions**
   ```python
   # Save model
   model_path = Path('../models') / f'{model_type}_cv{cv_scores.mean():.4f}.pkl'
   model_path.parent.mkdir(exist_ok=True)
   joblib.dump(model, model_path)
   print(f"Model saved: {model_path}")

   # Save predictions
   submission = pd.DataFrame({
       'id': test.index,  # Adjust based on competition requirements
       'prediction': predictions
   })

   submission_path = Path('../submissions') / f'{model_type}_cv{cv_scores.mean():.4f}.csv'
   submission_path.parent.mkdir(exist_ok=True)
   submission.to_csv(submission_path, index=False)
   print(f"Predictions saved: {submission_path}")
   ```

3. Execute training notebook:
   ```bash
   jupyter nbconvert --to notebook --execute notebooks/02-train-$MODEL_TYPE.ipynb
   ```

## Output

- Path to training notebook
- Cross-validation scores
- Feature importance (if available)
- Path to saved model
- Path to predictions file ready for submission
