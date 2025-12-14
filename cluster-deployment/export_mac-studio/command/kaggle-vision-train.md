# Kaggle Computer Vision Training Command

Train vision models for image competitions with modern architectures.

## Arguments

- `competition-name`: The Kaggle competition identifier
- `task-type`: Type of vision task (classification, segmentation, regression)
- `target-column` (optional): Name of target variable if applicable

## Task

1. **Navigate to competition directory**:
   ```bash
   cd ~/kaggle-competitions/$COMPETITION_NAME
   ```

2. **Detect task type and create training notebook**:

   Create `notebooks/03-vision-train-$TASK_TYPE.ipynb` with:

   **Cell 1: Setup and Imports**
   ```python
   import torch
   import torch.nn as nn
   import torch.optim as optim
   from torch.utils.data import Dataset, DataLoader
   import torchvision.transforms as transforms
   from torchvision import models

   import timm  # PyTorch Image Models
   import albumentations as A
   from albumentations.pytorch import ToTensorV2

   import cv2
   import numpy as np
   import pandas as pd
   from pathlib import Path
   from sklearn.model_selection import StratifiedKFold, KFold
   from tqdm import tqdm
   import matplotlib.pyplot as plt
   import seaborn as sns

   # Check for GPU
   device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
   print(f"Using device: {device}")

   # Set random seeds for reproducibility
   torch.manual_seed(42)
   np.random.seed(42)
   ```

   **Cell 2: Task-Specific Model Architecture**

   **For Classification**:
   ```python
   # Load pre-trained model
   model_name = 'efficientnet_b4'  # or 'resnet50d', 'vit_base_patch16_224'
   num_classes = len(train['$TARGET_COLUMN'].unique())

   model = timm.create_model(
       model_name,
       pretrained=True,
       num_classes=num_classes
   )

   model = model.to(device)
   print(f"Model: {model_name}, Parameters: {sum(p.numel() for p in model.parameters()):,}")
   ```

   **For Regression (e.g., Image2Biomass)**:
   ```python
   # Regression model - single output
   model_name = 'efficientnet_b4'

   model = timm.create_model(
       model_name,
       pretrained=True,
       num_classes=1  # Single continuous value
   )

   model = model.to(device)
   criterion = nn.MSELoss()  # Mean Squared Error for regression
   ```

   **For Segmentation (e.g., Forgery Detection)**:
   ```python
   import segmentation_models_pytorch as smp

   # U-Net with EfficientNet encoder
   model = smp.Unet(
       encoder_name="efficientnet-b5",
       encoder_weights="imagenet",
       in_channels=3,
       classes=2,  # Forged vs authentic
       activation=None  # Use raw logits with BCEWithLogitsLoss
   )

   # Or DeepLabV3+ for better boundary detection
   # model = smp.DeepLabV3Plus(
   #     encoder_name="resnet101",
   #     encoder_weights="imagenet",
   #     classes=2
   # )

   model = model.to(device)
   criterion = smp.losses.DiceLoss(mode='binary')
   ```

   **Cell 3: Data Augmentation**
   ```python
   # Training augmentations
   train_transforms = A.Compose([
       A.Resize(224, 224),
       A.HorizontalFlip(p=0.5),
       A.VerticalFlip(p=0.5),
       A.RandomRotate90(p=0.5),
       A.ShiftScaleRotate(shift_limit=0.1, scale_limit=0.15, rotate_limit=45, p=0.5),
       A.OneOf([
           A.GaussNoise(var_limit=(10.0, 50.0)),
           A.GaussianBlur(),
           A.MotionBlur(),
       ], p=0.3),
       A.OneOf([
           A.OpticalDistortion(),
           A.GridDistortion(),
           A.ElasticTransform(),
       ], p=0.3),
       A.CLAHE(p=0.3),
       A.RandomBrightnessContrast(p=0.3),
       A.RandomGamma(p=0.3),
       A.Normalize(
           mean=[0.485, 0.456, 0.406],
           std=[0.229, 0.224, 0.225]
       ),
       ToTensorV2()
   ])

   # Validation augmentations (no randomness)
   val_transforms = A.Compose([
       A.Resize(224, 224),
       A.Normalize(
           mean=[0.485, 0.456, 0.406],
           std=[0.229, 0.224, 0.225]
       ),
       ToTensorV2()
   ])
   ```

   **Cell 4: Custom Dataset**
   ```python
   class ImageDataset(Dataset):
       def __init__(self, df, image_dir, transforms=None, task_type='classification'):
           self.df = df.reset_index(drop=True)
           self.image_dir = Path(image_dir)
           self.transforms = transforms
           self.task_type = task_type

       def __len__(self):
           return len(self.df)

       def __getitem__(self, idx):
           row = self.df.iloc[idx]

           # Load image
           img_path = self.image_dir / row['image_path']
           image = cv2.imread(str(img_path))
           image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

           # Get target
           if self.task_type == 'classification':
               target = row['$TARGET_COLUMN']
           elif self.task_type == 'regression':
               target = float(row['$TARGET_COLUMN'])
           elif self.task_type == 'segmentation':
               # Load mask
               mask_path = self.image_dir / row['mask_path']
               target = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)

           # Apply augmentations
           if self.transforms:
               if self.task_type == 'segmentation':
                   augmented = self.transforms(image=image, mask=target)
                   image = augmented['image']
                   target = augmented['mask']
               else:
                   augmented = self.transforms(image=image)
                   image = augmented['image']

           return image, target
   ```

   **Cell 5: Training Loop**
   ```python
   def train_epoch(model, loader, criterion, optimizer, device, task_type='classification'):
       model.train()
       running_loss = 0.0
       correct = 0
       total = 0

       pbar = tqdm(loader, desc='Training')
       for images, targets in pbar:
           images = images.to(device)
           targets = targets.to(device)

           if task_type == 'regression':
               targets = targets.float().unsqueeze(1)

           optimizer.zero_grad()
           outputs = model(images)
           loss = criterion(outputs, targets)
           loss.backward()
           optimizer.step()

           running_loss += loss.item()

           if task_type == 'classification':
               _, predicted = torch.max(outputs.data, 1)
               total += targets.size(0)
               correct += (predicted == targets).sum().item()

           pbar.set_postfix({'loss': running_loss / (pbar.n + 1)})

       epoch_loss = running_loss / len(loader)
       epoch_acc = 100 * correct / total if task_type == 'classification' else None

       return epoch_loss, epoch_acc

   def validate_epoch(model, loader, criterion, device, task_type='classification'):
       model.eval()
       running_loss = 0.0
       correct = 0
       total = 0

       with torch.no_grad():
           for images, targets in tqdm(loader, desc='Validation'):
               images = images.to(device)
               targets = targets.to(device)

               if task_type == 'regression':
                   targets = targets.float().unsqueeze(1)

               outputs = model(images)
               loss = criterion(outputs, targets)

               running_loss += loss.item()

               if task_type == 'classification':
                   _, predicted = torch.max(outputs.data, 1)
                   total += targets.size(0)
                   correct += (predicted == targets).sum().item()

       epoch_loss = running_loss / len(loader)
       epoch_acc = 100 * correct / total if task_type == 'classification' else None

       return epoch_loss, epoch_acc
   ```

   **Cell 6: Cross-Validation Training**
   ```python
   # Configuration
   N_FOLDS = 5
   EPOCHS = 30
   BATCH_SIZE = 32
   LEARNING_RATE = 1e-4

   # Prepare data
   train_df = pd.read_csv('../data/train.csv')

   # K-Fold cross-validation
   if '$TARGET_COLUMN' in train_df.columns and task_type == 'classification':
       kfold = StratifiedKFold(n_splits=N_FOLDS, shuffle=True, random_state=42)
       splits = kfold.split(train_df, train_df['$TARGET_COLUMN'])
   else:
       kfold = KFold(n_splits=N_FOLDS, shuffle=True, random_state=42)
       splits = kfold.split(train_df)

   fold_scores = []

   for fold, (train_idx, val_idx) in enumerate(splits):
       print(f"\n{'='*50}")
       print(f"Fold {fold + 1}/{N_FOLDS}")
       print(f"{'='*50}")

       # Split data
       train_fold = train_df.iloc[train_idx]
       val_fold = train_df.iloc[val_idx]

       # Create datasets
       train_dataset = ImageDataset(
           train_fold,
           '../data/train_images',
           transforms=train_transforms,
           task_type='$TASK_TYPE'
       )
       val_dataset = ImageDataset(
           val_fold,
           '../data/train_images',
           transforms=val_transforms,
           task_type='$TASK_TYPE'
       )

       # Create dataloaders
       train_loader = DataLoader(
           train_dataset,
           batch_size=BATCH_SIZE,
           shuffle=True,
           num_workers=4,
           pin_memory=True
       )
       val_loader = DataLoader(
           val_dataset,
           batch_size=BATCH_SIZE,
           shuffle=False,
           num_workers=4,
           pin_memory=True
       )

       # Initialize model
       model = timm.create_model(model_name, pretrained=True, num_classes=num_classes)
       model = model.to(device)

       # Optimizer and scheduler
       optimizer = optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=1e-5)
       scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS)

       # Training loop
       best_val_loss = float('inf')

       for epoch in range(EPOCHS):
           print(f"\nEpoch {epoch + 1}/{EPOCHS}")

           train_loss, train_acc = train_epoch(
               model, train_loader, criterion, optimizer, device, task_type='$TASK_TYPE'
           )
           val_loss, val_acc = validate_epoch(
               model, val_loader, criterion, device, task_type='$TASK_TYPE'
           )

           scheduler.step()

           print(f"Train Loss: {train_loss:.4f}")
           if train_acc:
               print(f"Train Acc: {train_acc:.2f}%")
           print(f"Val Loss: {val_loss:.4f}")
           if val_acc:
               print(f"Val Acc: {val_acc:.2f}%")

           # Save best model
           if val_loss < best_val_loss:
               best_val_loss = val_loss
               torch.save(model.state_dict(), f'../models/vision_model_fold{fold}.pth')
               print(f"✓ Saved best model (val_loss: {val_loss:.4f})")

       fold_scores.append(best_val_loss)
       print(f"\nFold {fold + 1} Best Val Loss: {best_val_loss:.4f}")

   # Cross-validation summary
   print(f"\n{'='*50}")
   print("Cross-Validation Results")
   print(f"{'='*50}")
   print(f"Mean CV Loss: {np.mean(fold_scores):.4f}")
   print(f"Std CV Loss: {np.std(fold_scores):.4f}")
   print(f"Fold Scores: {[f'{score:.4f}' for score in fold_scores]}")
   ```

   **Cell 7: Test Predictions**
   ```python
   # Load test data
   test_df = pd.read_csv('../data/test.csv')
   test_dataset = ImageDataset(
       test_df,
       '../data/test_images',
       transforms=val_transforms,
       task_type='$TASK_TYPE'
   )
   test_loader = DataLoader(
       test_dataset,
       batch_size=BATCH_SIZE,
       shuffle=False,
       num_workers=4
   )

   # Ensemble predictions from all folds
   all_predictions = []

   for fold in range(N_FOLDS):
       print(f"Predicting with fold {fold + 1} model...")

       model = timm.create_model(model_name, pretrained=False, num_classes=num_classes)
       model.load_state_dict(torch.load(f'../models/vision_model_fold{fold}.pth'))
       model = model.to(device)
       model.eval()

       fold_predictions = []

       with torch.no_grad():
           for images, _ in tqdm(test_loader):
               images = images.to(device)
               outputs = model(images)

               if task_type == 'classification':
                   probs = torch.softmax(outputs, dim=1)
                   fold_predictions.append(probs.cpu().numpy())
               elif task_type == 'regression':
                   fold_predictions.append(outputs.cpu().numpy())
               elif task_type == 'segmentation':
                   probs = torch.sigmoid(outputs)
                   fold_predictions.append(probs.cpu().numpy())

       all_predictions.append(np.concatenate(fold_predictions))

   # Average predictions across folds
   final_predictions = np.mean(all_predictions, axis=0)

   if task_type == 'classification':
       final_predictions = np.argmax(final_predictions, axis=1)
   elif task_type == 'regression':
       final_predictions = final_predictions.flatten()

   # Create submission
   submission = pd.DataFrame({
       'id': test_df['id'],
       '$TARGET_COLUMN': final_predictions
   })

   submission_path = f'../submissions/vision_{model_name}_cv{np.mean(fold_scores):.4f}.csv'
   submission.to_csv(submission_path, index=False)
   print(f"\n✓ Submission saved to: {submission_path}")
   print(submission.head(10))
   ```

   **Cell 8: Test-Time Augmentation (TTA)**
   ```python
   # Optional: Improve predictions with Test-Time Augmentation
   def predict_with_tta(model, image, transforms_list, device):
       model.eval()
       predictions = []

       with torch.no_grad():
           for transform in transforms_list:
               augmented = transform(image=image)
               img_tensor = augmented['image'].unsqueeze(0).to(device)
               output = model(img_tensor)
               predictions.append(output.cpu().numpy())

       return np.mean(predictions, axis=0)

   # TTA transforms (horizontal flip, vertical flip, rotations)
   tta_transforms = [
       val_transforms,
       A.Compose([A.HorizontalFlip(p=1.0), *val_transforms.transforms]),
       A.Compose([A.VerticalFlip(p=1.0), *val_transforms.transforms]),
       A.Compose([A.RandomRotate90(p=1.0), *val_transforms.transforms]),
   ]

   # Run TTA predictions (slower but more accurate)
   # final_predictions_tta = predict_with_tta(...)
   ```

3. **Launch Jupyter Lab**:
   ```bash
   cd ~/kaggle-competitions/$COMPETITION_NAME
   jupyter lab notebooks/03-vision-train-$TASK_TYPE.ipynb
   ```

## Output

- ✓ Vision training notebook created with task-specific architecture
- ✓ Pre-trained model loaded (EfficientNet, ResNet, ViT, or U-Net)
- ✓ Data augmentation pipeline configured
- ✓ Cross-validation training with fold ensembling
- ✓ Test predictions generated
- ✓ Submission file saved to submissions/ directory
- Path to training notebook and submission file
