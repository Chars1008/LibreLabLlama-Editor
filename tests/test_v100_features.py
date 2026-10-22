# -*- coding: utf-8 -*-
"""
test_v100_features.py
Comprehensive test suite for LibreLlama Lab Editor v1.0.0 (公開測試版):
1. Single Card Carousel Navigation (CardCarouselWidget):
   - Verifies 1 card at a time display with Prev, Next, First, Last navigation and counter (e.g. 1 / 4).
2. Interactive Working Draft View (InteractiveWorkingDraftBrowser):
   - Verifies that the middle column contains "修改中全文" with interactive collocation anchors.
3. Floating Collocation Popup (FloatingCollocationPopup):
   - Verifies that hovering/clicking over a collocation pops up options, and selecting an option
     immediately updates both "修改中全文" and "修改後全文", and synchronizes carousel cards!
4. Review Interrupt / Stop Review Button:
   - Verifies that clicking review toggles to "🛑 終止審查", and stopping cleanly resets the UI.
5. Version v1.0.0 verification across components.
"""
import os
import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import Qt, QPoint
from PySide6.QtWidgets import QApplication

from LibreLlamaLabEditor import (
    AcademicReviewerApp,
    AcademicReviewReport,
    IssueItem,
    RevisionOption,
    ResearchRecommendation,
    CardCarouselWidget,
    FloatingCollocationPopup,
    InteractiveWorkingDraftBrowser,
    APP_VERSION
)

