import httpx
import structlog

from preprocessing.config import settings
from preprocessing.schemas import EmbeddingResult

logger = structlog.get_logger()


async def generate_embedding(text: str) -> EmbeddingResult:
    """Generate an embedding for the given text using Ollama."""
    url = f"{settings.ollama_base_url}/api/embed"
    payload = {
        "model": settings.ollama_embed_model,
        "input": text,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()

    embedding = data["embeddings"][0]
    logger.debug(
        "embedding generated",
        model=settings.ollama_embed_model,
        dimensions=len(embedding),
    )
    return EmbeddingResult(
        embedding=embedding,
        model=data.get("model", settings.ollama_embed_model),
        token_count=data.get("total_duration", 0),
    )
