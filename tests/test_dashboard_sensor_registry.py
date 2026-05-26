"""Integration tests for GET /api/sensor/registry endpoint.

TDD RED phase — tests define expected endpoint behaviour before implementation.
Uses per-test isolated in-memory DBs (unique cache= names) to avoid shared-state bleed.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import itertools

import pytest

_db_counter = itertools.count(1)


def _make_isolated_client():
    """Return a (TestClient, TestingSession) pair using a unique in-memory SQLite DB."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from quirk.dashboard.api.app import create_app
    from quirk.dashboard.api.deps import get_db
    from quirk.models import Base
    from fastapi.testclient import TestClient

    db_name = f"registry_test_{next(_db_counter)}"
    engine = create_engine(
        f"sqlite:///file:{db_name}?mode=memory&cache=shared&uri=true",
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

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app, headers={"X-Quirk-Request": "1"})
    return client, TestingSession


def _seed_sensor(db, *, sensor_id, segment, sensor_version="1.0", last_push_at=None,
                 enrolled_at=None, expected_cadence_minutes=1440):
    """Seed a Sensor row into the test DB."""
    from quirk.models import Sensor
    now = datetime.now(timezone.utc).replace(tzinfo=None)
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
    """Registry endpoint with seeded sensor rows — each test gets an isolated DB."""

    def test_registry_returns_one_sensor(self):
        """Seeding one sensor → registry returns exactly one item."""
        client, TestingSession = _make_isolated_client()
        db = TestingSession()
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        _seed_sensor(db, sensor_id="s-abc", segment="dmz", sensor_version="1.2",
                     last_push_at=now - timedelta(minutes=5))
        db.close()

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

    def test_current_sensor_status(self):
        """A sensor that just pushed has status 'current'."""
        client, TestingSession = _make_isolated_client()
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        db = TestingSession()
        _seed_sensor(db, sensor_id="s-cur", segment="corp",
                     last_push_at=now - timedelta(minutes=5),
                     expected_cadence_minutes=1440)
        db.close()

        resp = client.get("/api/sensor/registry")
        assert resp.status_code == 200
        sensors = resp.json()["sensors"]
        assert len(sensors) == 1
        assert sensors[0]["status"] == "current"

    def test_never_pushed_sensor_status_unknown(self):
        """A sensor that never pushed has status 'unknown'."""
        client, TestingSession = _make_isolated_client()
        db = TestingSession()
        _seed_sensor(db, sensor_id="s-new", segment="ot", last_push_at=None)
        db.close()

        resp = client.get("/api/sensor/registry")
        assert resp.status_code == 200
        sensors = resp.json()["sensors"]
        assert len(sensors) == 1
        assert sensors[0]["status"] == "unknown"

    def test_stale_sensor_status(self):
        """A sensor that pushed > 2×cadence ago (but < 30 days) → 'stale'."""
        client, TestingSession = _make_isolated_client()
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        db = TestingSession()
        # cadence=60 min → 2×60=120 min threshold; push was 130 min ago
        _seed_sensor(db, sensor_id="s-stale", segment="dmz",
                     last_push_at=now - timedelta(minutes=130),
                     expected_cadence_minutes=60)
        db.close()

        resp = client.get("/api/sensor/registry")
        assert resp.status_code == 200
        sensors = resp.json()["sensors"]
        assert len(sensors) == 1
        assert sensors[0]["status"] == "stale"

    def test_response_fields_complete(self):
        """Each registry item has sensor_id, segment, sensor_version, last_push_at, status."""
        client, TestingSession = _make_isolated_client()
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        db = TestingSession()
        _seed_sensor(db, sensor_id="s-full", segment="corp", sensor_version="2.1",
                     last_push_at=now - timedelta(minutes=10), expected_cadence_minutes=1440)
        db.close()

        resp = client.get("/api/sensor/registry")
        assert resp.status_code == 200
        items = resp.json()["sensors"]
        assert len(items) == 1
        item = items[0]
        assert set(item.keys()) >= {"sensor_id", "segment", "sensor_version", "last_push_at", "status"}
