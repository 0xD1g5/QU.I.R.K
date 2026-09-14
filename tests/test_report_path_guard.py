"""Phase 200 / RPT-03: guard unit tests + the runtime-enumeration
dashboard-exclusion sweep for path-shaped report config fields.

RPT-03's actual deliverable is the sweep below, not the guard unit tests
alone. Before this file existed, the exclusion of path-shaped fields
(`logo_path`, `template_dir`, `openapi_spec_path`) from every
dashboard-exposed surface — pydantic schemas, overlay allowlists, and the
effective-config `_SECTION_TITLES` allowlist — was recorded only as PROSE in
`quirk/dashboard/api/schemas.py`'s `AdvancedScanFields` docstring (D-04).
Prose is not a guarantee: nothing re-checks it when a new field or a new
allowlist is added. This file mechanizes the exclusion by re-enumerating the
occurrence set from live source at *run time* on every test run — the Phase
182 lesson (a hand-derived/written list of "known sites" is not a safeguard;
only a scan that regenerates its occurrence set from installed source is).

The registry-sweep discipline (non-vacuous enumeration, named offenders on
failure, run-time regeneration rather than a hand-written list) mirrors
`tests/test_skip_registry.py::test_no_unregistered_skips`.
"""
from __future__ import annotations

import warnings

import pytest
from pydantic import BaseModel

from quirk.config import validate_report_path_field

# Phase 200 / RPT-03: the path-shaped leaf field names that must NEVER appear
# on a dashboard-exposed surface, per the `assessment.logo_path` /
# `scan.openapi_spec_path` lesson (schemas.py D-04 docstring).
PATH_FIELD_REGISTRY: frozenset[str] = frozenset(
    {"logo_path", "template_dir", "openapi_spec_path"}
)


# ---------------------------------------------------------------------------
# Guard unit tests
# ---------------------------------------------------------------------------


class TestValidateReportPathFieldTraversal:
    def test_traversal_template_dir_raises_coded_error(self):
        with pytest.raises(ValueError) as excinfo:
            validate_report_path_field("report.template_dir", "../../etc")
        message = str(excinfo.value)
        assert "QRK-CONFIG-003" in message
        assert "report.template_dir" in message
        assert "../../etc" in message

    def test_traversal_logo_path_raises_coded_error(self):
        with pytest.raises(ValueError) as excinfo:
            validate_report_path_field(
                "report.branding.logo_path", "../secrets/logo.png"
            )
        message = str(excinfo.value)
        assert "QRK-CONFIG-003" in message
        assert "report.branding.logo_path" in message
        assert "../secrets/logo.png" in message

    def test_traversal_assessment_logo_path_raises_coded_error(self):
        with pytest.raises(ValueError) as excinfo:
            validate_report_path_field("assessment.logo_path", "foo/../../bar.png")
        assert "QRK-CONFIG-003" in str(excinfo.value)


class TestValidateReportPathFieldAcceptance:
    def test_none_and_empty_values_accepted(self):
        # Every field is optional — falsy values must never raise.
        validate_report_path_field("report.template_dir", None)
        validate_report_path_field("report.template_dir", "")
        validate_report_path_field("report.branding.logo_path", None)
        validate_report_path_field("assessment.logo_path", "")

    def test_absolute_non_traversal_template_dir_accepted(self, tmp_path):
        validate_report_path_field("report.template_dir", str(tmp_path))

    def test_relative_non_traversal_logo_path_accepted_when_missing(self, caplog):
        # No traversal shape; the file need not exist for logo_path (asymmetry).
        with caplog.at_level("WARNING"):
            validate_report_path_field(
                "report.branding.logo_path", "assets/logo.png"
            )


class TestValidateReportPathFieldTypeGuard:
    """Phase 200 review WR-02: a truthy non-string YAML value (int/list/
    mapping/float/bool) must raise the coded CONFIG-003 error naming the
    field and the received type — never an uncoded TypeError from pathlib."""

    @pytest.mark.parametrize(
        "bad_value", [123, 1.5, True, ["a", "b"], {"x": "y"}],
        ids=["int", "float", "bool", "list", "mapping"],
    )
    def test_non_string_value_raises_coded_error(self, bad_value):
        with pytest.raises(ValueError) as excinfo:
            validate_report_path_field("report.template_dir", bad_value)
        message = str(excinfo.value)
        assert "QRK-CONFIG-003" in message
        assert "report.template_dir" in message
        assert type(bad_value).__name__ in message

    def test_non_string_logo_path_raises_coded_error(self):
        with pytest.raises(ValueError) as excinfo:
            validate_report_path_field("report.branding.logo_path", [1, 2])
        message = str(excinfo.value)
        assert "QRK-CONFIG-003" in message
        assert "report.branding.logo_path" in message

    def test_falsy_non_string_values_still_treated_as_absent(self):
        # Falsy values of any type mean "not set" — they return before the
        # type rung, matching the every-field-is-optional contract.
        validate_report_path_field("report.template_dir", 0)
        validate_report_path_field("report.branding.logo_path", [])


