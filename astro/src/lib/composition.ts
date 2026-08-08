import compositionData from "../../data/onsen_composition.json";

export type CompositionIngredient = {
  name: string;
  symbol?: string;
  mg_kg?: number | null;
};

export type CompositionTreatment = {
  applied?: boolean;
  reason?: string;
};

export type OnsenComposition = {
  fsq_id: string;
  name: string;
  address?: string;
  checkin_date?: string;
  confidence?: "high" | "medium" | "low";
  spring_name?: string;
  spring_quality?: string;
  spring_quality_class?: string;
  source_temp_c?: number | null;
  use_temp_c?: number | null;
  ph?: number | null;
  ph_lab?: number | null;
  yield_l_min?: number | null;
  evaporation_residue_mg_kg?: number | null;
  dissolved_solids_mg_kg?: number | null;
  total_ingredients_mg_kg?: number | null;
  cations?: CompositionIngredient[];
  cations_total_mg_kg?: number | null;
  anions?: CompositionIngredient[];
  anions_total_mg_kg?: number | null;
  undissociated?: CompositionIngredient[];
  undissociated_total_mg_kg?: number | null;
  dissolved_gas?: CompositionIngredient[];
  dissolved_gas_total_mg_kg?: number | null;
  treatment?: Record<string, CompositionTreatment>;
  indications?: string[];
  contraindications?: string[];
  analyzed_on?: string;
  analyzer?: string;
  analyzer_registration?: string;
  notes?: string;
  source_photos?: string[];
};

type CompositionData = {
  generated_on?: string;
  stats?: {
    places?: number;
    composition_photos?: number;
    not_composition_photos?: number;
  };
  places?: OnsenComposition[];
  not_composition_photos?: string[];
};

// 掲示の「加水・加温・循環・消毒」を表示順に固定する
export const TREATMENT_LABELS: { key: string; label: string }[] = [
  { key: "kasui", label: "加水" },
  { key: "kaon", label: "加温" },
  { key: "junkan", label: "循環ろ過" },
  { key: "shodoku", label: "消毒" },
];

const data = compositionData as CompositionData;

export function getOnsenCompositions(): OnsenComposition[] {
  return data.places || [];
}

export function getCompositionMap(): Map<string, OnsenComposition> {
  return new Map(
    getOnsenCompositions()
      .filter((entry) => entry.fsq_id)
      .map((entry) => [entry.fsq_id, entry]),
  );
}

/** 一覧のバッジや検索インデックス向けに、施設ごとの要約だけを返す */
export function compositionSummaryByFsqId() {
  const summary: Record<
    string,
    { quality?: string; qualityClass?: string; ph?: number | null; sourceTemp?: number | null; total?: number | null }
  > = {};

  getOnsenCompositions().forEach((entry) => {
    if (!entry.fsq_id) return;
    summary[entry.fsq_id] = {
      quality: entry.spring_quality,
      qualityClass: entry.spring_quality_class,
      ph: entry.ph ?? null,
      sourceTemp: entry.source_temp_c ?? null,
      total: entry.total_ingredients_mg_kg ?? null,
    };
  });

  return summary;
}

export function summarizeCompositions(entries: OnsenComposition[] = getOnsenCompositions()) {
  const withPh = entries.filter((entry) => typeof entry.ph === "number");
  const withTotal = entries.filter((entry) => typeof entry.total_ingredients_mg_kg === "number");

  const mostAlkaline = withPh.reduce<OnsenComposition | null>(
    (current, entry) => (!current || (entry.ph as number) > (current.ph as number) ? entry : current),
    null,
  );
  const richest = withTotal.reduce<OnsenComposition | null>(
    (current, entry) =>
      !current || (entry.total_ingredients_mg_kg as number) > (current.total_ingredients_mg_kg as number)
        ? entry
        : current,
    null,
  );
  const hottest = entries.reduce<OnsenComposition | null>(
    (current, entry) =>
      typeof entry.source_temp_c === "number" &&
      (!current || entry.source_temp_c > (current.source_temp_c as number))
        ? entry
        : current,
    null,
  );

  return {
    count: entries.length,
    photos: entries.reduce((sum, entry) => sum + (entry.source_photos?.length || 0), 0),
    mostAlkaline,
    richest,
    hottest,
    generatedOn: data.generated_on || "",
  };
}

/** 「単純温泉」「ナトリウム－塩化物温泉」など、泉質名でまとめたカウント */
export function qualityBreakdown(entries: OnsenComposition[] = getOnsenCompositions()) {
  const counts = new Map<string, number>();
  entries.forEach((entry) => {
    const quality = entry.spring_quality;
    if (!quality) return;
    counts.set(quality, (counts.get(quality) || 0) + 1);
  });

  return [...counts.entries()]
    .map(([quality, count]) => ({ quality, count }))
    .sort((a, b) => b.count - a.count || a.quality.localeCompare(b.quality, "ja"));
}

export type QualityGroup = {
  key: string;
  label: string;
};

