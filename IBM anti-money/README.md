# IBM Anti-Money Laundering Dataset Directory

This directory contains the IBM synthetic financial transaction AML datasets (Large, Medium, and Small scales across High/Low Illicit ratios).

## Tracked Files in GitHub
- `HI-Small_accounts.csv` (32.48 MB)
- `HI-Small_Patterns.txt` (0.31 MB)
- `HI-Medium_Patterns.txt` (2.17 MB)
- `HI-Large_Patterns.txt` (13.17 MB)
- `LI-Small_accounts.csv` (45.06 MB)
- `LI-Small_Patterns.txt` (0.09 MB)
- `LI-Medium_Patterns.txt` (0.37 MB)
- `LI-Large_Patterns.txt` (1.85 MB)

## Raw Transaction Files Exceeding GitHub's 100MB Limit
Due to GitHub's strict 100MB per-file upload limit, the raw multi-gigabyte transaction CSV files are excluded from Git:
- `HI-Large_Trans.csv` (16.26 GB)
- `LI-Large_Trans.csv` (15.96 GB)
- `HI-Medium_Trans.csv` (2.89 GB)
- `LI-Medium_Trans.csv` (2.83 GB)
- `LI-Small_Trans.csv` (620 MB)
- `HI-Small_Trans.csv` (453 MB)
- `HI-Large_accounts.csv` (140 MB)
- `HI-Medium_accounts.csv` (138 MB)
- `LI-Large_accounts.csv` (137 MB)
- `LI-Medium_accounts.csv` (135 MB)

To run the offline high-volume pipeline locally, place the full IBM AML transaction CSVs in this folder.
