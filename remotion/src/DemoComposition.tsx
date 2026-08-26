import React from "react";
import { AbsoluteFill, Audio, Series, staticFile, useVideoConfig } from "remotion";
import { AnimatedBackground } from "./components/AnimatedBackground";
import { CaptionOverlay } from "./components/CaptionOverlay";
import { PillarsDiagram } from "./scenes/PillarsDiagram";
import { PhishingScenario } from "./scenes/PhishingScenario";
import { DataFlowDiagram } from "./scenes/DataFlowDiagram";

/** Hand-picked real scenes from the training, each paired with the animated
 * scene template that actually illustrates what is being said - used to
 * validate the explainer style before scaling to all 17 chapters. */
export const DEMO_SCENES = [
  { sceneId: "chapter_01_scene_02", duration: 20.6, kind: "pillars" as const },
  { sceneId: "chapter_04_scene_08", duration: 10.0, kind: "phishing" as const },
  { sceneId: "chapter_01_scene_07", duration: 6.1, kind: "flow" as const },
];

const NARRATION: Record<string, string> = {
  chapter_01_scene_02:
    "à la confidentialité des données le deuxième volet c'est l'intégrité l'intégrité c'est quoi ? c'est que l'intégrité vise à s'assurer que les données et les systèmes restent intacts et non altérés",
  chapter_04_scene_08:
    "une entreprise de confiance en demandant à la personne de partager des informations confidentielles alors le gros souci aujourd'hui avec le phishing",
  chapter_01_scene_07:
    "par exemple le système aujourd'hui il y a des systèmes qui font ça automatiquement ce qu'on appelle les systèmes de contrôle d'intégrité",
};

export const DemoComposition: React.FC = () => {
  const { fps } = useVideoConfig();

  return (
    <AbsoluteFill>
      <AnimatedBackground />
      <Series>
        {DEMO_SCENES.map(({ sceneId, duration, kind }) => {
          const durationInFrames = Math.round(duration * fps);
          return (
            <Series.Sequence key={sceneId} durationInFrames={durationInFrames}>
              {kind === "pillars" && (
                <PillarsDiagram
                  label="Les 3 piliers de la sécurité"
                  items={["Confidentialité", "Intégrité", "Disponibilité"]}
                  roof="Sécurité des données"
                  durationInFrames={durationInFrames}
                />
              )}
              {kind === "phishing" && (
                <PhishingScenario label="Le phishing en pratique" durationInFrames={durationInFrames} />
              )}
              {kind === "flow" && (
                <DataFlowDiagram
                  label="Contrôle d'intégrité automatique"
                  sources={["Fichiers", "Bases", "Systèmes"]}
                  hub="Contrôle"
                  result="Intégrité validée"
                  durationInFrames={durationInFrames}
                />
              )}
              <CaptionOverlay narration={NARRATION[sceneId]} durationInFrames={durationInFrames} />
              <Audio src={staticFile(`audio/${sceneId}.wav`)} />
            </Series.Sequence>
          );
        })}
      </Series>
    </AbsoluteFill>
  );
};
