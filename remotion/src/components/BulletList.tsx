import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { BOUNCY, COLORS, FONT } from "../theme";
import { splitItems } from "../types";
import { AnimatedBackground } from "./AnimatedBackground";

const PALETTE = [COLORS.accent, COLORS.accent2, COLORS.accent3, COLORS.accent, COLORS.accent2];

export const BulletList: React.FC<{ text: string }> = ({ text }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const items = splitItems(text, 5);

  return (
    <AbsoluteFill style={{ justifyContent: "center", padding: "0 12%" }}>
      <AnimatedBackground />
      {items.map((item, i) => {
        const delay = i * 7;
        const s = spring({ frame: frame - delay, fps, config: BOUNCY });
        const opacity = interpolate(frame - delay, [0, 10], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
        const translateX = interpolate(s, [0, 1], [-90, 0]);
        const pulse = 1 + Math.sin((frame - delay) / 12) * 0.06 * Math.min(1, Math.max(0, s));
        const color = PALETTE[i % PALETTE.length];
        return (
          <div
            key={i}
            style={{
              display: "flex",
              alignItems: "center",
              marginBottom: 32,
              opacity,
              transform: `translateX(${translateX}px)`,
              background: COLORS.card,
              border: `1px solid ${COLORS.cardBorder}`,
              borderRadius: 18,
              padding: "22px 32px",
            }}
          >
            <div
              style={{
                width: 22,
                height: 22,
                borderRadius: 11,
                background: color,
                marginRight: 28,
                flexShrink: 0,
                boxShadow: `0 0 16px ${color}`,
                transform: `scale(${pulse})`,
              }}
            />
            <div style={{ color: COLORS.text, fontFamily: FONT, fontSize: 40, fontWeight: 600, lineHeight: 1.3 }}>{item}</div>
          </div>
        );
      })}
    </AbsoluteFill>
  );
};
