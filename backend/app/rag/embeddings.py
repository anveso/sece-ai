"""Thin wrapper around the OpenAI embeddings endpoint."""
from typing import List

from openai import OpenAI

from ..config import settings

_client = OpenAI(api_key=settings.openai_api_key)


def embed_texts(texts: List[str]) -> List[List[float]]:
    if not texts:
        return []
    response = _client.embeddings.create(model=settings.embedding_model, input=texts)
    return [item.embedding for item in response.data]


def embed_query(text: str) -> List[float]:
    return embed_texts([text])[0]