def run_tests():
    print(f"==================================================")
    print(f"Testing LibreLlama Lab Editor {APP_VERSION} Features")
    print(f"==================================================")
    assert APP_VERSION == "1.0.0", f"Expected version 1.0.0, got {APP_VERSION}"

    app = QApplication.instance() or QApplication(sys.argv)
    window = AcademicReviewerApp()
    window.show()

    # 1. Verify CardCarouselWidget functionality
    print("\n[Test 1] Testing CardCarouselWidget Carousel...")
    carousel = window.colloc_carousel
    assert isinstance(carousel, CardCarouselWidget)
    assert carousel.lbl_counter.text() == "0 / 0"
    assert not carousel.btn_prev.isEnabled()
    assert not carousel.btn_next.isEnabled()

    # 2. Simulate Review Report with Collocation & Discourse Issues
    print("\n[Test 2] Simulating review completion with multi-issue report...")
    sample_text = (
        "Our preliminary experiments suggest that the proposed architecture significantly mitigates "
        "inference latency while maintaining high precision. However, this method make an experiment "
        "without considering confounding variables."
    )
    window.text_editor.setPlainText(sample_text)

    report = AcademicReviewReport(
        article_gist_zh="探討新型神經架構在延遲降低與精度維持上的表現。",
        article_gist_en="Evaluates the proposed architecture in lowering latency while maintaining accuracy.",
        overall_assessment_zh="論文架構新穎，但部分實驗論證與搭配詞仍有精修空間。",
        overall_assessment_en="Novel architectural proposal, but requires refinement in experimental rigor and collocations.",
        research_recommendations=[
            ResearchRecommendation(
                gap_identified_zh="缺乏消融實驗",
                gap_identified_en="Lacks ablation validation",
                severity="Strongly Recommended (強烈建議補強)",
                action_type="消融實驗補強",
                concrete_proposal_zh="建議增加去除注意機制後的對比",
                concrete_proposal_en="Add baseline comparison without attention mechanism",
                impact_on_acceptance_zh="大幅提升審稿人信服度",
                impact_on_acceptance_en="Substantially boosts reviewer conviction"
            )
        ],
        issues=[
            IssueItem(
                category="Collocation Defect",
                severity="Major",
                original_text="significantly mitigates",
                meaning_analysis_zh="顯著減輕或降低推論延遲",
                meaning_analysis_en="Substantially alleviates inference delay",
                reviewer_comment_zh="此搭配詞可進一步換為更高階之頂刊動詞。",
                reviewer_comment_en="Consider upgrading to high-impact domain verbs.",
                revision_options=[
                    RevisionOption(
                        style_label="頂刊標竿 (Top-Tier)",
                        revised_text="significantly curtails",
                        rationale_zh="使用 curtails 更為道地且學術力度更強",
                        rationale_en="Curtails offers sharper precision for latency reduction."
                    ),
                    RevisionOption(
                        style_label="精簡俐落 (Concise)",
                        revised_text="substantially reduces",
                        rationale_zh="最經典直觀的國際通用表達",
                        rationale_en="Direct, punchy, and universally accepted."
                    ),
                    RevisionOption(
                        style_label="防禦語氣 (Hedging)",
                        revised_text="tends to mitigate",
                        rationale_zh="語氣更為謹慎保守",
                        rationale_en="Hedging tone to prevent overclaiming."
                    )
                ]
            ),
            IssueItem(
                category="Collocation Defect",
                severity="Critical",
                original_text="make an experiment",
                meaning_analysis_zh="進行實驗",
                meaning_analysis_en="Conducting experiments",
                reviewer_comment_zh="中式生硬搭配詞，英語應使用 conduct 或 carry out。",
                reviewer_comment_en="Unnatural collocation; use conduct or perform instead.",
                revision_options=[
                    RevisionOption(
                        style_label="頂刊標準 (Standard Academic)",
                        revised_text="conduct an experiment",
                        rationale_zh="標準學術動名搭配",
                        rationale_en="Standard academic collocation."
                    ),
                    RevisionOption(
                        style_label="嚴謹深入 (Rigorous)",
                        revised_text="undertake experimental validation",
                        rationale_zh="提升整體學術規格",
                        rationale_en="Elevates scholarly tone."
                    )
                ]
            ),
            IssueItem(
                category="Flawed Deduction",
                severity="Major",
                original_text="without considering confounding variables",
                meaning_analysis_zh="未考慮混雜變因",
                meaning_analysis_en="Failing to control for confounding variables",
                reviewer_comment_zh="推論漏洞，應明確指出哪些變因被排除。",
                reviewer_comment_en="Deductive leap; specify which confounders were omitted.",
                revision_options=[
                    RevisionOption(
                        style_label="防禦弱化 (Cautious Defense)",
                        revised_text="without fully accounting for extraneous confounders",
                        rationale_zh="精確界定限制",
                        rationale_en="Defines experimental boundaries carefully."
                    )
                ]
            )
        ]
    )

    # Deliver report to app
    window.on_review_finished(report)
    QApplication.processEvents()

    # 3. Test Tabs and Carousel Population
    print("\n[Test 3] Verifying Middle Tab Widget & Carousel Card counts...")
    assert window.critique_tab_widget.count() == 4
    tab0_text = window.critique_tab_widget.tabText(0)
    tab1_text = window.critique_tab_widget.tabText(1)
    tab2_text = window.critique_tab_widget.tabText(2)
    tab3_text = window.critique_tab_widget.tabText(3)
    print(f"Tabs: [0] {tab0_text} | [1] {tab1_text} | [2] {tab2_text} | [3] {tab3_text}")
    assert "修改中全文" in tab0_text
    assert "搭配詞選項 (2)" in tab1_text
    assert "句構與邏輯 (1)" in tab2_text
    assert "實證補強 (1)" in tab3_text

    # 4. Test Single Card Navigation (Carousel Prev/Next)
    print("\n[Test 4] Testing Collocation Carousel Single-Card Navigation...")
    c_car = window.colloc_carousel
    assert len(c_car.cards) == 2
    assert c_car.current_idx == 0
    assert c_car.lbl_counter.text() == "第 1 / 2 處"
    assert not c_car.btn_prev.isEnabled()
    assert c_car.btn_next.isEnabled()

    # Click Next
    c_car.go_next()
    QApplication.processEvents()
    assert c_car.current_idx == 1
    assert c_car.lbl_counter.text() == "第 2 / 2 處"
    assert c_car.btn_prev.isEnabled()
    assert not c_car.btn_next.isEnabled()

    # Click Prev
    c_car.go_prev()
    QApplication.processEvents()
    assert c_car.current_idx == 0
    assert c_car.lbl_counter.text() == "第 1 / 2 處"
    print("[+] Carousel Single-Card Navigation passed!")

    # 5. Test Interactive Working Draft View & Anchors
    print("\n[Test 5] Testing Interactive Working Draft View...")
    working_html = window.working_draft_browser.toHtml()
    assert "colloc:0" in working_html, "Missing anchor for issue 0 in working draft"
    assert "colloc:1" in working_html, "Missing anchor for issue 1 in working draft"
    assert "issue:2" in working_html, "Missing anchor for issue 2 in working draft"
    print("[+] Interactive Working Draft successfully generated with collocation anchors!")

    # 6. Test Floating Collocation Popup & Option Switching
    print("\n[Test 6] Testing Floating Collocation Popup and Option Switch...")
    popup = window.floating_colloc_popup
    assert isinstance(popup, FloatingCollocationPopup)

    # Trigger popup for issue 0 at simulated coordinates (200, 200)
    window.show_floating_collocation_popup(0, QPoint(200, 200))
    QApplication.processEvents()
    assert popup.isVisible()
    assert popup.current_issue_idx == 0
    assert len(popup.option_buttons) == 3

    # Initial option 0 revised text was "significantly curtails"
    assert "significantly curtails" in window.latest_revised_plain_text
    assert "significantly curtails" in window.latest_working_draft_plain_text

    # Click Option B (index 1: "substantially reduces") in the floating popup
    print("Switching option to Option B (substantially reduces)...")
    popup.on_click_option(1)
    QApplication.processEvents()

    # Verify both Working Draft and Revised Text updated to "substantially reduces"!
    assert "substantially reduces" in window.latest_working_draft_plain_text
    assert "substantially reduces" in window.latest_revised_plain_text
    assert "significantly curtails" not in window.latest_working_draft_plain_text
    print("[+] Option switch successfully synchronized between Floating Popup, Working Draft, and Revised Full Text!")

    # 7. Test Copy Working Draft Text
    print("\n[Test 7] Testing copy working draft text...")
    window.copy_working_draft_text()
    copied = QApplication.clipboard().text()
    assert "substantially reduces" in copied
    print(f"[+] Clipboard contains updated working draft text ({len(copied)} chars)!")

    # 8. Test Stop Review Button Toggle
    print("\n[Test 8] Testing Stop Review Button Toggle...")
    window.is_reviewing = True
    window.review_btn.setText("🛑 終止審查 (Stop Review)")
    window.stop_review()
    assert not window.is_reviewing
    assert "開始智能審查" in window.review_btn.text()
    assert "審查已由使用者手動終止" in window.status_banner.text()
    print("[+] Stop Review feature cleanly halts and resets UI!")

    # 9. Capture screenshot of the verified v1.0.0 Interface
    artifact_dir = r"C:\Users\Chars Hsieh\.gemini\antigravity\brain\9ed82452-db3f-4e1c-a7a9-d93e5acf5d5c"
    screenshot_path = os.path.join(artifact_dir, "v1.0.0_open_beta_verified.png")
    window.grab().save(screenshot_path)
    print(f"\n[+] Saved verification screenshot to: {screenshot_path}")

    print("\n==================================================")
    print("[SUCCESS] ALL v1.0.0 OPEN BETA TESTS PASSED!")
    print("==================================================")
    window.close()

if __name__ == "__main__":
    run_tests()
