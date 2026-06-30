"""
Streamlit UI — Eightfold Multi-Source Candidate Intelligence Platform.

Architecture contract:
  - All business logic lives in src/analytics/pipeline_runner.py
  - This file contains ONLY rendering logic
  - No pipeline calls outside of _run_pipeline()
  - No imports of pipeline internals (adapters, parsers, etc.)
"""
import streamlit as st
import json
import os
import pandas as pd
from datetime import datetime
from typing import Optional

from src.analytics.pipeline_runner import PipelineRunner, SourceInput, PipelineResult
from src.analytics.quality_analyzer import QualityReport
from src.projection.engine import ProjectionEngine

# ── Page configuration ────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Candidate Intelligence Platform",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Session State ─────────────────────────────────────────────────────────────
if "result" not in st.session_state:
    st.session_state["result"] = None

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Pipeline Configuration")

    st.subheader("Source Priority Weights")
    st.caption("Higher value = higher authority when resolving field conflicts.")
    p_notes = st.slider("Recruiter Notes",         10, 50, 30)
    p_json  = st.slider("ATS JSON Profile",         10, 50, 20)
    p_csv   = st.slider("CSV Export",               10, 50, 20)
    p_file  = st.slider("Resume (PDF / DOCX)",       10, 50, 10)

    # These are the USER-CONFIGURED weights (slider values).
    # At button-click time we rebuild a runtime dict keyed by actual filenames.
    p_source_types = {
        "csv":  p_csv,
        "json": p_json,
        "txt":  p_notes,
        "pdf":  p_file,
        "docx": p_file,
    }

    st.divider()
    st.subheader("Field Visibility")
    st.caption("Choose which fields appear in the Golden Record output.")

    _ALL_FIELDS = [
        "candidate_id",
        "full_name",
        "emails",
        "phones",
        "location",
        "links",
        "headline",
        "years_experience",
        "skills",
        "experience",
        "education",
        "provenance",
        "overall_confidence",
    ]

    selected_fields = st.multiselect(
        "Fields to extract / display",
        options=_ALL_FIELDS,
        default=_ALL_FIELDS,
        help="Uncheck any field to hide it from the Golden Record output.",
    )

    st.divider()
    st.subheader("Output Projection Schema")
    st.caption("Runtime schema config — edits apply immediately to projected output.")
    _default_proj = {
        "fields": [
            {"path": "candidate_name", "from": "full_name",     "type": "string",   "required": True},
            {"path": "primary_email",  "from": "emails[0]",     "type": "string",   "required": True},
            {"path": "phone_e164",     "from": "phones[0]",     "type": "string",   "normalize": "E164"},
            {"path": "skills_list",    "from": "skills[].name", "type": "string[]", "normalize": "canonical"},
        ],
        "include_confidence": True,
        "on_missing": "null",
    }
    projection_config_str = st.text_area(
        "JSON Schema Config",
        value=json.dumps(_default_proj, indent=2),
        height=260,
    )

# ── Page Header ───────────────────────────────────────────────────────────────
st.title("Candidate Intelligence Platform")
st.caption("Multi-source ingestion, merge, and projection pipeline with full audit transparency.")
st.divider()

# ── Main Layout ───────────────────────────────────────────────────────────────
left, right = st.columns([1, 1], gap="large")

