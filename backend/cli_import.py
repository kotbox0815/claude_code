import sys
from pathlib import Path

from backend.database import Base, SessionLocal, engine
from backend.importer import ImportError, import_csv


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python -m backend.cli_import <pfad-zur-csv>")
        sys.exit(1)

    path = Path(sys.argv[1])
    if not path.is_file():
        print(f"Datei nicht gefunden: {path}")
        sys.exit(1)

    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        content = path.read_bytes()
        report = import_csv(db, filename=path.name, content=content)
        print(f"Import OK: Report #{report.id}, {report.row_count} Zeilen importiert.")
    except ImportError as exc:
        print(f"Import fehlgeschlagen: {exc}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