/** 散布図の色分け用に、泉質名をおおまかな系統へ寄せる */
export function qualityGroup(entry: OnsenComposition): QualityGroup {
  const quality = entry.spring_quality || "";

  if (quality.includes("硫黄")) return { key: "sulfur", label: "硫黄泉" };
  if (quality.includes("鉄")) return { key: "iron", label: "鉄泉" };
  if (quality.includes("単純温泉")) return { key: "simple", label: "単純温泉" };
  if (quality.includes("塩化物")) return { key: "chloride", label: "塩化物泉" };
  if (quality.includes("炭酸水素塩")) return { key: "bicarbonate", label: "炭酸水素塩泉" };
  if (quality.includes("硫酸塩")) return { key: "sulfate", label: "硫酸塩泉" };
  return { key: "other", label: "その他" };
}

export type ScatterPoint = {
  fsqId: string;
  name: string;
  ph: number;
  total: number;
  group: QualityGroup;
};

export function scatterPoints(entries: OnsenComposition[] = getOnsenCompositions()): ScatterPoint[] {
  return entries
    .filter(
      (entry) => typeof entry.ph === "number" && typeof entry.total_ingredients_mg_kg === "number",
    )
    .map((entry) => ({
      fsqId: entry.fsq_id,
      name: entry.name,
      ph: entry.ph as number,
      total: entry.total_ingredients_mg_kg as number,
      group: qualityGroup(entry),
    }));
}

// --- 散布図（pH × 成分総計）のレイアウト ---

export const SCATTER_CHART = {
  width: 760,
  height: 440,
  left: 58,
  right: 18,
  top: 20,
  bottom: 46,
};

/** 上下端（pH9.9・182.5mg/kg の京王高尾山温泉、16850mg/kg の松代荘）が枠の外に出ない範囲 */
const PH_DOMAIN = [5.5, 10.2];
const TOTAL_DOMAIN = [150, 20000];

export const SCATTER_PH_TICKS = [6, 7, 8, 9, 10];
export const SCATTER_TOTAL_TICKS = [200, 1000, 3000, 10000];

export const scatterPlotWidth = SCATTER_CHART.width - SCATTER_CHART.left - SCATTER_CHART.right;
export const scatterPlotHeight = SCATTER_CHART.height - SCATTER_CHART.top - SCATTER_CHART.bottom;

export const phToX = (ph: number) =>
  SCATTER_CHART.left + ((ph - PH_DOMAIN[0]) / (PH_DOMAIN[1] - PH_DOMAIN[0])) * scatterPlotWidth;

export const totalToY = (total: number) => {
  const ratio =
    (Math.log10(total) - Math.log10(TOTAL_DOMAIN[0])) /
    (Math.log10(TOTAL_DOMAIN[1]) - Math.log10(TOTAL_DOMAIN[0]));
  return SCATTER_CHART.top + scatterPlotHeight - ratio * scatterPlotHeight;
};

const LABEL_FONT_SIZE = 12;
const LABEL_ASCENT = 9;
const LABEL_DESCENT = 3;
const LABEL_GAP = 3;
const DOT_RADIUS = 6;

