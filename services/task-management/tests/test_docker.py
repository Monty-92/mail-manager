"""Docker container tests for the task management service.

Run with: pytest tests/test_docker.py -v
Requires: Docker daemon running

These tests are marked with @pytest.mark.docker and can be skipped
via: pytest -m "not docker"
"""

import subprocess
import time
from pathlib import Path

import httpx
import pytest

SERVICE_NAME = "task-management"
IMAGE_TAG = "mailmanager-task-management:test"
CONTAINER_NAME = "test-task-management"
CONTAINER_PORT = 8006
HOST_PORT = 18006

SERVICE_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def docker_image():
    """Build the Docker image for the task management service."""
    build_result = subprocess.run(
        ["docker", "build", "-t", IMAGE_TAG, "."],
        cwd=str(SERVICE_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert build_result.returncode == 0, f"Docker build failed:\n{build_result.stderr}"
    yield IMAGE_TAG
    subprocess.run(["docker", "rmi", IMAGE_TAG], capture_output=True)


@pytest.fixture(scope="module")
def docker_container(docker_image):
    """Run the container and wait for it to be healthy."""
    subprocess.run(["docker", "rm", "-f", CONTAINER_NAME], capture_output=True)

    run_result = subprocess.run(
        [
            "docker", "run", "-d",
            "--name", CONTAINER_NAME,
            "-p", f"{HOST_PORT}:{CONTAINER_PORT}",
            "-e", "DATABASE_URL=postgresql+asyncpg://test:test@localhost:5432/test",
            "-e", "REDIS_URL=redis://localhost:6379/0",
            docker_image,
        ],
        capture_output=True,
        text=True,
    )
    assert run_result.returncode == 0, f"Docker run failed:\n{run_result.stderr}"

    base_url = f"http://localhost:{HOST_PORT}"
    healthy = False
    for _ in range(30):
        try:
            resp = httpx.get(f"{base_url}/health", timeout=2.0)
            if resp.status_code == 200:
                healthy = True
                break
        except httpx.HTTPError:
            pass
        time.sleep(1)

    if not healthy:
        logs = subprocess.run(
            ["docker", "logs", CONTAINER_NAME], capture_output=True, text=True
        )
        subprocess.run(["docker", "rm", "-f", CONTAINER_NAME], capture_output=True)
        pytest.fail(f"Container did not become healthy.\nLogs:\n{logs.stdout}\n{logs.stderr}")

    yield base_url

    subprocess.run(["docker", "rm", "-f", CONTAINER_NAME], capture_output=True)


@pytest.mark.docker
class TestDockerBuild:
    def test_image_builds_successfully(self, docker_image):
        """The Docker image builds without errors."""
        result = subprocess.run(
            ["docker", "image", "inspect", docker_image],
            capture_output=True,
        )
        assert result.returncode == 0


@pytest.mark.docker
class TestDockerContainer:
    def test_health_endpoint(self, docker_container):
        """Container health endpoint returns ok."""
        resp = httpx.get(f"{docker_container}/health", timeout=5.0)
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    def test_list_tasks_endpoint_registered(self, docker_container):
        """GET /tasks route is accessible."""
        resp = httpx.get(f"{docker_container}/tasks", timeout=5.0)
        assert resp.status_code in (200, 500)

    def test_list_task_lists_endpoint_registered(self, docker_container):
        """GET /tasks/lists route is accessible."""
        resp = httpx.get(f"{docker_container}/tasks/lists", timeout=5.0)
        assert resp.status_code in (200, 500)

    def test_extract_endpoint_registered(self, docker_container):
        """POST /tasks/extract/{email_id} route is accessible."""
        resp = httpx.post(f"{docker_container}/tasks/extract/test-id", timeout=5.0)
        assert resp.status_code in (200, 500)

    def test_email_tasks_endpoint_registered(self, docker_container):
        """GET /tasks/email/{email_id} route is accessible."""
        resp = httpx.get(f"{docker_container}/tasks/email/test-id", timeout=5.0)
        assert resp.status_code in (200, 500)

    def test_get_task_endpoint_registered(self, docker_container):
        """GET /tasks/{task_id} route is accessible."""
        resp = httpx.get(f"{docker_container}/tasks/test-id", timeout=5.0)
        assert resp.status_code in (404, 500)

    def test_openapi_docs_available(self, docker_container):
        """OpenAPI schema is served with the correct title."""
        resp = httpx.get(f"{docker_container}/openapi.json", timeout=5.0)
        assert resp.status_code == 200
        assert resp.json()["info"]["title"] == "Task Management Service"
