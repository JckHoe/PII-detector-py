#!/usr/bin/env python3

import os
import sys
import subprocess
import shutil
import platform
from pathlib import Path
from typing import Optional

def install_pyinstaller():
    try:
        import PyInstaller
        print("PyInstaller already installed")
    except ImportError:
        print("Installing PyInstaller...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)

def get_embedded_model_path() -> Optional[str]:
    try:
        base_dir = Path(sys._MEIPASS)
    except AttributeError:
        base_dir = Path(__file__).parent
    model_dir = base_dir / "en_core_web_trf"
    return str(model_dir) if model_dir.exists() else None

def build_binary():
    current_dir = Path(__file__).parent.resolve()
    model_dir = current_dir / "extracted_model" / "en_core_web_trf" / "en_core_web_trf-3.8.0"
    
    if not model_dir.exists():
        print(f"Error: spaCy model not found at {model_dir}")
        print("Please run: python -m spacy download en_core_web_trf && python -m spacy package en_core_web_trf extracted_model --force")
        return None

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
        "--hidden-import=spacy_curated_transformers",
        "--hidden-import=presidio_analyzer",
        "--hidden-import=presidio_anonymizer", 
        "--hidden-import=regex_pii_detector",
        "--hidden-import=presidio_pii_detector",
        "--hidden-import=spacy_ner_pii_detector",
        "--hidden-import=combined_pii_detector",
        "--collect-data=spacy",
        "--collect-data=spacy_curated_transformers",
        "--collect-data=presidio_analyzer",
        "--collect-data=presidio_anonymizer",
        f"--add-data={model_dir}:{'en_core_web_trf'}",  # Embed the model folder under this name
        # Optimize binary size
        "--exclude-module=tkinter",
        "--exclude-module=matplotlib",
        "--exclude-module=IPython",
        "--exclude-module=jupyter",
        "--exclude-module=notebook",
        str(current_dir / "pii_cli.py")
    ]

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

            print("Testing binary...")
            test_result = subprocess.run([str(binary_path), "--help"], capture_output=True, text=True, timeout=30)
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
