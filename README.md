# FFastGPU

FFastGPU is a Windows GUI wrapper for FFmpeg that fully utilizes NVIDIA GPU encoders/decoders for accelerated video processing.

## Features
- One-click batch video re-encoding with GPU acceleration (NVENC/NVDEC)
- Real-time system monitoring (CPU, RAM, GPU usage and temperature)
- Drag and drop file support
- Dark/light theme toggle
- Auto-generated output filenames with encoding parameters
- Comprehensive logging system
- Built as a single executable with PyInstaller

## Installation
Download the latest release from the [Releases page](https://github.com/Msadr471/FFastGPU/releases).

### System Requirements
- Windows 10/11
- NVIDIA GPU with supported drivers
- FFmpeg and FFprobe installed in system PATH
- NVIDIA System Management Interface (nvidia-smi) for monitoring

## Usage
1. Launch FFastGPU.exe
2. Add video files (MP4/MKV) via "Add Files" button or drag & drop
3. Configure encoding settings (bitrate, FPS, preset, etc.)
4. Select output folder and format
5. Click "Start Conversion" to begin processing
6. Monitor progress and system statistics in real-time

## Build Instructions (Developers)

### Requirements:
- Python 3.8+
- PyInstaller
- Dependencies in requirements.txt

### Build steps:
1. Clone the repository
2. Install dependencies:
```bash
pip install -r requirements.txt
Run the build script:

```bash
build.bat