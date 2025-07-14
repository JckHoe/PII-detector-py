#!/usr/bin/env python3
"""Build script to create executable binary using PyInstaller."""

import subprocess
import sys
import os
import shutil
import platform

def main():
    """Build the CLI tool into a standalone executable."""
    print("Building executable binary...")
    
    if os.path.exists("dist"):
        shutil.rmtree("dist")
    if os.path.exists("build"):
        shutil.rmtree("build")

    system = platform.system().lower()
    arch = platform.machine().lower()
    if arch in ['x86_64', 'amd64']:
        arch = 'amd64'
    elif arch in ['aarch64', 'arm64']:
        arch = 'arm64'

    binary_name = f"pii-cli-{system}-{arch}"
    if system == "windows":
        binary_name += ".exe"
    
    cmd = [
        "pyinstaller",
        "--onefile",           
        "--name", binary_name, 
        "--clean",           
        "--noconfirm",
        "--collect-all", "curated_transformers",
        "--collect-all", "spacy_curated_transformers",
        "--hidden-import", "spacy_curated_transformers",
        "--hidden-import", "spacy_curated_transformers.language",
        "--hidden-import", "spacy_curated_transformers.pipeline.curated_transformer",
        "--hidden-import", "spacy_curated_transformers.tokenization",
        "--hidden-import", "regex",
        "pii_cli.py"
    ]
    
    try:
        print("Starting PyInstaller build (this may take several minutes)...")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=1200)
        print("Build successful!")
        print(f"Executable created: dist/{binary_name}")
        
        if os.name != 'nt':
            executable_path = f"dist/{binary_name}"
            if os.path.exists(executable_path):
                os.chmod(executable_path, 0o755)
                print(f"Made {executable_path} executable")
        
        return True
        
    except subprocess.TimeoutExpired:
        print("Build timed out after 5 minutes. This may indicate a hanging process.")
        print("Try running the build command manually to see the full output.")
        return False
    except subprocess.CalledProcessError as e:
        print(f"Build failed: {e}")
        print(f"Error output: {e.stderr}")
        return False
    except FileNotFoundError:
        print("Error: PyInstaller not found. Please install it with: pip install pyinstaller")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
