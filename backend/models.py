from datetime import datetime, timezone

from sqlalchemy import ForeignKey, Integer, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    source_host: Mapped[str | None] = mapped_column(String, nullable=True)
    imported_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    row_count: Mapped[int] = mapped_column(Integer, default=0)

    entries: Mapped[list["CdpEntry"]] = relationship(
        back_populates="report", cascade="all, delete-orphan"
    )


class CdpEntry(Base):
    __tablename__ = "cdp_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    report_id: Mapped[int] = mapped_column(ForeignKey("reports.id"), nullable=False)

    host: Mapped[str] = mapped_column(String, index=True)
    cluster: Mapped[str] = mapped_column(String, index=True)
    vswitch: Mapped[str] = mapped_column(String, index=True)
    pnic: Mapped[str] = mapped_column(String)
    speed: Mapped[str] = mapped_column(String)
    mac: Mapped[str] = mapped_column(String, index=True)
    device_id: Mapped[str] = mapped_column(String, index=True)
    device_serial: Mapped[str | None] = mapped_column(String, index=True, nullable=True)
    port_id: Mapped[str] = mapped_column(String)

    report: Mapped["Report"] = relationship(back_populates="entries")
