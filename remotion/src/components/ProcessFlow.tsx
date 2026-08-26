import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { BOUNCY, COLORS, FONT } from "../theme";
import { splitItems } from "../types";
import { AnimatedBackground } from "./AnimatedBackground";

export const ProcessFlow: React.FC<{ text: string }> = ({ text }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const items = splitItems(text, 4);

  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
      <AnimatedBackground />
      <div style={{ display: "flex", alignItems: "center" }}>
        {items.map((item, i) => {
          const delay = i * 11;
          const s = spring({ frame: frame - delay, fps, config: BOUNCY });
          const opacity = interpolate(frame - delay, [0, 10], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
          const arrowProgress = interpolate(frame - delay - 8, [0, 14], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
          const bob = Math.sin((frame - delay) / 18) * 5 * Math.min(1, Math.max(0, s));
          return (
            <React.Fragment key={i}>
              <div
                style={{
                  opacity,
                  transform: `scale(${s}) translateY(${bob}px)`,
                  background: `linear-gradient(160deg, ${COLORS.card}, rgba(56,189,248,0.10))`,
                  border: `2px solid ${COLORS.accent}`,
                  borderRadius: 18,
                  padding: "28px 32px",
                  maxWidth: 250,
                  textAlign: "center",
                  boxShadow: `0 8px 30px ${COLORS.accent}33`,
                }}
              >
                <div
                  style={{
                    color: COLORS.bg,
                    background: COLORS.accent,
                    borderRadius: 20,
                    width: 34,
                    height: 34,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    margin: "0 auto 14px",
                    fontFamily: FONT,
                    fontSize: 18,
                    fontWeight: 800,
                  }}
                >
                  {i + 1}
                </div>
                <div style={{ color: COLORS.text, fontFamily: FONT, fontSize: 25, fontWeight: 600, lineHeight: 1.3 }}>{item}</div>
              </div>
              {i < items.length - 1 && (
                <div style={{ width: 70, height: 3, margin: "0 14px", overflow: "hidden", position: "relative" }}>
                  <div
                    style={{
                      position: "absolute",
                      inset: 0,
                      background: `linear-gradient(90deg, ${COLORS.accent}, ${COLORS.accent2})`,
                      transform: `scaleX(${arrowProgress})`,
                      transformOrigin: "left",
                    }}
                  />
                </div>
              )}
            </React.Fragment>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
