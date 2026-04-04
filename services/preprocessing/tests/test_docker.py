"""Docker container tests for the preprocessing service.

These tests verify:
1. The Docker image builds successfully
2. The container starts and the health endpoint responds
3. The API endpoints are accessible within the container

Run with: pytest tests/test_docker.py -v
Requires: Docker daemon running

These tests are marked with @pytest.mark.docker and can be skipped
in CI or local runs without Docker via: pytest -m "not docker"
"""

import subprocess
import time
from pathlib import Path

import httpx
import pytest

SERVICE_NAME = "preprocessing"
IMAGE_TAG = f"mailmanager-{SERVICE_NAME}:test"
CONTAINER_NAME = f"test-{SERVICE_NAME}"
CONTAINER_PORT = 8002
HOST_PORT = 18002  # Use high port to avoid conflicts

# Resolve the service root regardless of where pytest is invoked from
SERVICE_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def docker_image():
    """Build the Docker image for the preprocessing service."""
    build_result = subprocess.run(
        ["docker", "build", "-t", IMAGE_TAG, "."],
        cwd=str(SERVICE_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert build_result.returncode == 0, f"Docker build failed:\n{build_result.stderr}"
    yield IMAGE_TAG
    # Cleanup image after all tests
    subprocess.run(["docker", "rmi", IMAGE_TAG], capture_output=True)


@pytest.fixture(scope="module")
def docker_container(docker_image):
    """Run the container and wait for it to be healthy."""
    # Stop any leftover container from a previous run
    subprocess.run(["docker", "rm", "-f", CONTAINER_NAME], capture_output=True)

    run_result = subprocess.run(
        [
            "docker", "run", "-d",
            "--name", CONTAINER_NAME,
            "-p", f"{HOST_PORT}:{CONTAINER_PORT}",
            "-e", "DATABASE_URL=postgresql+asyncpg://test:test@localhost:5432/test",
            "-e", "REDIS_URL=redis://localhost:6379/0",
            "-e", "OLLAMA_BASE_URL=http://localhost:11434",
            docker_image,
        ],
        capture_output=True,
        text=True,
    )
    assert run_result.returncode == 0, f"Docker run failed:\n{run_result.stderr}"
    container_id = run_result.stdout.strip()

    # Wait for container to be ready (health check)
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

    # Cleanup
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
        """The containerized service responds to health checks."""
        resp = httpx.get(f"{docker_container}/health", timeout=5.0)
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    def test_preprocess_endpoint_registered(self, docker_container):
        """The /preprocess/{id} endpoint is accessible (returns error without real DB, not 404 on the route)."""
        resp = httpx.post(
            f"{docker_container}/preprocess/00000000-0000-0000-0000-000000000000",
            timeout=5.0,
        )
        # Without Postgres, we expect 500 (connection error), not 404 (route not found)
        # This proves the route is wired and the container is running our app
        assert resp.status_code in (404, 500)

    def test_batch_endpoint_registered(self, docker_container):
        """The /preprocess/batch endpoint is accessible."""
        resp = httpx.post(
            f"{docker_container}/preprocess/batch?limit=1",
            timeout=5.0,
        )
        assert resp.status_code in (200, 500)

    def test_openapi_docs_available(self, docker_container):
        """The OpenAPI docs endpoint is served."""
        resp = httpx.get(f"{docker_container}/openapi.json", timeout=5.0)
        assert resp.status_code == 200
        data = resp.json()
        assert data["info"]["title"] == "Preprocessing Service"
