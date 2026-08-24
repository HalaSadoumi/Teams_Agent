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


class ScriptOutput(BaseModel):
    script: str


VISUAL_TYPES = [
    "title_card",
    "bullet_list",
    "icon_row",
    "process_flow",
    "comparison",
    "stat_highlight",
    "quote",
    "timeline",
]


class StoryboardSceneLLM(BaseModel):
    narration: str
    visual_type: str
    visual_description: str
    on_screen_text: str
    transition: str


class StoryboardLLMOutput(BaseModel):
    scenes: list[StoryboardSceneLLM]


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


_SCRIPT_PROMPT = """Tu es un redacteur pedagogique qui transforme la transcription brute \
d'un chapitre de formation en un script de narration pour un cours e-learning.

Le script doit :
- preserver fidelement le sens et les faits de la transcription originale (aucune invention)
- supprimer les elements conversationnels superflus (hesitations, repetitions, "euh", \
"donc voila", apartes hors-sujet, interruptions techniques)
- ameliorer la clarte et la fluidite : une vraie narration de cours, pas une copie du transcript
- conserver la terminologie technique exacte
- relier les idees de maniere naturelle, comme un texte continu destine a etre lu a voix haute
- NE PAS resumer agressivement : l'objectif est de transformer, pas de condenser. Le script \
doit couvrir tous les points substantiels de la transcription (voir le principe fondamental \
du projet : ce n'est pas un resume video).

Utilise systematiquement les accents et diacritiques francais corrects (é, è, à, ç, etc.).
Reponds uniquement avec le script final, en francais, sans titre ni note.

--- TRANSCRIPTION BRUTE DU CHAPITRE ---
{transcript}

--- TEXTE OCR DES DIAPOSITIVES / ECRAN (contexte additionnel) ---
{ocr_text}
"""


def generate_script(transcript: str, ocr_text: str) -> str:
    client = _get_client()
    prompt = _SCRIPT_PROMPT.format(
        transcript=transcript or "(aucune parole detectee)",
        ocr_text=ocr_text or "(aucun texte detecte a l'ecran)",
    )
    response = _generate_content(
        client,
        model=settings.gemini_model,
        contents=[prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ScriptOutput,
        ),
    )
    return ScriptOutput.model_validate_json(response.text).script


_STORYBOARD_PROMPT = """Tu es un realisateur de motion design qui transforme un script de \
narration en storyboard pour une video de cours e-learning : motion graphics (texte anime, \
icones, diagrammes), PAS de diapositives brutes ni de capture de reunion (cahier des \
charges, section 6.1).

Decoupe le script ci-dessous en une sequence de scenes visuelles courtes (environ 10 a 25 \
secondes de narration chacune, decoupees a des frontieres de phrases naturelles). Pour \
chaque scene, fournis :
- "narration" : l'extrait EXACT et complet du script correspondant a cette scene. Mises bout \
a bout dans l'ordre, les narrations de toutes les scenes doivent reconstituer exactement le \
script original, sans rien omettre ni modifier.
- "visual_type" : un type choisi EXACTEMENT parmi cette liste : {visual_types}
- "visual_description" : description concrete de l'animation (ce qui apparait, bouge, \
s'enchaine a l'ecran)
- "on_screen_text" : texte court affiche a l'ecran (mots-cles, chiffres, titre) ; chaine vide \
si non pertinent
- "transition" : "fade", "cut", ou "slide"

Chaque visuel doit avoir une fonction explicative claire, jamais purement decorative.
Utilise systematiquement les accents et diacritiques francais corrects (é, è, à, ç, etc.).
Reponds en francais.

--- SCRIPT ---
{script}

--- TEXTE OCR DES DIAPOSITIVES / ECRAN (contexte additionnel, pour t'inspirer des schemas / \
donnees presentes) ---
{ocr_text}
"""


def generate_storyboard_scenes(script: str, ocr_text: str) -> list[StoryboardSceneLLM]:
    client = _get_client()
    prompt = _STORYBOARD_PROMPT.format(
        script=script,
        ocr_text=ocr_text or "(aucun texte detecte a l'ecran)",
        visual_types=", ".join(VISUAL_TYPES),
    )
    response = _generate_content(
        client,
        model=settings.gemini_model,
        contents=[prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=StoryboardLLMOutput,
        ),
    )
    return StoryboardLLMOutput.model_validate_json(response.text).scenes


class SegmentDecision(BaseModel):
    index: int
    decision: str  # "garder" | "couper"


