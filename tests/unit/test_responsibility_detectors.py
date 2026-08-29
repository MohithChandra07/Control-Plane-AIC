"""Unit tests for ToxicityDetector, BiasDetector, and expanded PII patterns."""

from detectors.pii.regex_pii import detect_pii
from detectors.responsibility import BiasDetector, ToxicityDetector


def test_toxicity_detector_catches_profanity_and_harassment():
    detector = ToxicityDetector()
    finding, matches = detector.scan("You are such an asshole, shut the fuck up!")
    assert finding.evaluated is True
    assert finding.detected is True
    assert finding.score >= 0.8
    assert len(matches) >= 2


def test_toxicity_detector_clean_text():
    detector = ToxicityDetector()
    finding, matches = detector.scan("Thank you for reaching out to support today.")
    assert finding.evaluated is True
    assert finding.detected is False
    assert finding.score == 0.0
    assert len(matches) == 0


def test_bias_detector_catches_gender_and_racial_bias():
    detector = BiasDetector()
    finding, matches = detector.scan("Women can't do engineering work and all minorities always fail.")
    assert finding.evaluated is True
    assert finding.detected is True
    assert finding.score >= 0.8
    assert len(matches) >= 1


def test_bias_detector_clean_text():
    detector = BiasDetector()
    finding, matches = detector.scan("Our team consists of qualified software engineers from diverse backgrounds.")
    assert finding.evaluated is True
    assert finding.detected is False
    assert len(matches) == 0


def test_expanded_pii_detector_api_keys():
    matches = detect_pii("My secret key is sk-proj-1234567890abcdef1234567890")
    categories = [m.category for m in matches]
    assert "api_key" in categories
