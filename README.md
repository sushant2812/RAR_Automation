# RAR Automation

A desktop application that watches a download folder and automatically extracts new RAR or ZIP archives when downloads finish. Built with Python and PyQt5.

## Features

- **Watch & extract** — Monitors a folder for new `.rar` or `.zip` files and extracts them when the download completes
- **Progress feedback** — Progress bar and status messages during extraction
- **System tray** — Minimize to tray; optional notification when extraction completes
- **Supported formats** — RAR and ZIP

## Prerequisites

- **Python 3** or greater
- **UnRAR** (for RAR extraction) — `rarfile` uses the system `unrar` command. Install as needed:
  - **macOS:** `brew install unrar`
  - **Windows:** [Download UnRAR](https://www.rarlab.com/rar_add.htm) and add to PATH

## Installation

1. Clone or download this repository:
   ```bash
   git clone <repository-url>
   cd RAR_Automation
   ```

2. Create a virtual environment (recommended):
   ```bash
   python3 -m venv venv
   source venv/bin/activate   # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install rarfile PyQt5
   ```

   Or use a requirements file (create one with):
   ```bash
   pip install rarfile PyQt5
   pip freeze | grep -E "rarfile|PyQt5" > requirements.txt
   ```
   Then: `pip install -r requirements.txt`

4. Ensure the UI file `test.ui` is in the same directory as `main.py`. (If your file is named `main.ui`, either rename it to `test.ui` or change the `loadUi("test.ui", self)` line in `main.py` to match.)

## How to Run

1. From the project directory, run:
   ```bash
   python main.py
   ```

2. **Set the directories** in the app:
   - **Download folder** — Folder where your browser or download manager saves files (e.g. `~/Downloads`)
   - **Extraction folder** — Folder where extracted contents should go (e.g. `~/Extracted`)

3. Click **Start**. The app will:
   - Wait until it detects a new file in the download folder
   - Wait for the download to finish (no temporary `.cr` file)
   - Extract the new RAR or ZIP into a subfolder in the extraction directory
   - Show a tray notification when extraction is complete

4. Start your download in the browser or download manager; the app will pick up and extract the new archive when it’s done.

## Usage Notes

- Only the **first new** RAR or ZIP that appears after clicking Start is processed per run. For another file, click Start again after setting directories.
- Closing the window with “Minimize to tray” checked hides the app to the system tray instead of exiting. Use the tray menu to Show or Exit.
- The app must stay running while the download is in progress so it can detect when the file is complete and then extract it.

## Project Structure

```
RAR_Automation/
├── main.py      # Application entry point and UI logic
├── test.ui      # PyQt5 UI layout (must be present)
└── README.md
```

## Troubleshooting

| Issue | Suggestion |
|-------|------------|
| “ModuleNotFoundError: No module named 'rarfile'” or “PyQt5” | Run `pip install rarfile PyQt5` in the same environment you use to run `python main.py`. |
| RAR extraction fails | Install UnRAR (`brew install unrar` on macOS) and ensure `unrar` is on your PATH. |
| “Download hasn’t been started” forever | Confirm the download folder path is correct and that you’ve started a download into that folder. |
| UI doesn’t load | Ensure `test.ui` exists next to `main.py`, or update the `loadUi(...)` path in `main.py` to your UI filename. |
