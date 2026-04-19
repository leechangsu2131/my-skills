from fastapi.testclient import TestClient

from webapp.main import create_app


def test_homepage_renders_uploaded_batch_shell(tmp_path) -> None:
    client = TestClient(create_app(tmp_path))

    response = client.get("/")

    assert response.status_code == 200
    assert "Teacher Review Workstation" in response.text
    assert "batch" in response.text.lower()


def test_workspace_store_uses_data_web_directory(tmp_path) -> None:
    app = create_app(tmp_path)

    assert app.state.store.data_dir == tmp_path / "data" / "web"
    assert app.state.store.db_path == tmp_path / "data" / "web" / "app.db"
