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

export function formatMgKg(value?: number | null) {
  if (typeof value !== "number") return "";
  if (value >= 1000) return `${value.toLocaleString("ja-JP")} mg/kg`;
  return `${value} mg/kg`;
}

export function formatTemp(value?: number | null) {
  return typeof value === "number" ? `${value}℃` : "";
}