/** 括弧書きは図では読み切れないので落とす（「コタン温泉 (コタン温泉 露天風呂)」→「コタン温泉」） */
function shortLabel(name: string) {
  return name.replace(/\s*[（(].*$/, "").trim() || name;
}

/** SVG の text は等幅ではないので、半角を 0.55em・全角を 1em として概算する */
function estimateLabelWidth(text: string) {
  let em = 0;
  for (const char of text) {
    em += /[ -~｡-ﾟ]/.test(char) ? 0.55 : 1;
  }
  return em * LABEL_FONT_SIZE;
}

type Rect = { x1: number; y1: number; x2: number; y2: number };

function overlapArea(a: Rect, b: Rect) {
  const w = Math.min(a.x2, b.x2) - Math.max(a.x1, b.x1);
  const h = Math.min(a.y2, b.y2) - Math.max(a.y1, b.y1);
  return w > 0 && h > 0 ? w * h : 0;
}

type Anchor = "start" | "middle" | "end";

function labelRect(cx: number, baseline: number, width: number, anchor: Anchor): Rect {
  const x1 = anchor === "start" ? cx : anchor === "end" ? cx - width : cx - width / 2;
  return {
    x1: x1 - LABEL_GAP,
    y1: baseline - LABEL_ASCENT - LABEL_GAP,
    x2: x1 + width + LABEL_GAP,
    y2: baseline + LABEL_DESCENT + LABEL_GAP,
  };
}

/**
 * 点ごとに候補位置を近い順に試し、既に置いたラベル・全ての点・枠の外と
 * 重ならない場所を選ぶ。全滅した場合は重なりが最小の候補へ逃がす。
 */
const CANDIDATES: { anchor: Anchor; dx: number; dy: number }[] = [];
for (const [dy, rank] of [
  [-12, 0],
  [16, 0],
  [4, 1],
  [-25, 2],
  [29, 2],
  [-16, 3],
  [21, 3],
  [-38, 4],
  [42, 4],
  [-29, 5],
  [34, 5],
  [-51, 6],
  [55, 6],
  [-42, 7],
  [47, 7],
  [-64, 8],
  [68, 8],
  [-77, 9],
  [81, 9],
] as [number, number][]) {
  const horizontals: { anchor: Anchor; dx: number }[] =
    rank % 2 === 1 || Math.abs(dy) < 12
      ? [
          { anchor: "start", dx: DOT_RADIUS + 4 },
          { anchor: "end", dx: -(DOT_RADIUS + 4) },
        ]
      : [
          { anchor: "middle", dx: 0 },
          { anchor: "start", dx: DOT_RADIUS + 4 },
          { anchor: "end", dx: -(DOT_RADIUS + 4) },
        ];
  for (const horizontal of horizontals) {
    CANDIDATES.push({ anchor: horizontal.anchor, dx: horizontal.dx, dy });
  }
}

export type ScatterLayoutPoint = ScatterPoint & {
  x: number;
  y: number;
  label: string;
  labelX: number;
  labelY: number;
  anchor: Anchor;
  leader: { x1: number; y1: number; x2: number; y2: number } | null;
};

export function layoutScatterPoints(
  points: ScatterPoint[] = scatterPoints(),
): ScatterLayoutPoint[] {
  const positioned = points.map((point) => ({
    point,
    x: phToX(point.ph),
    y: totalToY(point.total),
    label: shortLabel(point.name),
  }));

  const dotRects: Rect[] = positioned.map((item) => ({
    x1: item.x - DOT_RADIUS - 1,
    y1: item.y - DOT_RADIUS - 1,
    x2: item.x + DOT_RADIUS + 1,
    y2: item.y + DOT_RADIUS + 1,
  }));

  const bounds: Rect = {
    x1: SCATTER_CHART.left,
    y1: SCATTER_CHART.top,
    x2: SCATTER_CHART.width - SCATTER_CHART.right,
    y2: SCATTER_CHART.top + scatterPlotHeight,
  };

  // 近くに点が多いものほど逃げ場が少ないので先に置く
  const order = positioned
    .map((item, index) => {
      const crowding = positioned.filter(
        (other) => other !== item && Math.abs(other.x - item.x) < 90 && Math.abs(other.y - item.y) < 60,
      ).length;
      return { index, crowding };
    })
    .sort((a, b) => b.crowding - a.crowding || a.index - b.index)
    .map((item) => item.index);

  const placed: Rect[] = [];
  const results: ScatterLayoutPoint[] = new Array(positioned.length);

  for (const index of order) {
    const item = positioned[index];
    const width = estimateLabelWidth(item.label);

    let best: { candidate: (typeof CANDIDATES)[number]; rect: Rect; cost: number } | null = null;

    for (const candidate of CANDIDATES) {
      const cx = item.x + candidate.dx;
      const baseline = item.y + candidate.dy;
      const rect = labelRect(cx, baseline, width, candidate.anchor);

      // 枠からはみ出す候補は、はみ出した幅ぶんのペナルティを付ける
      const outside =
        Math.max(0, bounds.x1 - rect.x1) +
        Math.max(0, rect.x2 - bounds.x2) +
        Math.max(0, bounds.y1 - rect.y1) +
        Math.max(0, rect.y2 - bounds.y2);

      let cost = outside * 100;
      for (const other of placed) cost += overlapArea(rect, other);
      for (const dot of dotRects) cost += overlapArea(rect, dot);

      if (cost === 0) {
        best = { candidate, rect, cost };
        break;
      }
      if (!best || cost < best.cost) best = { candidate, rect, cost };
    }

    const chosen = best!;
    placed.push(chosen.rect);

    const labelX = item.x + chosen.candidate.dx;
    const labelY = item.y + chosen.candidate.dy;
    const distance = Math.hypot(labelX - item.x, labelY - LABEL_ASCENT / 2 - item.y);

    results[index] = {
      ...item.point,
      x: item.x,
      y: item.y,
      label: item.label,
      labelX,
      labelY,
      anchor: chosen.candidate.anchor,
      // 点から離して置いたものは、どの点のラベルか分かるよう引き出し線でつなぐ
      leader:
        distance > 26
          ? {
              x1: item.x,
              y1: item.y,
              x2: labelX,
              y2: labelY - (chosen.candidate.dy < 0 ? -LABEL_DESCENT : LABEL_ASCENT / 2),
            }
          : null,
    };
  }

  return results;
}

export function formatMgKg(value?: number | null) {
  if (typeof value !== "number") return "";
  if (value >= 1000) return `${value.toLocaleString("ja-JP")} mg/kg`;
  return `${value} mg/kg`;
}

export function formatTemp(value?: number | null) {
  return typeof value === "number" ? `${value}℃` : "";
}
