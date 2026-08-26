import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { COLORS, FONT } from "../theme";
import { ConceptIcon } from "../components/ConceptIcon";

/** Definition / key-message beat, and the fallback when no diagram fits: a
 * statement set typographically under the scene's concept icon. */
export const TitleStatement: React.FC<{
  label?: string;
  primary: string;
  icon: string;
  durationInFrames: number;
}> = ({ label, primary, icon }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame: frame - 4, fps, config: { damping: 12 } });
  const opacity = interpolate(frame, [0, 12], [0, 1], { extrapolateRight: "clamp" });
  const float = Math.sin(frame / 24) * 5;
  const text = primary || label || "";

  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", flexDirection: "column" }}>
      <div style={{ marginBottom: 44 }}>
        <ConceptIcon icon={icon} />
      </div>
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
  );
};
