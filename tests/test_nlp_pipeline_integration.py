# -*- coding: utf-8 -*-
"""
Test script for verifying AcademicNLPPipeline and its integration with LibreLlama Lab Editor.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json

from academic_nlp_pipeline import AcademicNLPPipeline, DiagnosticItem, AutoSanitizeChange, PipelineResult
from LibreLlamaLabEditor import PreflightChecker, PreflightMatch

def test_pipeline_core():
    print("=== Testing AcademicNLPPipeline Core ===")
    
    # 1. Test Auto-Sanitize
    test_text_units = "Incubated 10mL of 50uM solution at 37°C for 24h, centrifuged at 12000rpm."
    sanitized, changes = AcademicNLPPipeline.auto_sanitize(test_text_units)
    print(f"[Sanitize Units] Result: {sanitized}")
    assert "10 mL" in sanitized, "10mL should become 10 mL"
    assert "50 uM" in sanitized, "50uM should become 50 uM"
    assert "37 °C" in sanitized, "37°C should become 37 °C"
    assert "24 h" in sanitized, "24h should become 24 h"
    assert "12000 rpm" in sanitized, "12000rpm should become 12000 rpm"
    assert len(changes) >= 5, f"Expected at least 5 unit changes, got {len(changes)}"

    test_text_verbs = "We will discuss about the theory, mention about the protocol, and emphasize on the conclusion."
    sanitized_v, changes_v = AcademicNLPPipeline.auto_sanitize(test_text_verbs)
    print(f"[Sanitize Verbs] Result: {sanitized_v}")
    assert "discuss the theory" in sanitized_v, "discuss about should become discuss"
    assert "mention the protocol" in sanitized_v, "mention about should become mention"
    assert "emphasize the conclusion" in sanitized_v, "emphasize on should become emphasize"

    # 2. Test Rule-Based Diagnostics (JSON Schema)
    sample_diagnostics = (
        "Although the methodology was rigorous, but errors occurred. "
        "The mechanism of these cells are not fully understood. "
        "These observations indicates a new pathway. "
        "This demonstrates that our hypothesis was correct. "
        "We performed an analysis of the samples and conducted a measurement of the velocity. "
        "The newly discovered mammalian protein which was synthesized during the late embryonic developmental stage "
        "in the transgenic laboratory animal models was observed to be dramatically upregulated under persistent oxidative stress conditions, "
        "leading to severe downstream cellular apoptosis and extensive tissue degradation."
    )
    result = AcademicNLPPipeline.process(sample_diagnostics)
    json_str = result.to_json(indent=2)
    print("[JSON Output Verification]:")
    print(json_str[:500] + "\n...")

    data = json.loads(json_str)
    assert "original_text" in data
    assert "sanitized_text" in data
    assert "sanitize_changes" in data
    assert "diagnostics" in data
    assert len(data["diagnostics"]) > 0

    rule_ids = {d["rule_id"] for d in data["diagnostics"]}
    print(f"Captured Rule IDs: {rule_ids}")
    assert "RULE_DOUBLE_CONJUNCTION_ALTHOUGH_BUT" in rule_ids, "Double conjunction although/but should be caught"
    assert "RULE_SVA_MISMATCH" in rule_ids, "SVA mismatch should be caught"
    assert "RULE_BARE_DEMONSTRATIVE" in rule_ids, "Bare demonstrative should be caught"
    assert "RULE_HEAVY_NOMINALIZATION" in rule_ids, "Heavy nominalization should be caught"
    assert "RULE_PASSIVE_VOICE" in rule_ids, "Passive voice should be caught"
    assert "RULE_OVERLY_LONG_SENTENCE" in rule_ids, "Long sentence > 35 words should be caught"

    print("=== Core Pipeline Tests PASSED! ===\n")

def test_preflight_integration():
    print("=== Testing PreflightChecker Integration ===")
    sample = (
        "We don't know the exact answer. Although we tried hard, but we failed. "
        "The mechanism are unknown. 10mL was used. We will discuss about it."
    )
    matches = PreflightChecker.scan(sample, is_en=False)
    print(f"Total Preflight Matches found: {len(matches)}")
    match_cats = [m.category for m in matches]
    print(f"Categories: {match_cats}")
    assert any("縮寫" in c or "Contraction" in c for c in match_cats), "Contractions should be caught"
    assert any("主謂" in c or "Agreement" in c for c in match_cats), "SVA should be caught"
    assert any("雙重連接詞" in c or "Conjunction" in c for c in match_cats), "Double conjunction should be caught"

    fixed = PreflightChecker.fix_all_issues(sample)
    print(f"Fixed Text:\n{fixed}")
    assert "do not" in fixed, "don't should be expanded to do not"
    assert "10 mL" in fixed, "10mL should be auto-sanitized to 10 mL"
    assert "discuss it" in fixed, "discuss about it should become discuss it"

    print("=== Preflight Integration Tests PASSED! ===\n")

if __name__ == "__main__":
    test_pipeline_core()
    test_preflight_integration()
    print("ALL TESTS COMPLETED SUCCESSFULLY!")
