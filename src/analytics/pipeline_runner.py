"""
PipelineRunner — single orchestration point for the full candidate pipeline.

Replaces the inline Streamlit orchestration code with a cleanly tested,
decoupled class that:
  - Accepts source descriptors (file bytes + metadata)
  - Runs every pipeline stage with millisecond timing
  - Uses InstrumentedMergeEngine to capture conflict metadata
  - Builds per-source SourceDiagnostic reports
  - Returns a rich PipelineResult dataclass

No Streamlit imports. No UI logic. Fully testable in isolation.
"""
import os
import time
import tempfile
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple

from pydantic import ValidationError

from src.adapters.base import RawPayload
from src.adapters.csv_adapter import CSVAdapter
from src.adapters.json_adapter import JSONAdapter
from src.normalizers.normalizer import CandidateNormalizer
from src.parser.structured_parser import StructuredParser
from src.parser.text_parser import TextParser
from src.identity.resolver import IdentityResolver
from src.projection.engine import ProjectionEngine
from src.models.canonical import (
    CanonicalCandidate, InternalCandidate, ConflictRecord, SourceDiagnostic
)
from src.analytics.conflict_tracker import InstrumentedMergeEngine
from src.analytics.decision_explainer import DecisionExplainer, FieldExplanation
from src.analytics.quality_analyzer import DataQualityAnalyzer, QualityReport
from src.utils import logger


@dataclass
class SourceInput:
    """Descriptor for a single input source."""
    name: str           # display name / filename
    content_type: str   # 'csv' | 'json' | 'txt' | 'pdf' | 'docx'
    raw_bytes: Optional[bytes] = None   # file content
    text: Optional[str] = None          # plain text (for recruiter notes)


@dataclass
class TimelineStage:
    """A single stage in the merge timeline."""
    stage: str
    status: str      # 'ok' | 'skipped' | 'error'
    duration_ms: float
    detail: Optional[str] = None


@dataclass
class PipelineStats:
    files_processed: int = 0
    records_parsed: int = 0
    fields_compared: int = 0
    fields_merged: int = 0
    conflicts_detected: int = 0
    duplicates_removed: int = 0
    validation_rules_executed: int = 0
    overall_runtime_ms: float = 0.0
    adapter_runtime_ms: float = 0.0
    parser_runtime_ms: float = 0.0
    normalizer_runtime_ms: float = 0.0
    identity_runtime_ms: float = 0.0
    merge_runtime_ms: float = 0.0
    validation_runtime_ms: float = 0.0
    projection_runtime_ms: float = 0.0


@dataclass
class PipelineResult:
    canonical: Optional[CanonicalCandidate]
    conflict_report: List[ConflictRecord]
    decision_explanations: List[FieldExplanation]
    quality_report: Optional[QualityReport]
    parse_diagnostics: List[SourceDiagnostic]
    merge_timeline: List[TimelineStage]
    pipeline_stats: PipelineStats
    validation_errors: List[str] = field(default_factory=list)
    error: Optional[str] = None


def _ms(start: float) -> float:
    return round((time.perf_counter() - start) * 1000, 2)


def _build_diagnostic(
    source_name: str,
    content_type: str,
    raw_data: Dict[str, Any],
    parse_time_ms: float,
    confidence: float,
    error: Optional[str] = None,
) -> SourceDiagnostic:
    """Build a SourceDiagnostic from raw parser output."""
    all_sections = ["name", "emails", "phones", "skills", "experience", "education", "links", "headline"]
    present = []
    missing = []

    def _has(key):
        val = raw_data.get(key)
        if isinstance(val, list):
            return bool(val)
        if isinstance(val, dict):
            return any(v for v in val.values())
        return val is not None and val != ""

    for sec in all_sections:
        if _has(sec):
            present.append(sec)
        else:
            missing.append(sec)

    links = raw_data.get("links") or {}
    links_found = sum(1 for v in links.values() if v)

    return SourceDiagnostic(
        source_name=source_name,
        content_type=content_type,
        parse_time_ms=parse_time_ms,
        emails_found=len(raw_data.get("emails") or []),
        phones_found=len(raw_data.get("phones") or []),
        skills_found=len(raw_data.get("skills") or []),
        experience_count=len(raw_data.get("experience") or []),
        education_count=len(raw_data.get("education") or []),
        links_found=links_found,
        has_name=bool(raw_data.get("full_name")),
        has_headline=bool(raw_data.get("headline")),
        sections_found=present,
        sections_missing=missing,
        parser_confidence=confidence,
        error=error,
    )


