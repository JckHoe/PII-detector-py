#!/usr/bin/env python3

import os
import sys
import subprocess
import shutil
from pathlib import Path

def install_pyinstaller():
    try:
        import PyInstaller
        print("PyInstaller already installed")
    except ImportError:
        print("Installing PyInstaller...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)

def build_binary():
    current_dir = Path(__file__).parent
    
    # Find spaCy model path
    try:
        result = subprocess.run([
            sys.executable, "-c", 
            "import en_core_web_sm; print(en_core_web_sm.__file__)"
        ], capture_output=True, text=True, check=True)
        model_path = Path(result.stdout.strip()).parent
        print(f"Found spaCy model at: {model_path}")
    except subprocess.CalledProcessError:
        print("Warning: Could not find en_core_web_sm model")
        model_path = None
    
    pyinstaller_args = [
        "pyinstaller",
        "--onefile",
        "--name=pii-cli",
        "--console",
        "--clean",
        f"--distpath={current_dir}/dist",
        f"--workpath={current_dir}/build",
        f"--specpath={current_dir}",
        "--hidden-import=en_core_web_sm",
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
        str(current_dir / "pii_cli.py")
    ]
    
    # Add spaCy model data if found
    if model_path:
        pyinstaller_args.insert(-1, f"--add-data={model_path}:en_core_web_sm")
    
    print("Building binary with PyInstaller...")
    print(f"Command: {' '.join(pyinstaller_args)}")
    
    try:
        result = subprocess.run(pyinstaller_args, check=True, capture_output=True, text=True)
        print("Build successful!")
        
        binary_path = current_dir / "dist" / "pii-cli"
        if binary_path.exists():
            size_mb = binary_path.stat().st_size / (1024 * 1024)
            print(f"Binary created: {binary_path}")
            print(f"Size: {size_mb:.1f} MB")
            
            os.chmod(binary_path, 0o755)
            print("Made binary executable")
            
            return binary_path
        else:
            print("Error: Binary not found after build")
            return None
            
    except subprocess.CalledProcessError as e:
        print(f"Build failed: {e}")
        print(f"Error output: {e.stderr}")
        return None

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
    
    install_pyinstaller()
    create_spec_file()
    
    binary_path = build_binary()
    
    if binary_path:
        print("\n" + "=" * 30)
        print("Build Complete!")
        print(f"Binary location: {binary_path}")
        print("\nUsage examples:")
        print(f'echo "Contact John at john@email.com" | {binary_path}')
        print(f'{binary_path} --help')
    else:
        print("Build failed!")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())