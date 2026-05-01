# Subproblem 1: Confirm Official Source And Blockers

## 1. Goal
Verify the exact statements in the official THUIR ZhihuRec-Dataset README and determine whether the official download path can be used directly from the terminal or must stop for manual confirmation.

## 2. Why this step exists
The user asked for the official source only, does not want the 100M dataset downloaded by mistake, and explicitly wants the process to stop if the official link is only a webpage download page.

## 3. Files involved
- `plan/zhihurec-1m-setup/README.md` - tracks task status and dependency.
- `plan/zhihurec-1m-setup/01-confirm-source-and-blockers.md` - records the confirmation task.

## 4. Exact changes
- Open the official `THUIR/ZhihuRec-Dataset` README.
- Confirm that `ZhihuRec-1M` is described as an official smaller dataset.
- Confirm that the dataset description lists eight files.
- Confirm that the README download entry points to the official dataset download link.
- Inspect the official link enough to determine whether it is a direct file or a share webpage.
- If the link is a share webpage, stop before automatic download and report the blocker clearly.

## 5. Out of scope
- Downloading any dataset files.
- Creating the local inspection script.
- Writing dataset check output.

## 6. Done condition
There is a clear yes or no answer for each README requirement, plus a clear statement about whether terminal download can proceed or must stop for manual confirmation.

## 7. Verification
- Open the official README and cite the matching lines.
- Inspect the HTTP response or page content of the official download link.
- Confirm whether it resolves to a directory share webpage or a direct file download.

## 8. Expected output
A grounded decision about whether the workflow can continue automatically.

## 9. Notes for the next step
If the official link is a share webpage, Step 2 should stop after creating only the safe local folder layout. If the user later confirms the download page contents, Step 2 can continue with the exact official files.

## 10. Risks or ambiguity
The share page may expose files through JavaScript APIs rather than plain links. Even if technical download is possible, the user instruction says to stop when the official entry is a webpage download page.