class SegmentClassification(BaseModel):
    decisions: list[SegmentDecision]


_CLASSIFY_PROMPT = """Tu es un monteur audio qui prepare la narration originale (voix reelle \
de l'intervenant, pas de synthese vocale) d'un cours e-learning a partir d'un enregistrement \
de formation.

Pour CHAQUE segment de transcription numerote ci-dessous, decide s'il faut :
- "garder" : contenu a preserver (explications, definitions, exemples, procedures, faits \
techniques, demonstrations, conclusions) ou contenu a traiter avec discernement mais qui \
apporte une valeur reelle (questions pertinentes, echanges utiles) ;
- "couper" : contenu a nettoyer (hesitations, "euh", repetitions accidentelles, silences, \
apartes hors-sujet, interruptions techniques, redondances pures d'un meme point deja fait).

L'objectif n'est PAS une compression agressive : dans le doute, garde le segment. Le resultat \
sera assemble tel quel (audio reel decoupe et recolle), donc chaque segment "garde" doit rester \
comprehensible seul, sans dependre d'un segment coupe juste avant.

Reponds pour CHAQUE segment ci-dessous, avec le meme index, sans en omettre aucun.

--- SEGMENTS ---
{segments_text}
"""


def classify_segments(indexed_texts: list[tuple[int, str]]) -> dict[int, str]:
    """Returns {segment_index: "garder" | "couper"}."""
    client = _get_client()
    segments_text = "\n".join(f"[{i}] {text}" for i, text in indexed_texts)
    prompt = _CLASSIFY_PROMPT.format(segments_text=segments_text)

    response = _generate_content(
        client,
        model=settings.gemini_model,
        contents=[prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=SegmentClassification,
        ),
    )
    parsed = SegmentClassification.model_validate_json(response.text)
    return {d.index: d.decision for d in parsed.decisions}


class VisualPlanLLM(BaseModel):
    index: int
    visual_type: str
    visual_description: str
    on_screen_text: str
    transition: str


class VisualPlanOutput(BaseModel):
    plans: list[VisualPlanLLM]


_VISUAL_PLAN_PROMPT = """Tu es un realisateur de motion design qui habille visuellement la \
narration originale (voix reelle de l'intervenant, deja decoupee en scenes) d'un cours \
e-learning : motion graphics (texte anime, icones, diagrammes), PAS de diapositives brutes ni \
de capture de reunion (cahier des charges, section 6.1).

Pour CHAQUE scene de narration numerotee ci-dessous, propose le visuel qui l'accompagne. \
Reponds pour CHAQUE scene, avec le meme index, sans en omettre aucune :
- "index" : le meme numero que le segment d'entree correspondant
- "visual_type" : un type choisi EXACTEMENT parmi cette liste : {visual_types}
- "visual_description" : description concrete de l'animation (ce qui apparait, bouge, \
s'enchaine a l'ecran)
- "on_screen_text" : texte court affiche a l'ecran (mots-cles, chiffres, titre) ; chaine vide \
si non pertinent
- "transition" : "fade", "cut", ou "slide"

Chaque visuel doit avoir une fonction explicative claire, jamais purement decorative.
Utilise systematiquement les accents et diacritiques francais corrects (é, è, à, ç, etc.).
Reponds en francais.

--- SCENES DE NARRATION (texte reel, deja fixe - ne le modifie pas) ---
{scenes_text}

--- TEXTE OCR DES DIAPOSITIVES / ECRAN (contexte additionnel) ---
{ocr_text}
"""


def generate_visual_plan(
    indexed_narrations: list[tuple[int, str]], ocr_text: str
) -> dict[int, VisualPlanLLM]:
    client = _get_client()
    scenes_text = "\n".join(f"[{i}] {text}" for i, text in indexed_narrations)
    prompt = _VISUAL_PLAN_PROMPT.format(
        scenes_text=scenes_text,
        ocr_text=ocr_text or "(aucun texte detecte a l'ecran)",
        visual_types=", ".join(VISUAL_TYPES),
    )
    response = _generate_content(
        client,
        model=settings.gemini_model,
        contents=[prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=VisualPlanOutput,
        ),
    )
    parsed = VisualPlanOutput.model_validate_json(response.text)
    by_index = {plan.index: plan for plan in parsed.plans}

    default_plan = VisualPlanLLM(
        index=-1, visual_type="bullet_list", visual_description="", on_screen_text="", transition="fade"
    )
    return {idx: by_index.get(idx, default_plan) for idx, _ in indexed_narrations}
