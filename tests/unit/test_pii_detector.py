from detectors.pii.regex_pii import detect_pii, quick_pii_scan, redact


def test_detects_phone_number():
    matches = detect_pii("The customer's phone number is 9876543210.")
    assert [m.category for m in matches] == ["phone"]
    assert matches[0].text == "9876543210"


def test_detects_email():
    matches = detect_pii("Reach me at jane.doe@example.com please.")
    assert [m.category for m in matches] == ["email"]


def test_detects_government_id():
    matches = detect_pii("SSN on file: 123-45-6789.")
    assert [m.category for m in matches] == ["government_id"]


def test_no_false_positive_on_clean_text():
    assert detect_pii("Refunds are available within 30 days of purchase.") == []


def test_redact_replaces_matched_span_only():
    text = "Call us at 9876543210 for help."
    matches = detect_pii(text)
    assert redact(text, matches) == "Call us at [REDACTED_PHONE] for help."


def test_quick_pii_scan_matches_detect_pii_presence():
    assert quick_pii_scan("Phone: 9876543210") is True
    assert quick_pii_scan("Refunds are available within 30 days.") is False
