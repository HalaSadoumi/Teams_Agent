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


# --- Animated explainer scenes (Sprint 3, visual generation) -----------------
#
# Controlled vocabulary of animated scene archetypes. Each maps 1:1 to a
# React/Remotion component that draws and animates itself; keeping the list
# closed (rather than free-form visual descriptions) is what makes the
# renderer generic - the LLM picks an archetype and fills its text slots,
# and no scene needs bespoke code.
SCENE_ARCHETYPES = {
    "pillars": "2 a 4 fondements/piliers nommes qui s'elevent (les composantes d'un concept)",
    "actor_action_target": "un acteur agit sur une cible, avec un effet (un envoi, une demande, une attaque, une sollicitation)",
    "data_flow": "des sources alimentent une etape centrale puis un resultat (collecte, traitement, validation)",
    "concentric_layers": "des couches/niveaux successifs autour d'un element central",
    "comparison": "deux situations opposees cote a cote (bon vs mauvais, avant/apres, deux options)",
    "checklist": "une liste de points/regles qui se cochent une a une",
    "stat_reveal": "un chiffre cle mis en avant avec son contexte (pourcentage, montant, duree)",
    "timeline": "des etapes qui se succedent dans le temps (processus, evolution, chronologie)",
    "state_change": "des elements qui passent d'un etat a un autre (verrouillage, validation, transformation)",
    "permission_matrix": "des roles/profils avec des droits ou acces differencies",
    "separated_groups": "des groupes ou zones cloisonnes, separes par une barriere",
    "title_statement": "une definition ou un message cle affiche typographiquement, sans schema",
}

# Domain-neutral icon vocabulary, validated against the installed
# lucide-react package. The LLM picks one per scene, so the visuals adapt to
# any subject matter instead of depending on a hardcoded keyword dictionary
# built for one domain.
SCENE_ICONS = [
    "User", "Users", "UserCheck", "UserX", "UserPlus", "UserMinus", "Handshake", "Baby",
    "GraduationCap", "Briefcase", "Crown", "Contact", "Mail", "MessageSquare", "MessageCircle", "Phone",
    "Megaphone", "Bell", "Send", "Share2", "Video", "Mic", "Languages", "FileText",
    "Files", "Folder", "FolderOpen", "ClipboardList", "ClipboardCheck", "BookOpen", "Newspaper", "Database",
    "Table", "Archive", "FileSignature", "Receipt", "Stamp", "Banknote", "Coins", "CreditCard",
    "PiggyBank", "TrendingUp", "TrendingDown", "ChartBar", "ChartPie", "ChartLine", "Calculator", "ShoppingCart",
    "Tag", "Landmark", "Building2", "Store", "Factory", "Clock", "Calendar", "CalendarDays",
    "Timer", "Hourglass", "History", "AlarmClock", "Laptop", "Smartphone", "Monitor", "Server",
    "Cloud", "Wifi", "Globe", "Code", "Terminal", "Cpu", "HardDrive", "Printer",
    "Plug", "Settings", "Wrench", "Cog", "Shield", "ShieldCheck", "ShieldAlert", "Lock",
    "Unlock", "Key", "KeyRound", "Fingerprint", "Eye", "EyeOff", "Bug", "Siren",
    "Flame", "Radar", "Check", "CheckCheck", "X", "Ban", "Plus", "Minus",
    "ArrowRight", "ArrowUp", "ArrowDown", "RefreshCw", "Play", "Pause", "Search", "Filter",
    "Download", "Upload", "Link", "Copy", "Trash2", "Pencil", "Save", "AlertCircle",
    "AlertTriangle", "AlertOctagon", "Info", "HelpCircle", "CircleQuestionMark", "Lightbulb", "Sparkles", "Star",
    "Award", "Trophy", "Target", "Flag", "MapPin", "Map", "Truck", "Package",
    "Plane", "Car", "Home", "Warehouse", "Route", "Navigation", "HeartPulse", "Stethoscope",
    "Activity", "Brain", "Hand", "Smile", "Frown", "ThumbsUp", "ThumbsDown", "Scale",
    "Gavel", "Leaf", "Droplet", "Zap", "Sun", "Recycle", "Layers", "GitBranch",
    "Workflow", "Network", "Puzzle", "Scissors", "Compass", "Bookmark", "Percent",
]


