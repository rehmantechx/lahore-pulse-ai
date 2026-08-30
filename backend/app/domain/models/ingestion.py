"""Ingestion domain models.

Represents the lifecycle of data ingestion operations.
Every ingestion execution is traceable with full accounting
of records received, accepted, rejected, and duplicated.

These models do NOT represent environmental data — they
represent the operational process of acquiring data.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class IngestionOperation(StrEnum):
    """Types of ingestion operations."""

    HISTORICAL = "historical"
    LIVE = "live"
    BACKFILL = "backfill"


class IngestionStatus(StrEnum):
    """Status of an ingestion run."""

    RUNNING = "running"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"


class RecordStatus(StrEnum):
    """Outcome of an individual record during ingestion."""

    ACCEPTED = "accepted"
    REJECTED = "rejected"
    DUPLICATE = "duplicate"
    INVALID = "invalid"


class IngestionRun(BaseModel):
    """A single ingestion execution.

    Tracks the full lifecycle of one ingestion operation,
    including timing, record counts, and error information.

    Every field is designed to answer operational questions:
    - When did it run?
    - Which provider?
    - How many records came in?
    - How many were accepted vs rejected?
    - Did it fail? Why?
    """

    run_id: str = Field(
        default="",
        description="Unique run identifier",
    )
    provider: str = Field(
        default="",
        description="Provider identifier (e.g., 'openmeteo', 'openaq')",
    )
    operation: IngestionOperation = Field(
        default=IngestionOperation.HISTORICAL,
        description="Type of ingestion operation",
    )
    started_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When the ingestion run started",
    )
    finished_at: datetime | None = Field(
        default=None,
        description="When the ingestion run finished",
    )
    status: IngestionStatus = Field(
        default=IngestionStatus.RUNNING,
        description="Current status of the ingestion run",
    )
    total_records: int = Field(
        default=0,
        description="Total records received from source",
    )
    accepted_records: int = Field(
        default=0,
        description="Records that passed validation and were stored",
    )
    rejected_records: int = Field(
        default=0,
        description="Records that failed validation",
    )
    duplicated_records: int = Field(
        default=0,
        description="Records skipped because they already existed",
    )
    error_summary: str | None = Field(
        default=None,
        description="Error message if the run failed",
    )
    metadata: dict | None = Field(
        default=None,
        description="Additional run metadata (date range, parameters, etc.)",
    )

    def __init__(self, **data: object) -> None:
        """Initialize with auto-generated run_id if not provided."""
        if not data.get("run_id"):
            import uuid

            data["run_id"] = str(uuid.uuid4())
        super().__init__(**data)

    def finish(
        self,
        status: IngestionStatus,
        accepted_records: int | None = None,
        rejected_records: int | None = None,
        error_summary: str | None = None,
    ) -> None:
        """Mark the ingestion run as finished."""
        self.finished_at = datetime.now(UTC)
        self.status = status
        if accepted_records is not None:
            self.accepted_records = accepted_records
        if rejected_records is not None:
            self.rejected_records = rejected_records
        if error_summary is not None:
            self.error_summary = error_summary

    @property
    def duration_seconds(self) -> float | None:
        """Duration of the ingestion run in seconds."""
        if self.finished_at is None:
            return None
        return (self.finished_at - self.started_at).total_seconds()

    @property
    def acceptance_rate(self) -> float:
        """Fraction of received records that were accepted."""
        if self.total_records == 0:
            return 0.0
        return self.accepted_records / self.total_records


class IngestionRecord(BaseModel):
    """Outcome of a single record during ingestion.

    Every record processed by the ingestion pipeline gets
    an entry here, regardless of outcome. This provides
    full traceability for debugging and auditing.
    """

    record_id: str = Field(
        default="",
        description="Unique record identifier",
    )
    run_id: str = Field(
        default="",
        description="Reference to the ingestion run",
    )
    source_identifier: str | None = Field(
        default=None,
        description="Original identifier from the external source",
    )
    status: RecordStatus = Field(
        ...,
        description="Outcome of processing this record",
    )
    observation_id: str | None = Field(
        default=None,
        description="ID of the stored observation (if accepted)",
    )
    error: str | None = Field(
        default=None,
        description="Reason for rejection or duplication",
    )

    def __init__(self, **data: object) -> None:
        """Initialize with auto-generated record_id if not provided."""
        if not data.get("record_id"):
            import uuid

            data["record_id"] = str(uuid.uuid4())
        super().__init__(**data)