# ─────────────────────────── LEFT: INPUT ─────────────────────────────────────
with left:
    st.subheader("Input Sources")

    with st.expander("CSV Export File", expanded=True):
        uploaded_csv  = st.file_uploader("Upload ATS or recruiter CSV export", type=["csv"], key="up_csv")
        if uploaded_csv:
            st.success(f"Loaded: {uploaded_csv.name}")

    with st.expander("ATS JSON Profile", expanded=True):
        uploaded_json = st.file_uploader("Upload ATS candidate JSON profile",  type=["json"], key="up_json")
        if uploaded_json:
            st.success(f"Loaded: {uploaded_json.name}")

    with st.expander("Recruiter Notes (Unstructured Text)", expanded=True):
        notes_text = st.text_area(
            "Paste recruiter notes or resume text",
            value="",
            height=180,
            key="notes_input",
        )

    with st.expander("Resume Document (PDF / DOCX)", expanded=True):
        uploaded_doc  = st.file_uploader("Upload PDF or Word Document",         type=["pdf", "docx"], key="up_doc")
        if uploaded_doc:
            st.success(f"Loaded: {uploaded_doc.name}")

    st.divider()
    run_btn = st.button("Run Pipeline", use_container_width=True, type="primary")

    if run_btn:
        sources = []

        if uploaded_csv:
            sources.append(SourceInput(
                name=uploaded_csv.name,
                content_type="csv",
                raw_bytes=uploaded_csv.getvalue(),
            ))

        if uploaded_json:
            sources.append(SourceInput(
                name=uploaded_json.name,
                content_type="json",
                raw_bytes=uploaded_json.getvalue(),
            ))

        if notes_text.strip():
            sources.append(SourceInput(
                name="recruiter_notes.txt",
                content_type="txt",
                text=notes_text,
            ))

        if uploaded_doc:
            ext = uploaded_doc.name.rsplit(".", 1)[-1].lower()
            sources.append(SourceInput(
                name=uploaded_doc.name,
                content_type=ext,
                raw_bytes=uploaded_doc.getvalue(),
            ))

        if not sources:
            st.warning("Provide at least one input source before running the pipeline.")
        else:
            try:
                proj_config = json.loads(projection_config_str)
            except json.JSONDecodeError as e:
                st.error(f"Invalid projection schema JSON: {e}")
                proj_config = None

            with st.spinner("Running pipeline..."):
                # Build a runtime priorities dict keyed by the ACTUAL uploaded
                # filenames so MergeEngine._get_priority() always finds an exact
                # match, regardless of what the user named their files.
                source_priorities_runtime: dict = {}
                for src in sources:
                    source_priorities_runtime[src.name] = p_source_types.get(
                        src.content_type, 10
                    )

                runner = PipelineRunner(source_priorities=source_priorities_runtime)
                result: PipelineResult = runner.run(sources=sources, projection_config=proj_config)
                st.session_state["result"] = result
                st.session_state["proj_config"] = proj_config

            if result.error:
                st.error(result.error)
            elif result.validation_errors:
                st.error("Validation failed — see output panel.")
            else:
                st.success(
                    f"Pipeline complete in {result.pipeline_stats.overall_runtime_ms:.0f} ms — "
                    f"{result.pipeline_stats.records_parsed} source(s) merged."
                )