class SceneVisualPlan(BaseModel):
    index: int
    archetype: str
    label: str
    items: list[str]
    primary: str
    secondary: str
    icon: str
    image_prompt: str


class SceneVisualPlanOutput(BaseModel):
    plans: list[SceneVisualPlan]


_SCENE_VISUAL_PROMPT = """Tu es un directeur artistique de video pedagogique. Pour chaque \
scene de narration ci-dessous (texte reel, deja fixe - ne le reecris jamais), choisis le \
schema anime qui ILLUSTRE ce qui est dit, et fournis les textes courts a afficher dedans.

Archetypes disponibles (choisis l'identifiant exact) :
{archetypes}

Pour chaque scene, reponds avec :
- "index" : le meme numero que la scene d'entree
- "archetype" : un identifiant EXACT de la liste ci-dessus
- "label" : titre court de la scene (3-6 mots), affiche en haut
- "items" : les elements nommes du schema, 2 a 4 libelles TRES courts (1-3 mots chacun).
  Selon l'archetype : les fondements (pillars), les sources (data_flow), les couches
  (concentric_layers), les deux cotes (comparison), les points a cocher (checklist), les
  etapes (timeline), les roles (permission_matrix), les groupes (separated_groups).
  Pour actor_action_target, stat_reveal, state_change et title_statement, mets une liste vide.
- "primary" : selon l'archetype - l'etape centrale (data_flow), le chiffre (stat_reveal,
  ex. "61%"), le message principal (title_statement), l'acteur qui agit
  (actor_action_target), l'etat final (state_change), l'element central
  (concentric_layers), sinon chaine vide
- "secondary" : selon l'archetype - le resultat final (data_flow), le libelle du chiffre
  (stat_reveal), la synthese (pillars), la cible qui subit l'action (actor_action_target),
  la precision sous le schema (state_change, permission_matrix, separated_groups),
  sinon chaine vide
- "icon" : une icone illustrant le concept principal de la scene, choisie EXACTEMENT dans
  cette liste : {icons}
- "image_prompt" : une description visuelle EN ANGLAIS, en 6 a 12 mots, de l'illustration
  d'ambiance a generer en fond de scene. Decris une situation ou un objet concret lie au
  propos (ex. "employee reviewing documents at office desk"). N'y mets JAMAIS de texte,
  de mot ecrit, de chiffre, de logo ni de marque.

Choisis l'archetype d'apres le SENS de la narration, pas au hasard, et varie les archetypes \
d'une scene a l'autre quand le contenu s'y prete. Si aucun schema ne convient vraiment, \
utilise "title_statement".

Tous les textes affiches doivent etre en francais, courts, et utiliser les accents corrects \
(é, è, à, ç) - sauf "image_prompt" qui est en anglais. Reponds pour CHAQUE scene, sans en \
omettre aucune.

--- SCENES DE NARRATION ---
{scenes_text}

--- TEXTE OCR DES DIAPOSITIVES (contexte, pour reprendre les termes affiches a l'ecran) ---
{ocr_text}
"""


