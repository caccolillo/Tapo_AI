#!/usr/bin/env python3
"""
Tapo Camera Image Capture Script
Captures images from Tapo cameras and saves them in lossless formats.
Supports both RTSP stream capture and HTTP API methods.
"""

import cv2
import requests
import base64
import hashlib
import time
import os
import sys
import io
from datetime import datetime
from urllib.parse import quote
import argparse
from PIL import Image
import numpy as np

class TapoCamera:
    def __init__(self, ip, username, password):
        self.ip = ip
        self.username = username
        self.password = password
        self.token = None
        self.session = requests.Session()
        
    def _encrypt_credentials(self):
        """Simple credential encoding for Tapo API"""
        auth_string = f"{self.username}:{self.password}"
        return base64.b64encode(auth_string.encode()).decode()
    
    def _get_auth_token(self):
        """Get authentication token from camera"""
        url = f"http://{self.ip}/stok=0/ds"
        
        payload = {
            "method": "login",
            "params": {
                "hashed": True,
                "username": base64.b64encode(self.username.encode()).decode(),
                "password": base64.b64encode(
                    hashlib.md5(self.password.encode()).hexdigest().encode()
                ).decode()
            }
        }
        
        try:
            response = self.session.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("error_code") == 0:
                    self.token = data.get("result", {}).get("stok")
                    return True
            return False
        except Exception as e:
            print(f"Authentication failed: {e}")
            return False
    
    def capture_via_rtsp(self, output_path, format_type="PNG"):
        """Capture image using RTSP stream"""
        # Common RTSP URLs for Tapo cameras
        rtsp_urls = [
            f"rtsp://{self.username}:{self.password}@{self.ip}:554/stream1",
            f"rtsp://{self.username}:{self.password}@{self.ip}:554/stream2",
            f"rtsp://{self.username}:{quote(self.password)}@{self.ip}:554/stream1"
        ]
        
        for rtsp_url in rtsp_urls:
            print(f"Trying RTSP URL: rtsp://{self.username}:***@{self.ip}:554/stream1")
            
            cap = cv2.VideoCapture(rtsp_url)
            
            # Try to set timeout if supported by OpenCV version
            try:
                cap.set(cv2.CAP_PROP_TIMEOUT, 10000)  # 10 second timeout
            except AttributeError:
                # Fallback for older OpenCV versions
                print("Note: Timeout setting not supported in this OpenCV version")
            
            if cap.isOpened():
                print("RTSP connection established...")
                
                # Read a few frames to ensure we get a good one
                # Add a timeout mechanism for older OpenCV versions
                start_time = time.time()
                timeout_seconds = 15
                
                for attempt in range(10):  # Try more attempts for reliability
                    if time.time() - start_time > timeout_seconds:
                        print("Timeout reached while reading frames")
                        break
                        
                    ret, frame = cap.read()
                    if ret and frame is not None and frame.size > 0:
                        print(f"Successfully captured frame (attempt {attempt + 1})")
                        break
                    time.sleep(0.2)  # Wait a bit between attempts
                
                if ret and frame is not None and frame.size > 0:
                    # Convert BGR to RGB for PIL
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    
                    # Save using PIL for better format control
                    img = Image.fromarray(frame_rgb)
                    
                    if format_type.upper() == "PNG":
                        img.save(output_path, "PNG", optimize=False)
                    elif format_type.upper() == "TIFF":
                        img.save(output_path, "TIFF", compression=None)
                    elif format_type.upper() == "BMP":
                        img.save(output_path, "BMP")
                    
                    cap.release()
                    return True, f"Image captured via RTSP: {frame.shape[1]}x{frame.shape[0]}"
                else:
                    print("Failed to capture valid frame")
                
                cap.release()
            else:
                print("Failed to open RTSP connection")
            
        return False, "Failed to capture via RTSP"
    
    def capture_via_http(self, output_path, format_type="PNG"):
        """Capture image using HTTP API"""
        if not self.token and not self._get_auth_token():
            return False, "Authentication failed"
        
        # Try snapshot endpoint
        snapshot_url = f"http://{self.ip}/stok={self.token}/ds"
        
        payload = {
            "method": "get",
            "params": {
                "image": {
                    "name": ["snapshot"]
                }
            }
        }
        
        try:
            response = self.session.post(snapshot_url, json=payload, timeout=15)
            
            if response.status_code == 200:
                # Check if response is JSON (error) or image data
                content_type = response.headers.get('content-type', '').lower()
                
                if 'image' in content_type:
                    # Direct image response
                    with open(output_path, 'wb') as f:
                        f.write(response.content)
                    return True, "Image captured via HTTP API"
                
                elif 'application/json' in content_type:
                    # JSON response might contain base64 image
                    data = response.json()
                    if data.get("error_code") == 0:
                        image_data = data.get("result", {}).get("image", {}).get("snapshot")
                        if image_data:
                            # Decode base64 image
                            image_bytes = base64.b64decode(image_data)
                            
                            # Convert to PIL Image for format conversion
                            img = Image.open(io.BytesIO(image_bytes))
                            
                            if format_type.upper() == "PNG":
                                img.save(output_path, "PNG", optimize=False)
                            elif format_type.upper() == "TIFF":
                                img.save(output_path, "TIFF", compression=None)
                            elif format_type.upper() == "BMP":
                                img.save(output_path, "BMP")
                            
                            return True, "Image captured via HTTP API"
            
            return False, f"HTTP API failed: {response.status_code}"
            
        except Exception as e:
            return False, f"HTTP capture failed: {e}"

