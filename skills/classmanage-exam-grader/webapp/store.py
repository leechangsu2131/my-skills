from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4


@dataclass(slots=True)
class BatchRecord:
    id: str
    title: str
    status: str
    folder: str


@dataclass(slots=True)
class SubmissionRecord:
    id: str
    batch_id: str
    student_name: str
    student_number: int | None
    status: str
    total_score: float
    total_points: float
    review_count: int
    payload_path: str
    source_pdf_path: str
    output_pdf_path: str | None = None


class WorkspaceStore:
    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace
        self.data_dir = workspace / "data" / "web"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.data_dir / "app.db"
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_db(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                create table if not exists batches (
                    id text primary key,
                    title text not null,
                    status text not null,
                    folder text not null
                );
                create table if not exists submissions (
                    id text primary key,
                    batch_id text not null,
                    student_name text not null,
                    student_number integer,
                    status text not null,
                    total_score real not null,
                    total_points real not null,
                    review_count integer not null,
                    payload_path text not null,
                    source_pdf_path text not null,
                    output_pdf_path text,
                    foreign key(batch_id) references batches(id)
                );
                """
            )
            self._migrate_schema(connection)

    def _migrate_schema(self, connection: sqlite3.Connection) -> None:
        columns = {
            row["name"]
            for row in connection.execute("pragma table_info(submissions)").fetchall()
        }
        if "output_pdf_path" not in columns:
            connection.execute("alter table submissions add column output_pdf_path text")

    def create_batch(self, title: str) -> BatchRecord:
        batch_id = uuid4().hex[:12]
        batch_folder = self.data_dir / "batches" / batch_id
        batch_folder.mkdir(parents=True, exist_ok=True)
        record = BatchRecord(id=batch_id, title=title, status="processed", folder=str(batch_folder))
        with self._connect() as connection:
            connection.execute(
                "insert into batches(id, title, status, folder) values(?, ?, ?, ?)",
                (record.id, record.title, record.status, record.folder),
            )
        return record

    def update_batch_title(self, batch_id: str, title: str) -> None:
        with self._connect() as connection:
            connection.execute("update batches set title = ? where id = ?", (title, batch_id))

    def update_batch_status(self, batch_id: str, status: str) -> None:
        with self._connect() as connection:
            connection.execute("update batches set status = ? where id = ?", (status, batch_id))

    def add_submission(
        self,
        batch_id: str,
        student_name: str,
        student_number: int | None,
        status: str,
        total_score: float,
        total_points: float,
        review_count: int,
        payload_path: Path,
        source_pdf_path: Path,
        output_pdf_path: Path | None = None,
    ) -> SubmissionRecord:
        submission_id = uuid4().hex[:12]
        record = SubmissionRecord(
            id=submission_id,
            batch_id=batch_id,
            student_name=student_name,
            student_number=student_number,
            status=status,
            total_score=total_score,
            total_points=total_points,
            review_count=review_count,
            payload_path=str(payload_path),
            source_pdf_path=str(source_pdf_path),
            output_pdf_path=str(output_pdf_path) if output_pdf_path else None,
        )
        with self._connect() as connection:
            connection.execute(
                """
                insert into submissions(
                    id, batch_id, student_name, student_number, status, total_score, total_points,
                    review_count, payload_path, source_pdf_path, output_pdf_path
                ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.id,
                    record.batch_id,
                    record.student_name,
                    record.student_number,
                    record.status,
                    record.total_score,
                    record.total_points,
                    record.review_count,
                    record.payload_path,
                    record.source_pdf_path,
                    record.output_pdf_path,
                ),
            )
        return record

    def update_submission_status(self, submission_id: str, status: str, review_count: int) -> None:
        with self._connect() as connection:
            connection.execute(
                "update submissions set status = ?, review_count = ? where id = ?",
                (status, review_count, submission_id),
            )

    def update_submission_output(self, submission_id: str, output_pdf_path: Path) -> None:
        with self._connect() as connection:
            connection.execute(
                "update submissions set output_pdf_path = ? where id = ?",
                (str(output_pdf_path), submission_id),
            )

    def list_batches(self) -> list[BatchRecord]:
        with self._connect() as connection:
            rows = connection.execute("select id, title, status, folder from batches order by rowid desc").fetchall()
        return [BatchRecord(**dict(row)) for row in rows]

    def get_batch(self, batch_id: str) -> BatchRecord:
        with self._connect() as connection:
            row = connection.execute(
                "select id, title, status, folder from batches where id = ?",
                (batch_id,),
            ).fetchone()
        if row is None:
            raise KeyError(batch_id)
        return BatchRecord(**dict(row))

    def list_submissions(self, batch_id: str) -> list[SubmissionRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                select id, batch_id, student_name, student_number, status, total_score, total_points,
                       review_count, payload_path, source_pdf_path, output_pdf_path
                from submissions where batch_id = ? order by rowid asc
                """,
                (batch_id,),
            ).fetchall()
        return [SubmissionRecord(**dict(row)) for row in rows]

    def get_submission(self, submission_id: str) -> SubmissionRecord:
        with self._connect() as connection:
            row = connection.execute(
                """
                select id, batch_id, student_name, student_number, status, total_score, total_points,
                       review_count, payload_path, source_pdf_path, output_pdf_path
                from submissions where id = ?
                """,
                (submission_id,),
            ).fetchone()
        if row is None:
            raise KeyError(submission_id)
        return SubmissionRecord(**dict(row))

    def save_payload(self, path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def load_payload(self, path: str | Path) -> dict[str, Any]:
        return json.loads(Path(path).read_text(encoding="utf-8"))
