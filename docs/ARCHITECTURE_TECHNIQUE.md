# Documentation technique approfondie

Public visé : ingénieurs / développeurs. Ce document détaille l'architecture réelle du code
(`src/s2m_pipeline/`), les choix d'implémentation et leur justification, au niveau module par
module. Il ne remplace pas le [cahier des charges](cahier_des_charges.pdf) (exigences) ni le
[guide débutant](GUIDE_PROJET.md) (vue d'ensemble accessible) — c'est le niveau « code ».

**Convention de statut**, appliquée strictement dans tout ce document :

| Statut | Signification |
|---|---|
| ✅ Implémenté et validé | Code en place, exécuté avec succès sur la vidéo réelle complète (1h35) |
| 🟡 Implémenté, validé partiellement | Code en place et fonctionnel, mais exécuté seulement sur un sous-ensemble (ex. 1 chapitre sur 17) |
| ⚪ Conçu, non implémenté | Décrit dans le cahier des charges / prévu dans l'architecture, aucun code correspondant n'existe encore |

---

## 1. Vue d'ensemble architecturale

```
video.mp4
   │
   ▼
[pipeline.py]  ── ingestion ────────────────────────────────────────► scenes.json, transcript.json,
   │  extract → enhance → transcribe → diarize → detect scenes → OCR   subtitles.srt/.vtt, audio.wav
   ▼
[chaptering.py] ── segmentation sémantique + LLM multimodal ────────► chapters.json
   │  embeddings.py (boundary detection) + llm.py (titre/résumé/points clés)
   ▼
[content_selection.py] ── classification garder/couper (LLM) ───────► (en mémoire, par chapitre)
   ▼
[narration_original.py] ── groupement + découpage/recollage audio ──► storyboard.json + clips .wav
   │  + llm.py (planification visuelle)
   ▼
⚪ génération des visuels (non implémenté)
   ▼
⚪ assemblage vidéo final (non implémenté)
```

Chaîne alternative, implémentée mais non retenue comme chemin principal (voir §4.10) :
`script.py` (réécriture LLM) → `storyboard.py` (découpage du script réécrit) →
`narration.py`/`tts.py` (synthèse vocale edge-tts) — produit le même schéma `StoryboardScene`
que `narration_original.py`, donc interchangeable en aval.

## 2. Stack technique

| Composant | Bibliothèque | Version min. | Justification |
|---|---|---|---|
| Extraction / manipulation audio-vidéo | FFmpeg (CLI, subprocess) | — | Déjà central au pipeline, filtres `afftdn`/`loudnorm` intégrés, pas de dépendance Python supplémentaire |
| ASR | `faster-whisper` | ≥1.0.0 | CTranslate2 (pas PyTorch), quantification int8, tourne correctement sur CPU |
| Diarisation (optionnelle) | `pyannote.audio` | ≥3.1.0 | Nécessite `HF_TOKEN` ; dégradation gracieuse si absent |
| Détection de scènes visuelles | `scenedetect[opencv]` | ≥0.6.4 | `ContentDetector`, CPU uniquement |
| OCR | `pytesseract` + Tesseract-OCR (binaire) | ≥0.3.10 | Pack `fra.traineddata` embarqué localement (voir §4.5) |
| Embeddings sémantiques | `sentence-transformers` (`all-MiniLM-L6-v2`) | ≥3.0.0 | 384 dimensions, léger, CPU |
| LLM multimodal | `google-genai` (Gemini) | ≥1.0.0 | Contexte large, entrée image native, tier gratuit |
| Retry / backoff | `tenacity` | ≥8.2.0 | Décorateur déclaratif, réutilisé sur tous les appels LLM |
| TTS (chemin alternatif) | `edge-tts` | ≥6.1.0 | Gratuit, sans clé API, voix FR/EN de bonne qualité |
| Validation / sérialisation | `pydantic` | ≥2.6.0 | Schémas typés, `model_validate_json` pour parser directement la sortie structurée du LLM |

Python 3.11, environnement virtuel (`.venv`), pas de dépendance GPU (CUDA) — conformément à la
contrainte du cahier des charges (§10).

## 3. Modèles de données (`models.py`)

Quatre schémas Pydantic assurent la traçabilité entre étapes :

```python
class TranscriptSegment(BaseModel):
    start: float
    end: float
    text: str
    speaker: str | None = None

class Scene(BaseModel):
    id: str
    start: float
    end: float
    speaker: str | None = None
    transcript: str = ""
    ocr_text: str = ""
    visual_description: str | None = None   # rempli en Sprint 2 (LLM), pas en Sprint 1
    topic: str | None = None                 # idem
    importance: float | None = None          # idem, jamais peuplé à ce stade
    frame_path: str | None = None

class Chapter(BaseModel):
    id: str
    title: str
    start: float
    end: float
    summary: str = ""
    key_points: list[str] = []

class StoryboardScene(BaseModel):
    scene_id: str
    chapter_id: str
    duration: float
    narration: str
    visual_type: str
    visual_description: str
    on_screen_text: str = ""
    transition: str = "fade"
    audio_path: str | None = None    # ajouté hors schéma cahier des charges §8.3 : chemin du
                                       # clip audio réel (voix originale) ou synthétisé (TTS)
```

`topic` et `importance` sur `Scene` restent `None` dans l'implémentation actuelle — prévus par
le schéma du cahier des charges (§8.1) mais jamais renseignés, ni en Sprint 1 ni en Sprint 2 (le
chapitrage travaille directement sur `TranscriptSegment`, pas sur `Scene.topic`). ⚪

## 4. Détail par module

### 4.1 `config.py`

`Settings` (dataclass frozen), valeurs lues depuis `.env` via `python-dotenv`. Paramètres
empiriquement calibrés à noter explicitement :

```python
scene_detect_threshold: float = 27.0        # PySceneDetect ContentDetector
min_scene_len_seconds: float = 2.0
chapter_window_seconds: float = 60.0        # taille de fenêtre avant embedding
chapter_similarity_threshold: float = 0.55  # cf. §4.9, calibré empiriquement (0.45→0.65 testés)
chapter_min_seconds: float = 180.0
whisper_model_size: str = "small"           # compute_type="int8" fixé dans transcription.py
gemini_model: str = "gemini-flash-lite-latest"  # cf. §4.7, bascule après épuisement de quota
tts_voice: str = "fr-FR-DeniseNeural"
```

### 4.2 `audio.py`

Quatre fonctions, toutes des wrappers `subprocess.run(["ffmpeg", ...])` :

- `extract_audio(video_path, output_wav_path, sample_rate=16000)` → mono, PCM 16-bit
  (`pcm_s16le`), 16 kHz — format standard d'entrée pour Whisper.
- `enhance_audio(input_wav_path, output_wav_path)` → chaîne de filtres FFmpeg
  `afftdn=nf=-25,loudnorm=I=-16:TP=-1.5:LRA=11` :
  - `afftdn` : débruitage spectral (FFT), seuil de bruit à -25 dB ;
  - `loudnorm` : normalisation de loudness EBU R128, cible -16 LUFS / true peak -1.5 dBTP /
    plage dynamique 11 LU — standard pour du contenu parlé.
  Appliqué une seule fois sur l'audio maître, en amont de la transcription ET de la narration
  voix originale (source unique, cf. `pipeline.py` §4.6).
- `extract_clip(audio_path, start, end, output_path)` → `ffmpeg -ss <start> -to <end> -c copy`
  (stream copy, pas de ré-encodage — fiable sur PCM/WAV où chaque échantillon est adressable).
- `concat_clips(clip_paths, output_path)` → démuxeur `concat` FFmpeg (fichier de liste
  temporaire, supprimé après usage), `-c copy` — nécessite des clips de même format, garanti
  ici puisqu'ils proviennent tous du même fichier maître.
- `audio_duration_seconds(audio_path)` → `ffprobe -show_entries format=duration`.

### 4.3 `transcription.py`

`WhisperModel(settings.whisper_model_size, device="cpu", compute_type="int8")`, instance
globale paresseuse (`_model` module-level, initialisée au premier appel). `transcribe()` passe
`vad_filter=True` (détection d'activité vocale intégrée à faster-whisper, élimine les silences
avant transcription) et `language=settings.whisper_language` (`"fr"` par défaut, ou `None`
pour auto-détection).

### 4.4 `diarization.py`

Dégradation gracieuse à trois niveaux : `settings.hf_token` absent → `diarize()` retourne `[]`
immédiatement (pas d'import pyannote) ; `pyannote.audio` non installé → `ImportError` capturée
→ `[]` ; sinon, pipeline `pyannote/speaker-diarization-3.1`. `speaker_at(turns, timestamp)`
fait une recherche linéaire (`O(n)` par appel) — non optimisé, acceptable vu le volume actuel.
**Non exercé en pratique** : aucun `HF_TOKEN` configuré à ce jour, tous les segments portent
`speaker="speaker_1"` implicitement (valeur par défaut de `_majority_speaker` dans
`pipeline.py` quand `speaker_turns` est vide).

### 4.5 `scenes.py` / `ocr.py`

`detect_scenes()` : `SceneManager` + `ContentDetector(threshold=27.0,
min_scene_len=int(2.0 * frame_rate))`. Fallback : si aucune coupure détectée, retourne une
scène unique couvrant toute la vidéo (`video.duration.get_seconds()`).

`ocr.py` contient un contournement Windows notable : l'installeur `winget` de Tesseract
(UB-Mannheim) ne fournit que le pack anglais. Le module :
1. résout `tesseract.exe` via `shutil.which`, avec repli sur
   `C:\Program Files\Tesseract-OCR\tesseract.exe` si absent du PATH ;
2. force `TESSDATA_PREFIX` vers un dossier local `.tessdata/` (non versionné, gitignored)
   contenant `fra.traineddata` (téléchargé depuis `tessdata_fast`) + `eng.traineddata` copié
   du dossier système — évite de dépendre de l'installation système pour le FR.
`extract_text(frame_path, lang="fra+eng")`.

### 4.6 `pipeline.py` — orchestrateur Sprint 1

`run(video_path, work_dir) -> PipelineResult` (dataclass : `scenes`, `transcript_segments`,
`audio_path`). Séquence stricte à six étapes (numérotées `[i/6]` dans les logs) :

1. `extract_audio` → `audio_raw.wav`
2. `enhance_audio` → `audio.wav` (devient la source unique pour transcription ET narration
   voix originale en aval)
3. `transcribe(audio.wav)`
4. `diarize` (optionnel)
5. `detect_scenes(video_path)` — **sur la vidéo, pas sur l'audio** : détection visuelle
   indépendante de la piste audio
6. par scène visuelle : `extract_frame` (frame médiane) + `ocr.extract_text` + fusion avec les
   `TranscriptSegment` chevauchants (`_overlapping_transcript`, filtre `seg.start < end and
   seg.end > start`) + `_majority_speaker` (vote majoritaire, `max(set(...), key=list.count)`)

`main()` (CLI) écrit `scenes.json`, `transcript.json`, `subtitles.srt`/`.vtt`
(`subtitles.py` — génération SRT/VTT directe depuis `TranscriptSegment`, hors périmètre MVP du
cahier des charges §14 mais ajoutée : coût quasi nul, timestamps déjà disponibles).

**✅ Implémenté et validé** — exécuté sur la vidéo réelle complète (1h35) : 2 438 segments de
transcription, 18 scènes visuelles.

### 4.7 `llm.py` — client Gemini et prompts

Client paresseux (`_get_client()`, singleton module-level), erreur explicite si
`GEMINI_API_KEY` absent.

**Gestion des erreurs transitoires** :
```python
def _is_transient(exc): return isinstance(exc, genai_errors.APIError) and exc.code in (429, 500, 503, 504)

@retry(retry=retry_if_exception(_is_transient), stop=stop_after_attempt(5),
       wait=wait_exponential(multiplier=2, min=2, max=30), reraise=True)
def _generate_content(client, **kwargs): return client.models.generate_content(**kwargs)
```
Tous les appels passent par ce wrapper unique.

**Incident de quota réel** (retenu ici car il a directement façonné le code) : `gemini-3.6-flash`
limité à 20 req/j sur le tier gratuit (`GenerateRequestsPerDayPerProjectPerModel-FreeTier`).
Épuisé après 9 des 17 chapitres. Réponse en deux temps :
1. bascule du modèle par défaut vers `gemini-flash-lite-latest` (quota séparé) ;
2. `chaptering.build_chapters()` accepte `checkpoint_path` (écriture JSON après **chaque**
   chapitre, pas seulement en fin de run) + `resume=True` (relit le checkpoint, ne régénère que
   les `chapter_id` manquants).

Régression détectée en cours de bascule : `gemini-flash-lite-latest` produisait du texte
français sans diacritiques (« securite »). Corrigé par une contrainte explicite ajoutée à
chaque prompt : *« Utilise systématiquement les accents et diacritiques français corrects
(é, è, à, ç, etc.) »*.

**Fonctions exposées** (toutes en sortie structurée, `response_mime_type="application/json"` +
`response_schema=<PydanticModel>`, parsées via `Model.model_validate_json(response.text)`) :

| Fonction | Entrée | Sortie | Utilisée par |
|---|---|---|---|
| `generate_chapter_content` | transcript + OCR + frames (images PIL) | `ChapterContent` (title, summary, key_points) | `chaptering.py` |
| `generate_script` | transcript + OCR | `ScriptOutput` (script réécrit) | `script.py` (chemin alternatif) |
| `generate_storyboard_scenes` | script réécrit + OCR | `list[StoryboardSceneLLM]` | `storyboard.py` (chemin alternatif) |
| `classify_segments` | liste indexée `(i, texte_horodaté)` | `dict[int, "garder"\|"couper"]` | `content_selection.py` |
| `generate_visual_plan` | liste indexée `(i, narration_reelle)` + OCR | `dict[int, VisualPlanLLM]` | `narration_original.py` |

Alignement d'index robuste sur `classify_segments`/`generate_visual_plan` : le schéma de sortie
inclut un champ `index` explicite (pas de dépendance à l'ordre positionnel du LLM) ; tout index
d'entrée absent de la réponse reçoit une valeur par défaut sûre (`"garder"` pour la
classification — cohérent avec le principe « pas de compression agressive » du cahier des
charges §5.4 ; un plan visuel générique pour `generate_visual_plan`).

### 4.8 `embeddings.py`

`SentenceTransformer("all-MiniLM-L6-v2")`, singleton paresseux. `similarity_drops(texts)` :
encode avec `normalize_embeddings=True` (vecteurs unitaires), similarité cosinus réduite à un
simple produit scalaire `np.dot(v[i-1], v[i])`. Retourne une liste de similarités,
`sims[0] = 1.0` par convention (rien ne précède la première fenêtre).

### 4.9 `chaptering.py` — segmentation + génération de contenu

Algorithme en quatre passes :

1. `_group_into_windows(segments, window_seconds=60.0)` — regroupe les `TranscriptSegment`
   consécutifs en fenêtres d'≈60 s (accumulation jusqu'à dépassement du seuil, pas de
   chevauchement).
2. `_propose_boundaries(windows)` — `embeddings.similarity_drops` sur le texte de chaque
   fenêtre ; toute fenêtre `i` avec `sim[i] < chapter_similarity_threshold` devient une
   frontière candidate.
3. `_merge_short_chapters(boundaries, windows)` — fusionne en avant toute frontière produisant
   un chapitre `< chapter_min_seconds` ; passe finale pour fusionner un dernier chapitre trop
   court dans son prédécesseur.
4. Par chapitre retenu : texte chevauchant + OCR dédupliqué des `Scene` chevauchantes
   (`dict.fromkeys` pour dédupliquer en préservant l'ordre) + jusqu'à 3 frames représentatives
   espacées uniformément (`_representative_frames`, pas de sur-échantillonnage si ≤3 scènes
   visuelles couvrent le chapitre) → `llm.generate_chapter_content`.

**Calibrage empirique du seuil** — mode `--dry-run` (aucun appel LLM, juste
`_print_boundary_preview`) utilisé pour tester `chapter_similarity_threshold` sans consommer de
quota :

| Seuil | Chapitres | Durée max | Observation |
|---|---|---|---|
| 0.45 | 6 | 37,5 min | sous-segmentation : une seule fenêtre de 60 s tombe sous le seuil sur une plage de 37 min |
| 0.55 | 17 | 10,1 min | retenu — 3-10 min/chapitre, plusieurs fusions exactement à la borne (180 s), signe d'un réglage cohérent |
| 0.60 | 21 | — | sur-segmentation, nombreux chapitres clampés au minimum |
| 0.65 | 25 | — | idem, plus marqué |

**✅ Implémenté et validé** — 17 chapitres sur la vidéo complète, checkpointing/`--resume`
exercés en conditions réelles (panne de quota).

### 4.10 Deux chemins narration, un schéma de sortie commun

**Chemin A — synthèse vocale (implémenté, non retenu comme chemin principal)** :
`script.py` (`generate_script`, réécriture complète du transcript) → `storyboard.py`
(`generate_storyboard_scenes`, le LLM découpe LUI-MÊME le script réécrit en scènes et renvoie
la narration verbatim — instruction explicite de reconstitution exacte, non garantie à 100 %
par le modèle : un écart d'un mot a été observé lors de la validation, « sur des réseaux » →
« sur nos réseaux ») → `narration.py`/`tts.py` (edge-tts, `synthesize()` async via
`edge_tts.Communicate`, puis `audio_duration_seconds` mesure la durée réelle du clip généré
pour corriger l'estimation par nombre de mots — l'estimation initiale, `len(narration.split())
/ 2.3`, s'est révélée systématiquement ~15-20 % trop longue face à la synthèse edge-tts).

**Chemin B — voix originale (retenu, cahier des charges §6.2 option 1)** :
`content_selection.classify_chapter_segments` (classification LLM garder/couper par segment,
prompt explicite sur les trois catégories §5.4) → `narration_original._group_kept_segments`
(regroupement des segments consécutifs *gardés* en scènes de ~20 s cible
`_TARGET_SCENE_SECONDS`, nouvelle scène si écart > `_MAX_GAP_SECONDS=3.0` s entre deux segments
gardés — un écart signale du contenu coupé entre eux) → `audio.extract_clip` +
`audio.concat_clips` (découpage/recollage direct depuis `audio.wav`, le fichier maître déjà
débruité) → `llm.generate_visual_plan` (le LLM ne reçoit **que** la narration déjà fixée, ne la
réécrit jamais — contrairement au chemin A).

Différence clé de fiabilité : le chemin B élimine le problème d'estimation de durée du chemin
A — la durée est mesurée directement sur le clip audio réel après découpage/recollage, jamais
estimée.

**🟡 Implémenté, validé sur 1 chapitre** (`chapter_00`, vidéo de test 3 min : 9 scènes,
classification quasi intégralement « garder » sur ce clip, aucune coupure audible détectée à
l'écoute des clips générés). **Non exécuté sur l'ensemble des 17 chapitres** de la vidéo
complète à la date de rédaction.

### 4.11 Ce qui n'existe pas encore

⚪ **Génération des visuels** — aucun module. Le cahier des charges (§9) prescrit Remotion
(React + FFmpeg) ; ni Node.js ni de projet Remotion ne sont initialisés dans le dépôt à ce
jour. `StoryboardScene.visual_type` est restreint à un vocabulaire contrôlé de 8 valeurs
(`llm.VISUAL_TYPES` : `title_card`, `bullet_list`, `icon_row`, `process_flow`, `comparison`,
`stat_highlight`, `quote`, `timeline`) — choix délibéré pour borner le nombre de composants
Remotion à construire, mais aucun composant n'est encore écrit.

⚪ **Assemblage vidéo final** — aucun module orchestrant la composition
narration + visuel + transitions par scène, ni la concaténation chapitre → cours complet.

⚪ **`Scene.topic` / `Scene.importance`** — champs du schéma §8.1, jamais peuplés (le
chapitrage opère sur `TranscriptSegment`, pas sur ces champs).

## 5. Tableau récapitulatif de l'état d'implémentation

| Composant | Module(s) | Statut |
|---|---|---|
| Extraction + amélioration audio | `audio.py` | ✅ |
| Transcription ASR | `transcription.py` | ✅ |
| Diarisation | `diarization.py` | ⚪ (code présent, jamais exercé — pas de `HF_TOKEN`) |
| Détection de scènes visuelles + OCR | `scenes.py`, `ocr.py` | ✅ |
| Sous-titres SRT/VTT | `subtitles.py` | ✅ |
| Segmentation sémantique | `embeddings.py`, `chaptering.py` | ✅ |
| Génération titre/résumé/points clés (LLM multimodal) | `llm.py`, `chaptering.py` | ✅ |
| Script réécrit + storyboard + TTS (chemin A) | `script.py`, `storyboard.py`, `narration.py`, `tts.py` | ✅ (validé 1 chapitre), non retenu comme chemin principal |
| Classification garder/couper | `content_selection.py` | 🟡 (validé 1 chapitre) |
| Narration voix originale + storyboard (chemin B) | `narration_original.py` | 🟡 (validé 1 chapitre) |
| Génération des visuels (motion graphics) | — | ⚪ |
| Assemblage vidéo final | — | ⚪ |

## 6. Limitations connues et dette technique

- `diarization.speaker_at` : recherche linéaire, non problématique au volume actuel mais à
  revoir si le nombre de tours de parole augmente significativement.
- Le chemin A (TTS) et le chemin B (voix originale) coexistent dans le dépôt sans mécanisme de
  sélection unifié (pas de flag CLI commun) — chacun s'invoque via son propre module.
- Aucun test automatisé (pytest) n'est présent ; la validation s'est faite par exécution
  manuelle et inspection des sorties JSON/audio.
- `_representative_frames` (chaptering.py) et le calcul de similarité (embeddings.py) n'ont pas
  de limite explicite sur la taille du texte envoyé au LLM pour un chapitre — pas de problème
  observé jusqu'ici (chapitres de quelques minutes), à surveiller si la durée moyenne augmente.

## 7. Prochaines étapes techniques

1. Exécuter `content_selection.py` + `narration_original.py` sur les 17 chapitres de la vidéo
   complète (actuellement validé sur 1 seul).
2. Initialiser un projet Remotion (Node.js), un composant React par valeur de `visual_type`.
3. Écrire l'orchestrateur d'assemblage (scène → chapitre → cours complet), FFmpeg pour le
   multiplexage audio/vidéo final.
4. Décider explicitement, au niveau code, du sort du chemin A (le conserver comme alternative
   sélectionnable, ou le retirer du chemin principal documenté).

*Document mis à jour le 24 août 2026.*