class TestValidateReportPathFieldTemplateDirMustBeDirectory:
    def test_template_dir_pointing_at_a_file_raises_coded_error(self, tmp_path):
        file_path = tmp_path / "not_a_dir.txt"
        file_path.write_text("not a directory")
        with pytest.raises(ValueError) as excinfo:
            validate_report_path_field("report.template_dir", str(file_path))
        message = str(excinfo.value)
        assert "QRK-CONFIG-003" in message
        assert "report.template_dir" in message

    def test_template_dir_that_does_not_exist_raises_coded_error(self, tmp_path):
        missing_dir = tmp_path / "does-not-exist"
        with pytest.raises(ValueError) as excinfo:
            validate_report_path_field("report.template_dir", str(missing_dir))
        assert "QRK-CONFIG-003" in str(excinfo.value)


class TestValidateReportPathFieldLogoPathToleratesMissingFile:
    def test_missing_logo_path_warns_and_does_not_raise(self, caplog):
        with caplog.at_level("WARNING"):
            # Must not raise — render-time `_load_logo_b64` already degrades
            # gracefully to a logo-less cover page (T-200-08).
            validate_report_path_field(
                "report.branding.logo_path", "/tmp/definitely-does-not-exist-xyz.png"
            )
        assert any(
            "report.branding.logo_path" in record.message for record in caplog.records
        ), "missing logo_path must warn, naming the field"

    def test_missing_assessment_logo_path_warns_and_does_not_raise(self, caplog):
        with caplog.at_level("WARNING"):
            validate_report_path_field(
                "assessment.logo_path", "/tmp/also-does-not-exist-xyz.png"
            )
        assert any(
            "assessment.logo_path" in record.message for record in caplog.records
        )


# ---------------------------------------------------------------------------
# Registry sweep — runtime enumeration, non-vacuous, named-offenders on failure
# ---------------------------------------------------------------------------


def _enumerate_dashboard_schema_models():
    """Every pydantic BaseModel subclass defined in schemas.py, enumerated
    from `vars()` at run time rather than a hand-written import list."""
    import quirk.dashboard.api.schemas as schemas_module

    models = [
        obj
        for obj in vars(schemas_module).values()
        if isinstance(obj, type)
        and issubclass(obj, BaseModel)
        and obj.__module__ == schemas_module.__name__
    ]
    return models


def test_dashboard_schema_enumeration_is_not_vacuous():
    """A regenerate-from-source enumeration that finds nothing is
    indistinguishable from a broken/deleted import — this must never pass
    silently."""
    models = _enumerate_dashboard_schema_models()
    assert models, "enumeration must never be vacuous — no BaseModel found in schemas.py"


def test_no_dashboard_schema_exposes_a_path_field():
    models = _enumerate_dashboard_schema_models()
    assert models, "enumeration must never be vacuous"

    offenders = []
    for model in models:
        for field_name in model.model_fields:
            if field_name in PATH_FIELD_REGISTRY:
                offenders.append(f"{model.__name__}.{field_name}")

    if offenders:
        pytest.fail(
            "Path-shaped field(s) found on a dashboard-exposed pydantic model "
            "(RPT-03 containment violation) — the phase's dashboard work is "
            "EXCLUSION, not exposure:\n  " + "\n  ".join(sorted(offenders))
        )


def _enumerate_overlay_allowlists():
    """Every `_KNOWN_*_OVERLAY_KEYS` frozenset in `quirk.dashboard.api.routes.jobs`,
    discovered by name-prefix scan over `vars()` at run time — NOT a hard-coded
    pair of names, so a future third allowlist is caught automatically."""
    import quirk.dashboard.api.routes.jobs as jobs_module

    allowlists = {
        name: value
        for name, value in vars(jobs_module).items()
        if name.startswith("_KNOWN_") and name.endswith("_OVERLAY_KEYS")
        and isinstance(value, frozenset)
    }
    return allowlists


def test_overlay_allowlist_enumeration_is_not_vacuous():
    allowlists = _enumerate_overlay_allowlists()
    assert allowlists, (
        "enumeration must never be vacuous — no _KNOWN_*_OVERLAY_KEYS "
        "frozenset found in quirk.dashboard.api.routes.jobs"
    )


def test_no_overlay_allowlist_contains_a_path_field():
    allowlists = _enumerate_overlay_allowlists()
    assert allowlists, "enumeration must never be vacuous"

    union_keys: set[str] = set()
    for keys in allowlists.values():
        union_keys |= keys

    offenders = union_keys & PATH_FIELD_REGISTRY
    if offenders:
        pytest.fail(
            "Path-shaped field(s) found in a dashboard overlay allowlist "
            "(RPT-03 containment violation):\n  "
            + "\n  ".join(sorted(offenders))
        )


