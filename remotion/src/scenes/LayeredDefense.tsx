import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { COLORS, FONT } from "../theme";
import { SceneLabel } from "../illustrations/primitives";

const PALETTE = [COLORS.accent3, COLORS.accent2, COLORS.accent, COLORS.accent2];

/** Concentric protection layers building outward from the asset at the
 * centre — the "defense in depth" beat. */
export const LayeredDefense: React.FC<{ label?: string; items: string[]; durationInFrames: number }> = ({
  label,
  items,
  durationInFrames,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = frame / durationInFrames;
  const layers = items.slice(0, 4);
  const labelOpacity = interpolate(p, [0.02, 0.12], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const corePulse = 1 + Math.sin(frame / 11) * 0.05;

  return (
    <AbsoluteFill>
      {label && <SceneLabel text={label} opacity={labelOpacity} />}
      <svg width="100%" height="100%" viewBox="-960 -540 1920 1080">
        <g transform="translate(0 80)">
          {layers
            .map((item, i) => ({ item, i }))
            .reverse()
            .map(({ item, i }) => {
              const delay = 12 + (layers.length - 1 - i) * 15;
              const s = spring({ frame: frame - delay, fps, config: { damping: 13 } });
              const radius = 120 + (i + 1) * 82;
              const color = PALETTE[i % PALETTE.length];
              return (
                <g key={i} opacity={s}>
                  <circle
                    cx={0}
                    cy={0}
                    r={radius * s}
                    fill="none"
                    stroke={color}
                    strokeWidth={4}
                    strokeDasharray="14 10"
                    opacity={0.85}
                  />
                  <rect
                    x={-118}
                    y={-radius * s - 22}
                    width={236}
                    height={44}
                    rx={22}
                    fill="#0A0E1A"
                    stroke={color}
                    strokeWidth={3}
                  />
                  <text
                    x={0}
                    y={-radius * s + 8}
                    textAnchor="middle"
                    fill={COLORS.text}
                    fontFamily={FONT}
                    fontSize={24}
                    fontWeight={700}
                  >
                    {item}
                  </text>
                </g>
              );
            })}
          <g transform={`scale(${corePulse})`}>
            <circle r={94} fill={`${COLORS.accent}33`} stroke={COLORS.accent} strokeWidth={5} />
            <text y={10} textAnchor="middle" fill={COLORS.text} fontFamily={FONT} fontSize={28} fontWeight={800}>
              Données
            </text>
          </g>
        </g>
      </svg>
    </AbsoluteFill>
  );
};
