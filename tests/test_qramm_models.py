"""Tests for QRAMM ORM models and database initialization (Phase 51 — QRAMM-01).

RED phase: These tests are written before implementation and must fail initially.
GREEN phase: Pass after QRAMMSession, QRAMMAnswer, QRAMMProfile added to models.py
             and _ensure_qramm_tables() added to db.py.
"""
import os
import tempfile

import pytest
from sqlalchemy import inspect as sa_inspect


class TestQRAMMModelsRegistration:
    """QRAMM ORM classes must be importable and registered on Base.metadata."""

    def test_qramm_session_importable(self):
        from quirk.models import QRAMMSession  # noqa: F401

    def test_qramm_answer_importable(self):
        from quirk.models import QRAMMAnswer  # noqa: F401

    def test_qramm_profile_importable(self):
        from quirk.models import QRAMMProfile  # noqa: F401

    def test_all_three_registered_on_base_metadata(self):
        from quirk.models import Base, QRAMMAnswer, QRAMMProfile, QRAMMSession  # noqa: F401

        tables = Base.metadata.tables
        assert "qramm_sessions" in tables, f"qramm_sessions missing from {list(tables)}"
        assert "qramm_answers" in tables, f"qramm_answers missing from {list(tables)}"
        assert "qramm_profiles" in tables, f"qramm_profiles missing from {list(tables)}"

    def test_float_in_sqlalchemy_import(self):
        """Float must be imported so QRAMMProfile.multiplier Column works."""
        import quirk.models as m
        import inspect

        src = inspect.getsource(m)
        assert "Float" in src, "Float not found in quirk/models.py source"


class TestQRAMMSessionColumns:
    """QRAMMSession must have the QRAMM-01 schema columns."""

    def _table(self):
        from quirk.models import Base, QRAMMSession  # noqa: F401
        return Base.metadata.tables["qramm_sessions"]

    def test_tablename(self):
        from quirk.models import QRAMMSession
        assert QRAMMSession.__tablename__ == "qramm_sessions"

    def test_has_id_primary_key(self):
        t = self._table()
        assert "id" in t.c

    def test_has_org_name(self):
        t = self._table()
        assert "org_name" in t.c

    def test_has_created_at(self):
        t = self._table()
        assert "created_at" in t.c

    def test_has_updated_at(self):
        t = self._table()
        assert "updated_at" in t.c

    def test_has_model_version(self):
        t = self._table()
        assert "model_version" in t.c

    def test_has_profile_id(self):
        t = self._table()
        assert "profile_id" in t.c

    def test_has_status(self):
        t = self._table()
        assert "status" in t.c

    def test_has_score_json(self):
        t = self._table()
        assert "score_json" in t.c


class TestQRAMMAnswerColumns:
    """QRAMMAnswer must have QRAMM-01 + Phase-53 pre-provisioned columns."""

    def _table(self):
        from quirk.models import Base, QRAMMAnswer  # noqa: F401
        return Base.metadata.tables["qramm_answers"]

    def test_tablename(self):
        from quirk.models import QRAMMAnswer
        assert QRAMMAnswer.__tablename__ == "qramm_answers"

    def test_has_session_id(self):
        t = self._table()
        assert "session_id" in t.c

    def test_has_question_number(self):
        t = self._table()
        assert "question_number" in t.c

    def test_has_dimension(self):
        t = self._table()
        assert "dimension" in t.c

    def test_has_practice_area(self):
        t = self._table()
        assert "practice_area" in t.c

    def test_has_answer_value(self):
        t = self._table()
        assert "answer_value" in t.c

    def test_has_suggested_answer_phase53_preprovision(self):
        """Phase 53 pre-provisioned column — avoids ALTER TABLE later."""
        t = self._table()
        assert "suggested_answer" in t.c

    def test_has_confirmed_at_phase53_preprovision(self):
        t = self._table()
        assert "confirmed_at" in t.c

    def test_has_evidence_source_phase53_preprovision(self):
        t = self._table()
        assert "evidence_source" in t.c


class TestQRAMMProfileColumns:
    """QRAMMProfile must have QRAMM-01 schema columns including Float multiplier."""

    def _table(self):
        from quirk.models import Base, QRAMMProfile  # noqa: F401
        return Base.metadata.tables["qramm_profiles"]

    def test_tablename(self):
        from quirk.models import QRAMMProfile
        assert QRAMMProfile.__tablename__ == "qramm_profiles"

    def test_has_session_id(self):
        t = self._table()
        assert "session_id" in t.c

    def test_has_industry(self):
        t = self._table()
        assert "industry" in t.c

    def test_has_org_size(self):
        t = self._table()
        assert "org_size" in t.c

    def test_has_data_sensitivity(self):
        t = self._table()
        assert "data_sensitivity" in t.c

    def test_has_regulatory_obligations(self):
        t = self._table()
        assert "regulatory_obligations" in t.c

    def test_has_geographic_scope(self):
        t = self._table()
        assert "geographic_scope" in t.c

    def test_has_multiplier_float(self):
        from sqlalchemy import Float as SAFloat
        t = self._table()
        assert "multiplier" in t.c
        assert isinstance(t.c["multiplier"].type, SAFloat)

    def test_has_created_at(self):
        t = self._table()
        assert "created_at" in t.c


