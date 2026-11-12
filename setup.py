#!/usr/bin/env python3
"""
Setup script for DK_AI System
Helps users initialize the project with necessary files and configurations
"""

import os
import sys
import subprocess
from pathlib import Path

def print_header(text):
    """Print a formatted header"""
    print("\n" + "="*60)
    print(f"  {text}")
    print("="*60 + "\n")

def check_python_version():
    """Check if Python version is 3.10 or higher"""
    print_header("Checking Python Version")
    if sys.version_info < (3, 10):
        print("Error: Python 3.10 or higher is required")
        print(f"   Current version: {sys.version}")
        return False
    print(f"✓ Python version: {sys.version.split()[0]}")
    return True

def create_directories():
    """Create necessary directories if they don't exist"""
    print_header("Creating Directories")
    directories = ['weights', 'test_videos', 'templates', 'src', 'outputs', 'images', 'static']
    
    for directory in directories:
        path = Path(directory)
        if not path.exists():
            path.mkdir(parents=True)
            print(f"✓ Created directory: {directory}/")
        else:
            print(f"  Directory exists: {directory}/")

def create_env_file():
    """Create .env file from .env.example if it doesn't exist"""
    print_header("Setting Up Environment File")
    
    if Path('.env').exists():
        print("  .env file already exists")
        overwrite = input("  Do you want to overwrite it? (y/n): ").lower()
        if overwrite != 'y':
            print("  Skipping .env creation")
            return
    
    if Path('.env.example').exists():
        # Copy .env.example to .env
        with open('.env.example', 'r') as example:
            content = example.read()
        
        with open('.env', 'w') as env:
            env.write(content)
        
        print("✓ Created .env file from .env.example")
        print("\n  IMPORTANT: Edit .env file and add your:")
        print("  - GEMINI_API_KEY")
        print("  - RTSP_FRONT (camera URL)")
        print("  - RTSP_BACK (camera URL)")
    else:
        print("⚠ Warning: .env.example not found")
        print("  Please create .env file manually")

def install_dependencies():
    """Install Python dependencies"""
    print_header("Installing Dependencies")
    
    if not Path('requirements.txt').exists():
        print("Error: requirements.txt not found")
        return False
    
    print("Installing packages from requirements.txt...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✓ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError:
        print("Error: Failed to install dependencies")
        return False

def check_model_weights():
    """Check if model weights exist"""
    print_header("Checking Model Weights")
    
    weights_dir = Path('weights')
    required_weights = ['yolo11s.pt', 'license-plate-finetune-v1l.pt']
    
    missing_weights = []
    for weight in required_weights:
        weight_path = weights_dir / weight
        if weight_path.exists():
            print(f"✓ Found: {weight}")
        else:
            print(f"Missing: {weight}")
            missing_weights.append(weight)
    
    if missing_weights:
        print("\n⚠ Warning: Some model weights are missing")
        print("  Please download the following models:")
        if 'yolo11s.pt' in missing_weights:
            print("  - yolo11s.pt: https://github.com/ultralytics/ultralytics (or auto-downloaded by ultralytics)")
        if 'license-plate-finetune-v1l.pt' in missing_weights:
            print("  - license-plate-finetune-v1l.pt: Contact repository owner")
        print("\n  Place them in the 'weights/' directory")

def display_next_steps():
    """Display next steps for the user"""
    print_header("Setup Complete!")
    
    print("Next steps:")
    print("\n1. Configure your environment:")
    print("   - Edit .env file with your API keys and camera URLs")
    print("   - Get Gemini API key: https://makersuite.google.com/app/apikey")
    print("\n2. Download model weights (if missing):")
    print("   - Place yolo11s.pt and license-plate-finetune-v1l.pt in weights/ directory")
    print("\n3. Test the system:")
    print("   python ai_server_test.py")
    print("\n4. Run production server:")
    print("   python ai_server.py")
    print("\n5. Setup mobile app:")
    print("   cd mobile_flutter")
    print("   flutter pub get")
    print("   flutter run")
    
    print("\nFor more details, see README.md")
    print("="*60 + "\n")

def main():
    """Main setup function"""
    print("\n")
    print("╔════════════════════════════════════════════════════════╗")
    print("║         DK_AI System - Setup Wizard                   ║")
    print("╚════════════════════════════════════════════════════════╝")
    
    if not check_python_version():
        sys.exit(1)
    create_directories()
    create_env_file()
    install_choice = input("\nDo you want to install dependencies now? (y/n): ").lower()
    if install_choice == 'y':
        install_dependencies()
    else:
        print("Skipping dependency installation")
        print("Run 'pip install -r requirements.txt' later")
    check_model_weights()
    display_next_steps()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user")
        sys.exit(0)
