import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { BOUNCY, COLORS, FONT } from "../theme";
import { AnimatedBackground } from "./AnimatedBackground";

export const TitleCard: React.FC<{ text: string }> = ({ text }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame, fps, config: BOUNCY });
  const opacity = interpolate(frame, [0, 12], [0, 1], { extrapolateRight: "clamp" });
  const rotate = interpolate(s, [0, 1], [-6, 0]);
  const float = Math.sin(frame / 20) * 6;
  const barGlow = 8 + Math.sin(frame / 10) * 6;

  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", flexDirection: "column" }}>
      <AnimatedBackground />
      <div
        style={{
          width: 10,
          height: 78,
          borderRadius: 6,
          background: `linear-gradient(180deg, ${COLORS.accent}, ${COLORS.accent3})`,
          marginBottom: 40,
          opacity,
          boxShadow: `0 0 ${barGlow}px ${COLORS.accent}`,
          transform: `scaleY(${s}) translateY(${float * 0.4}px)`,
        }}
      />
      <div
        style={{
          color: COLORS.text,
          fontFamily: FONT,
          fontSize: 66,
          fontWeight: 800,
          textAlign: "center",
          maxWidth: "80%",
          lineHeight: 1.22,
          opacity,
          letterSpacing: -0.5,
          textShadow: `0 0 40px ${COLORS.accent}55`,
          transform: `scale(${0.85 + 0.15 * s}) rotate(${rotate}deg) translateY(${float}px)`,
        }}
      >
        {text}
      </div>
    </AbsoluteFill>
  );
};
