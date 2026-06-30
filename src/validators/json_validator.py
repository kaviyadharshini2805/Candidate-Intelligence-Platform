import json
from typing import Tuple, Optional, Any

class JSONValidator:
    """
    Validator to check if a payload is valid JSON and handles malformed inputs.
    """
    @staticmethod
    def validate_string(json_str: str) -> Tuple[bool, Optional[str], Optional[Any]]:
        """
        Validates JSON string. Returns (is_valid, error_message, parsed_data).
        """
        try:
            data = json.loads(json_str)
            return True, None, data
        except json.JSONDecodeError as e:
            return False, f"Invalid JSON syntax: {e.msg} at line {e.lineno} col {e.colno}", None
        except Exception as e:
            return False, f"Parsing error: {str(e)}", None

    @staticmethod
    def validate_file(filepath: str) -> Tuple[bool, Optional[str], Optional[Any]]:
        """
        Validates JSON file. Returns (is_valid, error_message, parsed_data).
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return True, None, data
        except json.JSONDecodeError as e:
            return False, f"Invalid JSON syntax in file: {e.msg} at line {e.lineno} col {e.colno}", None
        except Exception as e:
            return False, f"Failed to read file: {str(e)}", None