def generate_scene_visual_plans(
    indexed_narrations: list[tuple[int, str]], ocr_text: str
) -> dict[int, SceneVisualPlan]:
    """Map each narration scene to an animated archetype + its text slots."""
    client = _get_client()
    scenes_text = "\n".join(f"[{i}] {text}" for i, text in indexed_narrations)
    archetypes = "\n".join(f"- {k} : {v}" for k, v in SCENE_ARCHETYPES.items())
    prompt = _SCENE_VISUAL_PROMPT.format(
        scenes_text=scenes_text,
        ocr_text=ocr_text or "(aucun texte detecte a l'ecran)",
        archetypes=archetypes,
        icons=", ".join(SCENE_ICONS),
    )
    response = _generate_content(
        client,
        model=settings.gemini_model,
        contents=[prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=SceneVisualPlanOutput,
        ),
    )
    parsed = SceneVisualPlanOutput.model_validate_json(response.text)
    by_index = {p.index: p for p in parsed.plans}

    result: dict[int, SceneVisualPlan] = {}
    for idx, text in indexed_narrations:
        plan = by_index.get(idx)
        if plan is None or plan.archetype not in SCENE_ARCHETYPES:
            # Safe fallback: show the narration as a typographic statement
            # rather than dropping the scene or guessing a wrong diagram.
            plan = SceneVisualPlan(
                index=idx,
                archetype="title_statement",
                label="",
                items=[],
                primary=text[:70],
                secondary="",
                icon="Info",
                image_prompt="abstract professional workspace atmosphere",
            )
        elif plan.icon not in SCENE_ICONS:
            # The model occasionally invents an icon name; snap it back to a
            # valid one so the renderer never has to guess.
            plan = plan.model_copy(update={"icon": "Info"})
        result[idx] = plan
    return result


# --- Comprehension quiz (post-MVP feature, cahier des charges section 14) ---


class QuizOption(BaseModel):
    letter: str
    text: str


class QuizQuestion(BaseModel):
    question: str
    options: list[QuizOption]
    correct_letters: list[str]
    explanation: str


class QuizOutput(BaseModel):
    questions: list[QuizQuestion]


_QUIZ_PROMPT = """Tu es un concepteur pedagogique. A partir du contenu d'un chapitre de \
formation ci-dessous, redige {count} questions de comprehension pour verifier que \
l'apprenant a retenu l'essentiel.

Regles :
- Les questions portent UNIQUEMENT sur ce qui est dit dans le contenu fourni. N'invente
  jamais un fait, un chiffre ou une regle qui n'y figure pas.
- Chaque question a 4 propositions, notees A, B, C, D.
- Certaines questions ont une seule bonne reponse, d'autres en ont plusieurs : varie.
  Indique toutes les bonnes lettres dans "correct_letters".
- Les mauvaises propositions doivent rester plausibles (pas d'absurdite evidente), sinon
  la question ne teste rien.
- "explanation" rappelle en une phrase pourquoi la ou les bonnes reponses le sont.
- Redige en francais, avec les accents corrects (é, è, à, ç).

--- TITRE DU CHAPITRE ---
{title}

--- RESUME ---
{summary}

--- POINTS CLES ---
{key_points}

--- CONTENU DETAILLE (transcription) ---
{transcript}
"""


def generate_quiz(
    title: str, summary: str, key_points: list[str], transcript: str, count: int = 3
) -> list[QuizQuestion]:
    """Write comprehension questions grounded in one chapter's actual content."""
    client = _get_client()
    prompt = _QUIZ_PROMPT.format(
        count=count,
        title=title,
        summary=summary,
        key_points="\n".join(f"- {k}" for k in key_points) or "(aucun)",
        transcript=transcript[:6000],
    )
    response = _generate_content(
        client,
        model=settings.gemini_model,
        contents=[prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=QuizOutput,
        ),
    )
    parsed = QuizOutput.model_validate_json(response.text)

    valid: list[QuizQuestion] = []
    for q in parsed.questions:
        letters = {o.letter.strip().upper() for o in q.options}
        correct = [c.strip().upper() for c in q.correct_letters]
        # Drop questions whose answer key doesn't match the options offered,
        # rather than shipping a quiz that cannot be scored correctly.
        if correct and all(c in letters for c in correct):
            valid.append(q)
    return valid
