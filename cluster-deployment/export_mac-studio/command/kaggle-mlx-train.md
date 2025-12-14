# Kaggle MLX Train Command

Train deep learning models using MLX for Apple Silicon acceleration.

## Arguments

- `competition-name`: The Kaggle competition identifier
- `model-type`: Model architecture (mlp, cnn, transformer, custom)
- `target-column`: Name of target variable

## Task

Use MLX for GPU-accelerated training on Apple Silicon. This command leverages the agentic system's MLX configuration for optimal performance.

1. Navigate to competition directory:
   ```bash
   cd ~/kaggle-competitions/$COMPETITION_NAME
   ```

2. Create MLX training script at `scripts/train_mlx.py`:

   ```python
   #!/usr/bin/env python3
   """MLX-accelerated training for Kaggle competition."""
   
   import sys
   sys.path.insert(0, '/Volumes/SSDRAID0/agentic-system')
   
   from mlx_config import get_kaggle_utils, get_mlx_config
   import mlx.core as mx
   import mlx.nn as nn
   import pandas as pd
   import numpy as np
   from pathlib import Path
   
   # Load competition data
   train_df = pd.read_csv('../data/train.csv')
   test_df = pd.read_csv('../data/test.csv')
   
   # Prepare features and target
   target_col = '$TARGET_COLUMN'
   feature_cols = [c for c in train_df.columns if c != target_col]
   
   X = train_df[feature_cols].values
   y = train_df[target_col].values.reshape(-1, 1)
   X_test = test_df[feature_cols].values
   
   print(f"Training data: {X.shape}")
   print(f"Test data: {X_test.shape}")
   
   # Get MLX utilities
   config = get_mlx_config()
   utils = get_kaggle_utils()
   
   # Preprocess data with MLX
   X_mlx = utils.preprocess_dataset(X, normalize=True)
   y_mlx = utils.preprocess_dataset(y, normalize=False)
   X_test_mlx = utils.preprocess_dataset(X_test, normalize=True)
   
   # Split train/validation
   X_train, X_val, y_train, y_val = utils.train_test_split(
       X_mlx, y_mlx,
       test_size=0.2,
       random_state=42
   )
   
   print(f"\nTrain set: {X_train.shape}")
   print(f"Validation set: {X_val.shape}")
   
   # Create model architecture based on type
   if '$MODEL_TYPE' == 'mlp':
       # Multi-layer perceptron
       model = utils.create_model(
           input_dim=X_train.shape[1],
           hidden_dims=[256, 128, 64],
           output_dim=y_train.shape[1],
           activation='relu'
       )
   
   elif '$MODEL_TYPE' == 'deep-mlp':
       # Deep MLP for complex patterns
       model = utils.create_model(
           input_dim=X_train.shape[1],
           hidden_dims=[512, 256, 128, 64, 32],
           output_dim=y_train.shape[1],
           activation='gelu'
       )
   
   elif '$MODEL_TYPE' == 'custom':
       # Custom architecture (modify as needed)
       class CustomModel(nn.Module):
           def __init__(self, input_dim, output_dim):
               super().__init__()
               self.layers = [
                   nn.Linear(input_dim, 256),
                   nn.ReLU(),
                   nn.Dropout(0.2),
                   nn.Linear(256, 128),
                   nn.ReLU(),
                   nn.Dropout(0.2),
                   nn.Linear(128, output_dim)
               ]
           
           def __call__(self, x):
               for layer in self.layers:
                   x = layer(x)
               return x
       
       model = CustomModel(X_train.shape[1], y_train.shape[1])
   
   print(f"\nModel architecture: $MODEL_TYPE")
   
   # Train with MLX GPU acceleration
   history = utils.train_model(
       model,
       X_train,
       y_train,
       epochs=100,
       batch_size=64,
       learning_rate=0.001,
       verbose=True
   )
   
   # Evaluate on validation set
   val_pred = model(X_val)
   val_loss = mx.mean((val_pred - y_val) ** 2)
   print(f"\nValidation Loss: {val_loss.item():.6f}")
   
   # Generate test predictions
   test_pred = model(X_test_mlx)
   test_pred_np = config.to_numpy(test_pred)
   
   print(f"\nTest predictions shape: {test_pred_np.shape}")
   
   # Save model
   model_dir = Path('../models')
   model_dir.mkdir(exist_ok=True)
   model_path = model_dir / f'mlx_${MODEL_TYPE}_val{val_loss.item():.4f}.npz'
   config.save_model(model, model_path)
   print(f"Model saved: {model_path}")
   
   # Create submission
   submission_dir = Path('../submissions')
   submission_dir.mkdir(exist_ok=True)
   
   submission_df = pd.DataFrame({
       'id': test_df.index,  # Adjust based on competition
       'prediction': test_pred_np.flatten()
   })
   
   submission_path = submission_dir / f'mlx_${MODEL_TYPE}_val{val_loss.item():.4f}.csv'
   submission_df.to_csv(submission_path, index=False)
   print(f"Submission saved: {submission_path}")
   
   # Plot training history
   import matplotlib.pyplot as plt
   plt.figure(figsize=(10, 6))
   plt.plot(history['loss'])
   plt.title('MLX Training Loss')
   plt.xlabel('Epoch')
   plt.ylabel('Loss')
   plt.grid(True)
   plt.savefig(model_dir / f'training_history_${MODEL_TYPE}.png')
   print(f"Training plot saved: {model_dir}/training_history_${MODEL_TYPE}.png")
   ```

3. Execute MLX training:
   ```bash
   python3 scripts/train_mlx.py
   ```

## Performance Benefits

- **Metal GPU Acceleration**: 5-10x faster than CPU on Apple Silicon
- **Unified Memory**: No CPU-GPU data transfer overhead
- **Energy Efficient**: Lower power consumption than external GPUs
- **Native Integration**: Optimized for M2 Max architecture

## Output

- Training progress with loss metrics
- Validation loss
- Saved model in NPZ format
- Submission CSV file
- Training history plot
