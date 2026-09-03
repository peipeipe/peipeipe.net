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

export type OnsenSpring = {
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

export type OnsenCompositionPlace = {
  fsq_id: string;
  name: string;
  address?: string;
  checkin_date?: string;
  springs: OnsenSpring[];
};

/** 集計・散布図向けに施設情報を付けて平坦化した源泉 */
export type OnsenComposition = OnsenSpring & {
  fsq_id: string;
  name: string;
  address?: string;
  checkin_date?: string;
  spring_index: number;
  spring_count: number;
};

type CompositionData = {
  generated_on?: string;
  stats?: {
    places?: number;
    springs?: number;
    composition_photos?: number;
    not_composition_photos?: number;
  };
  places?: unknown[];
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
  return getOnsenCompositionPlaces().flatMap((place) =>
    place.springs.map((spring, spring_index) => ({
      ...spring,
      fsq_id: place.fsq_id,
      name: place.name,
      address: place.address,
      checkin_date: place.checkin_date,
      spring_index,
      spring_count: place.springs.length,
    })),
  );
}

export function getOnsenCompositionPlaces(): OnsenCompositionPlace[] {
  return (data.places || []).map((raw) => {
    const entry = raw as unknown as Record<string, unknown>;
    const springs = Array.isArray(entry.springs)
      ? (entry.springs as OnsenSpring[])
      : [Object.fromEntries(
          Object.entries(entry).filter(([key]) => !["fsq_id", "name", "address", "checkin_date"].includes(key)),
        ) as OnsenSpring];
    return {
      fsq_id: String(entry.fsq_id || ""),
      name: String(entry.name || ""),
      ...(entry.address ? { address: String(entry.address) } : {}),
      ...(entry.checkin_date ? { checkin_date: String(entry.checkin_date) } : {}),
      springs,
    };
  });
}

export function getCompositionMap(): Map<string, OnsenComposition[]> {
  const result = new Map<string, OnsenComposition[]>();
  getOnsenCompositions().forEach((entry) => {
    if (!entry.fsq_id) return;
    result.set(entry.fsq_id, [...(result.get(entry.fsq_id) || []), entry]);
  });
  return result;
}

/** 一覧のバッジや検索インデックス向けに、施設ごとの要約だけを返す */
export function compositionSummaryByFsqId() {
  const summary: Record<
    string,
    { quality?: string; qualityClass?: string; ph?: number | null; sourceTemp?: number | null; total?: number | null }
  > = {};

  getCompositionMap().forEach((entries, fsqId) => {
    const unique = (values: (string | undefined)[]) => [...new Set(values.filter(Boolean))].join("／");
    const first = entries[0];
    summary[fsqId] = {
      quality: unique(entries.map((entry) => entry.spring_quality)),
      qualityClass: unique(entries.map((entry) => entry.spring_quality_class)),
      ph: first?.ph ?? null,
      sourceTemp: first?.source_temp_c ?? null,
      total: first?.total_ingredients_mg_kg ?? null,
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
    placeCount: new Set(entries.map((entry) => entry.fsq_id)).size,
    photos: new Set(entries.flatMap((entry) => entry.source_photos || [])).size,
    mostAlkaline,
    richest,
    hottest,
    generatedOn: data.generated_on || "",
  };
}

/** 散布図と同じ主系統でまとめた泉質のカウント */
export function qualityBreakdown(entries: OnsenComposition[] = getOnsenCompositions()) {
  const counts = new Map<string, number>();
  entries.forEach((entry) => {
    const group = qualityGroup(entry);
    counts.set(group.label, (counts.get(group.label) || 0) + 1);
  });

  return [...counts.entries()]
    .map(([quality, count]) => ({ quality, count }))
    .sort((a, b) => b.count - a.count || a.quality.localeCompare(b.quality, "ja"));
}

export type QualityGroup = {
  key: string;
  label: string;
};

export type QualityModifier = QualityGroup;

const SPECIAL_SIMPLE_GROUPS: { needle: string; group: QualityGroup }[] = [
  { needle: "単純二酸化炭素", group: { key: "carbon-dioxide", label: "二酸化炭素泉" } },
  { needle: "単純鉄", group: { key: "iron", label: "鉄泉" } },
  { needle: "単純酸性", group: { key: "acid", label: "酸性泉" } },
  { needle: "単純よう素", group: { key: "iodine", label: "よう素泉" } },
  { needle: "単純硫黄", group: { key: "sulfur", label: "硫黄泉" } },
  { needle: "単純弱放射能", group: { key: "radioactive", label: "放射能泉" } },
  { needle: "単純放射能", group: { key: "radioactive", label: "放射能泉" } },
];

const ANION_GROUPS: { needle: string; group: QualityGroup }[] = [
  { needle: "塩化物", group: { key: "chloride", label: "塩化物泉" } },
  { needle: "炭酸水素塩", group: { key: "bicarbonate", label: "炭酸水素塩泉" } },
  { needle: "硫酸塩", group: { key: "sulfate", label: "硫酸塩泉" } },
];

/**
 * 散布図の色分け用に泉質名を主系統へ寄せる。
 * 複合塩類泉は、泉質名に mval% の多い順で書かれた陰イオンのうち
 * 最初のものを主系統とする。特殊成分は qualityModifiers で別に示す。
 */
export function qualityGroup(entry: OnsenComposition): QualityGroup {
  const quality = entry.spring_quality || "";

  const specialSimple = SPECIAL_SIMPLE_GROUPS.find(({ needle }) => quality.includes(needle));
  if (specialSimple) return specialSimple.group;

  const primaryAnion = ANION_GROUPS
    .map((item) => ({ ...item, index: quality.indexOf(item.needle) }))
    .filter((item) => item.index >= 0)
    .sort((a, b) => a.index - b.index)[0];
  if (primaryAnion) return primaryAnion.group;

  if (quality.includes("単純温泉")) return { key: "simple", label: "単純温泉" };
  return { key: "other", label: "その他" };
}

/** 主系統とは別に見せる「含硫黄」などの特殊成分 */
export function qualityModifiers(entry: OnsenComposition): QualityModifier[] {
  const quality = entry.spring_quality || "";
  const modifiers: { needle: string; modifier: QualityModifier }[] = [
    { needle: "含硫黄", modifier: { key: "sulfur", label: "含硫黄" } },
    { needle: "含二酸化炭素", modifier: { key: "carbon-dioxide", label: "含二酸化炭素" } },
    { needle: "含放射能", modifier: { key: "radioactive", label: "含放射能" } },
    { needle: "含弱放射能", modifier: { key: "radioactive", label: "含弱放射能" } },
    { needle: "含鉄", modifier: { key: "iron", label: "含鉄" } },
    { needle: "含よう素", modifier: { key: "iodine", label: "含よう素" } },
  ];

  const result = modifiers
    .filter(({ needle }) => quality.includes(needle))
    .map(({ modifier }) => modifier);
  if (/^酸性(?:・|－|-)/.test(quality)) result.unshift({ key: "acid", label: "酸性" });
  return [...new Map(result.map((modifier) => [modifier.key, modifier])).values()];
}

export type ScatterPoint = {
  fsqId: string;
  anchorId: string;
  name: string;
  quality: string;
  ph: number;
  total: number;
  group: QualityGroup;
  modifiers: QualityModifier[];
};

export function scatterPoints(entries: OnsenComposition[] = getOnsenCompositions()): ScatterPoint[] {
  return entries
    .filter(
      (entry) => typeof entry.ph === "number" && typeof entry.total_ingredients_mg_kg === "number",
    )
    .map((entry) => ({
      fsqId: entry.fsq_id,
      anchorId: entry.spring_index === 0
        ? `composition-${entry.fsq_id}`
        : `composition-${entry.fsq_id}-spring-${entry.spring_index + 1}`,
      name: entry.spring_count > 1 && entry.spring_name
        ? `${entry.name} / ${entry.spring_name}`
        : entry.name,
      quality: entry.spring_quality || "",
      ph: entry.ph as number,
      total: entry.total_ingredients_mg_kg as number,
      group: qualityGroup(entry),
      modifiers: qualityModifiers(entry),
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

// global.css の .scatter-label と揃えること（幅の見積もりがこの値に依存している）
const LABEL_FONT_SIZE = 10;
const LABEL_ASCENT = 7;
const LABEL_DESCENT = 3;
const LABEL_GAP = 6;
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
 * ラベルの候補位置。どれも点のすぐ隣に限っている：離れた場所へ逃がすと
 * 引き出し線を引いてもどの点の名前なのか読み取れないため、
 * 置き場所がなければラベル自体を出さず（showLabel: false）、
 * 名前はホバー / フォーカスのツールチップと下の成分表カードに任せる。
 */
const SIDE_DX = DOT_RADIUS + 4;
const CANDIDATES: { anchor: Anchor; dx: number; dy: number }[] = [
  // 真上・真下（点が文字列の中央に来るので、長い名前でも取り違えにくい）
  { anchor: "middle", dx: 0, dy: -12 },
  { anchor: "start", dx: SIDE_DX, dy: -12 },
  { anchor: "end", dx: -SIDE_DX, dy: -12 },
  { anchor: "middle", dx: 0, dy: 16 },
  { anchor: "start", dx: SIDE_DX, dy: 16 },
  { anchor: "end", dx: -SIDE_DX, dy: 16 },
  // 真横
  { anchor: "start", dx: SIDE_DX, dy: 4 },
  { anchor: "end", dx: -SIDE_DX, dy: 4 },
  // 斜め。ここまで離すと引き出し線なしで読ませられる限界
  { anchor: "start", dx: SIDE_DX, dy: -16 },
  { anchor: "end", dx: -SIDE_DX, dy: -16 },
  { anchor: "start", dx: SIDE_DX, dy: 21 },
  { anchor: "end", dx: -SIDE_DX, dy: 21 },
];

export type ScatterLayoutPoint = ScatterPoint & {
  x: number;
  y: number;
  label: string;
  /** 重ならずに置ける場所が見つかった点だけ、図の中に名前を出す */
  showLabel: boolean;
  labelX: number;
  labelY: number;
  anchor: Anchor;
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
      // 自分の点だけは対象外。すぐ横に置くと余白ぶんは必ず触れるので、
      // ここを数えると自分の点から 25px 以上離れた場所しか「衝突なし」にならない
      dotRects.forEach((dot, dotIndex) => {
        if (dotIndex !== index) cost += overlapArea(rect, dot);
      });

      if (cost === 0) {
        best = { candidate, rect, cost };
        break;
      }
      if (!best || cost < best.cost) best = { candidate, rect, cost };
    }

    const chosen = best!;
    const showLabel = chosen.cost === 0;
    // 描かないラベルは場所を占有させない（後続の点の置き場所を減らさないため）
    if (showLabel) placed.push(chosen.rect);

    results[index] = {
      ...item.point,
      x: item.x,
      y: item.y,
      label: item.label,
      showLabel,
      labelX: item.x + chosen.candidate.dx,
      labelY: item.y + chosen.candidate.dy,
      anchor: chosen.candidate.anchor,
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
