# Windows: "Application Control policy has blocked this file" (pandas DLL error)

## What it means
Windows has a security feature that only allows trusted, signed program files to run.
pandas, numpy and many scientific libraries contain compiled files (`.pyd` / `.dll`)
that are often NOT signed. If Windows blocks one, `import pandas` fails with a message like:

    ImportError: DLL load failed while importing ... An Application Control policy has blocked this file.

Streamlit needs pandas, so the dashboard cannot start until this is fixed.
Changing the Python version does NOT fix this, because the block is about file
signatures, not Python compatibility.

## Step 0: Confirm the cause
From the project folder, with the virtual environment active:

    python scripts/check_environment.py

## Fix 1 (personal laptop, Windows 11): check Smart App Control
1. Press Start, type **Windows Security**, open it.
2. Go to **App & browser control** -> **Smart App Control settings**.
3. If it is **On** or **Evaluation**, it is the likely cause.
   Choose **Off**.
   WARNING: Microsoft does not allow turning it back On without resetting/reinstalling
   Windows. Only do this on a laptop you personally own.
4. Restart the laptop, activate the venv and run the check script again.

## Fix 2: Reinstall the blocked package cleanly
Sometimes a half-downloaded or quarantined file is the problem:

    python -m pip install --force-reinstall --no-cache-dir pandas numpy

## Fix 3: Move the project to a simple path
Paths with spaces, OneDrive sync or Downloads/Desktop can add problems. Use a path like:

    C:\Projects\smart-city-traffic-dashboard

Then create a new venv there (do not copy the old one; a venv cannot be moved).

## Fix 4: College or work laptop (managed by an administrator)
If Smart App Control is not present and the laptop belongs to an institute,
a WDAC / AppLocker policy is enforced by the IT admin. You cannot and should not
bypass it. Options: ask IT to allow your venv folder, use another personal laptop
for the group, or run the project on Google Colab / GitHub Codespaces for development.
