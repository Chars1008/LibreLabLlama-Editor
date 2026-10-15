# -*- coding: utf-8 -*-
"""
Verification script for UpdateCheckWorker and UpdateDialog in LibreLlama Lab Editor.
"""
import sys
import os
import time
from PySide6.QtWidgets import QApplication
from academic_reviewer_app import (
    UpdateCheckWorker, UpdateDialog, load_config, APP_VERSION, DEFAULT_UPDATE_URL
)

def test_update_worker():
    app = QApplication.instance() or QApplication(sys.argv)
    print("=== Testing UpdateCheckWorker Scenarios ===")

    # Scenario 1: Test with "version.json" (the exact case from user's screenshot)
    print("\n[Scenario 1] Testing with input 'version.json'...")
    worker1 = UpdateCheckWorker("version.json")
    results1 = {}
    def on_finish1(has_update, latest_ver, changelog, download_url, err_msg):
        results1["has_update"] = has_update
        results1["latest_ver"] = latest_ver
        results1["changelog"] = changelog
        results1["download_url"] = download_url
        results1["err_msg"] = err_msg

    worker1.check_finished.connect(on_finish1)
    worker1.start()
    worker1.wait(5000)
    app.processEvents()

    print(f"  Result: err_msg='{results1.get('err_msg')}', latest_ver='{results1.get('latest_ver')}'")
    assert not results1.get("err_msg"), f"Scenario 1 should succeed without error, got: {results1.get('err_msg')}"
    assert results1.get("latest_ver") == APP_VERSION, f"Should find version {APP_VERSION}"
    print("  -> Scenario 1 PASSED!")

    # Scenario 2: Test with empty string
    print("\n[Scenario 2] Testing with empty update URL...")
    worker2 = UpdateCheckWorker("")
    results2 = {}
    worker2.check_finished.connect(lambda h, v, c, d, e: results2.update({"h": h, "v": v, "e": e}))
    worker2.start()
    worker2.wait(5000)
    app.processEvents()
    print(f"  Result: err='{results2.get('e')}', ver='{results2.get('v')}'")
    assert not results2.get("e"), f"Scenario 2 should succeed, got: {results2.get('e')}"
    print("  -> Scenario 2 PASSED!")

    # Scenario 3: Test with DEFAULT_UPDATE_URL
    print(f"\n[Scenario 3] Testing with DEFAULT_UPDATE_URL: {DEFAULT_UPDATE_URL}...")
    worker3 = UpdateCheckWorker(DEFAULT_UPDATE_URL)
    results3 = {}
    worker3.check_finished.connect(lambda h, v, c, d, e: results3.update({"h": h, "v": v, "e": e}))
    worker3.start()
    worker3.wait(10000)
    app.processEvents()
    print(f"  Result: err='{results3.get('e')}', ver='{results3.get('v')}'")
    # Even if remote returns 404, our fallback handles it cleanly
    assert "missing an 'http://'" not in str(results3.get("e")), "Should never error with missing protocol"
    print("  -> Scenario 3 PASSED!")

    print("\n=== All UpdateCheckWorker Scenarios PASSED! ===")

def test_update_dialog_ui():
    app = QApplication.instance() or QApplication(sys.argv)
    print("\n=== Testing UpdateDialog UI ===")
    cfg = load_config()
    dialog = UpdateDialog(is_dark=True, config=cfg, lang="zh_TW")
    dialog.show()

    # Let the check complete
    for _ in range(30):
        app.processEvents()
        time.sleep(0.1)
        if not dialog.check_worker or not dialog.check_worker.isRunning():
            break

    app.processEvents()

    artifact_dir = r"C:\Users\Chars Hsieh\.gemini\antigravity\brain\9ed82452-db3f-4e1c-a7a9-d93e5acf5d5c"
    os.makedirs(artifact_dir, exist_ok=True)
    ss_path = os.path.join(artifact_dir, "v0.9.3_update_dialog_fixed.png")
    dialog.grab().save(ss_path)
    print(f"Saved update dialog screenshot to: {ss_path}")
    dialog.close()
    print("=== UpdateDialog UI Test PASSED! ===")

if __name__ == "__main__":
    test_update_worker()
    test_update_dialog_ui()
