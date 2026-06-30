import pytest
from src.normalizers.normalizer import CandidateNormalizer

def test_normalize_name():
    norm = CandidateNormalizer()
    assert norm.normalize_name("john doe") == "John Doe"
    assert norm.normalize_name("Dr. Jane Smith, PhD") == "Jane Smith"
    assert norm.normalize_name("  MR.  ALEX   RODRIGUEZ  ") == "Alex Rodriguez"
    assert norm.normalize_name(None) == "Unknown Candidate"

def test_normalize_email():
    norm = CandidateNormalizer()
    assert norm.normalize_email("   JOHN.DOE@EXAMPLE.COM  ") == "john.doe@example.com"
    assert norm.normalize_email("invalid-email") is None
    assert norm.normalize_email(None) is None

def test_normalize_phone():
    norm = CandidateNormalizer(default_country_code="US")
    # Test local US phone mapped to E.164
    assert norm.normalize_phone("2024561111") == "+12024561111"
    # Test custom standard E.164 formats
    assert norm.normalize_phone("+91 98765 43210") == "+919876543210"
    assert norm.normalize_phone("00919876543210") == "+919876543210"
    assert norm.normalize_phone("(555) 123-4567") == "+15551234567"
    assert norm.normalize_phone(None) is None

def test_normalize_date():
    norm = CandidateNormalizer()
    # Relative values map to None
    assert norm.normalize_date("Present") is None
    assert norm.normalize_date("current") is None
    # YYYY-MM formats
    assert norm.normalize_date("2020-05") == "2020-05"
    assert norm.normalize_date("05/2018") == "2018-05"
    assert norm.normalize_date("5/2018") == "2018-05"
    # Textual format
    assert norm.normalize_date("Jan 2020") == "2020-01"
    assert norm.normalize_date("December 2023") == "2023-12"
    # Year only
    assert norm.normalize_date("2015") == "2015-01"
    assert norm.normalize_date(None) is None

def test_normalize_country():
    norm = CandidateNormalizer()
    assert norm.normalize_country("United States") == "US"
    assert norm.normalize_country("usa") == "US"
    assert norm.normalize_country("India") == "IN"
    assert norm.normalize_country("germany") == "DE"
    assert norm.normalize_country(None) is None

def test_normalize_skill():
    norm = CandidateNormalizer()
    assert norm.normalize_skill("js") == "JavaScript"
    assert norm.normalize_skill("python3") == "Python"
    assert norm.normalize_skill("docker-compose") == "Docker"
    assert norm.normalize_skill("unknown_skill") == "unknown_skill"

def test_normalize_url():
    norm = CandidateNormalizer()
    assert norm.normalize_url("linkedin.com/in/user?ref=tracker") == "https://linkedin.com/in/user"
    assert norm.normalize_url("http://github.com/user") == "http://github.com/user"
    assert norm.normalize_url("portfolio.io") == "https://portfolio.io"
    assert norm.normalize_url(None) is None
