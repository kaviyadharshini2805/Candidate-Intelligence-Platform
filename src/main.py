import argparse
import json
import os
import sys
from typing import List, Dict, Any

# Adjust path to enable absolute imports from parent directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.adapters.base import BaseInputAdapter, ADAPTER_REGISTRY
# Import adapters package to trigger registration decorators
import src.adapters
from src.parser import StructuredParser, TextParser, BaseParser
from src.normalizers import CandidateNormalizer
from src.identity import IdentityResolver
from src.merge import MergeEngine
from src.projection import ProjectionEngine
from src.models.canonical import InternalCandidate

def get_adapter_and_parser(filepath: str) -> tuple[BaseInputAdapter, BaseParser]:
    """
    Factory function mapping file extensions dynamically via the pluggable ADAPTER_REGISTRY.
    """
    _, ext = os.path.splitext(filepath.lower())
    
    if ext not in ADAPTER_REGISTRY:
        supported_exts = ", ".join(ADAPTER_REGISTRY.keys()).upper()
        raise ValueError(f"Unsupported file format: {ext}. Supported: {supported_exts}")
        
    adapter_class, parser_name = ADAPTER_REGISTRY[ext]
    
    # Resolve parser name to concrete parser instance
    if parser_name == "structured":
        parser = StructuredParser()
    elif parser_name == "text":
        parser = TextParser()
    elif parser_name == "json":
        from src.parser.json_parser import JSONParser
        parser = JSONParser()
    else:
        raise ValueError(f"Unknown parser type: {parser_name}")
        
    return adapter_class(filepath), parser

def run_pipeline(input_files: List[str], config_path: str) -> List[Dict[str, Any]]:
    """
    Orchestrates the ingestion, parsing, normalization, resolution, merging,
    and projection phases.
    """
    # 1. Initialize core pipeline services
    normalizer = CandidateNormalizer()
    identity_resolver = IdentityResolver()
    merge_engine = MergeEngine()
    projection_engine = ProjectionEngine(normalizer)

    # Load custom projection configuration
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    # 2. Ingest, Parse and Normalize each input source
    internal_records: List[InternalCandidate] = []
    
    for file in input_files:
        if not os.path.exists(file):
            print(f"Warning: File {file} does not exist. Skipping.")
            continue
            
        try:
            adapter, parser = get_adapter_and_parser(file)
            
            # Step A: Ingest (Read)
            raw_payload = adapter.read()
            
            # Step B: Extract/Parse
            raw_data = parser.parse(raw_payload)
            
            # Step C: Normalize & Map to rich InternalCandidate
            internal_candidate = normalizer.normalize_to_internal(raw_data, raw_payload)
            internal_records.append(internal_candidate)
            print(f"Ingested and parsed '{file}' successfully.")
            
        except Exception as e:
            print(f"Error processing file '{file}': {e}. Skipping.", file=sys.stderr)

    if not internal_records:
        print("No candidates were successfully ingested.", file=sys.stderr)
        return []

    # 3. Identity Resolution (Match keys to group candidates)
    # Map matched candidates to lists
    grouped_candidates: Dict[str, List[InternalCandidate]] = {}
    
    for candidate in internal_records:
        # Check against already grouped golden record IDs
        existing_list = [list_val[0] for list_val in grouped_candidates.values()]
        resolved_id = identity_resolver.resolve(candidate, existing_list)
        candidate.candidate_id = resolved_id
        
        # If resolved via fuzzy matching, tag incoming candidate fields
        if candidate.candidate_id in identity_resolver.resolved_metadata:
            meta = identity_resolver.resolved_metadata[candidate.candidate_id]
            if candidate.full_name:
                candidate.full_name.provenance.match_type = meta["match_type"]
                candidate.full_name.provenance.match_confidence = meta["confidence_score"]
                candidate.full_name.provenance.decision_reason = (
                    f"Fuzzy resolution match with existing candidate {meta['matched_with_name']} "
                    f"({meta['status']} score: {meta['confidence_score']})"
                )
        
        if resolved_id not in grouped_candidates:
            grouped_candidates[resolved_id] = []
        grouped_candidates[resolved_id].append(candidate)

    # 4. Merge Engine (Conflict Resolution)
    golden_records: List[InternalCandidate] = []
    for candidate_id, records in grouped_candidates.items():
        if len(records) == 1:
            golden_records.append(records[0])
            print(f"Candidate {candidate_id} has single source record. No merge needed.")
        else:
            # Sequentially merge multiple records for the same candidate
            base_record = records[0]
            for next_record in records[1:]:
                base_record = merge_engine.merge(base_record, next_record)
            golden_records.append(base_record)
            print(f"Merged {len(records)} records for Candidate {candidate_id} into Golden Record.")

    # 5. Projection & Validation
    output_profiles = []
    for golden_internal in golden_records:
        # A: Convert rich internal representation to validated Canonical model
        canonical_candidate = golden_internal.to_canonical()
        
        # B: Project to custom format using configuration rules
        projected_profile = projection_engine.project(canonical_candidate, config)
        output_profiles.append(projected_profile)

    return output_profiles

def main():
    parser = argparse.ArgumentParser(
        description="Eightfold Multi-Source Candidate Data Transformer Ingestion CLI"
    )
    parser.add_argument(
        "--inputs", "-i",
        nargs="+",
        required=True,
        help="Paths to structured (CSV, JSON) and unstructured (PDF, DOCX, TXT) candidate source files."
    )
    parser.add_argument(
        "--config", "-c",
        required=True,
        help="Path to JSON configuration specifying the projection engine rules."
    )
    parser.add_argument(
        "--output", "-o",
        default="output_profile.json",
        help="Path to save the resulting projected JSON profiles."
    )

    args = parser.parse_args()

    try:
        results = run_pipeline(args.inputs, args.config)
        
        # Ensure output folder exists
        output_dir = os.path.dirname(args.output)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # Write results
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
            
        print(f"\nPipeline execution successful. Results written to: {args.output}")
        
    except Exception as e:
        print(f"Fatal error in pipeline: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
