/** OR-01 closed reason codes → short UI copy keys (0076). */

const LABELS: Record<string, { zh: string; en: string }> = {
  DOMAIN_MISMATCH: {
    zh: "主语类型不在属性定义域内",
    en: "Subject type is outside the property domain",
  },
  RANGE_MISMATCH: {
    zh: "宾语类型不在属性值域内",
    en: "Object type is outside the property range",
  },
  DISJOINT_TYPE: {
    zh: "端点类型与互斥声明冲突",
    en: "Endpoint types conflict with a disjointness axiom",
  },
  DATATYPE_INVALID: {
    zh: "属性值不符合声明的数据类型",
    en: "Value does not match the declared datatype",
  },
  UNIT_CONFLICT: {
    zh: "单位与属性声明冲突",
    en: "Unit conflicts with the property declaration",
  },
  ONTOLOGY_VERSION_STALE: {
    zh: "本体已变，需重新对齐",
    en: "Ontology changed; re-alignment needed",
  },
  EVIDENCE_MISSING: {
    zh: "缺少可落库的证据",
    en: "Required evidence is missing",
  },
  AMBIGUOUS_BINDING: {
    zh: "候选不唯一或两票不一致",
    en: "Ambiguous binding or disagreeing votes",
  },
  UNKNOWN_ENDPOINT_TYPE: {
    zh: "端点类型未知，需人工确认",
    en: "Endpoint type unknown; needs a person",
  },
};

export function reasonCodeLabel(code: string, lang: "zh" | "en"): string {
  const row = LABELS[code];
  if (!row) return code;
  return lang === "zh" ? row.zh : row.en;
}

export function validationDecisionLabel(
  decision: string | null | undefined,
  lang: "zh" | "en",
): string | null {
  if (!decision) return null;
  if (decision === "needs_review") {
    return lang === "zh" ? "需人工审核" : "Needs review";
  }
  if (decision === "rejected") {
    return lang === "zh" ? "校验拒绝" : "Validation rejected";
  }
  if (decision === "accepted") {
    return lang === "zh" ? "校验通过" : "Validation accepted";
  }
  return decision;
}
