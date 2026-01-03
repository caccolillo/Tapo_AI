# Tapo Camera Image Capture Script

This script captures **still images from TP-Link Tapo IP cameras** and saves them in **lossless formats** (PNG, TIFF, BMP).
The camera has to be configured with a static IP address, and username and password must be set as well from the TAPO Android app.

## How it works
- Connects to the camera using its **IP address and credentials**
- Captures a snapshot using:
  1. **RTSP video stream** (default, preferred)
  2. **HTTP API snapshot** (fallback)
- Saves the image using **PIL** to avoid compression loss

## Features
- Automatic RTSP → HTTP fallback
- Supports PNG, TIFF (uncompressed), BMP
- Single capture or **continuous capture** at fixed intervals
- Prints basic image info after saving

## Usage
```bash
python tapo_capture.py <ip> <username> <password> [options]
```

### Options
- `-o, --output` – output file path  
- `-f, --format` – PNG | TIFF | BMP (default: PNG)  
- `-m, --method` – auto | rtsp | http  
- `--continuous N` – capture every N seconds

## Typical use cases
- Snapshot extraction from IP cameras
- Time-lapse recording
- Computer vision / CNN dataset generation


## Usage: 

python3 ./capture.py 192.168.0.253 USERNAME PASSWORD -f TIFF -o my_image.tiff