def capture_image(ip, username, password, output_path=None, format_type="PNG", method="auto"):
    """Main function to capture image from Tapo camera"""
    
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        extension = format_type.lower()
        output_path = f"tapo_capture_{ip}_{timestamp}.{extension}"
    
    camera = TapoCamera(ip, username, password)
    
    print(f"Capturing image from {ip}...")
    print(f"Output: {output_path}")
    print(f"Format: {format_type} (lossless)")
    
    success = False
    message = ""
    
    if method in ["auto", "rtsp"]:
        print("\nTrying RTSP method...")
        success, message = camera.capture_via_rtsp(output_path, format_type)
        
        if success:
            print(f"✓ {message}")
            return output_path
    
    if not success and method in ["auto", "http"]:
        print("\nTrying HTTP API method...")
        success, message = camera.capture_via_http(output_path, format_type)
        
        if success:
            print(f"✓ {message}")
            return output_path
    
    if not success:
        print(f"✗ Failed to capture image: {message}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Capture images from Tapo cameras")
    parser.add_argument("ip", help="Camera IP address")
    parser.add_argument("username", help="Camera username")
    parser.add_argument("password", help="Camera password")
    parser.add_argument("-o", "--output", help="Output file path")
    parser.add_argument("-f", "--format", choices=["PNG", "TIFF", "BMP"], 
                       default="PNG", help="Output format (default: PNG)")
    parser.add_argument("-m", "--method", choices=["auto", "rtsp", "http"],
                       default="auto", help="Capture method (default: auto)")
    parser.add_argument("--continuous", type=int, metavar="SECONDS",
                       help="Continuous capture every N seconds (Ctrl+C to stop)")
    
    args = parser.parse_args()
    
    if args.continuous:
        print(f"Starting continuous capture every {args.continuous} seconds...")
        print("Press Ctrl+C to stop")
        
        try:
            counter = 1
            while True:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = f"tapo_capture_{args.ip}_{timestamp}.{args.format.lower()}"
                
                print(f"\n--- Capture #{counter} ---")
                result = capture_image(args.ip, args.username, args.password, 
                                     output_path, args.format, args.method)
                
                if result:
                    print(f"Saved: {result}")
                else:
                    print("Capture failed")
                
                counter += 1
                time.sleep(args.continuous)
                
        except KeyboardInterrupt:
            print("\nContinuous capture stopped by user")
    else:
        # Single capture
        result = capture_image(args.ip, args.username, args.password, 
                             args.output, args.format, args.method)
        
        if result:
            print(f"\n✓ Image saved successfully: {result}")
            
            # Display image info
            try:
                with Image.open(result) as img:
                    print(f"Image size: {img.size[0]}x{img.size[1]}")
                    print(f"Color mode: {img.mode}")
                    print(f"File size: {os.path.getsize(result):,} bytes")
            except Exception as e:
                print(f"Could not read image info: {e}")
        else:
            print("\n✗ Failed to capture image")
            sys.exit(1)

if __name__ == "__main__":
    # Example usage if run without arguments
    if len(sys.argv) == 1:
        print("Tapo Camera Image Capture Script")
        print("\nUsage:")
        print("  python tapo_capture.py <ip> <username> <password> [options]")
        print("\nExample:")
        print("  python tapo_capture.py 192.168.1.100 admin password123")
        print("  python tapo_capture.py 192.168.1.100 admin password123 -f TIFF -o my_image.tiff")
        print("  python tapo_capture.py 192.168.1.100 admin password123 --continuous 30")
        print("\nLossless formats supported: PNG, TIFF, BMP")
        print("Methods: auto (tries RTSP then HTTP), rtsp, http")
        sys.exit(0)
    
    main()
