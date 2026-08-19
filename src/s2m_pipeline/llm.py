"""Gemini-based content generation: chapter titling (Sprint 2), and later
script/storyboard generation (Sprint 3).

Multimodal by design (cahier des charges section 5.2, "point critique du
projet"): the model is given the transcript text, the OCR'd slide text, AND
the actual frame image(s) together, so it can reason about what's shown on
screen even when that information never appears in speech or OCR (e.g. a
diagram's layout, a highlighted region, a demo).
"""

from __future__ import annotations

from pathlib import Path

from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from PIL import Image
from pydantic import BaseModel
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from .config import settings


def _is_transient(exc: BaseException) -> bool:
    """Retry on rate limits / server-side overload, not on bad requests."""
    return isinstance(exc, genai_errors.APIError) and exc.code in (429, 500, 503, 504)


@retry(
    retry=retry_if_exception(_is_transient),
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=2, max=30),
    reraise=True,
)
def _generate_content(client: genai.Client, **kwargs):
    return client.models.generate_content(**kwargs)

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY not set. Add it to .env (see .env.example).")
        _client = genai.Client(api_key=settings.gemini_api_key)
    return _client


class ChapterContent(BaseModel):
    title: str
    summary: str
    key_points: list[str]


_CHAPTER_PROMPT = """Tu es un ingenieur pedagogique qui prepare un cours e-learning \
a partir d'un enregistrement de formation interne d'entreprise.

Voici un extrait : la transcription de ce que dit l'intervenant, le texte OCR \
extrait des diapositives ou de l'ecran partage a ce moment, et une ou plusieurs \
captures d'ecran representatives.

Analyse ensemble ce que l'intervenant DIT et ce qui est MONTRE a l'ecran : une \
diapositive peut contenir des informations (schemas, listes, titres) absentes de \
la transcription, et inversement. Les deux se completent.

Produis pour ce segment :
- un titre de chapitre court et precis (5-8 mots)
- un resume fidele de 2-3 phrases
- 3 a 5 points cles a retenir

Reponds en francais, avec un contenu strictement fidele a la source (pas d'invention).
Utilise systematiquement les accents et diacritiques francais corrects (é, è, à, ç, etc.) :
"securite" est une faute, la forme correcte est "sécurité".

--- TRANSCRIPTION ---
{transcript}

--- TEXTE OCR DES DIAPOSITIVES / ECRAN ---
{ocr_text}
"""


def generate_chapter_content(
    transcript: str, ocr_text: str, frame_paths: list[Path]
) -> ChapterContent:
    client = _get_client()
    prompt = _CHAPTER_PROMPT.format(
        transcript=transcript or "(aucune parole detectee)",
        ocr_text=ocr_text or "(aucun texte detecte a l'ecran)",
    )

    contents: list = [prompt]
    for frame_path in frame_paths:
        contents.append(Image.open(frame_path))

    response = _generate_content(
        client,
        model=settings.gemini_model,
        contents=contents,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ChapterContent,
        ),
    )
    return ChapterContent.model_validate_json(response.text)
