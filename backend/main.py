from pathlib import Path

from fastapi import Depends, FastAPI, File, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from backend.database import Base, engine, get_db
from backend.importer import ImportError as CdpImportError
from backend.importer import import_csv
from backend.models import CdpEntry, Report

BASE_DIR = Path(__file__).resolve().parent.parent

Base.metadata.create_all(bind=engine)

app = FastAPI(title="CDP Report Suchportal")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(request, "index.html")


@app.get("/upload", response_class=HTMLResponse)
def upload_page(request: Request):
    return templates.TemplateResponse(request, "upload.html")


@app.get("/reports", response_class=HTMLResponse)
def reports_page(request: Request):
    return templates.TemplateResponse(request, "reports.html")


@app.post("/api/reports/upload")
async def upload_report(file: UploadFile = File(...), db: Session = Depends(get_db)):
    content = await file.read()
    try:
        report = import_csv(db, filename=file.filename or "upload.csv", content=content)
    except CdpImportError as exc:
        return {"error": str(exc)}
    return {
        "id": report.id,
        "filename": report.filename,
        "row_count": report.row_count,
        "imported_at": report.imported_at.isoformat(),
    }


@app.get("/api/reports")
def list_reports(db: Session = Depends(get_db)):
    reports = db.scalars(select(Report).order_by(Report.imported_at.desc())).all()
    return [
        {
            "id": r.id,
            "filename": r.filename,
            "source_host": r.source_host,
            "imported_at": r.imported_at.isoformat(),
            "row_count": r.row_count,
        }
        for r in reports
    ]


@app.get("/api/entries")
def list_entries(
    q: str | None = None,
    host: str | None = None,
    cluster: str | None = None,
    vswitch: str | None = None,
    device_id: str | None = None,
    report_id: int | None = None,
    limit: int = 200,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    stmt = select(CdpEntry)

    if report_id is not None:
        stmt = stmt.where(CdpEntry.report_id == report_id)
    if host:
        stmt = stmt.where(CdpEntry.host.ilike(f"%{host}%"))
    if cluster:
        stmt = stmt.where(CdpEntry.cluster.ilike(f"%{cluster}%"))
    if vswitch:
        stmt = stmt.where(CdpEntry.vswitch.ilike(f"%{vswitch}%"))
    if device_id:
        stmt = stmt.where(CdpEntry.device_id.ilike(f"%{device_id}%"))
    if q:
        like = f"%{q}%"
        conditions = [
            CdpEntry.host.ilike(like),
            CdpEntry.cluster.ilike(like),
            CdpEntry.vswitch.ilike(like),
            CdpEntry.pnic.ilike(like),
            CdpEntry.speed.ilike(like),
            CdpEntry.mac.ilike(like),
            CdpEntry.device_id.ilike(like),
            CdpEntry.device_serial.ilike(like),
            CdpEntry.port_id.ilike(like),
        ]
        if "missing" in q.lower():
            conditions.append(CdpEntry.device_id == "")
            conditions.append(CdpEntry.port_id == "")
        stmt = stmt.where(or_(*conditions))

    total = len(db.scalars(stmt).all())
    stmt = stmt.order_by(CdpEntry.host, CdpEntry.pnic).limit(limit).offset(offset)
    entries = db.scalars(stmt).all()

    return {
        "total": total,
        "items": [
            {
                "id": e.id,
                "report_id": e.report_id,
                "host": e.host,
                "cluster": e.cluster,
                "vswitch": e.vswitch,
                "pnic": e.pnic,
                "speed": e.speed,
                "mac": e.mac,
                "device_id": e.device_id,
                "device_serial": e.device_serial,
                "port_id": e.port_id,
            }
            for e in entries
        ],
    }


@app.get("/api/entries/{entry_id}")
def get_entry(entry_id: int, db: Session = Depends(get_db)):
    entry = db.get(CdpEntry, entry_id)
    if entry is None:
        return {"error": "not found"}
    return {
        "id": entry.id,
        "report_id": entry.report_id,
        "host": entry.host,
        "cluster": entry.cluster,
        "vswitch": entry.vswitch,
        "pnic": entry.pnic,
        "speed": entry.speed,
        "mac": entry.mac,
        "device_id": entry.device_id,
        "device_serial": entry.device_serial,
        "port_id": entry.port_id,
    }


@app.delete("/api/reset")
def reset_database(db: Session = Depends(get_db)):
    db.query(CdpEntry).delete()
    db.query(Report).delete()
    db.commit()
    return JSONResponse({"ok": True, "message": "Datenbank wurde geleert."})


@app.get("/api/facets")
def get_facets(db: Session = Depends(get_db)):
    clusters = db.scalars(select(CdpEntry.cluster).distinct().order_by(CdpEntry.cluster)).all()
    vswitches = db.scalars(select(CdpEntry.vswitch).distinct().order_by(CdpEntry.vswitch)).all()
    return {"clusters": clusters, "vswitches": vswitches}
