# Sprint 1 — État d'avancement

## Sprint prévu
Sprint 1 correspond à :
- cadrage,
- mise en place de l’environnement,
- pipeline d’ingestion,
- extraction audio,
- transcription ASR,
- OCR des diapositives,
- détection de scènes,
- première représentation multimodale.

## Ce qui a déjà été réalisé
- Extraction de l’audio depuis la vidéo source.
- Génération d’un master audio 48 kHz mono pour la production.
- Génération d’un fichier audio dédié ASR : 16 kHz mono, normalisé.
- Mise à jour du pipeline pour transcrire à partir de l’audio ASR.
- Extraction de keyframes depuis la vidéo.
- Mise en place d’un pipeline de détection de scènes sémantiques.
- Affichage initial d’une structure de chapitres et de scènes.
- Création d’une vidéo assemblée de démonstration (`demo_sample_60s.mp4`).
- Documentation en français pour le superviseur (`docs/rapport_superviseur_fr.md`).

## Ce qui reste à faire dans Sprint 1
- Vérifier et corriger l’assemblage final pour s’assurer que l’audio est bien audible dans toutes les versions dérivées.
- Confirmer l’intégration OCR des diapositives dans le pipeline et vérifier les résultats.
- Finaliser la détection de scènes basée sur la multimodalité (texte + images).
- Consolider les objets de sortie : scènes structurées, métadonnées de chapitres, premier storyboard.
- Préparer un premier rendu transformé de 1 à 2 chapitres si possible.

## Remarque sur l’audio
- La vidéo de démonstration contient effectivement une piste audio.
- Un fichier audio extrait a été généré pour vérification : `data/processed/actual/demo_sample_60s_audio.wav`.
- Si la vidéo semble sans son, il faut vérifier le lecteur ou écouter directement le fichier WAV.

## Conclusion
Le projet est bien aligné sur Sprint 1 : la base du pipeline d’ingestion est en place et produit des artefacts exploitables.
La prochaine étape est de stabiliser l’assemblage audio/vidéo et de compléter l’analyse multimodale pour générer une première version transformée du cours.
