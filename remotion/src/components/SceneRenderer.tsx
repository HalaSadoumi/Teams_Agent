import React from "react";
import { StoryboardScene, VisualPlan } from "../types";
import { PillarsDiagram } from "../scenes/PillarsDiagram";
import { ActorActionTarget } from "../scenes/ActorActionTarget";
import { DataFlowDiagram } from "../scenes/DataFlowDiagram";
import { ConcentricLayers } from "../scenes/ConcentricLayers";
import { ComparisonScene } from "../scenes/ComparisonScene";
import { ChecklistScene } from "../scenes/ChecklistScene";
import { StatReveal } from "../scenes/StatReveal";
import { TimelineScene } from "../scenes/TimelineScene";
import { StateChange } from "../scenes/StateChange";
import { PermissionMatrix } from "../scenes/PermissionMatrix";
import { SeparatedGroups } from "../scenes/SeparatedGroups";
import { TitleStatement } from "../scenes/TitleStatement";

/** Generic dispatch: every scene is rendered purely from its generated visual
 * plan (archetype + text slots), so no scene needs bespoke code and adding an
 * archetype means one component plus one vocabulary entry on the Python side.
 * The archetypes are deliberately domain-neutral - "actor acts on target"
 * rather than "phishing attack" - so the same set serves any subject matter. */
export const SceneRenderer: React.FC<{
  scene: StoryboardScene;
  plan: VisualPlan | undefined;
  durationInFrames: number;
}> = ({ scene, plan, durationInFrames }) => {
  const p: VisualPlan = plan ?? {
    archetype: "title_statement",
    label: "",
    items: [],
    primary: "",
    secondary: "",
    icon: "Info",
    image_prompt: "",
  };
  const common = { label: p.label, durationInFrames };

  switch (p.archetype) {
    case "pillars":
      return <PillarsDiagram {...common} items={p.items} roof={p.secondary} />;
    case "actor_action_target":
      return <ActorActionTarget {...common} primary={p.primary} secondary={p.secondary} />;
    case "data_flow":
      return <DataFlowDiagram {...common} sources={p.items} hub={p.primary} result={p.secondary} />;
    case "concentric_layers":
      return <ConcentricLayers {...common} items={p.items} primary={p.primary} />;
    case "comparison":
      return <ComparisonScene {...common} items={p.items} />;
    case "checklist":
      return <ChecklistScene {...common} items={p.items} />;
    case "stat_reveal":
      return <StatReveal {...common} primary={p.primary} secondary={p.secondary} />;
    case "timeline":
      return <TimelineScene {...common} items={p.items} />;
    case "state_change":
      return <StateChange {...common} primary={p.primary} secondary={p.secondary} />;
    case "permission_matrix":
      return <PermissionMatrix {...common} items={p.items} primary={p.primary} secondary={p.secondary} />;
    case "separated_groups":
      return <SeparatedGroups {...common} items={p.items} secondary={p.secondary} />;
    case "title_statement":
    default:
      return <TitleStatement {...common} primary={p.primary} icon={p.icon} />;
  }
};
