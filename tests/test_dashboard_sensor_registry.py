"""Integration tests for GET /api/sensor/registry endpoint.

TDD RED phase — tests define expected endpoint behaviour before implementation.
Uses dashboard_client fixture (in-memory SQLite, auth bypassed via X-Quirk-Request header).
"""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest


def _seed_sensor(db, *, sensor_id, segment, sensor_version="1.0", last_push_at=None, enrolled_at=None,
                 expected_cadence_minutes=1440):
    """Seed a Sensor row into the test DB."""
    from quirk.models import Sensor
    now = datetime(2026, 5, 26, 12, 0, 0)
    if enrolled_at is None:
        enrolled_at = now - timedelta(hours=1)
    s = Sensor(
        sensor_id=sensor_id,
        segment=segment,
        sensor_version=sensor_version,
        last_push_at=last_push_at,
        enrolled_at=enrolled_at,
        expected_cadence_minutes=expected_cadence_minutes,
    )
    db.add(s)
    db.commit()
    return s


class TestSensorRegistryEmpty:
    """Registry endpoint when no sensors are enrolled."""

    def test_no_sensors_returns_empty_list(self, dashboard_client):
        resp = dashboard_client.get("/api/sensor/registry")
        assert resp.status_code == 200
        data = resp.json()
        assert "sensors" in data
        assert data["sensors"] == []


class TestSensorRegistrySeeded:
    """Registry endpoint with seeded sensor rows."""

    def test_registry_returns_one_sensor(self, dashboard_client):
        """Seeding one sensor → registry returns exactly one item."""
        from quirk.dashboard.api.deps import get_db
        from quirk.dashboard.api.app import create_app
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from quirk.models import Base
        from fastapi.testclient import TestClient

        engine = create_engine(
            "sqlite:///file::memory:?cache=shared&uri=true",
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(engine)
        TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

        def override_get_db():
            db = TestingSession()
            try:
                yield db
            finally:
                db.close()

        db = TestingSession()
        _seed_sensor(db, sensor_id="s-abc", segment="dmz", sensor_version="1.2",
                     last_push_at=datetime(2026, 5, 26, 11, 59, 0))
        db.close()

        app = create_app()
        app.dependency_overrides[get_db] = override_get_db
        client = TestClient(app, headers={"X-Quirk-Request": "1"})

        resp = client.get("/api/sensor/registry")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["sensors"]) == 1
        item = data["sensors"][0]
        assert item["sensor_id"] == "s-abc"
        assert item["segment"] == "dmz"
        assert item["sensor_version"] == "1.2"
        assert "last_push_at" in item
        assert "status" in item

    def test_current_sensor_status(self, dashboard_client):
        """A sensor that just pushed has status 'current'."""
        from quirk.dashboard.api.deps import get_db
        from quirk.dashboard.api.app import create_app
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from quirk.models import Base
        from fastapi.testclient import TestClient

        engine = create_engine(
            "sqlite:///file::memory:?cache=shared&uri=true",
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(engine)
        TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

        def override_get_db():
            db = TestingSession()
            try:
                yield db
            finally:
                db.close()

        from datetime import timezone
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        db = TestingSession()
        # Just pushed — within cadence
        _seed_sensor(db, sensor_id="s-cur", segment="corp",
                     last_push_at=now - timedelta(minutes=5),
                     expected_cadence_minutes=1440)
        db.close()

        app = create_app()
        app.dependency_overrides[get_db] = override_get_db
        client = TestClient(app, headers={"X-Quirk-Request": "1"})

        resp = client.get("/api/sensor/registry")
        assert resp.status_code == 200
        sensors = resp.json()["sensors"]
        assert len(sensors) == 1
        assert sensors[0]["status"] == "current"

    def test_never_pushed_sensor_status_unknown(self, dashboard_client):
        """A sensor that never pushed has status 'unknown'."""
        from quirk.dashboard.api.deps import get_db
        from quirk.dashboard.api.app import create_app
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from quirk.models import Base
        from fastapi.testclient import TestClient

        engine = create_engine(
            "sqlite:///file::memory:?cache=shared&uri=true",
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(engine)
        TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

        def override_get_db():
            db = TestingSession()
            try:
                yield db
            finally:
                db.close()

        db = TestingSession()
        _seed_sensor(db, sensor_id="s-new", segment="ot", last_push_at=None)
        db.close()

        app = create_app()
        app.dependency_overrides[get_db] = override_get_db
        client = TestClient(app, headers={"X-Quirk-Request": "1"})

        resp = client.get("/api/sensor/registry")
        assert resp.status_code == 200
        sensors = resp.json()["sensors"]
        assert len(sensors) == 1
        assert sensors[0]["status"] == "unknown"

    def test_stale_sensor_status(self, dashboard_client):
        """A sensor that pushed > 2×cadence ago (but < 30 days) → 'stale'."""
        from quirk.dashboard.api.deps import get_db
        from quirk.dashboard.api.app import create_app
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from quirk.models import Base
        from fastapi.testclient import TestClient

        engine = create_engine(
            "sqlite:///file::memory:?cache=shared&uri=true",
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(engine)
        TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

        def override_get_db():
            db = TestingSession()
            try:
                yield db
            finally:
                db.close()

        from datetime import timezone
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        db = TestingSession()
        # cadence=60 min → 2×60=120 min threshold; push was 130 min ago
        _seed_sensor(db, sensor_id="s-stale", segment="dmz",
                     last_push_at=now - timedelta(minutes=130),
                     expected_cadence_minutes=60)
        db.close()

        app = create_app()
        app.dependency_overrides[get_db] = override_get_db
        client = TestClient(app, headers={"X-Quirk-Request": "1"})

        resp = client.get("/api/sensor/registry")
        assert resp.status_code == 200
        sensors = resp.json()["sensors"]
        assert len(sensors) == 1
        assert sensors[0]["status"] == "stale"
