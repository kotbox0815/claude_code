from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import Base, get_db
from backend.main import app

FIXTURE = Path(__file__).parent / "fixtures" / "sample_cdp_report.csv"


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine)

    def override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def upload_fixture(client):
    with open(FIXTURE, "rb") as f:
        return client.post(
            "/api/reports/upload",
            files={"file": (FIXTURE.name, f, "text/csv")},
        )


def test_upload_and_list_reports(client):
    res = upload_fixture(client)
    assert res.status_code == 200
    body = res.json()
    assert body["row_count"] == 36

    res = client.get("/api/reports")
    assert res.status_code == 200
    reports = res.json()
    assert len(reports) == 1
    assert reports[0]["row_count"] == 36


def test_search_entries_fulltext(client):
    upload_fixture(client)

    res = client.get("/api/entries", params={"q": "30:3e:a7:08:5e:d4"})
    data = res.json()
    assert data["total"] == 1
    assert data["items"][0]["host"] == "dfritesx01.dzbank.vrnet"


def test_search_entries_filters(client):
    upload_fixture(client)

    res = client.get("/api/entries", params={"cluster": "Tanzu-Test-FBE"})
    data = res.json()
    assert data["total"] == 12

    res = client.get("/api/entries", params={"host": "dfritesx01.dzbank.vrnet"})
    data = res.json()
    assert data["total"] == 4


def test_missing_pnics_none_when_single_report(client):
    upload_fixture(client)
    res = client.get("/api/missing-pnics")
    assert res.status_code == 200
    assert res.json() == []


def test_missing_pnics_detected(client):
    upload_fixture(client)

    # Second report with one pnic removed
    original = FIXTURE.read_bytes().decode("utf-8")
    lines = original.strip().splitlines()
    # Remove the second data row (vmnic0 of dfritesx01)
    reduced = "\n".join([lines[0]] + lines[2:]) + "\n"

    res = client.post(
        "/api/reports/upload",
        files={"file": ("reduced.csv", reduced.encode(), "text/csv")},
    )
    assert res.status_code == 200

    res = client.get("/api/missing-pnics")
    data = res.json()
    assert len(data) == 1
    assert data[0]["host"] == "dfritesx01.dzbank.vrnet"
    assert data[0]["pnic"] == "vmnic0"
    assert data[0]["last_seen_report_id"] == 1


def test_facets(client):
    upload_fixture(client)
    res = client.get("/api/facets")
    data = res.json()
    assert "Tanzu-Test-FBE" in data["clusters"]
    assert "dfvdstntaci03" in data["vswitches"]
