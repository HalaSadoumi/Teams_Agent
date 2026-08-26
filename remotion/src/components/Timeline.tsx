import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { BOUNCY, COLORS, FONT } from "../theme";
import { splitItems } from "../types";
import { AnimatedBackground } from "./AnimatedBackground";

const PALETTE = [COLORS.accent, COLORS.accent2, COLORS.accent3, COLORS.accent];

export const Timeline: React.FC<{ text: string }> = ({ text }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const items = splitItems(text, 4);
  const lineWidth = interpolate(frame, [0, 28], [0, 1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
      <AnimatedBackground />
      <div style={{ position: "relative", width: "74%", height: 220 }}>
        <div
          style={{
            position: "absolute",
            top: 110,
            left: 0,
            height: 4,
            width: `${lineWidth * 100}%`,
            background: `linear-gradient(90deg, ${COLORS.accent}, ${COLORS.accent2}, ${COLORS.accent3})`,
            borderRadius: 2,
            boxShadow: `0 0 12px ${COLORS.accent}77`,
          }}
        />
        <div style={{ display: "flex", justifyContent: "space-between", position: "relative" }}>
          {items.map((item, i) => {
            const delay = 6 + i * 11;
            const s = spring({ frame: frame - delay, fps, config: BOUNCY });
            const opacity = interpolate(frame - delay, [0, 10], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
            const above = i % 2 === 0;
            const color = PALETTE[i % PALETTE.length];
            const bob = Math.sin((frame - delay) / 16) * 4 * Math.min(1, Math.max(0, s));
            return (
              <div key={i} style={{ display: "flex", flexDirection: "column", alignItems: "center", width: 190 }}>
                {above && (
                  <div
                    style={{
                      color: COLORS.text,
                      fontFamily: FONT,
                      fontSize: 25,
                      fontWeight: 600,
                      textAlign: "center",
                      opacity,
                      marginBottom: 14,
                      transform: `scale(${s}) translateY(${bob}px)`,
                    }}
                  >
                    {item}
                  </div>
                )}
                <div
                  style={{
                    width: 26,
                    height: 26,
                    borderRadius: 13,
                    background: color,
                    opacity,
                    transform: `scale(${s})`,
                    marginTop: above ? 96 : 0,
                    boxShadow: `0 0 18px ${color}`,
                    border: `3px solid ${COLORS.bg}`,
                  }}
                />
                {!above && (
                  <div
                    style={{
                      color: COLORS.text,
                      fontFamily: FONT,
                      fontSize: 25,
                      fontWeight: 600,
                      textAlign: "center",
                      opacity,
                      marginTop: 14,
                      transform: `scale(${s}) translateY(${bob}px)`,
                    }}
                  >
                    {item}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </AbsoluteFill>
  );
};
