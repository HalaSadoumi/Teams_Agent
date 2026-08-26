export interface StoryboardScene {
  scene_id: string;
  chapter_id: string;
  duration: number;
  narration: string;
  visual_type: string;
  visual_description: string;
  on_screen_text: string;
  transition: string;
  audio_path: string | null;
}

/** Split a short on-screen-text string into up to `max` display items, for
 * visual types that show a list/row (bullet_list, icon_row, process_flow,
 * timeline). The data model only carries one short string per scene (see
 * cahier des charges section 8.3), so list-like visuals fake multiple items
 * by splitting on common delimiters; a plain phrase with no delimiter is
 * shown as a single item. */
export function splitItems(text: string, max = 4): string[] {
  const parts = text
    .split(/\s*(?:,|\/|;|→|->| - | et | & )\s*/i)
    .map((s) => s.trim())
    .filter(Boolean);
  return (parts.length > 1 ? parts : [text]).slice(0, max);
}

/** Split on-screen-text into two sides for the comparison visual. */
export function splitComparison(text: string): [string, string] {
  const m = text.split(/\s+(?:vs\.?|contre|\/)\s+/i);
  if (m.length >= 2) return [m[0].trim(), m[1].trim()];
  const items = splitItems(text, 2);
  return [items[0], items[1] ?? ""];
}

/** Extract a leading number/percentage from on-screen-text, if present. */
export function extractStat(text: string): { value: string; label: string } {
  const m = text.match(/^\s*([\d]+(?:[.,]\d+)?\s*%?)\s*[-:—]?\s*(.*)$/);
  if (m && m[1]) return { value: m[1], label: m[2] || text };
  return { value: "", label: text };
}

/** LLM-generated animated-scene plan, keyed by scene_id in scene_visuals.json.
 * `archetype` selects the Remotion component; the remaining fields are its
 * text slots (meaning varies per archetype - see SceneRenderer). */
export interface VisualPlan {
  archetype: string;
  label: string;
  items: string[];
  primary: string;
  secondary: string;
}
