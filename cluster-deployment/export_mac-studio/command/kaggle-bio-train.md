# Kaggle Bioinformatics Training Command

Train models for bioinformatics competitions (protein function, genomics, etc.).

## Arguments

- `competition-name`: The Kaggle competition identifier
- `task-type`: Type of bio task (protein-function, genomics, drug-discovery)
- `target-column` (optional): Name of target variable

## Task

1. **Navigate to competition directory**:
   ```bash
   cd ~/kaggle-competitions/$COMPETITION_NAME
   ```

2. **Install bioinformatics libraries**:
   ```bash
   pip install biopython fair-esm transformers torch
   pip install scikit-learn xgboost lightgbm
   pip install matplotlib seaborn plotly
   ```

3. **Create bioinformatics training notebook**:

   Create `notebooks/03-bio-train-$TASK_TYPE.ipynb` with:

   **Cell 1: Setup and Imports**
   ```python
   import torch
   import esm  # Protein language model
   from Bio import SeqIO, Seq
   from Bio.SeqUtils.ProtParam import ProteinAnalysis
   import numpy as np
   import pandas as pd
   from sklearn.model_selection import StratifiedKFold, train_test_split
   from sklearn.preprocessing import MultiLabelBinarizer, StandardScaler
   from sklearn.metrics import f1_score, hamming_loss, accuracy_score
   import xgboost as xgb
   import lightgbm as lgb
   from tqdm import tqdm
   import matplotlib.pyplot as plt
   import seaborn as sns

   # Check for GPU
   device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
   print(f"Using device: {device}")
   ```

   **Cell 2: Load Protein Language Model (ESM-2)**
   ```python
   # Load ESM-2 model (protein language model from Meta)
   print("Loading ESM-2 protein language model...")

   # Choose model size based on available memory
   # esm2_t33_650M_UR50D: 650M parameters (recommended)
   # esm2_t30_150M_UR50D: 150M parameters (faster)
   # esm2_t36_3B_UR50D: 3B parameters (best quality, requires large GPU)

   model, alphabet = esm.pretrained.esm2_t33_650M_UR50D()
   model = model.to(device)
   model.eval()
   batch_converter = alphabet.get_batch_converter()

   print(f"✓ Model loaded: {model.num_layers} layers")
   ```

   **Cell 3: Extract Protein Embeddings**
   ```python
   def get_protein_embedding(sequence, model, alphabet, batch_converter, device):
       """
       Extract embedding vector for a protein sequence
       """
       # Prepare data
       data = [("protein", sequence)]
       batch_labels, batch_strs, batch_tokens = batch_converter(data)
       batch_tokens = batch_tokens.to(device)

       # Extract embeddings
       with torch.no_grad():
           results = model(batch_tokens, repr_layers=[33], return_contacts=False)

       # Get per-token embeddings from last layer
       token_embeddings = results["representations"][33]

       # Average pooling (mean over sequence length)
       # Shape: [1, seq_len, embedding_dim] -> [1, embedding_dim]
       sequence_embedding = token_embeddings.mean(dim=1)

       return sequence_embedding.cpu().numpy()[0]

   # Test embedding extraction
   test_sequence = "MKTIIALSYIFCLVFADYKDDDDK"
   test_embedding = get_protein_embedding(
       test_sequence, model, alphabet, batch_converter, device
   )
   print(f"\nTest embedding shape: {test_embedding.shape}")
   print(f"Embedding dimension: {len(test_embedding)}")
   ```

   **Cell 4: Extract Sequence Features**
   ```python
   def extract_sequence_features(sequence):
       """
       Extract traditional sequence-based features
       """
       try:
           analysis = ProteinAnalysis(str(sequence))

           features = {
               # Basic properties
               'length': len(sequence),
               'molecular_weight': analysis.molecular_weight(),
               'aromaticity': analysis.aromaticity(),
               'instability_index': analysis.instability_index(),
               'isoelectric_point': analysis.isoelectric_point(),

               # Secondary structure
               'helix_fraction': analysis.secondary_structure_fraction()[0],
               'turn_fraction': analysis.secondary_structure_fraction()[1],
               'sheet_fraction': analysis.secondary_structure_fraction()[2],

               # Amino acid composition (20 features)
               **{f'aa_{aa}': analysis.get_amino_acids_percent().get(aa, 0)
                  for aa in 'ACDEFGHIKLMNPQRSTVWY'}
           }

           return features

       except Exception as e:
           print(f"Error extracting features: {e}")
           return {key: 0 for key in ['length', 'molecular_weight', 'aromaticity']}

   # Test feature extraction
   test_features = extract_sequence_features(test_sequence)
   print(f"\nExtracted {len(test_features)} features")
   print(f"Sample features: {list(test_features.items())[:5]}")
   ```

   **Cell 5: Load and Process Training Data**
   ```python
   # Load training data
   train_df = pd.read_csv('../data/train.csv')

   print(f"Training samples: {len(train_df)}")
   print(f"Columns: {train_df.columns.tolist()}")
   print(f"\nSample:")
   print(train_df.head())

   # Extract embeddings for all sequences
   print("\nExtracting protein embeddings...")

   embeddings = []
   seq_features_list = []

   for idx, row in tqdm(train_df.iterrows(), total=len(train_df)):
       sequence = row['sequence']

       # ESM-2 embedding
       embedding = get_protein_embedding(
           sequence, model, alphabet, batch_converter, device
       )
       embeddings.append(embedding)

       # Traditional features
       seq_features = extract_sequence_features(sequence)
       seq_features_list.append(seq_features)

   # Convert to arrays
   embeddings_array = np.array(embeddings)
   seq_features_df = pd.DataFrame(seq_features_list)

   # Combine features
   X_esm = embeddings_array
   X_traditional = seq_features_df.values

   # Concatenate
   X_combined = np.hstack([X_esm, X_traditional])

   print(f"\n✓ Feature extraction complete")
   print(f"  ESM embeddings shape: {X_esm.shape}")
   print(f"  Traditional features shape: {X_traditional.shape}")
   print(f"  Combined features shape: {X_combined.shape}")
   ```

   **Cell 6: Prepare Multi-Label Targets (for Protein Function)**
   ```python
   # Protein function prediction is typically multi-label
   # Each protein can have multiple GO (Gene Ontology) terms

   if '$TASK_TYPE' == 'protein-function':
       # Parse GO terms
       def parse_go_terms(go_string):
           """Parse GO terms from string format"""
           if pd.isna(go_string):
               return []
           return [term.strip() for term in go_string.split(';')]

       # Extract all GO terms
       train_df['go_terms_list'] = train_df['$TARGET_COLUMN'].apply(parse_go_terms)

       # Multi-label binarization
       mlb = MultiLabelBinarizer()
       y_multilabel = mlb.fit_transform(train_df['go_terms_list'])

       print(f"\nMulti-label setup:")
       print(f"  Number of GO terms (classes): {len(mlb.classes_)}")
       print(f"  Target matrix shape: {y_multilabel.shape}")
       print(f"  Average labels per protein: {y_multilabel.sum(axis=1).mean():.2f}")
       print(f"\nTop 10 GO terms:")
       term_counts = y_multilabel.sum(axis=0)
       top_indices = np.argsort(term_counts)[-10:]
       for idx in top_indices:
           print(f"  {mlb.classes_[idx]}: {term_counts[idx]} proteins")

   # For single-label tasks
   else:
       y_multilabel = train_df['$TARGET_COLUMN'].values
       mlb = None
   ```

   **Cell 7: Train Multi-Label Classifier**
   ```python
   # Cross-validation for multi-label classification
   N_FOLDS = 5
   kfold = StratifiedKFold(n_splits=N_FOLDS, shuffle=True, random_state=42)

   fold_scores = []
   models = []

   # Use first GO term for stratification
   stratify_labels = y_multilabel[:, 0] if len(y_multilabel.shape) > 1 else y_multilabel

   for fold, (train_idx, val_idx) in enumerate(kfold.split(X_combined, stratify_labels)):
       print(f"\n{'='*60}")
       print(f"Fold {fold + 1}/{N_FOLDS}")
       print(f"{'='*60}")

       X_train, X_val = X_combined[train_idx], X_combined[val_idx]
       y_train, y_val = y_multilabel[train_idx], y_multilabel[val_idx]

       # Scale features
       scaler = StandardScaler()
       X_train_scaled = scaler.fit_transform(X_train)
       X_val_scaled = scaler.transform(X_val)

       # Train XGBoost for each label (Binary Relevance)
       if '$TASK_TYPE' == 'protein-function':
           predictions = []

           for label_idx in tqdm(range(y_multilabel.shape[1]), desc="Training classifiers"):
               y_train_label = y_train[:, label_idx]
               y_val_label = y_val[:, label_idx]

               # Skip if label has too few positive examples
               if y_train_label.sum() < 5:
                   predictions.append(np.zeros(len(y_val_label)))
                   continue

               # Train classifier
               clf = xgb.XGBClassifier(
                   n_estimators=100,
                   max_depth=6,
                   learning_rate=0.1,
                   subsample=0.8,
                   colsample_bytree=0.8,
                   random_state=42,
                   tree_method='hist',
                   device='cuda' if torch.cuda.is_available() else 'cpu'
               )

               clf.fit(
                   X_train_scaled, y_train_label,
                   eval_set=[(X_val_scaled, y_val_label)],
                   verbose=False
               )

               # Predict
               y_pred_proba = clf.predict_proba(X_val_scaled)[:, 1]
               predictions.append(y_pred_proba)

           # Combine predictions
           y_pred_proba_all = np.column_stack(predictions)

           # Threshold at 0.5
           y_pred = (y_pred_proba_all > 0.5).astype(int)

       # For single-label tasks
       else:
           clf = xgb.XGBClassifier(
               n_estimators=1000,
               max_depth=8,
               learning_rate=0.01,
               subsample=0.8,
               colsample_bytree=0.8,
               random_state=42
           )
           clf.fit(X_train_scaled, y_train)
           y_pred = clf.predict(X_val_scaled)

       # Evaluate
       if '$TASK_TYPE' == 'protein-function':
           f1_micro = f1_score(y_val, y_pred, average='micro')
           f1_macro = f1_score(y_val, y_pred, average='macro')
           f1_samples = f1_score(y_val, y_pred, average='samples')
           hamming = hamming_loss(y_val, y_pred)

           print(f"\nFold {fold + 1} Results:")
           print(f"  F1 Micro: {f1_micro:.4f}")
           print(f"  F1 Macro: {f1_macro:.4f}")
           print(f"  F1 Samples: {f1_samples:.4f}")
           print(f"  Hamming Loss: {hamming:.4f}")

           fold_scores.append(f1_micro)
       else:
           acc = accuracy_score(y_val, y_pred)
           print(f"Fold {fold + 1} Accuracy: {acc:.4f}")
           fold_scores.append(acc)

       models.append({
           'scaler': scaler,
           'model': clf,
           'fold': fold
       })

   # Cross-validation summary
   print(f"\n{'='*60}")
   print("Cross-Validation Summary")
   print(f"{'='*60}")
   print(f"Mean Score: {np.mean(fold_scores):.4f} ± {np.std(fold_scores):.4f}")
   print(f"Fold Scores: {[f'{score:.4f}' for score in fold_scores]}")
   ```

   **Cell 8: Train Final Model on Full Dataset**
   ```python
   print("\nTraining final model on full dataset...")

   # Scale features
   scaler_final = StandardScaler()
   X_scaled_final = scaler_final.fit_transform(X_combined)

   # Train final model
   if '$TASK_TYPE' == 'protein-function':
       final_models = []

       for label_idx in tqdm(range(y_multilabel.shape[1]), desc="Training final models"):
           y_label = y_multilabel[:, label_idx]

           if y_label.sum() < 5:
               final_models.append(None)
               continue

           clf = xgb.XGBClassifier(
               n_estimators=100,
               max_depth=6,
               learning_rate=0.1,
               subsample=0.8,
               random_state=42
           )
           clf.fit(X_scaled_final, y_label)
           final_models.append(clf)

       # Save models
       import joblib
       joblib.dump({
           'models': final_models,
           'scaler': scaler_final,
           'mlb': mlb
       }, '../models/protein_function_model.pkl')

   else:
       clf_final = xgb.XGBClassifier(n_estimators=1000, max_depth=8, learning_rate=0.01)
       clf_final.fit(X_scaled_final, y_multilabel)

       import joblib
       joblib.dump({
           'model': clf_final,
           'scaler': scaler_final
       }, '../models/bio_model.pkl')

   print("✓ Final model saved")
   ```

   **Cell 9: Generate Test Predictions**
   ```python
   # Load test data
   test_df = pd.read_csv('../data/test.csv')

   print(f"\nProcessing {len(test_df)} test sequences...")

   # Extract embeddings and features
   test_embeddings = []
   test_seq_features = []

   for idx, row in tqdm(test_df.iterrows(), total=len(test_df)):
       sequence = row['sequence']

       # ESM-2 embedding
       embedding = get_protein_embedding(
           sequence, model, alphabet, batch_converter, device
       )
       test_embeddings.append(embedding)

       # Traditional features
       seq_features = extract_sequence_features(sequence)
       test_seq_features.append(seq_features)

   # Combine features
   X_test_esm = np.array(test_embeddings)
   X_test_traditional = pd.DataFrame(test_seq_features).values
   X_test_combined = np.hstack([X_test_esm, X_test_traditional])

   # Scale
   X_test_scaled = scaler_final.transform(X_test_combined)

   # Predict
   if '$TASK_TYPE' == 'protein-function':
       predictions = []

       for label_idx, clf in enumerate(tqdm(final_models, desc="Predicting")):
           if clf is None:
               predictions.append(np.zeros(len(test_df)))
           else:
               y_pred_proba = clf.predict_proba(X_test_scaled)[:, 1]
               predictions.append(y_pred_proba)

       y_pred_proba_all = np.column_stack(predictions)
       y_pred = (y_pred_proba_all > 0.5).astype(int)

       # Convert back to GO terms
       predicted_go_terms = mlb.inverse_transform(y_pred)

       # Format for submission
       submission = pd.DataFrame({
           'id': test_df['id'],
           '$TARGET_COLUMN': [';'.join(terms) if terms else '' for terms in predicted_go_terms]
       })

   else:
       y_pred = clf_final.predict(X_test_scaled)
       submission = pd.DataFrame({
           'id': test_df['id'],
           '$TARGET_COLUMN': y_pred
       })

   # Save submission
   submission_path = f'../submissions/bio_predictions_cv{np.mean(fold_scores):.4f}.csv'
   submission.to_csv(submission_path, index=False)

   print(f"\n✓ Submission saved: {submission_path}")
   print(f"Predictions: {len(submission)}")
   print(submission.head(10))
   ```

4. **Launch Jupyter Lab**:
   ```bash
   cd ~/kaggle-competitions/$COMPETITION_NAME
   jupyter lab notebooks/03-bio-train-$TASK_TYPE.ipynb
   ```

## Output

- ✓ Bioinformatics training notebook created
- ✓ ESM-2 protein language model loaded
- ✓ Protein embeddings extracted (650-dim vectors)
- ✓ Traditional sequence features computed
- ✓ Multi-label classification for protein function
- ✓ Cross-validation with ensemble
- ✓ Test predictions generated
- ✓ Submission file saved
- Path to training notebook and submission
