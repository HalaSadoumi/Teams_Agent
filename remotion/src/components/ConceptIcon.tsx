import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import * as Icons from "lucide-react";
import { COLORS } from "../theme";
import { chunkWords, getChunkAt } from "../narrationChunks";
import { matchConceptIcon } from "../conceptIcons";

const FALLBACK = Icons.ShieldCheck;

/** The core "editor followed the narration" element: as the caption line
 * changes, this shows a large icon matching a concept actually mentioned in
 * that line (e.g. "mot de passe" -> key icon), instead of a generic shape
 * unrelated to what's being said. Re-triggers its pop-in animation on every
 * chunk change (keyed by chunk index via localFrame). */
export const ConceptIcon: React.FC<{ narration: string; durationInFrames: number }> = ({
  narration,
  durationInFrames,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const chunks = chunkWords(narration);
  const { index, localFrame, chunkDuration } = getChunkAt(frame, durationInFrames, chunks.length);
  const iconName = matchConceptIcon(chunks[index]);
  const IconComp = (Icons as unknown as Record<string, typeof FALLBACK>)[iconName] ?? FALLBACK;

  const s = spring({ frame: localFrame, fps, config: { damping: 10, mass: 0.6, stiffness: 160 } });
  const opacity = interpolate(
    localFrame,
    [0, 8, Math.max(8, chunkDuration - 8), chunkDuration],
    [0, 1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );
  const bob = Math.sin(localFrame / 14) * 6;
  const rotate = interpolate(s, [0, 1], [-12, 0]);

  return (
    <div
      style={{
        position: "absolute",
        top: "20%",
        left: "50%",
        transform: "translateX(-50%)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        opacity,
      }}
    >
      <div
        style={{
          width: 176,
          height: 176,
          borderRadius: 88,
          background: `linear-gradient(135deg, ${COLORS.accent}2E, ${COLORS.card})`,
          border: `3px solid ${COLORS.accent}`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          boxShadow: `0 0 46px ${COLORS.accent}66`,
          transform: `scale(${s}) translateY(${bob}px) rotate(${rotate}deg)`,
        }}
      >
        <IconComp size={86} color={COLORS.accent} strokeWidth={1.6} />
      </div>
    </div>
  );
};
