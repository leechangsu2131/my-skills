import sqlite3

from webapp.store import WorkspaceStore


def test_workspace_store_adds_missing_output_pdf_path_column_for_existing_db(tmp_path) -> None:
    data_dir = tmp_path / "data" / "web"
    data_dir.mkdir(parents=True, exist_ok=True)
    db_path = data_dir / "app.db"

    connection = sqlite3.connect(db_path)
    connection.executescript(
        """
        create table batches (
            id text primary key,
            title text not null,
            status text not null,
            folder text not null
        );
        create table submissions (
            id text primary key,
            batch_id text not null,
            student_name text not null,
            student_number integer,
            status text not null,
            total_score real not null,
            total_points real not null,
            review_count integer not null,
            payload_path text not null,
            source_pdf_path text not null
        );
        """
    )
    connection.close()

    store = WorkspaceStore(tmp_path)

    with store._connect() as migrated:
        columns = {
            row["name"]
            for row in migrated.execute("pragma table_info(submissions)").fetchall()
        }

    assert "output_pdf_path" in columns
    assert store.db_path == tmp_path / "data" / "web" / "app.db"


def test_workspace_store_adds_batch_ocr_columns_for_existing_db(tmp_path) -> None:
    data_dir = tmp_path / "data" / "web"
    data_dir.mkdir(parents=True, exist_ok=True)
    db_path = data_dir / "app.db"

    connection = sqlite3.connect(db_path)
    connection.executescript(
        """
        create table batches (
            id text primary key,
            title text not null,
            status text not null,
            folder text not null
        );
        create table submissions (
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
            output_pdf_path text
        );
        """
    )
    connection.close()

    store = WorkspaceStore(tmp_path)

    with store._connect() as migrated:
        columns = {
            row["name"]
            for row in migrated.execute("pragma table_info(batches)").fetchall()
        }

    assert {"blank_exam_path", "ocr_metadata_path", "layout_status"} <= columns
