# -*- coding: utf-8 -*-
"""
build_release.py
Automated release builder for LibreLlama Lab Editor v0.9.3.
1. Compiles uninstaller (uninstall.exe)
2. Compiles application onedir bundle (LibreLlamaLabEditor)
3. Bundles uninstall.exe and version.json into dist/LibreLlamaLabEditor/
4. Compresses application directory into app_bundle.zip
5. Compiles single-file setup installer (LibreLlamaLabEditor_Setup_v0.9.3.exe)
"""
import os
import sys
import shutil
import zipfile
import subprocess
import time

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(PROJECT_DIR, "dist")
BUILD_DIR = os.path.join(PROJECT_DIR, "build")
APP_NAME = "LibreLlamaLabEditor"
SETUP_NAME = "LibreLlamaLabEditor_Setup_v0.9.3"

def run_cmd(cmd_list, desc):
    print(f"\n==========================================")
    print(f"[*] {desc}")
    print(f"    Command: {' '.join(cmd_list)}")
    print(f"==========================================")
    t0 = time.time()
    res = subprocess.run(cmd_list, cwd=PROJECT_DIR, text=True, capture_output=True, encoding="utf-8", errors="replace")
    dt = time.time() - t0
    if res.returncode != 0:
        print(f"[!] FAILED with exit code {res.returncode}")
        print("STDOUT:\n", res.stdout[-2000:])
        print("STDERR:\n", res.stderr[-2000:])
        raise RuntimeError(f"Step failed: {desc}")
    print(f"[+] Completed in {dt:.1f}s")
    return res.stdout

def create_app_bundle_zip(source_dir: str, zip_path: str):
    print(f"\n[*] Creating app_bundle.zip from {source_dir}...")
    t0 = time.time()
    with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, source_dir)
                z.write(abs_path, rel_path)
    dt = time.time() - t0
    size_mb = os.path.getsize(zip_path) / (1024 * 1024)
    print(f"[+] app_bundle.zip created successfully: {size_mb:.2f} MB in {dt:.1f}s")

def main():
    print(f"Starting build for LibreLlama Lab Editor (Project: {PROJECT_DIR})")
    
    # 1. Build uninstaller
    run_cmd([
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--name", "uninstall",
        "uninstall.py"
    ], "Step 1: Compiling uninstaller (uninstall.py)")

    uninstaller_exe = os.path.join(DIST_DIR, "uninstall.exe")
    if not os.path.exists(uninstaller_exe):
        raise FileNotFoundError(f"Missing {uninstaller_exe}")

    # 2. Build onedir application
    app_pyinstaller_args = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onedir",
        "--windowed",
        "--name", APP_NAME,
        "--collect-all", "en_core_web_sm",
        "--collect-all", "spacy",
        "--copy-metadata", "spacy",
        "--copy-metadata", "en_core_web_sm",
        "--hidden-import", "pydantic",
        "--hidden-import", "json_repair",
        "--hidden-import", "httpx",
        "--hidden-import", "ollama",
        "--hidden-import", "academic_nlp_pipeline",
        "academic_reviewer_app.py"
    ]
    run_cmd(app_pyinstaller_args, "Step 2: Compiling LibreLlamaLabEditor onedir bundle")

    app_dir = os.path.join(DIST_DIR, APP_NAME)
    if not os.path.exists(app_dir):
        raise FileNotFoundError(f"Missing {app_dir}")

    # 3. Copy uninstaller and version.json into app_dir
    print(f"[*] Copying uninstaller and metadata into {app_dir}...")
    shutil.copy2(uninstaller_exe, os.path.join(app_dir, "uninstall.exe"))
    shutil.copy2(os.path.join(PROJECT_DIR, "version.json"), os.path.join(app_dir, "version.json"))

    # 4. Create app_bundle.zip
    bundle_zip = os.path.join(PROJECT_DIR, "app_bundle.zip")
    create_app_bundle_zip(app_dir, bundle_zip)

    # 5. Build setup installer
    installer_args = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--name", SETUP_NAME,
        "--add-data", f"{bundle_zip};.",
        "--hidden-import", "httpx",
        "--hidden-import", "ollama",
        "--hidden-import", "PySide6",
        "installer.py"
    ]
    run_cmd(installer_args, f"Step 3: Compiling Setup Installer ({SETUP_NAME}.exe)")

    final_setup_exe = os.path.join(DIST_DIR, f"{SETUP_NAME}.exe")
    if not os.path.exists(final_setup_exe):
        raise FileNotFoundError(f"Setup installer not found: {final_setup_exe}")

    setup_size_mb = os.path.getsize(final_setup_exe) / (1024 * 1024)
    print("\n==================================================")
    print(f"[SUCCESS] BUILD COMPLETED SUCCESSFULLY!")
    print(f"    Target: {final_setup_exe}")
    print(f"    Size:   {setup_size_mb:.2f} MB")
    print("==================================================")

if __name__ == "__main__":
    main()
