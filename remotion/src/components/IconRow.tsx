import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { BOUNCY, COLORS, FONT } from "../theme";
import { splitItems } from "../types";
import { AnimatedBackground } from "./AnimatedBackground";

const PALETTE = [COLORS.accent, COLORS.accent2, COLORS.accent3, COLORS.accent];

export const IconRow: React.FC<{ text: string }> = ({ text }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const items = splitItems(text, 4);

  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
      <AnimatedBackground />
      <div style={{ display: "flex", gap: 64 }}>
        {items.map((item, i) => {
          const delay = i * 7;
          const s = spring({ frame: frame - delay, fps, config: BOUNCY });
          const opacity = interpolate(frame - delay, [0, 10], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
          const bob = Math.sin((frame - delay) / 15) * 8 * Math.min(1, Math.max(0, s));
          const spin = interpolate(s, [0, 1], [-25, 0]);
          const color = PALETTE[i % PALETTE.length];
          return (
            <div
              key={i}
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                opacity,
                transform: `scale(${s}) translateY(${bob}px) rotate(${spin}deg)`,
                width: 230,
              }}
            >
              <div
                style={{
                  width: 118,
                  height: 118,
                  borderRadius: 59,
                  background: `linear-gradient(135deg, ${color}33, ${COLORS.card})`,
                  border: `3px solid ${color}`,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  marginBottom: 24,
                  boxShadow: `0 0 26px ${color}55`,
                }}
              >
                <div style={{ color, fontFamily: FONT, fontSize: 46, fontWeight: 800 }}>
                  {item.trim().charAt(0).toUpperCase()}
                </div>
              </div>
              <div style={{ color: COLORS.text, fontFamily: FONT, fontSize: 27, fontWeight: 600, textAlign: "center", lineHeight: 1.3 }}>
                {item}
              </div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
