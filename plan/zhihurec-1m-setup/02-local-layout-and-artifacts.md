# Subproblem 2: Local Layout And Artifacts

## 1. Goal
Create the requested folder layout, and if the official source can be downloaded automatically, save the dataset files, verification report, and inspection script.

## 2. Why this step exists
The user wants a predictable local structure under the current workspace, a reproducible verification report, and a script that explains table fields and key relationships.

## 3. Files involved
- `data/zhihurec_1m/raw` - target folder for the dataset files.
- `data/zhihurec_1m/meta` - target folder for verification output.
- `scripts` - target folder for the helper script.
- `data/zhihurec_1m/meta/check.txt` - stores file completeness, non-empty checks, sample rows, and line counts.
- `scripts/inspect_zhihurec.py` - reads the eight files and prints field meanings plus key-link checks.

## 4. Exact changes
- Create the three requested directories if they do not already exist.
- If automatic download is allowed, fetch only the official 1M-related files into `data/zhihurec_1m/raw`.
- If the official source only provides the base eight files and README instructs users to derive the 1M split from top lines, record that generation rule instead of downloading 100M blindly.
- For each downloaded CSV, check that the file exists and is non-empty, print the first three lines, count total lines, and save the results into `data/zhihurec_1m/meta/check.txt`.
- Create `scripts/inspect_zhihurec.py` to load the eight files, print field descriptions based on the README, sample key relationships, and summarize which tables can join to which tables.

## 5. Out of scope
- Downloading the 100M dataset by default.
- Downloading unrelated papers, code, or alternative mirrors.
- Building downstream recommendation models.

## 6. Done condition
The requested local folders exist, and if download is permitted the eight files are present and checked, `check.txt` exists, and `inspect_zhihurec.py` exists.

## 7. Verification
- Run directory listing commands to confirm the folders exist.
- If files are downloaded, run file-size and line-count checks plus row sampling.
- Run `python scripts/inspect_zhihurec.py` after download to confirm the script can open the files and print the expected summary.

## 8. Expected output
Local dataset folders, a verification report, and a reusable inspection script.

## 9. Notes for the next step
If Step 1 remains blocked by manual confirmation, only the folder creation part of this step should be completed now.

## 10. Risks or ambiguity
The official source may not provide a dedicated 1M archive. In that case the implementation must explain the official top-N generation rule instead of inventing a custom sampling method.
