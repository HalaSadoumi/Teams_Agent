import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { BOUNCY, COLORS, FONT } from "../theme";
import { extractStat } from "../types";
import { AnimatedBackground } from "./AnimatedBackground";

export const StatHighlight: React.FC<{ text: string }> = ({ text }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { value, label } = extractStat(text);
  const s = spring({ frame, fps, config: BOUNCY });
  const opacity = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: "clamp" });
  const pulse = 1 + Math.sin(frame / 14) * 0.03;

  const numMatch = value.match(/[\d.,]+/);
  const numeric = numMatch ? parseFloat(numMatch[0].replace(",", ".")) : null;
  const suffix = numeric !== null ? value.slice(numMatch![0].length) : "";
  const counted =
    numeric !== null
      ? Math.round(interpolate(frame, [0, 30], [0, numeric], { extrapolateRight: "clamp" }) * 10) / 10
      : null;

  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", flexDirection: "column" }}>
      <AnimatedBackground />
      {value ? (
        <div
          style={{
            fontFamily: FONT,
            fontSize: 168,
            fontWeight: 900,
            opacity,
            transform: `scale(${s * pulse})`,
            marginBottom: 6,
            background: `linear-gradient(135deg, ${COLORS.accent}, ${COLORS.accent3})`,
            WebkitBackgroundClip: "text",
            backgroundClip: "text",
            color: "transparent",
            filter: `drop-shadow(0 0 40px ${COLORS.accent}66)`,
          }}
        >
          {counted !== null ? `${counted % 1 === 0 ? counted.toFixed(0) : counted}${suffix}` : value}
        </div>
      ) : null}
      <div
        style={{
          color: COLORS.text,
          fontFamily: FONT,
          fontSize: value ? 36 : 54,
          fontWeight: 700,
          textAlign: "center",
          maxWidth: "70%",
          opacity,
        }}
      >
        {label}
      </div>
    </AbsoluteFill>
  );
};
