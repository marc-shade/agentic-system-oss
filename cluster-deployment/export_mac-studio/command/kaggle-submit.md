# Kaggle Submit Command

Submit predictions to Kaggle competition and track results.

## Arguments

- `competition-name`: The Kaggle competition identifier
- `submission-file`: Path to submission CSV file (relative to competition dir)
- `message`: Submission description/message

## Task

1. Navigate to competition directory:
   ```bash
   cd ~/kaggle-competitions/$COMPETITION_NAME
   ```

2. Validate submission file format:
   ```python
   import pandas as pd

   submission = pd.read_csv('$SUBMISSION_FILE')
   print(f"Submission shape: {submission.shape}")
   print(f"Columns: {submission.columns.tolist()}")
   print(f"Sample rows:\n{submission.head()}")

   # Check for missing values
   if submission.isnull().any().any():
       print("WARNING: Submission contains missing values!")
       print(submission.isnull().sum())
   ```

3. Submit to Kaggle:
   ```bash
   kaggle competitions submit -c $COMPETITION_NAME \
       -f $SUBMISSION_FILE \
       -m "$MESSAGE"
   ```

4. Get recent submissions and scores:
   ```bash
   kaggle competitions submissions -c $COMPETITION_NAME
   ```

5. Update competition README with results:
   ```python
   import datetime

   # Append to README.md
   with open('README.md', 'a') as f:
       f.write(f"\n### Submission - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
       f.write(f"- Model: {Path('$SUBMISSION_FILE').stem}\n")
       f.write(f"- Message: $MESSAGE\n")
       f.write(f"- Score: [Check leaderboard]\n")
       f.write(f"- File: $SUBMISSION_FILE\n\n")
   ```

6. Display leaderboard position:
   ```bash
   # Wait a few seconds for score to update
   sleep 5
   kaggle competitions submissions -c $COMPETITION_NAME | head -n 5
   ```

## Output

- Submission confirmation
- Current leaderboard position
- Updated README with submission details
- Recommendations for next iteration
