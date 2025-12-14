# Kaggle Leaderboard Command

Check competition leaderboard and submission status.

## Arguments

- `competition-name`: The Kaggle competition identifier

## Task

1. Get competition overview:
   ```bash
   kaggle competitions list | grep -i "$COMPETITION_NAME"
   ```

2. Show leaderboard (top 10):
   ```bash
   kaggle competitions leaderboard -c $COMPETITION_NAME --show | head -n 15
   ```

3. Show your submissions and scores:
   ```bash
   kaggle competitions submissions -c $COMPETITION_NAME
   ```

4. Analyze submission progress:
   ```python
   import pandas as pd
   import subprocess

   # Get submissions
   result = subprocess.run(
       ['kaggle', 'competitions', 'submissions', '-c', '$COMPETITION_NAME'],
       capture_output=True,
       text=True
   )

   # Parse and display
   lines = result.stdout.strip().split('\n')
   if len(lines) > 1:
       print("Your Submission History:")
       print("=" * 80)
       for line in lines[:10]:  # Last 10 submissions
           print(line)

       # Extract scores and show improvement
       print("\n" + "=" * 80)
       print("Score Progression:")
       # Parse scores and show trend
   ```

5. Calculate metrics:
   - Total submissions made
   - Best score achieved
   - Latest score vs best score
   - Estimated leaderboard position

## Output

- Competition status
- Top leaderboard entries
- Your submission history
- Performance analysis
- Suggestions for improvement
