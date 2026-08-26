import React from "react";
import { AbsoluteFill, Audio, Series, staticFile, useVideoConfig } from "remotion";
import { StoryboardScene, VisualPlan } from "../types";
import { SceneRenderer } from "./SceneRenderer";
import { CaptionOverlay } from "./CaptionOverlay";
import { AnimatedBackground } from "./AnimatedBackground";
import visualPlansData from "../../public/scene_visuals.json";

const VISUAL_PLANS = visualPlansData as Record<string, VisualPlan>;

export const ChapterComposition: React.FC<{ scenes: StoryboardScene[] }> = ({ scenes }) => {
  const { fps } = useVideoConfig();

  return (
    <AbsoluteFill>
      {/* Rendered once, outside the Series, so the drifting background keeps
       * moving continuously across scene cuts instead of resetting. */}
      <AnimatedBackground />
      <Series>
        {scenes.map((scene) => {
          const durationInFrames = Math.max(1, Math.round(scene.duration * fps));
          return (
            <Series.Sequence key={scene.scene_id} durationInFrames={durationInFrames}>
              <SceneRenderer
                scene={scene}
                plan={VISUAL_PLANS[scene.scene_id]}
                durationInFrames={durationInFrames}
              />
              <CaptionOverlay narration={scene.narration} durationInFrames={durationInFrames} />
              <Audio src={staticFile(`audio/${scene.scene_id}.wav`)} />
            </Series.Sequence>
          );
        })}
      </Series>
    </AbsoluteFill>
  );
};
