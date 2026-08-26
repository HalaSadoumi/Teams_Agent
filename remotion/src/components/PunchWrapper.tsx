import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { COLORS } from "../theme";
import { chunkWords, getChunkAt } from "../narrationChunks";

/** Adds "edited by a human" energy at every concept change (and therefore
 * at every scene cut, since frame resets to 0 there too): a quick punch-in
 * zoom that settles back to normal, plus a brief flash - instead of content
 * just sitting static until the next hard cut. */
export const PunchWrapper: React.FC<{ narration: string; durationInFrames: number; children: React.ReactNode }> = ({
  narration,
  durationInFrames,
  children,
}) => {
  const frame = useCurrentFrame();
  const chunks = chunkWords(narration);
  const { localFrame } = getChunkAt(frame, durationInFrames, chunks.length);

  const scale = interpolate(localFrame, [0, 12], [1.09, 1], { extrapolateRight: "clamp" });
  const flash = interpolate(localFrame, [0, 3, 9], [0.35, 0.35, 0], { extrapolateRight: "clamp" });

  return (
    <div style={{ position: "absolute", inset: 0, transform: `scale(${scale})` }}>
      {children}
      <div style={{ position: "absolute", inset: 0, background: COLORS.accent, opacity: flash, mixBlendMode: "screen" }} />
    </div>
  );
};