# ─────────────────────────── RIGHT: OUTPUT ───────────────────────────────────
with right:
    result: Optional[PipelineResult] = st.session_state.get("result")
    proj_config = st.session_state.get("proj_config")

    if result is None:
        st.info("Run the pipeline to see results.")
    elif result.error:
        st.error(result.error)
    elif result.validation_errors:
        st.error("Validation Failed")
        for e in result.validation_errors:
            st.markdown(f"- {e}")
    else:
        c = result.canonical

        # ── Quick summary strip ───────────────────────────────────────────
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Quality Score",   f"{c.data_quality_score * 100:.0f}%")
        m2.metric("Sources Merged",  result.pipeline_stats.records_parsed)
        m3.metric("Conflicts",       result.pipeline_stats.conflicts_detected)
        m4.metric("Runtime",         f"{result.pipeline_stats.overall_runtime_ms:.0f} ms")
        st.divider()

        # ── Tabs ──────────────────────────────────────────────────────────
        (
            tab_golden,
            tab_conflicts,
            tab_explain,
            tab_quality,
            tab_heatmap,
            tab_timeline,
            tab_diag,
            tab_proj,
            tab_export,
        ) = st.tabs([
            "Golden Record",
            "Conflict Dashboard",
            "Decision Explanations",
            "Data Quality",
            "Confidence Heatmap",
            "Timeline & Stats",
            "Parser Diagnostics",
            "Custom Projection",
            "Export PDF",
        ])

        # ══════════════════════════════════════════════════════════════════
        # TAB 1 — GOLDEN RECORD
        # ══════════════════════════════════════════════════════════════════
        with tab_golden:
            sf = set(selected_fields)  # fields the user wants to see

            if not sf:
                st.warning("choose atleast one field to display result")

            # ── candidate_id ──────────────────────────────────────────────
            if "candidate_id" in sf:
                st.markdown("**Candidate ID**")
                st.code(c.candidate_id, language=None)

            # ── full_name ─────────────────────────────────────────────────
            if "full_name" in sf:
                st.markdown("**Full Name**")
                st.markdown(f"### {c.full_name}" if c.full_name else "_No name found_")

            # ── emails ────────────────────────────────────────────────────
            if "emails" in sf:
                st.markdown("**Email**")
                if c.emails:
                    for e in c.emails:
                        st.markdown(f"[Mail - {e}](mailto:{e})")
                else:
                    st.markdown("Mail id - No mail id found")

            # ── phones ────────────────────────────────────────────────────
            if "phones" in sf:
                st.markdown("**Phone**")
                if c.phones:
                    for p in c.phones:
                        st.markdown(f"`{p}`")
                else:
                    st.markdown("Phone - No phone number found")

            # ── location ──────────────────────────────────────────────────
            if "location" in sf:
                st.markdown("**Location**")
                loc     = c.location
                city    = loc[0] if len(loc) > 0 else None
                region  = loc[1] if len(loc) > 1 else None
                country = loc[2] if len(loc) > 2 else None
                if any([city, region, country]):
                    lc1, lc2, lc3 = st.columns(3)
                    lc1.metric("City",    city    or "—")
                    lc2.metric("Region",  region  or "—")
                    lc3.metric("Country", country or "—")
                else:
                    st.markdown("Location - No location found")

            # ── links ─────────────────────────────────────────────────────
            if "links" in sf:
                st.markdown("**Links**")
                links = c.links
                has_any = any([links.linkedin, links.github, links.portfolio, links.other])
                if has_any:
                    if links.linkedin:
                        st.markdown(f"LinkedIn: [{links.linkedin}]({links.linkedin})")
                    if links.github:
                        st.markdown(f"GitHub: [{links.github}]({links.github})")
                    if links.portfolio:
                        st.markdown(f"Portfolio: [{links.portfolio}]({links.portfolio})")
                    for o in links.other:
                        st.markdown(f"Other: [{o}]({o})")
                else:
                    st.markdown("Links - No links found")

            st.divider()

            # ── headline ──────────────────────────────────────────────────
            if "headline" in sf:
                st.markdown("**Headline**")
                st.markdown(c.headline if c.headline else "Headline - No headline found")

            # ── years_experience ──────────────────────────────────────────
            if "years_experience" in sf:
                st.markdown("**Years of Experience**")
                st.markdown(
                    f"`{c.years_experience}` year(s)"
                    if c.years_experience is not None
                    else "Years of experience - Not specified"
                )

            st.divider()

            # ── skills ────────────────────────────────────────────────────
            if "skills" in sf:
                st.markdown("**Skills**")
                if c.skills:
                    import pandas as pd
                    skill_rows = [
                        {
                            "Name":       s.name,
                            "Confidence": f"{int(s.confidence * 100)}%",
                            "Sources":    ", ".join(s.sources) if s.sources else "—",
                        }
                        for s in c.skills
                    ]
                    st.dataframe(pd.DataFrame(skill_rows), use_container_width=True, hide_index=True)
                else:
                    st.markdown("Skills - No skills found")

            st.divider()

            # ── experience ────────────────────────────────────────────────
            if "experience" in sf:
                st.markdown("**Work Experience**")
                if c.experience:
                    for exp in c.experience:
                        with st.container(border=True):
                            ec1, ec2 = st.columns([2, 1])
                            with ec1:
                                st.markdown(f"**{exp.title}** at **{exp.company}**")
                            with ec2:
                                st.caption(f"{exp.start or 'N/A'} → {exp.end or 'Present'}")
                            if exp.summary:
                                st.write(exp.summary)
                else:
                    st.markdown("Work experience - No experience found")

            st.divider()

            # ── education ─────────────────────────────────────────────────
            if "education" in sf:
                st.markdown("**Education**")
                if c.education:
                    for edu in c.education:
                        with st.container(border=True):
                            deg_field = " — ".join(filter(None, [edu.degree, edu.field]))
                            st.markdown(f"**{edu.institution}**")
                            if deg_field:
                                st.markdown(deg_field)
                            if edu.end_year:
                                st.caption(f"Graduated: {edu.end_year}")
                            else:
                                st.caption("Year of Graduation - Not mentioned")
                else:
                    st.markdown("Education - No education details found")

            st.divider()

            # ── provenance ────────────────────────────────────────────────
            if "provenance" in sf:
                st.markdown("**Provenance** *(where each value came from)*")
                if c.provenance:
                    import pandas as pd
                    prov_rows = [
                        {"Field": p.field, "Source": p.source, "Method": p.method}
                        for p in c.provenance
                    ]
                    st.dataframe(pd.DataFrame(prov_rows), use_container_width=True, hide_index=True)
                else:
                    st.markdown("Provenance - No provenance data available")

            st.divider()

            # ── overall_confidence ────────────────────────────────────────
            if "overall_confidence" in sf:
                st.markdown("**Overall Confidence**")
                st.progress(float(c.overall_confidence), text=f"{c.overall_confidence:.0%}")

            # ── Validation ────────────────────────────────────────────────
            st.divider()
            if c.validation_warnings:
                for w in c.validation_warnings:
                    st.warning(w)
            else:
                st.success("Validation passed — all canonical constraints satisfied.")

            with st.expander("Full Golden Record JSON"):
                st.json(c.model_dump())

            st.download_button(
                label="Download Golden Record JSON",
                data=json.dumps(c.model_dump(), indent=2, ensure_ascii=False).encode(),
                file_name="golden_record.json",
                mime="application/json",
                use_container_width=True,
            )

        # ══════════════════════════════════════════════════════════════════
        # TAB 2 — CONFLICT RESOLUTION DASHBOARD
        # ══════════════════════════════════════════════════════════════════
        with tab_conflicts:
            conflicts = result.conflict_report
            if not conflicts:
                st.info("No field-level conflicts were detected — all sources agreed or only one source provided each field.")
            else:
                st.markdown(
                    f"**{len(conflicts)} conflict(s) detected** across merged sources. "
                    "Each row shows what was selected, what was rejected, and why."
                )
                st.divider()

                for cr in conflicts:
                    with st.container():
                        st.markdown(f"##### Field: `{cr.field}`")

                        ca, cb = st.columns(2)
                        with ca:
                            st.markdown(f"**Source A:** `{cr.source_a}`")
                            st.markdown(f"Value: `{cr.value_a or '(empty)'}`")
                            st.caption(f"Confidence: {cr.confidence_a:.0%}   Priority: {cr.priority_a}")
                        with cb:
                            st.markdown(f"**Source B:** `{cr.source_b}`")
                            st.markdown(f"Value: `{cr.value_b or '(empty)'}`")
                            st.caption(f"Confidence: {cr.confidence_b:.0%}   Priority: {cr.priority_b}")

                        rule_labels = {
                            "source_priority": "Source priority",
                            "confidence":      "Extraction confidence",
                            "recency":         "Source recency (tie-breaker)",
                            "auto":            "Auto merge",
                            "both_retained":   "Both values retained",
                        }
                        rule_label = rule_labels.get(cr.decision_rule, cr.decision_rule)
                        st.success(
                            f"Selected: `{cr.winning_value or '(empty)'}` "
                            f"from **{cr.winner_source}** — Decision rule: **{rule_label}**"
                        )
                        if cr.rejected_value:
                            st.caption(f"Rejected: `{cr.rejected_value}`")
                        st.divider()

        # ══════════════════════════════════════════════════════════════════
        # TAB 3 — DECISION EXPLANATION ENGINE
        # ══════════════════════════════════════════════════════════════════
        with tab_explain:
            explanations = result.decision_explanations
            if not explanations:
                st.info("No field explanations available.")
            else:
                st.markdown(
                    f"**{len(explanations)} field(s) explained.** "
                    "For every merged field, this panel shows why the selected value won."
                )
                st.divider()

                rule_label_map = {
                    "source_priority": "Source Priority",
                    "confidence":      "Extraction Confidence",
                    "recency":         "Source Recency",
                    "single_source":   "Single Source",
                    "auto":            "Auto",
                }

                for ex in explanations:
                    with st.expander(f"{ex.field}  —  winner: {ex.winner_source}  ({ex.winner_confidence:.0%} confidence)"):
                        st.markdown(f"**Selected value:** `{ex.winner_value_preview}`")
                        st.markdown(f"**Winning source:** `{ex.winner_source}`")
                        st.markdown(f"**Extraction confidence:** {ex.winner_confidence:.0%}")
                        st.markdown(f"**Decision rule:** {rule_label_map.get(ex.decision_rule, ex.decision_rule)}")

                        st.markdown("**Reasons selected:**")
                        for r in ex.reasons:
                            st.markdown(f"- {r}")

                        if ex.alternative_sources:
                            st.markdown("**Alternative sources considered:**")
                            for alt in ex.alternative_sources:
                                st.markdown(
                                    f"- `{alt['source']}` — confidence: {alt['confidence']:.0%}, "
                                    f"priority: {alt['priority']}, value: `{alt['value_preview']}`"
                                )

        # ══════════════════════════════════════════════════════════════════
        # TAB 4 — DATA QUALITY REPORT
        # ══════════════════════════════════════════════════════════════════
        with tab_quality:
            qr: Optional[QualityReport] = result.quality_report
            if not qr:
                st.info("Quality report not available.")
            else:
                # Score overview
                sc1, sc2, sc3, sc4, sc5 = st.columns(5)
                sc1.metric("Overall",      f"{qr.overall_pct}%")
                sc2.metric("Completeness", f"{qr.completeness_pct}%")
                sc3.metric("Consistency",  f"{qr.consistency_pct}%")
                sc4.metric("Validity",     f"{qr.validity_pct}%")
                sc5.metric("Merge Quality",f"{qr.merge_quality_pct}%")

                st.divider()

                # Progress bars
                st.markdown("**Score Breakdown**")
                st.progress(qr.completeness_score,  text=f"Completeness   {qr.completeness_pct}%")
                st.progress(qr.consistency_score,   text=f"Consistency    {qr.consistency_pct}%")
                st.progress(qr.validity_score,      text=f"Validity       {qr.validity_pct}%")
                st.progress(qr.merge_quality_score, text=f"Merge Quality  {qr.merge_quality_pct}%")
                st.progress(qr.overall_score,       text=f"Overall        {qr.overall_pct}%")

                st.divider()

                col_miss, col_issues = st.columns(2)
                with col_miss:
                    st.markdown("**Missing Fields**")
                    if qr.missing_fields:
                        for f in qr.missing_fields:
                            st.markdown(f"- {f}")
                    else:
                        st.success("All expected fields present.")

                with col_issues:
                    st.markdown("**Duplicate / Conflicting Fields**")
                    if qr.duplicate_fields:
                        st.markdown("*Duplicates:*")
                        for f in qr.duplicate_fields:
                            st.markdown(f"- `{f}`")
                    if qr.conflicting_fields:
                        st.markdown("*Fields with multiple sources:*")
                        for f in qr.conflicting_fields:
                            st.markdown(f"- `{f}`")
                    if not qr.duplicate_fields and not qr.conflicting_fields:
                        st.success("No duplicates or conflicts.")

                st.divider()
                st.markdown("**Per-Field Completeness**")
                rows = [
                    {"Field": fq.field, "Present": "Yes" if fq.present else "No",
                     "Confidence": f"{int(fq.confidence * 100)}%" if fq.present else "—",
                     "Note": fq.note or ""}
                    for fq in qr.field_breakdown
                ]
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

                st.divider()
                st.markdown("**Validation Warnings**")
                if qr.validation_warnings:
                    for w in qr.validation_warnings:
                        st.warning(w)
                else:
                    st.success("No validation warnings.")

                st.divider()
                st.markdown("**Suggested Improvements**")
                for s in qr.suggestions:
                    st.info(s)

        # ══════════════════════════════════════════════════════════════════
        # TAB 5 — CONFIDENCE HEATMAP
        # ══════════════════════════════════════════════════════════════════
        with tab_heatmap:
            st.markdown(
                "Each extracted field is coloured by extraction confidence. "
                "Green = high, amber = medium, red = low."
            )
            st.divider()

            # Build field confidence table from provenance + skills
            heatmap_rows = []
            seen_fields = set()

            for pr in c.provenance:
                if pr.field not in seen_fields:
                    seen_fields.add(pr.field)
                    conf = pr.confidence_score or 0.6
                    if conf >= 0.85:
                        level = "High"
                    elif conf >= 0.65:
                        level = "Medium"
                    else:
                        level = "Low"
                    heatmap_rows.append({
                        "Field":      pr.field,
                        "Source":     pr.source,
                        "Method":     pr.method,
                        "Confidence": f"{int(conf * 100)}%",
                        "Level":      level,
                    })

            for sk in c.skills:
                conf = sk.confidence
                level = "High" if conf >= 0.85 else "Medium" if conf >= 0.65 else "Low"
                heatmap_rows.append({
                    "Field":      f"Skill: {sk.name}",
                    "Source":     ", ".join(sk.sources),
                    "Method":     "extraction",
                    "Confidence": f"{int(conf * 100)}%",
                    "Level":      level,
                })

            if not heatmap_rows:
                # Fallback scalar summary
                scalars = [
                    ("Full Name",   c.full_name is not None,          0.9),
                    ("Email",       bool(c.emails),                    1.0),
                    ("Phone",       bool(c.phones),                    0.85),
                    ("Headline",    bool(c.headline),                  0.7),
                    ("Location",    any(c.location),                   0.7),
                    ("Experience",  bool(c.experience),                0.8),
                    ("Education",   bool(c.education),                 0.75),
                    ("Skills",      bool(c.skills),                    c.overall_confidence),
                ]
                for label, present, conf in scalars:
                    conf = conf if present else 0.0
                    level = "High" if conf >= 0.85 else "Medium" if conf >= 0.65 else "Low" if conf > 0 else "Missing"
                    heatmap_rows.append({
                        "Field": label, "Source": "—", "Method": "—",
                        "Confidence": f"{int(conf * 100)}%" if present else "—",
                        "Level": level,
                    })

            df_heat = pd.DataFrame(heatmap_rows)

            def _colour_level(val):
                if val == "High":
                    return "background-color: #d4edda; color: #155724"
                elif val == "Medium":
                    return "background-color: #fff3cd; color: #856404"
                elif val == "Low":
                    return "background-color: #f8d7da; color: #721c24"
                return ""

            styled = df_heat.style.map(_colour_level, subset=["Level"])
            st.dataframe(styled, use_container_width=True, hide_index=True)

        # ══════════════════════════════════════════════════════════════════
        # TAB 6 — MERGE TIMELINE & PIPELINE STATS
        # ══════════════════════════════════════════════════════════════════
        with tab_timeline:
            st.markdown("**Pipeline Execution Timeline**")
            st.divider()

            for stage in result.merge_timeline:
                icon = {"ok": "✓", "skipped": "—", "error": "✗"}.get(stage.status, "?")
                colour = {"ok": "green", "skipped": "grey", "error": "red"}.get(stage.status, "black")
                st.markdown(
                    f"<span style='color:{colour}; font-weight:600'>{icon} {stage.stage}</span>"
                    + (f"  <span style='color:grey; font-size:0.85em'>({stage.duration_ms:.1f} ms)</span>" if stage.duration_ms else "")
                    + (f"<br><span style='color:grey; font-size:0.8em'>&nbsp;&nbsp;&nbsp;&nbsp;{stage.detail}</span>" if stage.detail else ""),
                    unsafe_allow_html=True,
                )
                if stage.stage != result.merge_timeline[-1].stage:
                    st.markdown("<div style='margin-left:8px; color:lightgrey; font-size:1.2em'>↓</div>", unsafe_allow_html=True)

            st.divider()
            st.markdown("**Pipeline Statistics**")
            ps = result.pipeline_stats

            stats_rows = [
                ("Files Processed",          str(ps.files_processed)),
                ("Records Parsed",           str(ps.records_parsed)),
                ("Fields Compared",          str(ps.fields_compared)),
                ("Fields Merged",            str(ps.fields_merged)),
                ("Conflicts Detected",       str(ps.conflicts_detected)),
                ("Duplicates Removed",       str(ps.duplicates_removed)),
                ("Validation Rules Executed",str(ps.validation_rules_executed)),
                ("Overall Runtime (ms)",     f"{ps.overall_runtime_ms:.1f}"),
                ("Adapter + Parser (ms)",    f"{ps.adapter_runtime_ms:.1f}"),
                ("Identity Resolution (ms)", f"{ps.identity_runtime_ms:.1f}"),
                ("Merge (ms)",               f"{ps.merge_runtime_ms:.1f}"),
                ("Validation (ms)",          f"{ps.validation_runtime_ms:.1f}"),
                ("Projection (ms)",          f"{ps.projection_runtime_ms:.1f}"),
            ]
            # Explicit str dtype prevents PyArrow mixed-type serialisation error
            stats_df = pd.DataFrame(stats_rows, columns=["Metric", "Value"]).astype(str)
            st.dataframe(stats_df, use_container_width=True, hide_index=True)

        # ══════════════════════════════════════════════════════════════════
        # TAB 7 — PARSER DIAGNOSTICS
        # ══════════════════════════════════════════════════════════════════
        with tab_diag:
            diags = result.parse_diagnostics
            if not diags:
                st.info("No parser diagnostics available.")
            else:
                for diag in diags:
                    with st.expander(
                        f"{diag.source_name}  ({diag.content_type.upper()})  "
                        f"— {diag.parse_time_ms:.1f} ms"
                        + ("  [ERROR]" if diag.error else ""),
                        expanded=True,
                    ):
                        if diag.error:
                            st.error(f"Parse error: {diag.error}")
                            continue

                        d1, d2, d3, d4 = st.columns(4)
                        d1.metric("Emails Found",     diag.emails_found)
                        d2.metric("Phones Found",     diag.phones_found)
                        d3.metric("Skills Found",     diag.skills_found)
                        d4.metric("Parser Confidence",f"{int(diag.parser_confidence * 100)}%")

                        d5, d6, d7, d8 = st.columns(4)
                        d5.metric("Experience Items",  diag.experience_count)
                        d6.metric("Education Items",   diag.education_count)
                        d7.metric("Links Found",       diag.links_found)
                        d8.metric("Parse Time (ms)",   f"{diag.parse_time_ms:.1f}")

                        col_found, col_miss = st.columns(2)
                        with col_found:
                            st.markdown("**Sections Found**")
                            for s in diag.sections_found:
                                st.markdown(f"- {s}")
                        with col_miss:
                            st.markdown("**Sections Missing**")
                            for s in diag.sections_missing:
                                st.markdown(f"- {s}")

        # ══════════════════════════════════════════════════════════════════
        # TAB 8 — CUSTOM PROJECTION
        # ══════════════════════════════════════════════════════════════════
        with tab_proj:
            st.markdown(
                "Dynamic field remapping driven by the sidebar schema config. "
                "No backend changes required."
            )
            if proj_config:
                try:
                    projected = ProjectionEngine().project(c, proj_config)
                    st.json(projected)
                    st.download_button(
                        label="Download Projected JSON",
                        data=json.dumps(projected, indent=2, ensure_ascii=False).encode(),
                        file_name="projected_output.json",
                        mime="application/json",
                        use_container_width=True,
                    )
                except Exception as e:
                    st.error(f"Projection error: {e}")
            else:
                st.info("No projection config available. Provide valid JSON in the sidebar.")

        # ══════════════════════════════════════════════════════════════════
        # TAB 9 — EXPORT PDF REPORT
        # ══════════════════════════════════════════════════════════════════
        with tab_export:
            st.markdown(
                "Generate a professional multi-page PDF report including candidate overview, "
                "skills, experience, provenance trace, and pipeline metadata."
            )
            if st.button("Generate PDF Report", use_container_width=True, type="primary"):
                try:
                    from src.exporters.pdf_exporter import CandidatePDFExporter
                    os.makedirs("output", exist_ok=True)
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    pdf_path = f"output/candidate_report_{ts}.pdf"
                    CandidatePDFExporter(c).export(pdf_path)
                    st.success(f"Report generated: `{pdf_path}`")
                    with open(pdf_path, "rb") as fh:
                        st.download_button(
                            label="Download PDF Report",
                            data=fh.read(),
                            file_name=os.path.basename(pdf_path),
                            mime="application/pdf",
                            use_container_width=True,
                        )
                except ImportError:
                    st.error("ReportLab is not installed. Run: pip install reportlab")
                except Exception as e:
                    st.error(f"PDF generation failed: {e}")
