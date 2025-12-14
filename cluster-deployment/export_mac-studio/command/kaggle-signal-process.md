# Kaggle Signal Processing Command

Process and digitize signal data (ECG, audio, sensor data) for competitions.

## Arguments

- `competition-name`: The Kaggle competition identifier
- `signal-type` (optional): Type of signal (ecg, audio, sensor, timeseries)

## Task

1. **Navigate to competition directory**:
   ```bash
   cd ~/kaggle-competitions/$COMPETITION_NAME
   ```

2. **Install signal processing libraries**:
   ```bash
   pip install scipy neurokit2 pytesseract easyocr opencv-python pdf2image
   pip install librosa soundfile  # For audio
   pip install wfdb heartpy  # For ECG/medical signals
   ```

3. **Create signal processing notebook**:

   Create `notebooks/03-signal-processing.ipynb` with:

   **Cell 1: Setup and Imports**
   ```python
   import cv2
   import numpy as np
   import pandas as pd
   from scipy import signal, ndimage
   from scipy.signal import find_peaks, butter, filtfilt, savgol_filter
   from pathlib import Path
   import matplotlib.pyplot as plt
   import seaborn as sns
   from tqdm import tqdm

   # ECG-specific
   import neurokit2 as nk

   # OCR for extracting labels
   import pytesseract
   import easyocr

   # Audio processing
   import librosa
   import soundfile as sf

   # Set visualization style
   sns.set_style('whitegrid')
   plt.rcParams['figure.figsize'] = (15, 8)
   ```

   **Cell 2: Image Preprocessing (for Scanned Signals like ECG)**
   ```python
   def preprocess_signal_image(img_path):
       """
       Preprocess scanned ECG/signal image for extraction
       """
       # Load image
       img = cv2.imread(str(img_path))
       gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

       # Deskew if needed
       coords = np.column_stack(np.where(gray > 0))
       angle = cv2.minAreaRect(coords)[-1]
       if angle < -45:
           angle = -(90 + angle)
       else:
           angle = -angle

       if abs(angle) > 0.5:  # Deskew if tilted
           (h, w) = gray.shape[:2]
           center = (w // 2, h // 2)
           M = cv2.getRotationMatrix2D(center, angle, 1.0)
           gray = cv2.warpAffine(
               gray, M, (w, h),
               flags=cv2.INTER_CUBIC,
               borderMode=cv2.BORDER_REPLICATE
           )

       # Denoise
       denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)

       # Enhance contrast
       clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
       enhanced = clahe.apply(denoised)

       return enhanced

   # Test preprocessing
   test_img_path = Path("../data/train_images/sample_ecg.png")
   if test_img_path.exists():
       processed = preprocess_signal_image(test_img_path)

       plt.figure(figsize=(15, 5))
       plt.subplot(1, 2, 1)
       plt.imshow(cv2.imread(str(test_img_path)))
       plt.title("Original")
       plt.axis('off')

       plt.subplot(1, 2, 2)
       plt.imshow(processed, cmap='gray')
       plt.title("Preprocessed")
       plt.axis('off')
       plt.show()
   ```

   **Cell 3: Grid Detection and Removal**
   ```python
   def remove_grid(img):
       """
       Remove grid lines from ECG/signal images
       """
       # Detect horizontal lines
       horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
       detect_horizontal = cv2.morphologyEx(img, cv2.MORPH_OPEN, horizontal_kernel, iterations=2)
       cnts = cv2.findContours(detect_horizontal, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
       cnts = cnts[0] if len(cnts) == 2 else cnts[1]
       for c in cnts:
           cv2.drawContours(img, [c], -1, (255,255,255), 2)

       # Detect vertical lines
       vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
       detect_vertical = cv2.morphologyEx(img, cv2.MORPH_OPEN, vertical_kernel, iterations=2)
       cnts = cv2.findContours(detect_vertical, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
       cnts = cnts[0] if len(cnts) == 2 else cnts[1]
       for c in cnts:
           cv2.drawContours(img, [c], -1, (255,255,255), 2)

       return img

   # Test grid removal
   if test_img_path.exists():
       processed = preprocess_signal_image(test_img_path)
       no_grid = remove_grid(processed.copy())

       plt.figure(figsize=(15, 5))
       plt.subplot(1, 2, 1)
       plt.imshow(processed, cmap='gray')
       plt.title("With Grid")
       plt.axis('off')

       plt.subplot(1, 2, 2)
       plt.imshow(no_grid, cmap='gray')
       plt.title("Grid Removed")
       plt.axis('off')
       plt.show()
   ```

   **Cell 4: Signal Trace Extraction**
   ```python
   def extract_signal_trace(binary_img):
       """
       Extract signal trace from binary image
       Returns array of y-coordinates for each x-position
       """
       signal_points = []

       for x in range(binary_img.shape[1]):
           col = binary_img[:, x]

           # Find darkest pixels (signal trace)
           y_coords = np.where(col < 128)[0]

           if len(y_coords) > 0:
               # Use median to handle thick lines
               y_median = np.median(y_coords)
               signal_points.append(y_median)
           else:
               # Interpolate missing points
               if len(signal_points) > 0:
                   signal_points.append(signal_points[-1])
               else:
                   signal_points.append(0)

       return np.array(signal_points)

   def extract_multiple_leads(img, num_leads=12):
       """
       Extract multiple ECG leads from single image
       """
       height = img.shape[0]
       lead_height = height // num_leads

       leads = []
       for i in range(num_leads):
           # Extract region for this lead
           y_start = i * lead_height
           y_end = (i + 1) * lead_height
           lead_img = img[y_start:y_end, :]

           # Extract signal
           lead_signal = extract_signal_trace(lead_img)
           leads.append(lead_signal)

       return leads

   # Test signal extraction
   if test_img_path.exists():
       processed = preprocess_signal_image(test_img_path)
       no_grid = remove_grid(processed.copy())

       # Threshold to binary
       _, binary = cv2.threshold(no_grid, 127, 255, cv2.THRESH_BINARY)

       # Extract signal
       extracted_signal = extract_signal_trace(binary)

       plt.figure(figsize=(15, 5))
       plt.subplot(2, 1, 1)
       plt.imshow(binary, cmap='gray')
       plt.title("Binary Image")
       plt.axis('off')

       plt.subplot(2, 1, 2)
       plt.plot(extracted_signal)
       plt.title("Extracted Signal")
       plt.xlabel("Pixel X")
       plt.ylabel("Pixel Y")
       plt.grid(True, alpha=0.3)
       plt.show()
   ```

   **Cell 5: OCR for Scale Extraction**
   ```python
   def extract_scale_info(img):
       """
       Extract scale information using OCR
       """
       # Initialize EasyOCR reader
       reader = easyocr.Reader(['en'])

       # OCR on image
       results = reader.readtext(img)

       scale_info = {
           'time_scale': None,  # e.g., 25 mm/s
           'voltage_scale': None,  # e.g., 10 mm/mV
       }

       for (bbox, text, prob) in results:
           text_lower = text.lower()

           # Look for time scale
           if 'mm/s' in text_lower:
               try:
                   value = float(''.join(filter(str.isdigit, text)))
                   scale_info['time_scale'] = value
               except:
                   pass

           # Look for voltage scale
           if 'mm/mv' in text_lower or 'mm/v' in text_lower:
               try:
                   value = float(''.join(filter(str.isdigit, text)))
                   scale_info['voltage_scale'] = value
               except:
                   pass

       return scale_info

   # Test OCR
   if test_img_path.exists():
       img = cv2.imread(str(test_img_path))
       scale_info = extract_scale_info(img)
       print(f"Scale information: {scale_info}")
   ```

   **Cell 6: Scale to Physical Units**
   ```python
   def pixels_to_physical_units(signal_pixels, scale_info, img_shape):
       """
       Convert pixel coordinates to physical units (mV, seconds)
       """
       height, width = img_shape

       # Convert Y (voltage)
       if scale_info['voltage_scale']:
           # Invert Y axis (top = high voltage)
           signal_inverted = height - signal_pixels

           # Normalize
           signal_normalized = signal_inverted / height

           # Scale to mV (assuming standard ECG range)
           signal_mv = (signal_normalized - 0.5) * 6.0  # Typical ±3mV range

       # Generate time axis
       if scale_info['time_scale']:
           # Time per pixel
           time_per_pixel = 1.0 / scale_info['time_scale']
           time_axis = np.arange(len(signal_pixels)) * time_per_pixel
       else:
           # Assume standard sampling rate
           time_axis = np.arange(len(signal_pixels)) / 500.0  # 500 Hz default

       return time_axis, signal_mv

   # Test conversion
   if test_img_path.exists():
       processed = preprocess_signal_image(test_img_path)
       _, binary = cv2.threshold(processed, 127, 255, cv2.THRESH_BINARY)
       signal_pixels = extract_signal_trace(binary)
       scale_info = extract_scale_info(cv2.imread(str(test_img_path)))

       time_axis, signal_mv = pixels_to_physical_units(
           signal_pixels,
           scale_info,
           processed.shape
       )

       plt.figure(figsize=(15, 5))
       plt.plot(time_axis, signal_mv)
       plt.title("ECG Signal in Physical Units")
       plt.xlabel("Time (seconds)")
       plt.ylabel("Voltage (mV)")
       plt.grid(True, alpha=0.3)
       plt.show()
   ```

   **Cell 7: Signal Processing and Feature Extraction**
   ```python
   def process_ecg_signal(signal, sampling_rate=500):
       """
       Process ECG signal and extract features
       """
       # Bandpass filter (0.5-40 Hz for ECG)
       sos = signal.butter(4, [0.5, 40], btype='band', fs=sampling_rate, output='sos')
       filtered = signal.sosfilt(sos, signal)

       # Detect R-peaks
       peaks, _ = find_peaks(filtered, distance=sampling_rate//3, prominence=0.3)

       # Calculate heart rate
       if len(peaks) > 1:
           rr_intervals = np.diff(peaks) / sampling_rate
           heart_rate = 60.0 / np.mean(rr_intervals)
       else:
           heart_rate = None

       # Use NeuroKit2 for comprehensive analysis
       signals_nk, info = nk.ecg_process(filtered, sampling_rate=sampling_rate)

       features = {
           'heart_rate': heart_rate,
           'num_beats': len(peaks),
           'rr_mean': np.mean(rr_intervals) if len(peaks) > 1 else None,
           'rr_std': np.std(rr_intervals) if len(peaks) > 1 else None,
           'signal_quality': nk.ecg_quality(filtered, sampling_rate=sampling_rate)
       }

       return filtered, peaks, features

   # Test processing
   if test_img_path.exists():
       # Get signal
       processed = preprocess_signal_image(test_img_path)
       _, binary = cv2.threshold(processed, 127, 255, cv2.THRESH_BINARY)
       signal_pixels = extract_signal_trace(binary)
       scale_info = extract_scale_info(cv2.imread(str(test_img_path)))
       time_axis, signal_mv = pixels_to_physical_units(signal_pixels, scale_info, processed.shape)

       # Process
       filtered, peaks, features = process_ecg_signal(signal_mv, sampling_rate=500)

       # Visualize
       plt.figure(figsize=(15, 8))

       plt.subplot(2, 1, 1)
       plt.plot(time_axis, signal_mv, alpha=0.7, label='Raw')
       plt.plot(time_axis, filtered, label='Filtered')
       plt.scatter(time_axis[peaks], filtered[peaks], c='red', marker='o', label='R-peaks')
       plt.title("ECG Signal Processing")
       plt.xlabel("Time (s)")
       plt.ylabel("Voltage (mV)")
       plt.legend()
       plt.grid(True, alpha=0.3)

       plt.subplot(2, 1, 2)
       plt.bar(features.keys(), [v if v is not None else 0 for v in features.values()])
       plt.title("Extracted Features")
       plt.xticks(rotation=45)
       plt.tight_layout()
       plt.show()

       print("\nExtracted Features:")
       for key, value in features.items():
           print(f"  {key}: {value}")
   ```

   **Cell 8: Batch Processing**
   ```python
   # Process all images in training set
   train_df = pd.read_csv('../data/train.csv')
   image_dir = Path('../data/train_images')

   results = []

   for idx, row in tqdm(train_df.iterrows(), total=len(train_df)):
       try:
           img_path = image_dir / row['image_filename']

           # Preprocess
           processed = preprocess_signal_image(img_path)
           no_grid = remove_grid(processed.copy())
           _, binary = cv2.threshold(no_grid, 127, 255, cv2.THRESH_BINARY)

           # Extract signal
           signal_pixels = extract_signal_trace(binary)

           # Extract scale
           scale_info = extract_scale_info(cv2.imread(str(img_path)))

           # Convert to physical units
           time_axis, signal_mv = pixels_to_physical_units(
               signal_pixels,
               scale_info,
               processed.shape
           )

           # Process and extract features
           filtered, peaks, features = process_ecg_signal(signal_mv)

           # Save
           result = {
               'id': row['id'],
               'signal_data': filtered.tolist(),
               'time_axis': time_axis.tolist(),
               **features
           }
           results.append(result)

       except Exception as e:
           print(f"Error processing {row['id']}: {e}")
           continue

   # Save results
   results_df = pd.DataFrame(results)
   results_df.to_csv('../data/processed_signals.csv', index=False)
   print(f"\n✓ Processed {len(results_df)} signals")
   print(results_df.head())
   ```

   **Cell 9: Create Submission**
   ```python
   # Load test data
   test_df = pd.read_csv('../data/test.csv')
   test_image_dir = Path('../data/test_images')

   predictions = []

   for idx, row in tqdm(test_df.iterrows(), total=len(test_df)):
       try:
           img_path = test_image_dir / row['image_filename']

           # Full pipeline
           processed = preprocess_signal_image(img_path)
           no_grid = remove_grid(processed.copy())
           _, binary = cv2.threshold(no_grid, 127, 255, cv2.THRESH_BINARY)
           signal_pixels = extract_signal_trace(binary)
           scale_info = extract_scale_info(cv2.imread(str(img_path)))
           time_axis, signal_mv = pixels_to_physical_units(signal_pixels, scale_info, processed.shape)
           filtered, peaks, features = process_ecg_signal(signal_mv)

           # Create prediction based on competition requirements
           prediction = {
               'id': row['id'],
               'heart_rate': features['heart_rate'],
               'signal_quality': features['signal_quality'],
               # Add other required fields
           }
           predictions.append(prediction)

       except Exception as e:
           print(f"Error: {e}")
           # Add default prediction
           predictions.append({
               'id': row['id'],
               'heart_rate': 70.0,  # Default
               'signal_quality': 'unknown'
           })

   # Create submission
   submission_df = pd.DataFrame(predictions)
   submission_df.to_csv('../submissions/signal_processing_predictions.csv', index=False)
   print(f"\n✓ Submission created ({len(submission_df)} samples)")
   print(submission_df.head())
   ```

4. **Launch Jupyter Lab**:
   ```bash
   cd ~/kaggle-competitions/$COMPETITION_NAME
   jupyter lab notebooks/03-signal-processing.ipynb
   ```

## Output

- ✓ Signal processing notebook created
- ✓ Image preprocessing pipeline (deskew, denoise, enhance)
- ✓ Grid detection and removal
- ✓ Signal trace extraction from images
- ✓ OCR for scale information
- ✓ Conversion to physical units (mV, seconds)
- ✓ Signal processing and feature extraction
- ✓ Batch processing for train/test sets
- ✓ Submission file generated
- Path to notebook and submission file
