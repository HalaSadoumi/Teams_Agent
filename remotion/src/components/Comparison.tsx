import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { BOUNCY, COLORS, FONT } from "../theme";
import { splitComparison } from "../types";
import { AnimatedBackground } from "./AnimatedBackground";

export const Comparison: React.FC<{ text: string }> = ({ text }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const [left, right] = splitComparison(text);

  const sLeft = spring({ frame, fps, config: BOUNCY });
  const sRight = spring({ frame: frame - 8, fps, config: BOUNCY });
  const opacityLeft = interpolate(frame, [0, 12], [0, 1], { extrapolateRight: "clamp" });
  const opacityRight = interpolate(frame - 8, [0, 12], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const vsScale = spring({ frame: frame - 4, fps, config: BOUNCY });

  const panel = (opacity: number, s: number, fromLeft: boolean, color: string): React.CSSProperties => ({
    flex: 1,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    padding: "0 60px",
    opacity,
    transform: `translateX(${(fromLeft ? -1 : 1) * (1 - s) * 100}px)`,
    borderTop: `4px solid ${color}`,
  });

  return (
    <AbsoluteFill style={{ flexDirection: "row" }}>
      <AnimatedBackground />
      <div style={panel(opacityLeft, sLeft, true, COLORS.accent)}>
        <div style={{ color: COLORS.text, fontFamily: FONT, fontSize: 40, fontWeight: 700, textAlign: "center", lineHeight: 1.3 }}>
          {left}
        </div>
      </div>
      <div
        style={{
          width: 66,
          height: 66,
          borderRadius: 33,
          background: `linear-gradient(135deg, ${COLORS.accent}, ${COLORS.accent3})`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: COLORS.bg,
          fontFamily: FONT,
          fontWeight: 800,
          fontSize: 20,
          flexShrink: 0,
          alignSelf: "center",
          transform: `scale(${vsScale})`,
          boxShadow: `0 0 30px ${COLORS.accent}77`,
        }}
      >
        VS
      </div>
      <div style={panel(opacityRight, sRight, false, COLORS.accent3)}>
        <div style={{ color: COLORS.text, fontFamily: FONT, fontSize: 40, fontWeight: 700, textAlign: "center", lineHeight: 1.3 }}>
          {right}
        </div>
      </div>
    </AbsoluteFill>
  );
};
