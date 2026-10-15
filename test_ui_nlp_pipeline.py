# -*- coding: utf-8 -*-
"""
Headless UI screenshot test for verifying NLP Pipeline in LibreLlama Lab Editor v0.9.3.
"""
import sys
import os
import time
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from academic_reviewer_app import AcademicReviewerApp

def main():
    app = QApplication(sys.argv)
    window = AcademicReviewerApp()
    window.resize(1500, 950)
    window.show()

    # Sample containing all targeted NLP errors:
    # 1. Scientific unit spacing: 10mL, 50uM, 37°C, 24h
    # 2. Transitive verb error: discuss about, emphasize on
    # 3. Double conjunction: Although ... but
    # 4. SVA mismatch: The mechanism of these cells are ...
    # 5. Bare demonstrative: This demonstrates that ...
    # 6. Nominalization: conducted an analysis of
    test_draft = (
        "Although the experimental procedure was complex, but we obtained valuable results.\n"
        "Cells were incubated at 37°C for 24h with 10mL of 50uM drug solution.\n"
        "We will discuss about the outcome and emphasize on the physiological impacts.\n"
        "The mechanism of these cells are not completely understood by researchers.\n"
        "This demonstrates that our molecular hypothesis is valid.\n"
        "We conducted an analysis of the collected protein samples."
    )

    # Step 1: Set text in draft editor and trigger preflight scan
    window.text_editor.setPlainText(test_draft)
    window.run_preflight_analysis()

    app.processEvents()

    artifact_dir = r"C:\Users\Chars Hsieh\.gemini\antigravity\brain\9ed82452-db3f-4e1c-a7a9-d93e5acf5d5c"
    os.makedirs(artifact_dir, exist_ok=True)
    screenshot_path1 = os.path.join(artifact_dir, "v0.9.3_preflight_diff.png")
    window.grab().save(screenshot_path1)
    print(f"Saved preflight diff screenshot to: {screenshot_path1}")

    # Step 2: Trigger quick fix
    window.auto_fix_preflight_issues()
    app.processEvents()

    screenshot_path2 = os.path.join(artifact_dir, "v0.9.3_autofix_applied.png")
    window.grab().save(screenshot_path2)
    print(f"Saved autofix applied screenshot to: {screenshot_path2}")

    window.close()
    print("UI Test Completed.")

if __name__ == "__main__":
    main()
