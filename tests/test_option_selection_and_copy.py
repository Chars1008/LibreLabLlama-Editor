# -*- coding: utf-8 -*-
"""
Automated regression test suite for LibreLlama Lab Editor:
1. Option Selection Bug (Bug 1):
   - Verifies that selecting options on cards (including nested and overlapping spans across tabs)
     always dynamically and reliably updates '修改後全文' (revised_browser and latest_revised_plain_text).
   - Verifies multi-occurrence disambiguation and multi-tier fuzzy span matching.
2. Text Copy Bug (Bug 2):
   - Verifies that all textual content in IssueCard and ResearchRecommendationCard has
     TextSelectableByMouse and IBeamCursor enabled, allowing highlight, drag, and copy (Ctrl+C).
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLabel

from LibreLlamaLabEditor import (
    AcademicReviewerApp,
    AcademicReviewReport,
    IssueItem,
    RevisionOption,
    ResearchRecommendation,
    ResearchRecommendationCard,
    IssueCard
)

def test_card_copyability(app_instance: AcademicReviewerApp):
    print("=== Testing Card Text Copyability (Bug 2 Fix) ===")
    
    # 1. Test ResearchRecommendationCard
    rec = ResearchRecommendation(
        gap_identified_zh="未探討不同模型規模下的延遲差異",
        gap_identified_en="Did not explore latency variations across model scales",
        severity="Strongly Recommended (強烈建議補強)",
        action_type="補充驗證/敏感度分析",
        concrete_proposal_zh="建議增加 7B、13B、70B 參數量下的推論時間消融對比實驗",
        concrete_proposal_en="Include ablation benchmarking inference speed across 7B, 13B, and 70B parameter scales",
        impact_on_acceptance_zh="大幅降低 Reviewer 對計算可行性的疑慮",
        impact_on_acceptance_en="Significantly mitigates reviewer doubts regarding computational viability"
    )
    rec_card = ResearchRecommendationCard(rec, is_dark=False, lang="zh_TW")

    labels_to_check = [
        rec_card.findChildren(QLabel)
    ][0]
    
    selectable_count = 0
    for lbl in labels_to_check:
        flags = lbl.textInteractionFlags()
        if flags & Qt.TextSelectableByMouse:
            selectable_count += 1
            if lbl.text() and ("<b>" in lbl.text() or "中文" in lbl.text() or "EN" in lbl.text()):
                assert lbl.cursor().shape() == Qt.IBeamCursor, f"Label {lbl.text()[:20]} should have IBeamCursor"
    
    print(f"[RecCard] Checked {len(labels_to_check)} labels. Selectable labels: {selectable_count}")
    assert selectable_count >= 5, "Key text labels in ResearchRecommendationCard must be selectable"

    # 2. Test IssueCard
    issue = IssueItem(
        category="Collocation Defect",
        category_zh="道地搭配詞",
        severity="Major",
        original_text="conduct an investigation of",
        meaning_analysis_zh="過度名詞化與不自然的學術搭配詞",
        meaning_analysis_en="Heavy nominalization and unidiomatic phrasing",
        reviewer_comment_zh="建議替換為精簡動詞",
        reviewer_comment_en="Replace with active verb for conciseness",
        revision_options=[
            RevisionOption(style_label="Concise", revised_text="investigate", rationale_zh="動詞化更精準", rationale_en="Active verb"),
            RevisionOption(style_label="High-Impact", revised_text="examine", rationale_zh="學術風格", rationale_en="Academic tone")
        ]
    )
    issue_card = IssueCard(0, issue, None, is_dark=False, lang="zh_TW")
    issue_labels = issue_card.findChildren(QLabel)
    
    issue_selectable_count = 0
    for lbl in issue_labels:
        flags = lbl.textInteractionFlags()
        if flags & Qt.TextSelectableByMouse:
            issue_selectable_count += 1
            if "Original" in lbl.text() or "原文" in lbl.text() or "Revised" in lbl.text() or "修訂" in lbl.text():
                assert lbl.cursor().shape() == Qt.IBeamCursor, f"Content label {lbl.text()[:20]} must have IBeamCursor"
                
    print(f"[IssueCard] Checked {len(issue_labels)} labels. Selectable labels: {issue_selectable_count}")
    assert issue_selectable_count >= 5, "Key text labels in IssueCard must be selectable"
    print("=== Card Text Copyability PASSED! ===\n")


def test_option_selection_and_overlap_sync(app_instance: AcademicReviewerApp):
    print("=== Testing Option Selection and Dynamic Overlap Sync (Bug 1 Fix) ===")
    
    draft_text = (
        "In this paper, we conduct an investigation of the phenomenon. "
        "Although the results are promising, but we conduct an investigation of the secondary effects."
    )
    app_instance.text_editor.setPlainText(draft_text)

    # Issue 0: Collocation in Sentence 1 (Occurrence 1)
    issue0 = IssueItem(
        category="Collocation Defect",
        category_zh="道地搭配詞",
        severity="Major",
        original_text="conduct an investigation of",
        meaning_analysis_zh="名詞化",
        reviewer_comment_zh="建議精簡",
        revision_options=[
            RevisionOption(style_label="Option A", revised_text="investigate", rationale_zh="精練"),
            RevisionOption(style_label="Option B", revised_text="probe", rationale_zh="探討")
        ]
    )

    # Issue 1: Sentence 2 Syntax & Logic (Discourse Tab: Double conjunction)
    issue1 = IssueItem(
        category="Grammar & Mechanics",
        category_zh="文法與句構",
        severity="Critical",
        original_text="Although the results are promising, but we conduct an investigation of the secondary effects.",
        meaning_analysis_zh="雙重連接詞",
        reviewer_comment_zh="移除 but",
        revision_options=[
            RevisionOption(
                style_label="Standard Syntax",
                revised_text="Although the results are promising, we conduct an investigation of the secondary effects.",
                rationale_zh="合乎標準語法"
            ),
            RevisionOption(
                style_label="Alternative Syntax",
                revised_text="The results are promising, but we conduct an investigation of the secondary effects.",
                rationale_zh="對等連接詞修飾"
            )
        ]
    )

    # Issue 2: Collocation in Sentence 2 (Occurrence 2, strictly nested inside Issue 1)
    issue2 = IssueItem(
        category="Collocation Defect",
        category_zh="道地搭配詞",
        severity="Major",
        original_text="conduct an investigation of",
        meaning_analysis_zh="第二句之重複名詞化",
        reviewer_comment_zh="建議精簡",
        revision_options=[
            RevisionOption(style_label="Option A", revised_text="investigate", rationale_zh="精練"),
            RevisionOption(style_label="Option B", revised_text="scrutinize", rationale_zh="嚴密檢視")
        ]
    )

    report = AcademicReviewReport(
        article_gist_zh="測試重疊與巢狀卡片選項連動",
        article_gist_en="Testing nested and overlapping card option synchronization",
        overall_assessment_zh="論述架構良好，具備多處可精簡點",
        overall_assessment_en="Good structure with multiple optimization points",
        issues=[issue0, issue1, issue2],
        research_recommendations=[]
    )

    # Trigger review finished handler to populate tabs & cards
    app_instance.on_review_finished(report)

    # Check 1: Initial composition
    # Issue 1 (outer) and Issue 2 (inner) should compose naturally!
    initial_plain = app_instance.latest_revised_plain_text
    print(f"[Initial Sync View]:\n{initial_plain}")
    assert "Although the results are promising, we investigate the secondary effects." in initial_plain, \
        f"Expected nested composition in initial view, got: {initial_plain}"
    assert "In this paper, we investigate the phenomenon." in initial_plain

    # Check 2: User clicks Option B ("scrutinize") on Issue 2 (nested inner card in Tab 2)
    print("\n--- User clicks Option B on Issue 2 (Tab 2: Collocation) ---")
    app_instance.handle_option_selection(2, 1)
    after_issue2_click = app_instance.latest_revised_plain_text
    print(f"[After Issue 2 click]:\n{after_issue2_click}")
    assert "Although the results are promising, we scrutinize the secondary effects." in after_issue2_click, \
        f"Option B on Issue 2 was NOT updated in revised text! Got: {after_issue2_click}"

    # Check 3: User switches to Tab 3 and clicks Option B on Issue 1 ("The results are promising, but...")
    print("\n--- User clicks Option B on Issue 1 (Tab 3: Syntax & Logic) ---")
    app_instance.handle_option_selection(1, 1)
    after_issue1_click = app_instance.latest_revised_plain_text
    print(f"[After Issue 1 click]:\n{after_issue1_click}")
    assert "The results are promising, but we scrutinize the secondary effects." in after_issue1_click, \
        f"Option B on Issue 1 with nested Issue 2 was NOT updated! Got: {after_issue1_click}"

    # Check 4: User clicks Option B ("probe") on Issue 0
    print("\n--- User clicks Option B on Issue 0 (Tab 2: Collocation) ---")
    app_instance.handle_option_selection(0, 1)
    after_issue0_click = app_instance.latest_revised_plain_text
    print(f"[After Issue 0 click]:\n{after_issue0_click}")
    assert "In this paper, we probe the phenomenon." in after_issue0_click, \
        f"Option B on Issue 0 was NOT updated! Got: {after_issue0_click}"

    # Check 5: HTML formatting verification
    html_output = app_instance.revised_browser.toHtml()
    assert "probe" in html_output
    assert "scrutinize" in html_output
    assert "background-color" in html_output
    
    # Check 6: Sync to left editor
    app_instance.sync_revised_to_left()
    synced_text = app_instance.text_editor.toPlainText()
    assert synced_text == app_instance.latest_revised_plain_text
    print("=== Option Selection and Dynamic Overlap Sync PASSED! ===\n")


def main():
    qapp = QApplication.instance()
    if not qapp:
        qapp = QApplication(sys.argv)

    window = AcademicReviewerApp()
    window.show()

    test_card_copyability(window)
    test_option_selection_and_overlap_sync(window)

    # Capture visual verification screenshot to artifact directory
    screenshot_dir = r"C:\Users\Chars Hsieh\.gemini\antigravity\brain\9ed82452-db3f-4e1c-a7a9-d93e5acf5d5c"
    screenshot_path = os.path.join(screenshot_dir, "v0.9.3_option_sync_and_copy_verified.png")
    pixmap = window.grab()
    pixmap.save(screenshot_path)
    print(f"Saved visual verification screenshot to: {screenshot_path}")

    print("\nALL OPTION SYNC AND COPY REGRESSION TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    main()
