from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base
from backend.importer import ImportError as CdpImportError
from backend.importer import import_csv, parse_device_id
from backend.models import CdpEntry

FIXTURE = Path(__file__).parent / "fixtures" / "sample_cdp_report.csv"


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_parse_device_id():
    assert parse_device_id("dfrx0159eq-1159(FDO260211XJ)") == ("dfrx0159eq-1159", "FDO260211XJ")
    assert parse_device_id("no-parens") == ("no-parens", None)


def test_import_csv_creates_report_and_entries(db_session):
    content = FIXTURE.read_bytes()
    report = import_csv(db_session, filename=FIXTURE.name, content=content)

    assert report.id is not None
    assert report.row_count == 36

    entries = db_session.query(CdpEntry).filter_by(report_id=report.id).all()
    assert len(entries) == 36

    first = entries[0]
    assert first.host == "dfritesx01.dzbank.vrnet"
    assert first.cluster == "Tanzu-Test-FBE"
    assert first.mac == "30:3e:a7:08:5e:d4"
    assert first.device_serial == "FDO260211XJ"


def test_import_skips_rows_without_vswitch(db_session):
    # Build a CSV where one row has an empty vSwitch
    csv_content = (
        '"Host";"Cluster";"vSwitch";"PNic";"Speed";"MAC";"DeviceID";"PortID"\n'
        '"host1";"cl1";"";"vmnic0";"10000";"aa:bb:cc:dd:ee:ff";"sw1(SN1)";"Eth1/1"\n'
        '"host1";"cl1";"vds1";"vmnic1";"10000";"aa:bb:cc:dd:ee:f0";"sw1(SN1)";"Eth1/2"\n'
    ).encode()
    report = import_csv(db_session, filename="test.csv", content=csv_content)
    assert report.row_count == 1  # row without vSwitch skipped


def test_import_stores_empty_device_id(db_session):
    csv_content = (
        '"Host";"Cluster";"vSwitch";"PNic";"Speed";"MAC";"DeviceID";"PortID"\n'
        '"host1";"cl1";"vds1";"vmnic0";"10000";"aa:bb:cc:dd:ee:ff";"";""\n'
    ).encode()
    report = import_csv(db_session, filename="test.csv", content=csv_content)
    assert report.row_count == 1
    entry = db_session.query(CdpEntry).filter_by(report_id=report.id).first()
    assert entry.device_id == ""
    assert entry.port_id == ""


def test_import_csv_rejects_bad_header(db_session):
    bad_content = b'"Foo";"Bar"\n"x";"y"\n'
    with pytest.raises(CdpImportError):
        import_csv(db_session, filename="bad.csv", content=bad_content)
