import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { COLORS, FONT } from "../theme";
import { ConceptIcon } from "../components/ConceptIcon";

/** Fallback / definition beat: a key statement set typographically, with a
 * concept icon above it matched to the words being said, so even the
 * "no diagram fits" case still tracks the narration instead of going blank. */
export const TitleStatement: React.FC<{
  label?: string;
  primary: string;
  narration: string;
  durationInFrames: number;
}> = ({ label, primary, narration, durationInFrames }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame: frame - 4, fps, config: { damping: 12 } });
  const opacity = interpolate(frame, [0, 12], [0, 1], { extrapolateRight: "clamp" });
  const float = Math.sin(frame / 24) * 5;
  const text = primary || label || "";

  return (
    <AbsoluteFill>
      <ConceptIcon narration={narration} durationInFrames={durationInFrames} />
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", paddingTop: 150 }}>
        <div style={{ maxWidth: "78%", textAlign: "center" }}>
          {label && primary && (
            <div
              style={{
                fontFamily: FONT,
                fontSize: 30,
                fontWeight: 800,
                letterSpacing: 3,
                textTransform: "uppercase",
                color: COLORS.accent,
                opacity,
                marginBottom: 22,
              }}
            >
              {label}
            </div>
          )}
          <div
            style={{
              fontFamily: FONT,
              fontSize: 58,
              fontWeight: 800,
              lineHeight: 1.28,
              color: COLORS.text,
              opacity,
              transform: `scale(${0.92 + 0.08 * s}) translateY(${float}px)`,
              textShadow: `0 0 44px ${COLORS.accent}44`,
            }}
          >
            {text}
          </div>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