def test_report_section_not_in_effective_config_section_titles():
    """CONTEXT boundary: the phase's dashboard work is EXCLUSION, not
    exposure. `report` settings must never surface on the dashboard
    effective-config view via `_SECTION_TITLES`."""
    from quirk.dashboard.api.routes.config import _SECTION_TITLES

    section_names = {name for name, _title in _SECTION_TITLES}
    assert "report" not in section_names, (
        "report: settings are deliberately NOT surfaced on the dashboard "
        "effective-config view (CONTEXT: exclusion, not exposure) — "
        "_SECTION_TITLES must never gain a 'report' entry"
    )


# ---------------------------------------------------------------------------
# Mutation check: a guard that cannot fail is not a guard.
#
# This dynamically builds a throwaway pydantic BaseModel carrying a
# `logo_path` field, injects it into a COPY of the schemas module's `vars()`
# namespace (never mutating the real module or any real source file), and
# proves the same enumeration+assertion logic used above would catch it.
# ---------------------------------------------------------------------------


def test_mutation_check_sweep_detects_an_injected_path_field():
    """Proves the sweep is not vacuously green: injecting a `logo_path`
    field into a dynamically-created BaseModel (monkeypatched into an
    enumerated namespace, never touching real schemas.py) makes the sweep
    fail, exactly like it would for a real regression."""
    from typing import Optional as _Optional

    class _ScratchModelWithLeakedPathField(BaseModel):
        logo_path: _Optional[str] = None

    scratch_namespace = {
        "_ScratchModelWithLeakedPathField": _ScratchModelWithLeakedPathField
    }
    models = [
        obj
        for obj in scratch_namespace.values()
        if isinstance(obj, type) and issubclass(obj, BaseModel)
    ]
    assert models, "scratch enumeration must not be vacuous"

    offenders = []
    for model in models:
        for field_name in model.model_fields:
            if field_name in PATH_FIELD_REGISTRY:
                offenders.append(f"{model.__name__}.{field_name}")

    assert offenders == ["_ScratchModelWithLeakedPathField.logo_path"], (
        "the sweep's own detection logic failed to catch an injected "
        "path-shaped field — a guard that cannot fail is not a guard"
    )


# ---------------------------------------------------------------------------
# Phase 209 Plan 05 (DELIV-01) — RPT-03 sweep, second axis: PARAMETERS.
#
# Phase 209 added `quirk/dashboard/api/routes/reports.py`, a dashboard route
# that serves files from `cfg.output.directory`. RPT-03's exclusion now has a
# second axis: not only "no path-shaped FIELD on a dashboard schema" (the
# sweep above) but also "no path-shaped PARAMETER on a dashboard route" — a
# route can leak the same class of surface a schema field can, just via a
# `{fmt}`-style path segment instead of a JSON body field. This section
# mirrors the file's existing register exactly: run-time regeneration
# (`reports.router.routes` walked fresh on every test run, never a
# hand-written route list), non-vacuity assertions, named offenders on
# failure, and a mutation check proving the assertion helper can actually
# detect an injected offender.
# ---------------------------------------------------------------------------

import typing as _typing


def _enumerate_report_route_path_params():
    """Walk `quirk.dashboard.api.routes.reports.router.routes` at run time,
    returning, for each route, the set of `{...}`-shaped path-parameter names
    paired with their resolved annotation from the endpoint function's
    signature. Never a hand-written route list — a future route added to
    this router is picked up automatically."""
    from quirk.dashboard.api.routes import reports

    entries = []
    for route in reports.router.routes:
        path = getattr(route, "path", "")
        if "{" not in path:
            continue
        endpoint = getattr(route, "endpoint", None)
        if endpoint is None:
            continue
        hints = _typing.get_type_hints(endpoint, include_extras=True)
        param_names = (
            list(route.param_convertors.keys())
            if hasattr(route, "param_convertors")
            else []
        )
        for name in param_names:
            entries.append((path, name, hints.get(name)))
    return entries


def test_report_route_enumeration_is_not_vacuous():
    """A sweep that finds nothing is indistinguishable from a broken import
    or a route module that silently failed to register — must never pass
    silently."""
    from quirk.dashboard.api.routes import reports

    all_routes = list(reports.router.routes)
    assert all_routes, (
        "VACUOUS SWEEP: quirk.dashboard.api.routes.reports.router has zero "
        "routes — this cannot be a working report-download router"
    )

    parameterised = _enumerate_report_route_path_params()
    assert parameterised, (
        "VACUOUS SWEEP: no parameterised ({...}) route found on "
        "reports.router — the download route's path-parameter surface "
        "could not be enumerated, so nothing downstream is actually being "
        "checked"
    )


