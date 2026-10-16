# -*- coding: utf-8 -*-
"""
Test script to verify degenerate repetition cleanup and JSON report salvage.
"""
import re
import json_repair
from academic_reviewer_app import AcademicReviewReport, IssueItem, ResearchRecommendation

def test_salvage():
    # Simulates the exact truncated output seen in user's screenshot
    corrupted_stream = (
        '{"article_gist_zh": "比較細菌產物對植物逆境的保護效果", '
        '"article_gist_en": "Compares bacterial products on plant stress tolerance", '
        '"overall_assessment_zh": "文稿架構完整，但部分實驗細節需加強說明。", '
        '"overall_assessment_en": "Draft has sound structure, but experimental details require clarification.", '
        '"revised_full_text": "Microbes that lower plant ethylene with ACC deaminase promote plant growth under stress.", '
        '"collocation_issues": ['
        '  {"category": "Collocation Defect", "original_text": "lower plant ethylene", "severity": "Major", '
        '   "reviewer_comment_en": "Use reduce or suppress for standard academic precision.", '
        '   "reviewer_comment_zh": "建議使用 reduce 或 suppress 提升精確度。", '
        '   "revision_options": [{"style_label": "High-Impact", "revised_text": "reduce plant ethylene", "rationale_zh": "道地搭配", "rationale_en": "Standard academic collocation"}]}'
        '],'
        '"discourse_issues": [], '
        '"research_recommendations": ['
        '  {"action_type": "Empirical Verification", "severity": "Strongly Recommended", '
        '   "gap_identified_zh": "細菌產物成分不明確", "gap_identified_en": "Bacterial products are not chemically characterized", '
        '   "concrete_proposal_zh": "應明確說明所測試的物質成分（例如：cell-free supernatants）。", '
        '   "concrete_proposal_en": "Explicitly define the chemical or biological nature of the bacterial products.", '
        '   "impact_on_acceptance_zh": "若不明確，審稿人會質疑實驗的科學嚴謹性。", '
        '   "impact_on_acceptance_en": "potentially leading to a rejection based on methodological vaguenesssackackackackackackackackackackackackackackackackackackackackackackackackackackackackackackackackackackackackackackack'
    )

    # 1. Clean degenerate repetitive tail
    cleaned = re.sub(r'(.{2,15}?)\1{4,}$', '', corrupted_stream)
    cleaned = re.sub(r'(.)\1{8,}$', '', cleaned)
    assert not cleaned.endswith("ackackackack")
    print(f"[1] Repeating tail stripped. Cleaned end: ...{repr(cleaned[-50:])}")

    # 2. Repair with json_repair
    data = json_repair.repair_json(cleaned, return_objects=True)
    assert isinstance(data, dict), "json_repair failed to return dict"
    print(f"[2] Repaired successfully into dict with keys: {list(data.keys())}")

    # 3. Verify Pydantic report reconstruction
    data['research_recommendations'] = [
        ResearchRecommendation(**r) for r in data.get('research_recommendations', [])
    ]
    data['collocation_issues'] = [
        IssueItem(**i) for i in data.get('collocation_issues', [])
    ]
    report = AcademicReviewReport(**data)
    assert report.overall_assessment_zh
    assert len(report.research_recommendations) == 1
    assert len(report.collocation_issues) == 1
    print("[3] Successfully reconstructed AcademicReviewReport without any exception!")
    print(f"    Rec concrete proposal: {report.research_recommendations[0].concrete_proposal_en}")
    print(f"    Rec impact salvaged: {report.research_recommendations[0].impact_on_acceptance_en}")
    print("\nALL REPETITION SALVAGE TESTS PASSED!")

if __name__ == "__main__":
    test_salvage()