class TestInitDbQRAMMTables:
    """init_db() must create qramm_* tables on a fresh and existing DB (idempotent)."""

    def test_fresh_db_creates_qramm_tables(self):
        from quirk.db import init_db

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        os.unlink(db_path)  # ensure fresh

        try:
            engine = init_db(db_path)
            names = set(sa_inspect(engine).get_table_names())
            assert "qramm_sessions" in names, f"qramm_sessions missing: {names}"
            assert "qramm_answers" in names, f"qramm_answers missing: {names}"
            assert "qramm_profiles" in names, f"qramm_profiles missing: {names}"
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)

    def test_init_db_idempotent_on_existing_db(self):
        """Re-running init_db() on a DB that already has QRAMM tables must not error."""
        from quirk.db import init_db

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        os.unlink(db_path)

        try:
            engine1 = init_db(db_path)
            names1 = set(sa_inspect(engine1).get_table_names())
            assert "qramm_sessions" in names1

            # Second call — must not raise
            engine2 = init_db(db_path)
            names2 = set(sa_inspect(engine2).get_table_names())
            assert "qramm_sessions" in names2
            assert "qramm_answers" in names2
            assert "qramm_profiles" in names2
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)

    def test_ensure_qramm_tables_function_exists_in_db_module(self):
        """_ensure_qramm_tables must be a callable in quirk.db."""
        import quirk.db as db_mod

        assert hasattr(db_mod, "_ensure_qramm_tables"), (
            "_ensure_qramm_tables not found in quirk.db"
        )
        assert callable(db_mod._ensure_qramm_tables)

    def test_ensure_qramm_tables_called_after_phase46(self):
        """Verify call order: _ensure_phase46_columns before _ensure_qramm_tables in init_db source."""
        import inspect
        import quirk.db as db_mod

        src = inspect.getsource(db_mod.init_db)
        p46_idx = src.find("_ensure_phase46_columns")
        qramm_idx = src.find("_ensure_qramm_tables")
        assert p46_idx != -1, "_ensure_phase46_columns not found in init_db"
        assert qramm_idx != -1, "_ensure_qramm_tables not found in init_db"
        assert qramm_idx > p46_idx, (
            "_ensure_qramm_tables must appear after _ensure_phase46_columns in init_db"
        )


# ---------- Phase 70 BLOCK-07: FK retrofit + PRAGMA enforcement ----------

def test_qramm_profiles_has_db_level_fk(tmp_path):
    """BLOCK-07/D-01+D-03: PRAGMA foreign_key_list reports a FK on
    qramm_profiles.session_id referencing qramm_sessions(id) ON DELETE SET NULL.
    """
    from sqlalchemy import text

    from quirk.db import init_db

    engine = init_db(str(tmp_path / "fk.db"))
    with engine.connect() as conn:
        rows = conn.execute(text("PRAGMA foreign_key_list('qramm_profiles')")).fetchall()
    # PRAGMA foreign_key_list row: (id, seq, table, from, to, on_update, on_delete, match)
    matching = [r for r in rows if r[2] == "qramm_sessions"]
    assert matching, f"No FK on qramm_profiles -> qramm_sessions. rows={rows!r}"
    on_delete = matching[0][6]
    assert on_delete == "SET NULL", (
        f"Expected ON DELETE SET NULL on qramm_profiles.session_id; got {on_delete!r}"
    )


def test_connect_event_enables_fk_pragma(tmp_path):
    """BLOCK-07/D-02: every newly opened SQLAlchemy connection has
    PRAGMA foreign_keys=1 (set by the module-level connect event listener).
    """
    from sqlalchemy import text

    from quirk.db import init_db

    engine = init_db(str(tmp_path / "pragma.db"))
    with engine.connect() as conn:
        val = conn.execute(text("PRAGMA foreign_keys")).scalar()
    assert val == 1, f"Expected PRAGMA foreign_keys=1, got {val!r}"


def test_qramm_profiles_fk_retrofit_idempotent(tmp_path):
    """BLOCK-07/D-01: init_db on the same on-disk DB twice does not raise,
    does not rebuild the table, and preserves rows inserted between calls.
    """
    from sqlalchemy import text

    from quirk.db import init_db

    db_path = str(tmp_path / "idem.db")
    engine = init_db(db_path)

    # Insert a profile row between the two init_db calls — second init_db
    # MUST NOT rebuild the table (which would lose this row had we forced
    # a rebuild). The idempotency guard should short-circuit on
    # PRAGMA foreign_key_list seeing the existing FK row.
    with engine.connect() as conn:
        conn.execute(
            text(
                "INSERT INTO qramm_profiles (industry) VALUES ('finance')"
            )
        )
        conn.commit()

    # Second init_db on the same path — must not raise.
    engine2 = init_db(db_path)

    with engine2.connect() as conn:
        cnt = conn.execute(
            text("SELECT COUNT(*) FROM qramm_profiles WHERE industry='finance'")
        ).scalar()
    assert cnt == 1, (
        f"Row inserted between init_db calls was lost — expected 1, got {cnt!r}; "
        "the rebuild migration must be idempotent."
    )
