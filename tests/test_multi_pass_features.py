import sys
import os
import re
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QPoint

from LibreLlamaLabEditor import (
    AcademicReviewerApp,
    ReviewWorker,
    IssueItem,
    RevisionOption,
    ResearchRecommendation,
    AcademicReviewReport
)

def test_multi_pass_suite():
    print("==================================================")
    print("Testing Multi-Pass Agentic & Reasoning Features")
    print("==================================================")
    app = QApplication.instance() or QApplication(sys.argv)
    window = AcademicReviewerApp()

    # 1. Test UI Pipeline combo
    print("[Test 1] Verifying Pipeline Mode Combo...")
    assert hasattr(window, 'pipeline_combo')
    assert window.pipeline_combo.count() == 2
    assert window.pipeline_combo.itemData(0) == "multi_pass"
    assert window.pipeline_combo.itemData(1) == "single_pass"
    print("[+] Pipeline mode selector present and properly configured!")

    # 2. Test ReviewWorker default parameters
    print("\n[Test 2] Verifying ReviewWorker defaults...")
    worker = ReviewWorker(
        text="Sample manuscript text",
        engine_mode="ollama",
        model_name="deepseek-r1:14b",
        api_config={"temperature": 0.2},
        ui_language="zh_TW",
        writing_mode="academic",
        context_scope="comprehensive",
        section_target="all"
    )
    assert worker.temperature == 0.2
    assert worker.pipeline_mode == "multi_pass"
    print("[+] ReviewWorker defaults verified (temperature=0.2, pipeline_mode=multi_pass)!")

    # 3. Test Reasoning Model <think> parser
    print("\n[Test 3] Testing <think> block isolation...")
    raw_with_think = """<think>
Deep reasoning trace: analyzing clauses, checking Figure 6 cross-references.
</think>
```json
{
  "collocation_issues": [
    {
      "original_text": "pH rose over the run",
      "category": "Collocation Defect",
      "severity": "Major",
      "reviewer_comment_en": "Unidiomatic collocation",
      "reviewer_comment_zh": "非自然搭配詞",
      "revision_options": [
        {
          "style_label": "Formal Register",
          "revised_text": "pH increased during the operation",
          "rationale_en": "More formal",
          "rationale_zh": "更正式"
        }
      ]
    }
  ]
}
```"""
    parsed = worker._parse_json_safely(raw_with_think)
    assert "collocation_issues" in parsed
    assert len(parsed["collocation_issues"]) == 1
    issue = worker.parse_issue_item(parsed["collocation_issues"][0])
    assert issue is not None
    assert issue.original_text == "pH rose over the run"
    assert issue.revision_options[0].revised_text == "pH increased during the operation"
    print("[+] <think> tags isolated and JSON parsed with 100% precision!")

    # 4. Test Prompt Builders for Pass 1, 2, 3
    print("\n[Test 4] Testing 3-Pass Prompt Builders...")
    p1 = worker.build_pass1_collocation_prompt()
    p2 = worker.build_pass2_discourse_prompt()
    p3 = worker.build_pass3_synthesis_prompt()

    assert "collocation_issues" in p1
    assert "discourse_issues" in p2 and "research_recommendations" in p2
    assert "revised_full_text" in p3 and "overall_assessment" in p3
    print("[+] All 3 specialized agent prompts validated!")

    # 5. Test Fallback Synthesis Generator
    print("\n[Test 5] Testing Fallback Text Alignment Generator...")
    text_orig = "The test began and pH rose over the run in the chamber."
    improved = worker.generate_fallback_improved_text(text_orig, [issue])
    assert "pH increased during the operation" in improved
    assert "pH rose over the run" not in improved
    print(f"[+] Fallback synthesis aligned successfully: '{improved}'")

    print("\n==================================================")
    print("[SUCCESS] ALL ADVANCED MULTI-PASS TESTS PASSED!")
    print("==================================================")

if __name__ == "__main__":
    test_multi_pass_suite()
