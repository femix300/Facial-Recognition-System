# Facial Recognition System - Installation & Testing Guide

This project is a Facial Recognition Attendance System built with Python, OpenCV, and Dlib. It allows real-time face detection and recognition for automated attendance management. This document provides comprehensive installation instructions, troubleshooting steps, and testing guidelines.

## 1. System Requirements

Before you begin, ensure you have the following:

- **Python 3.10 or 3.11** (recommended)
- **pip** (Python package manager)
- **Git** (for cloning repository and LFS)
- **Virtual environment** support
- **Windows/Linux/Mac** compatible

## 2. Quick Start - Virtual Environment Setup

### Step-by-Step Installation Process

1. **Open Command Prompt/Terminal**

2. **Check your Python version:**
   ```bash
   python --version
   ```
   *Make note of your Python version (e.g., 3.10.x or 3.11.x) as you'll need it for the Dlib installation.*

3. **Create a new folder for your virtual environment:**
   ```bash
   mkdir face_env
   ```

4. **Navigate into the folder:**
   ```bash
   cd face_env
   ```

5. **Create a virtual environment:**
   ```bash
   python -m venv venv
   ```

6. **Activate the virtual environment:**
   ```bash
   # On Windows
   venv\Scripts\activate
   
   # On Linux/Mac
   source venv/bin/activate
   ```
   *You should see `(venv)` at the beginning of your command prompt when activated.*

## 3. Installing Dependencies

### Standard Installation Process (Recommended First Step)

**Try this method first** - it's the standard Python approach and will work for most users:

```bash
# Make sure your virtual environment is activated
# Install all dependencies from requirements.txt
pip install -r requirements.txt
```

**If the above command succeeds**, skip to Section 4 (Large File Handling). **If it fails** (especially with dlib installation errors), continue with the alternative installation methods below.

### Alternative Installation Process (If requirements.txt fails)

Run the following commands **inside your activated virtual environment**:

```bash
# Install OpenCV
pip install opencv-python

# Fix NumPy compatibility issues
pip uninstall numpy
pip install numpy==1.26.4

# Install CMake (required for Dlib)
pip install cmake

# Attempt direct Dlib installation
pip install dlib
```

### 🔧 Dlib Installation Workaround

**If the direct `pip install dlib` command fails**, follow this workaround using precompiled wheel files:

#### Method 1: Download from Dlib Wheel Repository

1. **Download the wheel files collection:**
   - Go to: https://codeload.github.com/Cfuhfsgh/Dlib-library-Installation/zip/refs/heads/main
   - This will download a ZIP file containing wheel files for Python 3.11

2. **Extract the ZIP file:**
   - Extract the downloaded ZIP file to access the wheel files
   - Look for the file: `dlib-19.24.2-cp311-cp311-win_amd64.whl` (Windows 64-bit)

3. **Move the wheel file to your project directory:**
   ```bash
   # Navigate to your project directory
   cd face_env
   
   # Copy the Python 3.11 wheel file to this directory
   # The file should be: dlib-19.24.2-cp311-cp311-win_amd64.whl
   ```

4. **Install the wheel file:**
   ```bash
   # Make sure your virtual environment is activated
   # Install the wheel file for Python 3.11
   pip install dlib-19.24.2-cp311-cp311-win_amd64.whl
   ```

5. **Install remaining dependencies:**
   ```bash
   # After dlib is successfully installed, install remaining packages
   pip install -r requirements.txt --force-reinstall
   ```

#### Method 2: Manual Download (Alternative)

If Method 1 doesn't work, you can try to find a Python 3.11 compatible wheel file manually, but Method 1 is recommended as it contains the tested wheel files.

#### Wheel File Information:
- **cp311**: Python 3.11 (required)
- **win_amd64**: Windows 64-bit
- **win32**: Windows 32-bit (if available)

⚠️ **Important Notes:**
- This project specifically requires Python 3.11 due to wheel file availability
- If you're on Linux/Mac, look for appropriate wheel files in the downloaded ZIP
- If no compatible wheel file is found, you may need to compile Dlib from source or use conda: `conda install -c conda-forge dlib`

## 4. Large File Handling (Model Files)

The system requires pretrained models like `shape_predictor_68_face_landmarks.dat`. These large files are managed with Git LFS:

```bash
# Install Git LFS (Linux)
sudo apt-get install git-lfs

# Install Git LFS (Windows - download from git-lfs.github.io)
# Install Git LFS (Mac)
brew install git-lfs

# Initialize Git LFS
git lfs install

# Pull large files after cloning
git lfs pull
```

## 5. Installation Verification & Testing

To verify that OpenCV and Dlib are working correctly, create and run this test script:

### Create Test File
```bash
# Windows
notepad test_dlib_face_detection.py

# Linux/Mac
nano test_dlib_face_detection.py
```

