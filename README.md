# FFastGPU

FFastGPU is a Windows GUI wrapper for `ffmpeg` that fully utilizes GPU encoders/decoders.

## Features
- One-click video re-encoding with GPU acceleration
- Auto-incrementing version system
- Lightweight GUI built with PyQt
- Bundled as a single `.exe` with PyInstaller

## Installation
Download the latest release from the [Releases page](../../releases).

## Usage
1. Open the app.
2. Select a video file.
3. Choose encoding options.
4. Start re-encoding with GPU.

## Build (Developer)
Requirements:
- Python 3.11+
- PyInstaller

```bash
pip install -r requirements.txt
pyinstaller --clean --onefile --windowed --name "FFastGPU" FFastGPU.py