class PipelineRunner:
    """
    Orchestrates the complete candidate pipeline with instrumentation.

    Dependency injection pattern:
      - All services are created internally by default.
      - Override any service by passing it to the constructor.

    Usage:
        runner = PipelineRunner(source_priorities={...})
        result = runner.run(sources=[...], projection_config={...})
    """

    # Maps content_type → the canonical key suffix used in the priorities dict.
    # Used as a fallback when an exact filename is not present in the dict.
    _TYPE_SUFFIX: Dict[str, str] = {
        "csv":  ".csv",
        "json": ".json",
        "txt":  ".txt",
        "pdf":  ".pdf",
        "docx": ".docx",
    }

    def __init__(
        self,
        source_priorities: Optional[Dict[str, int]] = None,
        normalizer: Optional[CandidateNormalizer] = None,
        identity_resolver: Optional[IdentityResolver] = None,
        projection_engine: Optional[ProjectionEngine] = None,
        quality_analyzer: Optional[DataQualityAnalyzer] = None,
    ):
        # Template priorities — keyed by canonical names OR actual filenames.
        self._priorities = source_priorities or {
            "recruiter_notes.txt": 30,
            "ats_profile.json": 20,
            "recruiter_export.csv": 20,
            "resume.docx": 10,
            "resume.pdf": 10,
        }
        self._normalizer        = normalizer or CandidateNormalizer()
        self._identity_resolver = identity_resolver or IdentityResolver()
        self._projection_engine = projection_engine or ProjectionEngine(self._normalizer)
        self._quality_analyzer  = quality_analyzer or DataQualityAnalyzer()

    def _build_effective_priorities(self, sources: List[SourceInput]) -> Dict[str, int]:
        """
        Construct a priority dict that always contains an entry for every
        actual source filename that will appear in ProvenanceMetadata.

        Resolution order for each source:
          1. Exact filename match in self._priorities          (user already keyed by filename)
          2. Extension-based match against self._priorities keys  (fallback for template keys)
          3. Default priority 10
        """
        effective = dict(self._priorities)  # start with whatever the caller provided

        for src in sources:
            if src.name in effective:
                continue  # exact match already present — nothing to do

            # Find the priority by matching the file extension against existing keys
            ext = self._TYPE_SUFFIX.get(src.content_type, "")  # e.g. ".pdf"
            matched_priority = 10  # default
            for key, prio in self._priorities.items():
                if key.endswith(ext):
                    matched_priority = prio
                    break

            effective[src.name] = matched_priority

        return effective

    # ── Public API ──────────────────────────────────────────────────────────

    def run(
        self,
        sources: List[SourceInput],
        projection_config: Optional[Dict[str, Any]] = None,
    ) -> PipelineResult:
        overall_start = time.perf_counter()
        timeline: List[TimelineStage] = []
        stats = PipelineStats()
        diagnostics: List[SourceDiagnostic] = []
        internal_candidates: List[InternalCandidate] = []
        tmp_files: List[str] = []

        logger.log_event("pipeline", "Starting pipeline run", {"sources": [s.name for s in sources]})

        # Build a priority dict that maps every actual source filename to its
        # user-configured priority weight, resolving by extension when the
        # exact filename is not present.
        effective_priorities = self._build_effective_priorities(sources)
        logger.log_event("pipeline", "Effective priorities", effective_priorities)

        # ── Stage 1: Adapter + Parser + Normalizer per source ────────────────
        try:
            with open("debug_uploads/did_run.txt", "w") as f:
                f.write("PipelineRunner.run() executed!")
        except Exception:
            pass

        for src in sources:
            stage_start = time.perf_counter()
            try:
                internal, diag = self._ingest_source(src, tmp_files)
                diagnostics.append(diag)
                if internal:
                    internal_candidates.append(internal)
                    stats.records_parsed += 1
                    stats.files_processed += 1
                    timeline.append(TimelineStage(
                        stage=f"Parse: {src.name}",
                        status="ok",
                        duration_ms=_ms(stage_start),
                        detail=f"{diag.emails_found} emails, {diag.phones_found} phones, {diag.skills_found} skills",
                    ))
                else:
                    timeline.append(TimelineStage(
                        stage=f"Parse: {src.name}",
                        status="skipped" if not diag.error else "error",
                        duration_ms=_ms(stage_start),
                        detail=diag.error,
                    ))
            except Exception as exc:
                logger.log_error("ingest", exc)
                timeline.append(TimelineStage(
                    stage=f"Parse: {src.name}",
                    status="error",
                    duration_ms=_ms(stage_start),
                    detail=str(exc),
                ))
                diagnostics.append(SourceDiagnostic(
                    source_name=src.name,
                    content_type=src.content_type,
                    parse_time_ms=_ms(stage_start),
                    error=str(exc),
                ))
            finally:
                for path in tmp_files:
                    try:
                        os.remove(path)
                    except OSError:
                        pass
                tmp_files.clear()

        stats.adapter_runtime_ms = sum(t.duration_ms for t in timeline)
        stats.parser_runtime_ms = stats.adapter_runtime_ms

        if not internal_candidates:
            return PipelineResult(
                canonical=None,
                conflict_report=[],
                decision_explanations=[],
                quality_report=None,
                parse_diagnostics=diagnostics,
                merge_timeline=timeline,
                pipeline_stats=stats,
                error="No valid candidate records could be ingested from the provided sources.",
            )

        # ── Stage 2: Identity Resolution ─────────────────────────────────────
        id_start = time.perf_counter()
        try:
            grouped: Dict[str, List[InternalCandidate]] = {}
            for cand in internal_candidates:
                existing_list = [v[0] for v in grouped.values()]
                resolved_id = self._identity_resolver.resolve(cand, existing_list)
                cand.candidate_id = resolved_id
                grouped.setdefault(resolved_id, []).append(cand)

            deduped = len(internal_candidates) - len(grouped)
            stats.duplicates_removed = max(0, deduped)
            stats.identity_runtime_ms = _ms(id_start)
            timeline.append(TimelineStage(
                stage="Identity Resolution",
                status="ok",
                duration_ms=stats.identity_runtime_ms,
                detail=f"{len(grouped)} unique candidate(s), {stats.duplicates_removed} duplicate(s) merged",
            ))
            logger.log_event("identity", f"Resolved {len(grouped)} unique identities")
        except Exception as exc:
            logger.log_error("identity", exc)
            timeline.append(TimelineStage(
                stage="Identity Resolution",
                status="error",
                duration_ms=_ms(id_start),
                detail=str(exc),
            ))
            return PipelineResult(
                canonical=None,
                conflict_report=[],
                decision_explanations=[],
                quality_report=None,
                parse_diagnostics=diagnostics,
                merge_timeline=timeline,
                pipeline_stats=stats,
                error=f"Identity resolution failed: {exc}",
            )

        # ── Stage 3: Instrumented Merge ───────────────────────────────────────
        merge_start = time.perf_counter()
        # Use effective_priorities so every actual filename has an explicit entry.
        merge_engine = InstrumentedMergeEngine(source_priorities=effective_priorities)
        final_internal: Optional[InternalCandidate] = None

        try:
            golden_records: List[Tuple[InternalCandidate, int]] = []
            for cid, records in grouped.items():
                # Gather all source names that contributed to this candidate record
                cand_sources = []
                for rec in records:
                    def add_pv(pv):
                        if pv and pv.provenance and pv.provenance.source:
                            cand_sources.append(pv.provenance.source)
                    
                    if rec.full_name: add_pv(rec.full_name)
                    if rec.headline: add_pv(rec.headline)
                    if rec.years_experience: add_pv(rec.years_experience)
                    if rec.city: add_pv(rec.city)
                    if rec.region: add_pv(rec.region)
                    if rec.country: add_pv(rec.country)
                    if rec.linkedin: add_pv(rec.linkedin)
                    if rec.github: add_pv(rec.github)
                    if rec.portfolio: add_pv(rec.portfolio)
                    for x in rec.emails: add_pv(x)
                    for x in rec.phones: add_pv(x)
                    for x in rec.other_links: add_pv(x)
                    for x in rec.skills: add_pv(x)
                    for x in rec.experience:
                        add_pv(x.company)
                        add_pv(x.title)
                        if x.start: add_pv(x.start)
                        if x.end: add_pv(x.end)
                        if x.summary: add_pv(x.summary)
                    for x in rec.education:
                        add_pv(x.institution)
                        if x.degree: add_pv(x.degree)
                        if x.field: add_pv(x.field)
                        if x.end_year: add_pv(x.end_year)
                
                cand_sources = list(set(cand_sources))
                max_prio = max((effective_priorities.get(s, 10) for s in cand_sources), default=10)

                base = records[0]
                fields_before = self._count_fields(base)
                for nxt in records[1:]:
                    base = merge_engine.merge(base, nxt)
                fields_after = self._count_fields(base)
                stats.fields_compared += fields_after
                stats.fields_merged += fields_after
                golden_records.append((base, max_prio))

            # Select the candidate representing the highest source priority
            golden_records.sort(key=lambda x: x[1], reverse=True)
            final_internal = golden_records[0][0]
            conflict_report = merge_engine.get_conflicts()
            stats.conflicts_detected = len(conflict_report)
            stats.merge_runtime_ms = _ms(merge_start)

            timeline.append(TimelineStage(
                stage="Field Merge",
                status="ok",
                duration_ms=stats.merge_runtime_ms,
                detail=f"{stats.conflicts_detected} conflict(s) detected, {stats.fields_merged} fields merged",
            ))
            logger.log_event("merge", f"{stats.conflicts_detected} conflicts detected")
        except Exception as exc:
            logger.log_error("merge", exc)
            timeline.append(TimelineStage(
                stage="Field Merge",
                status="error",
                duration_ms=_ms(merge_start),
                detail=str(exc),
            ))
            return PipelineResult(
                canonical=None,
                conflict_report=[],
                decision_explanations=[],
                quality_report=None,
                parse_diagnostics=diagnostics,
                merge_timeline=timeline,
                pipeline_stats=stats,
                error=f"Merge failed: {exc}",
            )

        # ── Stage 4: Validation → Canonical ──────────────────────────────────
        val_start = time.perf_counter()
        canonical: Optional[CanonicalCandidate] = None
        validation_errors: List[str] = []

        try:
            canonical = final_internal.to_canonical()
            canonical.merge_conflicts = conflict_report
            canonical.parse_diagnostics = diagnostics
            stats.validation_rules_executed = 5   # known rules in to_canonical()
            stats.validation_runtime_ms = _ms(val_start)

            timeline.append(TimelineStage(
                stage="Validation",
                status="ok",
                duration_ms=stats.validation_runtime_ms,
                detail=f"{len(canonical.validation_warnings)} warning(s)",
            ))
            logger.log_stage("validation", canonical)
        except ValidationError as ve:
            stats.validation_runtime_ms = _ms(val_start)
            validation_errors = [
                "->".join(str(x) for x in err["loc"]) + ": " + err["msg"]
                for err in ve.errors()
            ]
            timeline.append(TimelineStage(
                stage="Validation",
                status="error",
                duration_ms=stats.validation_runtime_ms,
                detail=f"{len(validation_errors)} validation error(s)",
            ))
            return PipelineResult(
                canonical=None,
                conflict_report=conflict_report,
                decision_explanations=[],
                quality_report=None,
                parse_diagnostics=diagnostics,
                merge_timeline=timeline,
                pipeline_stats=stats,
                validation_errors=validation_errors,
            )

        # ── Stage 5: Analytics — Decision Explanations ─────────────────────
        explainer   = DecisionExplainer(source_priorities=self._priorities)
        explanations = explainer.explain(final_internal)

        # ── Stage 6: Analytics — Quality Report ────────────────────────────
        quality_report = self._quality_analyzer.analyze(canonical)

        # ── Stage 7: Projection ────────────────────────────────────────────
        proj_start = time.perf_counter()
        if projection_config:
            try:
                self._projection_engine.project(canonical, projection_config)
                stats.projection_runtime_ms = _ms(proj_start)
                timeline.append(TimelineStage(
                    stage="Projection",
                    status="ok",
                    duration_ms=stats.projection_runtime_ms,
                    detail=f"{len(projection_config.get('fields', []))} fields projected",
                ))
            except Exception as exc:
                stats.projection_runtime_ms = _ms(proj_start)
                timeline.append(TimelineStage(
                    stage="Projection",
                    status="error",
                    duration_ms=_ms(proj_start),
                    detail=str(exc),
                ))
        else:
            timeline.append(TimelineStage(
                stage="Projection",
                status="skipped",
                duration_ms=0.0,
                detail="No projection config provided",
            ))

        # ── Golden Record ───────────────────────────────────────────────────
        timeline.append(TimelineStage(
            stage="Golden Record",
            status="ok",
            duration_ms=0.0,
            detail=f"Candidate: {canonical.full_name}",
        ))

        # ── Persist outputs ─────────────────────────────────────────────────
        try:
            import json
            os.makedirs("output", exist_ok=True)
            with open("output/candidate_default.json", "w", encoding="utf-8") as fh:
                json.dump([canonical.model_dump()], fh, indent=2, ensure_ascii=False)
            if projection_config:
                proj_out = self._projection_engine.project(canonical, projection_config)
                with open("output/candidate_projected.json", "w", encoding="utf-8") as fh:
                    json.dump(proj_out, fh, indent=2, ensure_ascii=False)
        except Exception:
            pass

        stats.overall_runtime_ms = _ms(overall_start)
        logger.log_event("pipeline", "Pipeline complete", {"runtime_ms": stats.overall_runtime_ms})

        return PipelineResult(
            canonical=canonical,
            conflict_report=conflict_report,
            decision_explanations=explanations,
            quality_report=quality_report,
            parse_diagnostics=diagnostics,
            merge_timeline=timeline,
            pipeline_stats=stats,
            validation_errors=[],
        )

    # ── Private helpers ──────────────────────────────────────────────────────

    def _ingest_source(
        self,
        src: SourceInput,
        tmp_files: List[str],
    ) -> Tuple[Optional[InternalCandidate], SourceDiagnostic]:
        """Ingest a single source through adapter → parser → normalizer."""
        t_start = time.perf_counter()

        if src.content_type == "txt":
            # In-memory text — no file needed
            payload = RawPayload(source_name=src.name, content_type="txt", content=src.text or "")
            raw_data = TextParser().parse(payload)
            conf = raw_data.get("confidence", 0.6)
            internal = self._normalizer.normalize_to_internal(raw_data, payload)
            diag = _build_diagnostic(src.name, "txt", raw_data, _ms(t_start), conf)
            return internal, diag

        # File-based sources — write to temp file
        suffix = f".{src.content_type}"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(src.raw_bytes or b"")
            tmp_path = tmp.name
        tmp_files.append(tmp_path)
        
        try:
            with open(f"debug_uploads/{src.name}", "wb") as f:
                f.write(src.raw_bytes or b"")
        except Exception:
            pass

        if src.content_type == "csv":
            adapter = CSVAdapter(tmp_path)
            payload = adapter.read()
            payload.source_name = src.name
            raw_data = StructuredParser().parse(payload)
        elif src.content_type == "json":
            adapter = JSONAdapter(tmp_path)
            payload = adapter.read()
            payload.source_name = src.name
            raw_data = StructuredParser().parse(payload)
        elif src.content_type == "pdf":
            from src.adapters.pdf_adapter import PDFAdapter
            adapter = PDFAdapter(tmp_path)
            payload = adapter.read()
            payload.source_name = src.name
            raw_data = TextParser().parse(payload)
        elif src.content_type == "docx":
            from src.adapters.docx_adapter import DocxAdapter
            adapter = DocxAdapter(tmp_path)
            payload = adapter.read()
            payload.source_name = src.name
            raw_data = TextParser().parse(payload)
        else:
            raise ValueError(f"Unsupported content type: {src.content_type}")

        conf = raw_data.get("confidence", 0.6)
        internal = self._normalizer.normalize_to_internal(raw_data, payload)
        diag = _build_diagnostic(src.name, src.content_type, raw_data, _ms(t_start), conf)
        return internal, diag

    @staticmethod
    def _count_fields(candidate: InternalCandidate) -> int:
        count = 0
        for attr in ["full_name", "headline", "years_experience", "city", "region",
                      "country", "linkedin", "github", "portfolio"]:
            if getattr(candidate, attr):
                count += 1
        count += len(candidate.emails) + len(candidate.phones) + len(candidate.skills)
        count += len(candidate.experience) + len(candidate.education)
        return count