### Test Script Content
```python
import cv2
import dlib
import numpy as np

def main():
    print("WEBCAM FACE DETECTION TEST")
    print("="*40)
    print("Controls:")
    print("  'o' - Switch to OpenCV detection (Green boxes)")
    print("  'd' - Switch to dlib detection (Red boxes)")
    print("  'q' - Quit")
    print("  'c' - Capture screenshot")
    print("="*40)

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ Error: Could not access webcam")
        return

    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    dlib_detector = dlib.get_frontal_face_detector()
    detection_mode = 'opencv'
    frame_count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if gray.dtype != np.uint8:
            gray = gray.astype(np.uint8)

        if detection_mode == 'opencv':
            faces = face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(30, 30))
            for (x, y, w, h) in faces:
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                cv2.putText(frame, 'OpenCV', (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            face_count = len(faces)
            mode_color = (0, 255, 0)
        elif detection_mode == 'dlib':
            faces = dlib_detector(gray, 1)
            for face in faces:
                x, y, w, h = face.left(), face.top(), face.width(), face.height()
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 0, 255), 2)
                cv2.putText(frame, 'dlib', (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            face_count = len(faces)
            mode_color = (0, 0, 255)

        cv2.putText(frame, f'Mode: {detection_mode.upper()}', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, mode_color, 2)
        cv2.putText(frame, f'Faces: {face_count}', (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, mode_color, 2)
        cv2.imshow('Webcam Face Detection', frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('o'):
            detection_mode = 'opencv'
            print("Switched to OpenCV detection")
        elif key == ord('d'):
            detection_mode = 'dlib'
            print("Switched to dlib detection")
        elif key == ord('c'):
            filename = f'webcam_capture_{frame_count}.jpg'
            cv2.imwrite(filename, frame)
            print(f"Screenshot saved as {filename}")

    cap.release()
    cv2.destroyAllWindows()
    print("Test completed successfully!")

if __name__ == "__main__":
    main()
```

### Run the Test
```bash
python test_dlib_face_detection.py
```

**Expected Results:**
- A window should open showing your webcam feed
- Press 'o' to see OpenCV detection (green boxes)
- Press 'd' to see dlib detection (red boxes)
- Both should detect faces in real-time

## 6. Troubleshooting Common Issues

### Requirements.txt Installation Fails
**Problem**: `pip install -r requirements.txt` fails with various errors

**Solutions:**
1. **Check Python version**: Ensure you're using Python 3.10 or 3.11
2. **Upgrade pip**: `pip install --upgrade pip`
3. **Try with no cache**: `pip install -r requirements.txt --no-cache-dir`
4. **Fall back to individual installation**: Use the Alternative Installation Process (Section 3)

### Dlib Installation Fails
**Problem**: `pip install dlib` fails with compilation errors

**Solutions:**
1. Use the precompiled wheel method described above
2. Install Visual Studio Build Tools (Windows)
3. Use conda instead: `conda install -c conda-forge dlib`
4. Try: `pip install dlib --no-cache-dir`

### OpenCV Camera Access Issues
**Problem**: "Could not access webcam" error

**Solutions:**
1. Check if another application is using the camera
2. Try different camera indices: `cv2.VideoCapture(1)` or `cv2.VideoCapture(2)`
3. Grant camera permissions to your terminal/IDE

### NumPy Compatibility Issues
**Problem**: Version conflicts between OpenCV and NumPy

**Solution:**
```bash
pip uninstall numpy opencv-contrib-python
pip install -r requirements.txt --force-reinstall
```

### Virtual Environment Issues
**Problem**: Commands not working in virtual environment

**Solutions:**
1. Ensure virtual environment is activated (you should see `(venv)` in prompt)
2. Restart your terminal and reactivate: `venv\Scripts\activate`
3. Check Python path: `which python` (Linux/Mac) or `where python` (Windows)

### Mixed Installation Issues
**Problem**: Some packages installed via requirements.txt, others individually

**Solution:**
```bash
# Clean installation - uninstall all packages and reinstall
pip freeze > installed_packages.txt
pip uninstall -r installed_packages.txt -y
pip install -r requirements.txt
```

## 7. Dependencies Overview

This project uses several key libraries:
- **Django 5.2.6**: Web framework for the attendance system
- **OpenCV (opencv-contrib-python)**: Computer vision and image processing
- **Dlib 19.24.1**: Face detection and facial landmark detection
- **NumPy 1.26.4**: Numerical computing (pinned for compatibility)
- **MediaPipe 0.10.21**: Advanced face detection and processing
- **Matplotlib**: Plotting and visualization
- **Gunicorn**: Production WSGI server
- **PostgreSQL support**: Database connectivity

## 8. Installation Summary

### Recommended Installation Order:
1. **Set up virtual environment** (Section 2)
2. **Try `pip install -r requirements.txt`** (Section 3 - Standard Process)
3. **If that fails, use individual package installation** (Section 3 - Alternative Process)
4. **If dlib fails, use wheel file workaround** (Section 3 - Dlib Workaround)
5. **Set up Git LFS for model files** (Section 4)
6. **Run verification test** (Section 5)

## 9. Getting Help

If you encounter issues during installation:

1. **Check Python version compatibility**: Ensure you're using Python 3.10 or 3.11
2. **Verify virtual environment**: Make sure it's activated before installing packages
3. **Try requirements.txt first**: This is the standard approach and works for most users
4. **Use the wheel file workaround**: For persistent dlib installation issues
5. **Check system permissions**: Ensure camera access is granted
6. **Consult the troubleshooting section**: Common solutions for frequent problems

For additional support, create an issue in the project repository with:
- Your Python version (`python --version`)
- Operating system details
- Complete error messages
- Steps you've already tried
- Whether you tried `pip install -r requirements.txt` first

---

**Happy coding! 🚀**