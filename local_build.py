#!/usr/bin/env python3

import subprocess
import sys
import shutil
import os
from pathlib import Path

def find_spacy_model():
    """Find the locally installed spaCy model"""
    try:
        result = subprocess.run([
            sys.executable, "-c", 
            "import en_core_web_sm; print(en_core_web_sm.__file__)"
        ], capture_output=True, text=True, check=True, cwd=Path.cwd())
        
        model_init_path = result.stdout.strip()
        model_path = Path(model_init_path).parent
        print(f"Found spaCy model at: {model_path}")
        return model_path
        
    except subprocess.CalledProcessError:
        print("❌ spaCy model not found!")
        print("Please install it first with:")
        print("uv run python -m spacy download en_core_web_sm")
        return None

def build_with_local_model():
    """Build binary using locally installed spaCy model"""
    
    current_dir = Path(__file__).parent
    
    # Find the local spaCy model
    model_path = find_spacy_model()
    if not model_path:
        return None
    
    # Convert to absolute path for spec file
    model_path_abs = model_path.resolve()
    
    # Create spec file with local model
    spec_content = f'''# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# Local spaCy model path
model_path = r"{model_path_abs}"

a = Analysis(
    ['pii_cli.py'],
    pathex=[],
    binaries=[],
    datas=[(str(model_path), "en_core_web_sm")],
    hiddenimports=[
        'regex_pii_detector',
        'presidio_pii_detector', 
        'spacy_ner_pii_detector',
        'combined_pii_detector',
        'spacy',
        'presidio_analyzer',
        'presidio_anonymizer',
        'en_core_web_sm'
    ],
    hookspath=[],
    hooksconfig={{}},
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
'''
    
    # Write spec file
    spec_file = current_dir / "pii-cli-local.spec"
    with open(spec_file, 'w') as f:
        f.write(spec_content)
    
    print("Created spec file with local spaCy model")
    
    # Clean previous builds
    build_dir = current_dir / "build-local"
    dist_dir = current_dir / "dist"
    
    if build_dir.exists():
        shutil.rmtree(build_dir)
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    
    # Build
    cmd = [
        "pyinstaller", 
        "--clean",
        f"--distpath={dist_dir}",
        f"--workpath={build_dir}",
        str(spec_file)
    ]
    
    print(f"Building binary...")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✅ Build successful!")
        
        binary_path = dist_dir / "pii-cli"
        if binary_path.exists():
            size_mb = binary_path.stat().st_size / (1024 * 1024)
            print(f"Binary: {binary_path}")
            print(f"Size: {size_mb:.1f} MB")
            
            # Make executable
            os.chmod(binary_path, 0o755)
            
            return binary_path, build_dir, spec_file
        else:
            print("❌ Binary not found after build")
            return None, build_dir, spec_file
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Build failed: {e}")
        if e.stderr:
            print(f"Error: {e.stderr}")
        return None, build_dir, spec_file

def test_binary(binary_path):
    """Test the binary"""
    print(f"\nTesting: {binary_path}")
    
    test_text = "Contact John Doe at john.doe@example.com or call (555) 123-4567"
    
    try:
        result = subprocess.run([
            str(binary_path), "--strategy", "adaptive", "--quiet"
        ], input=test_text, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("✅ Test passed!")
            print(f"Input:  {test_text}")
            print(f"Output: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ Test failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Test error: {e}")
        return False

def cleanup(build_dir, spec_file):
    """Clean up build files"""
    print("\nCleaning up...")
    
    if build_dir and build_dir.exists():
        shutil.rmtree(build_dir)
        print(f"Removed: {build_dir}")
    
    if spec_file and spec_file.exists():
        spec_file.unlink()
        print(f"Removed: {spec_file}")
    
    # Clean other build artifacts
    for path in [Path("build"), Path("build-simple"), Path("build-final")]:
        if path.exists():
            shutil.rmtree(path)
            print(f"Removed: {path}")
    
    for spec in Path(".").glob("*.spec"):
        spec.unlink()
        print(f"Removed: {spec}")

def main():
    print("Local spaCy Model Binary Builder")
    print("=" * 35)
    
    # Build
    result = build_with_local_model()
    if result[0] is None:
        print("Build failed!")
        return 1
    
    binary_path, build_dir, spec_file = result
    
    # Test
    if test_binary(binary_path):
        # Clean up
        cleanup(build_dir, spec_file)
        
        print("\n" + "=" * 35)
        print("🎉 Success!")
        print(f"Binary: {binary_path}")
        print(f"Size: {binary_path.stat().st_size / (1024 * 1024):.1f} MB")
        print("\nUsage:")
        print(f'echo "PII text" | {binary_path} --strategy adaptive')
        print(f'{binary_path} --help')
        
        return 0
    else:
        print("❌ Tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())