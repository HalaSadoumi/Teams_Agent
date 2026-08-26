import React from "react";
import { StoryboardScene, VisualPlan } from "../types";
import { PillarsDiagram } from "../scenes/PillarsDiagram";
import { PhishingScenario } from "../scenes/PhishingScenario";
import { DataFlowDiagram } from "../scenes/DataFlowDiagram";
import { LayeredDefense } from "../scenes/LayeredDefense";
import { ComparisonScene } from "../scenes/ComparisonScene";
import { ChecklistScene } from "../scenes/ChecklistScene";
import { StatReveal } from "../scenes/StatReveal";
import { TimelineScene } from "../scenes/TimelineScene";
import { LockState } from "../scenes/LockState";
import { AccessControl } from "../scenes/AccessControl";
import { NetworkZones } from "../scenes/NetworkZones";
import { TitleStatement } from "../scenes/TitleStatement";

/** Generic dispatch: every scene is rendered purely from its LLM-generated
 * visual plan (archetype + text slots), so no scene needs bespoke code and
 * adding an archetype means adding one component + one vocabulary entry on
 * the Python side. */
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
  };
  const common = { label: p.label, durationInFrames };

  switch (p.archetype) {
    case "pillars":
      return <PillarsDiagram {...common} items={p.items} roof={p.secondary} />;
    case "attack_scenario":
      return <PhishingScenario {...common} />;
    case "data_flow":
      return <DataFlowDiagram {...common} sources={p.items} hub={p.primary} result={p.secondary} />;
    case "layered_defense":
      return <LayeredDefense {...common} items={p.items} />;
    case "comparison":
      return <ComparisonScene {...common} items={p.items} />;
    case "checklist":
      return <ChecklistScene {...common} items={p.items} />;
    case "stat_reveal":
      return <StatReveal {...common} primary={p.primary} secondary={p.secondary} />;
    case "timeline":
      return <TimelineScene {...common} items={p.items} />;
    case "lock_state":
      return <LockState {...common} primary={p.primary} secondary={p.secondary} />;
    case "access_control":
      return <AccessControl {...common} items={p.items} secondary={p.secondary} />;
    case "network_zones":
      return <NetworkZones {...common} items={p.items} secondary={p.secondary} />;
    case "title_statement":
    default:
      return <TitleStatement {...common} primary={p.primary} narration={scene.narration} />;
  }
};
