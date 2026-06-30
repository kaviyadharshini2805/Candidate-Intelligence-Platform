import re
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from src.models.canonical import CanonicalCandidate
from src.normalizers.normalizer import CandidateNormalizer

class ProjectionEngine:
    """
    Runtime-configurable Projection Engine.
    Transforms a CanonicalCandidate object into a customized output dictionary
    based on a JSON configuration file.
    """
    def __init__(self, normalizer: Optional[CandidateNormalizer] = None):
        self.normalizer = normalizer or CandidateNormalizer()

    def _evaluate_path(self, candidate: CanonicalCandidate, path: str) -> Any:
        """
        Evaluates dot-notation and list-indexing paths on CanonicalCandidate.
        Supports:
          - 'full_name'
          - 'emails[0]'
          - 'location[0]'
          - 'links.linkedin'
          - 'skills[].name'
          - 'experience[0].company'
        """
        parts = path.split('.')
        current: Any = candidate

        for idx, part in enumerate(parts):
            # Check for list indexing, e.g., 'emails[0]' or 'skills[]'
            list_match = re.match(r'([a-zA-Z0-9_-]+)\[(\d*)\]', part)
            if list_match:
                field_name = list_match.group(1)
                index_str = list_match.group(2)
                
                # Fetch field from object
                if hasattr(current, field_name):
                    current = getattr(current, field_name)
                elif isinstance(current, dict) and field_name in current:
                    current = current[field_name]
                else:
                    return None
                    
                # Handle empty bracket '[]' (map remaining path over list)
                if index_str == "":
                    if not isinstance(current, list):
                        return None
                    # We need to map the remaining path over all elements in the list
                    remaining_path = ".".join(parts[idx+1:])
                    if not remaining_path:
                        return current
                    # If remaining path exists, map it
                    result_list = []
                    for item in current:
                        # Recursively evaluate remaining path on list item
                        val = self._evaluate_subpath(item, remaining_path)
                        if val is not None:
                            result_list.append(val)
                    return result_list
                else:
                    # Specific index, e.g. '[0]'
                    index = int(index_str)
                    if isinstance(current, list) and index < len(current):
                        current = current[index]
                    else:
                        return None
            else:
                # Standard attribute
                if hasattr(current, part):
                    current = getattr(current, part)
                elif isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    return None
                    
        return current

    def _evaluate_subpath(self, obj: Any, path: str) -> Any:
        """
        Helper to evaluate paths on nested objects (like WorkHistoryItem or SkillItem).
        """
        parts = path.split('.')
        current = obj
        for part in parts:
            if hasattr(current, part):
                current = getattr(current, part)
            elif isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        return current

    def _apply_normalization(self, value: Any, norm_type: str) -> Any:
        if value is None:
            return None
            
        if norm_type == "E164":
            return self.normalizer.normalize_phone(str(value))
        elif norm_type == "canonical":
            if isinstance(value, list):
                return [self.normalizer.normalize_skill(str(v)) for v in value]
            return self.normalizer.normalize_skill(str(value))
        elif norm_type == "lowercase":
            if isinstance(value, list):
                return [str(v).lower() for v in value]
            return str(value).lower()
        elif norm_type == "anonymize":
            # Redact names to initials, skills to redacted placeholder
            if isinstance(value, str):
                # If name: John Doe -> J. D.
                words = value.split()
                if len(words) >= 2:
                    return " ".join([f"{w[0]}." for w in words])
                return "C. A."  # Candidate Anonymized
            elif isinstance(value, list):
                # Anonymize skills list
                return ["[Redacted Skill]" for _ in value]
        return value

    def _to_serializable(self, val: Any) -> Any:
        if isinstance(val, BaseModel):
            return val.model_dump()
        elif isinstance(val, list):
            return [self._to_serializable(v) for v in val]
        elif isinstance(val, dict):
            return {k: self._to_serializable(v) for k, v in val.items()}
        return val

    def _enforce_type(self, value: Any, target_type: str) -> Any:
        if value is None:
            return None
            
        if target_type == "string":
            if isinstance(value, list):
                str_vals = []
                for v in value:
                    if isinstance(v, dict):
                        str_vals.append(str(list(v.values())[0]) if v.values() else "")
                    else:
                        str_vals.append(str(v))
                return ", ".join(filter(None, str_vals))
            return str(value)
            
        elif target_type == "string[]":
            if not isinstance(value, list):
                return [str(value)]
            return [str(v) for v in value]
            
        elif target_type == "number":
            if isinstance(value, list):
                value = value[0] if value else None
            if value is None:
                return None
            try:
                val_str = str(value)
                return float(val_str) if '.' in val_str else int(val_str)
            except ValueError:
                return None
                
        elif target_type == "number[]":
            if not isinstance(value, list):
                value = [value]
            result = []
            for v in value:
                try:
                    val_str = str(v)
                    num = float(val_str) if '.' in val_str else int(val_str)
                    result.append(num)
                except ValueError:
                    continue
            return result
            
        elif target_type == "boolean":
            if isinstance(value, list):
                value = value[0] if value else False
            if isinstance(value, str):
                return value.lower() in ("true", "1", "yes", "y")
            return bool(value)
            
        return value

    def project(self, candidate: CanonicalCandidate, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Projects CanonicalCandidate into output dict using the config rules.
        """
        output: Dict[str, Any] = {}
        fields_config = config.get("fields", [])
        on_missing = config.get("on_missing", "null")
        include_confidence = config.get("include_confidence", True)

        seen_paths = set()

        for field_rule in fields_config:
            target_path = field_rule.get("path")
            if not target_path:
                continue

            # Check self-conflict
            if target_path in seen_paths:
                raise ValueError(f"Self-conflicting config: target path '{target_path}' is mapped multiple times!")
            seen_paths.add(target_path)

            source_path = field_rule.get("from") or target_path
            is_required = field_rule.get("required", False)
            norm_type = field_rule.get("normalize")
            target_type = field_rule.get("type")

            # Extract value from canonical model
            raw_value = self._evaluate_path(candidate, source_path)

            # Apply custom output-time normalization if specified
            if norm_type:
                value = self._apply_normalization(raw_value, norm_type)
            else:
                value = raw_value

            # Enforce target type if specified
            if target_type:
                value = self._enforce_type(value, target_type)

            # Handle missing values
            if value is None or (isinstance(value, list) and not value):
                if is_required:
                    if on_missing == "error":
                        raise ValueError(f"Required projected field '{target_path}' (from '{source_path}') is missing!")
                    elif on_missing == "omit":
                        continue
                    else:  # 'null'
                        output[target_path] = None
                else:
                    if on_missing == "omit":
                        continue
                    else:
                        output[target_path] = None
            else:
                output[target_path] = self._to_serializable(value)

        # Inject overall confidence and provenance if requested
        if include_confidence:
            output["overall_confidence"] = candidate.overall_confidence
            # Map provenance for projected fields
            projected_provenance = []
            for item in candidate.provenance:
                # Keep provenance record if its field matches a projected source path
                for field_rule in fields_config:
                    target_path = field_rule.get("path")
                    source_path = field_rule.get("from") or target_path
                    if item.field in source_path:
                        prov_dict = item.model_dump()
                        prov_dict["field"] = target_path # Map to renamed target path
                        projected_provenance.append(prov_dict)
                        break
            output["provenance"] = projected_provenance

        return output
