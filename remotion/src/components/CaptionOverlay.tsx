import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { COLORS, FONT } from "../theme";
import { chunkWords, getChunkAt } from "../narrationChunks";
import { isEmphasisWord } from "../conceptIcons";

/** Supporting subtitle band: shows the real narration a line at a time, with
 * keyword words accented. Deliberately restrained (bottom of frame, moderate
 * size) because in the explainer style the animated scene above is the main
 * event — the text is there to follow along, not to carry the video. */
export const CaptionOverlay: React.FC<{ narration: string; durationInFrames: number }> = ({
  narration,
  durationInFrames,
}) => {
  const frame = useCurrentFrame();
  const chunks = chunkWords(narration, 52);
  const { index, localFrame, chunkDuration } = getChunkAt(frame, durationInFrames, chunks.length);
  const words = chunks[index].split(" ");

  const opacity = interpolate(
    localFrame,
    [0, 6, Math.max(6, chunkDuration - 6), chunkDuration],
    [0, 1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );
  const rise = interpolate(localFrame, [0, 8], [16, 0], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ justifyContent: "flex-end", alignItems: "center", paddingBottom: 64 }}>
      <div
        style={{
          maxWidth: "80%",
          background: "rgba(8,12,22,0.78)",
          borderRadius: 16,
          padding: "18px 36px",
          opacity,
          transform: `translateY(${rise}px)`,
          border: `1px solid ${COLORS.cardBorder}`,
        }}
      >
        <div style={{ fontFamily: FONT, fontSize: 34, fontWeight: 600, lineHeight: 1.35, textAlign: "center" }}>
          {words.map((w, i) => (
            <span key={i} style={{ color: isEmphasisWord(w) ? COLORS.accent : COLORS.text, marginRight: 9 }}>
              {w}
            </span>
          ))}
        </div>
      </div>
    </AbsoluteFill>
  );
};
