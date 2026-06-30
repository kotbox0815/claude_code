import csv
import io
import re

from sqlalchemy.orm import Session

from backend.models import CdpEntry, Report

EXPECTED_HEADER = ["Host", "Cluster", "vSwitch", "PNic", "Speed", "MAC", "DeviceID", "PortID"]

DEVICE_ID_RE = re.compile(r"^(?P<name>.+)\((?P<serial>[^()]+)\)$")


class ImportError(Exception):
    pass


def parse_device_id(device_id: str) -> tuple[str, str | None]:
    match = DEVICE_ID_RE.match(device_id.strip())
    if not match:
        return device_id.strip(), None
    return match.group("name").strip(), match.group("serial").strip()


def import_csv(db: Session, filename: str, content: bytes, source_host: str | None = None) -> Report:
    text = content.decode("utf-8-sig")
    reader = csv.reader(io.StringIO(text), delimiter=";", quotechar='"')

    rows = [row for row in reader if any(cell.strip() for cell in row)]
    if not rows:
        raise ImportError("CSV-Datei ist leer")

    header = [cell.strip() for cell in rows[0]]
    if header != EXPECTED_HEADER:
        raise ImportError(f"Unerwarteter CSV-Header: {header}")

    report = Report(filename=filename, source_host=source_host, row_count=0)
    db.add(report)
    db.flush()

    count = 0
    for row in rows[1:]:
        if len(row) != len(EXPECTED_HEADER):
            continue
        host, cluster, vswitch, pnic, speed, mac, device_id, port_id = (cell.strip() for cell in row)
        device_name, device_serial = parse_device_id(device_id)
        entry = CdpEntry(
            report_id=report.id,
            host=host,
            cluster=cluster,
            vswitch=vswitch,
            pnic=pnic,
            speed=speed,
            mac=mac,
            device_id=device_id,
            device_serial=device_serial,
            port_id=port_id,
        )
        db.add(entry)
        count += 1

    report.row_count = count
    db.commit()
    db.refresh(report)
    return report
