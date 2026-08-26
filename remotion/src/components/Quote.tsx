import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { BOUNCY, COLORS, FONT } from "../theme";
import { AnimatedBackground } from "./AnimatedBackground";

export const Quote: React.FC<{ text: string }> = ({ text }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame, fps, config: BOUNCY });
  const opacity = interpolate(frame, [0, 18], [0, 1], { extrapolateRight: "clamp" });
  const markSpin = interpolate(s, [0, 1], [-30, 0]);
  const float = Math.sin(frame / 22) * 6;

  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", padding: "0 15%" }}>
      <AnimatedBackground />
      <div
        style={{
          color: COLORS.accent,
          fontFamily: FONT,
          fontSize: 120,
          lineHeight: 0.4,
          opacity,
          marginBottom: 26,
          transform: `scale(${s}) rotate(${markSpin}deg)`,
          textShadow: `0 0 40px ${COLORS.accent}88`,
        }}
      >
        “
      </div>
      <div
        style={{
          color: COLORS.text,
          fontFamily: FONT,
          fontSize: 46,
          fontWeight: 600,
          fontStyle: "italic",
          textAlign: "center",
          lineHeight: 1.4,
          opacity,
          transform: `translateY(${float}px)`,
        }}
      >
        {text}
      </div>
    </AbsoluteFill>
  );
};
