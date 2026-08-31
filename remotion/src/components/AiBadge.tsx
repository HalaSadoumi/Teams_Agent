import React from "react";
import { AbsoluteFill } from "remotion";
import { COLORS, FONT } from "../theme";

/** Persistent notice that the course was produced automatically.
 *
 * The narration is the speaker's real audio, but the structure, wording of
 * on-screen labels and all imagery are machine-generated, so a viewer should
 * know errors are possible. Kept small and low-contrast in a corner: visible
 * on inspection, never competing with the content. */
export const AiBadge: React.FC = () => (
  <AbsoluteFill style={{ pointerEvents: "none" }}>
    <div
      style={{
        position: "absolute",
        top: 26,
        right: 30,
        display: "flex",
        alignItems: "center",
        gap: 9,
        padding: "8px 15px",
        borderRadius: 999,
        background: "rgba(8,12,22,0.55)",
        border: `1px solid ${COLORS.cardBorder}`,
        fontFamily: FONT,
        fontSize: 19,
        fontWeight: 600,
        color: COLORS.textDim,
        letterSpacing: 0.3,
      }}
    >
      <span
        style={{
          width: 9,
          height: 9,
          borderRadius: "50%",
          background: COLORS.accent,
          boxShadow: `0 0 9px ${COLORS.accent}`,
        }}
      />
      Contenu généré par IA
    </div>
  </AbsoluteFill>
);