def test_report_route_path_params_are_enum_constrained():
    """Every path parameter on reports.router must be Literal- or
    Enum-typed, never bare str/Path/Any — D-04's containment guard depends
    on this. The Literal's member set is asserted exactly, so widening the
    enum (e.g. adding a 6th format) is a deliberate, test-visible act."""
    import enum

    expected_members = {"html", "pdf", "docx", "cbom-json", "cbom-xml"}
    entries = _enumerate_report_route_path_params()
    assert entries, "enumeration must never be vacuous"

    for path, name, annotation in entries:
        assert annotation is not str, (
            f"route {path!r} parameter {name!r} is bare `str` — RPT-03's "
            "second axis requires a Literal/Enum-typed path parameter"
        )
        assert annotation not in (None, _typing.Any), (
            f"route {path!r} parameter {name!r} has no usable annotation "
            f"({annotation!r}) — cannot be a Path/Any-typed free-form param"
        )

        origin = _typing.get_origin(annotation)
        if origin is _typing.Literal:
            members = set(_typing.get_args(annotation))
        elif isinstance(annotation, type) and issubclass(annotation, enum.Enum):
            members = {member.value for member in annotation}
        else:
            pytest.fail(
                f"route {path!r} parameter {name!r} annotation {annotation!r} "
                "is neither typing.Literal nor an enum.Enum subclass"
            )

        assert members == expected_members, (
            f"route {path!r} parameter {name!r} member set {members} != "
            f"expected {expected_members} — a widened/narrowed enum must be "
            "a deliberate, test-visible act"
        )


def test_report_route_exposes_no_branding_or_template_surface():
    """Criterion 6's proof: RPT-03's dashboard exclusion still holds AFTER
    Phase 209, checked by a test rather than by a diff. No route on
    reports.router may expose a path segment, query parameter, or
    request-body model naming any PATH_FIELD_REGISTRY member, and the
    module's own source text must contain no reference to report.branding
    or report.template_dir."""
    import inspect

    from quirk.dashboard.api.routes import reports

    for route in reports.router.routes:
        path = getattr(route, "path", "")
        for member in PATH_FIELD_REGISTRY:
            assert member not in path, (
                f"route path {path!r} references path-shaped field "
                f"{member!r} — RPT-03 containment violation"
            )

        endpoint = getattr(route, "endpoint", None)
        if endpoint is None:
            continue
        try:
            sig = inspect.signature(endpoint)
        except (TypeError, ValueError):
            continue
        for param_name, param in sig.parameters.items():
            assert param_name not in PATH_FIELD_REGISTRY, (
                f"route {path!r} endpoint parameter {param_name!r} is a "
                "path-shaped field name — RPT-03 containment violation"
            )
            annotation = param.annotation
            if isinstance(annotation, type) and issubclass(annotation, BaseModel):
                for field_name in annotation.model_fields:
                    assert field_name not in PATH_FIELD_REGISTRY, (
                        f"route {path!r} request-body model "
                        f"{annotation.__name__}.{field_name} is a "
                        "path-shaped field name — RPT-03 containment "
                        "violation"
                    )

    source_text = inspect.getsource(reports)
    assert "report.branding" not in source_text, (
        "reports.py source text references report.branding — RPT-03 "
        "containment violation"
    )
    assert "report.template_dir" not in source_text, (
        "reports.py source text references report.template_dir — RPT-03 "
        "containment violation"
    )


def test_mutation_check_report_route_sweep_detects_a_str_path_param():
    """Proves the parameter-annotation assertion helper is not vacuously
    green: constructs a throwaway APIRouter with a deliberately offending
    str-typed path parameter and asserts the same shape of check used above
    flags it. Without this, a sweep that silently passes on everything is
    indistinguishable from a working one."""
    from fastapi import APIRouter

    scratch_router = APIRouter()

    @scratch_router.get("/scratch/{leaked}")
    def _scratch_endpoint(leaked: str) -> dict:  # pragma: no cover - never called
        return {"leaked": leaked}

    offenders = []
    for route in scratch_router.routes:
        path = getattr(route, "path", "")
        if "{" not in path:
            continue
        endpoint = getattr(route, "endpoint", None)
        hints = _typing.get_type_hints(endpoint, include_extras=True)
        param_names = (
            list(route.param_convertors.keys())
            if hasattr(route, "param_convertors")
            else []
        )
        for name in param_names:
            annotation = hints.get(name)
            if annotation is str:
                offenders.append(f"{path}:{name}")

    assert offenders == ["/scratch/{leaked}:leaked"], (
        "the mutation-check sweep failed to detect an injected str-typed "
        "path parameter — a guard that cannot fail is not a guard"
    )
