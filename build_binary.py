#!/usr/bin/env python3

import os
import sys
import subprocess
import shutil
import platform
from pathlib import Path

def install_pyinstaller():
    try:
        import PyInstaller
        print("PyInstaller already installed")
    except ImportError:
        print("Installing PyInstaller...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)

def find_spacy_model():
    """Find spaCy model with better error handling"""
    model_candidates = [
        "en_core_web_trf",
        "en_core_web_sm", 
        "en_core_web_md",
        "en_core_web_lg"
    ]
    
    for model_name in model_candidates:
        try:
            result = subprocess.run([
                sys.executable, "-c", 
                f"import {model_name}; print({model_name}.__file__)"
            ], capture_output=True, text=True, check=True)
            model_path = Path(result.stdout.strip()).parent
            print(f"Found spaCy model '{model_name}' at: {model_path}")
            return model_path, model_name
        except subprocess.CalledProcessError:
            continue
    
    print("Warning: No spaCy model found. Install with: python -m spacy download en_core_web_trf")
    return None, None

def build_binary():
    current_dir = Path(__file__).parent
    
    # Find spaCy model path
    model_path, model_name = find_spacy_model()
    
    # Get platform-specific binary name
    system = platform.system().lower()
    arch = platform.machine().lower()
    if arch in ['x86_64', 'amd64']:
        arch = 'amd64'
    elif arch in ['aarch64', 'arm64']:
        arch = 'arm64'
    
    binary_name = f"pii-cli-{system}-{arch}"
    if system == "windows":
        binary_name += ".exe"
    
    pyinstaller_args = [
        "pyinstaller",
        "--onefile",
        f"--name={binary_name}",
        "--console",
        "--clean",
        f"--distpath={current_dir}/dist",
        f"--workpath={current_dir}/build",
        f"--specpath={current_dir}",
        "--hidden-import=spacy",
        "--hidden-import=presidio_analyzer",
        "--hidden-import=presidio_anonymizer", 
        "--hidden-import=regex_pii_detector",
        "--hidden-import=presidio_pii_detector",
        "--hidden-import=spacy_ner_pii_detector",
        "--hidden-import=combined_pii_detector",
        "--collect-data=spacy",
        "--collect-data=presidio_analyzer",
        "--collect-data=presidio_anonymizer",
        # Optimize binary size
        "--exclude-module=tkinter",
        "--exclude-module=matplotlib",
        "--exclude-module=IPython",
        "--exclude-module=jupyter",
        "--exclude-module=notebook",
        str(current_dir / "pii_cli.py")
    ]
    
    # Add spaCy model data if found
    if model_path and model_name:
        pyinstaller_args.insert(-1, f"--hidden-import={model_name}")
        pyinstaller_args.insert(-1, f"--add-data={model_path}:{model_name}")
    
    print("Building binary with PyInstaller...")
    print(f"Command: {' '.join(pyinstaller_args)}")
    
    try:
        result = subprocess.run(pyinstaller_args, check=True, capture_output=True, text=True)
        print("Build successful!")
        
        binary_path = current_dir / "dist" / binary_name
        if binary_path.exists():
            size_mb = binary_path.stat().st_size / (1024 * 1024)
            print(f"Binary created: {binary_path}")
            print(f"Size: {size_mb:.1f} MB")
            print(f"Platform: {system}-{arch}")
            
            if system != "windows":
                os.chmod(binary_path, 0o755)
                print("Made binary executable")
            
            # Test the binary
            print("Testing binary...")
            test_result = subprocess.run([str(binary_path), "--help"], 
                                       capture_output=True, text=True, timeout=30)
            if test_result.returncode == 0:
                print("Binary test passed!")
            else:
                print(f"Binary test failed: {test_result.stderr}")
            
            return binary_path
        else:
            print("Error: Binary not found after build")
            return None
            
    except subprocess.CalledProcessError as e:
        print(f"Build failed: {e}")
        print(f"Error output: {e.stderr}")
        if e.stdout:
            print(f"Build output: {e.stdout}")
        return None
    except subprocess.TimeoutExpired:
        print("Binary test timed out")
        return binary_path if 'binary_path' in locals() else None

def create_spec_file():
    spec_content = """
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['pii_cli.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'spacy',
        'en_core_web_sm',
        'presidio_analyzer',
        'presidio_anonymizer',
        'regex_pii_detector',
        'spacy_ner_pii_detector',
        'presidio_pii_detector',
        'combined_pii_detector'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='pii-cli',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
"""
    
    with open("pii-cli.spec", "w") as f:
        f.write(spec_content.strip())
    
    print("Created pii-cli.spec file")

def main():
    print("PII CLI Binary Builder")
    print("=" * 30)
    
    # Check if we're in CI environment
    is_ci = os.environ.get('CI', '').lower() == 'true'
    
    install_pyinstaller()
    
    binary_path = build_binary()
    
    if binary_path:
        print("\n" + "=" * 30)
        print("Build Complete!")
        print(f"Binary location: {binary_path}")
        
        if not is_ci:
            print("\nUsage examples:")
            print(f'echo "Contact John at john@email.com" | {binary_path}')
            print(f'{binary_path} --help')
        
        # Output binary info for CI
        if is_ci:
            print(f"::set-output name=binary_path::{binary_path}")
            print(f"::set-output name=binary_name::{binary_path.name}")
    else:
        print("Build failed!")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())