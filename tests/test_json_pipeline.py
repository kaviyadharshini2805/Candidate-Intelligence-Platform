import os
import pytest
from src.validators.json_validator import JSONValidator
from src.parser.json_parser import JSONParser
from src.adapters.json_adapter import JSONAdapter
from src.adapters.base import RawPayload
from src.normalizers.normalizer import CandidateNormalizer

def test_json_validator():
    valid_json = '{"profile": {"name": "Kavi", "email": "kavi@gmail.com"}}'
    is_valid, err, data = JSONValidator.validate_string(valid_json)
    assert is_valid
    assert err is None
    assert data["profile"]["name"] == "Kavi"

    malformed_json = '{"profile": {"name": "Kavi", "email": "kavi@gmail.com"'
    is_valid, err, data = JSONValidator.validate_string(malformed_json)
    assert not is_valid
    assert "Invalid JSON syntax" in err
    assert data is None

def test_json_parser_nested_and_arrays():
    parser = JSONParser()
    json_data = {
        "profile": {
            "name": "Jane Doe",
            "emails": ["jane.doe@example.com"],
            "location": {
                "city": "San Francisco",
                "region": "California",
                "country": "US"
            },
            "skills": [
                "Python",
                {"name": "FastAPI"}
            ],
            "experience": [
                {
                    "company": "Stripe",
                    "title": "Software Engineer",
                    "summary": "Backend developer."
                }
            ]
        }
    }
    payload = RawPayload(content=json_data, content_type="json", source_name="ats_profile.json")
    parsed = parser.parse(payload)
    
    assert parsed["full_name"] == "Jane Doe"
    assert parsed["emails"] == ["jane.doe@example.com"]
    assert parsed["location"] == ["San Francisco", "California", "US"]
    assert parsed["skills"] == ["Python", "FastAPI"]
    assert len(parsed["experience"]) == 1
    assert parsed["experience"][0]["company"] == "Stripe"

def test_json_adapter_flow(tmp_path):
    json_file = tmp_path / "valid.json"
    json_file.write_text('{"name": "Alex"}', encoding="utf-8")
    
    adapter = JSONAdapter(str(json_file))
    payload = adapter.read()
    assert payload.content_type == "json"
    assert payload.content["name"] == "Alex"

    invalid_file = tmp_path / "invalid.json"
    invalid_file.write_text('{"name": "Alex"', encoding="utf-8")
    
    invalid_adapter = JSONAdapter(str(invalid_file))
    with pytest.raises(ValueError) as exc:
        invalid_adapter.read()
    assert "Malformed JSON" in str(exc.value)
