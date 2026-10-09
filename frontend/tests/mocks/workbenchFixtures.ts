/** Shared workbench test data: stable UUIDs, timestamps and contract-shaped records. */

const SOURCE_ID = "11111111-1111-4111-8111-111111111111";
export const VERSION_ID = "22222222-2222-4222-8222-222222222222";
export const CLAIM_ID = "33333333-3333-4333-8333-333333333333";
const EVIDENCE_ID = "44444444-4444-4444-8444-444444444444";
const CREATED_AT = "2026-10-10T08:00:00+08:00";

export const sampleSourceOut = {
  id: SOURCE_ID,
  title: "史記·秦始皇本紀",
  origin: "中華書局點校本",
  usage_terms: "個人研究使用",
  created_at: CREATED_AT,
  updated_at: CREATED_AT,
};

export const sampleVersionOut = {
  id: VERSION_ID,
  source_id: SOURCE_ID,
  label: "整理稿一",
  content_sha256: "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
  created_at: CREATED_AT,
};

export const sampleSourceSummary = {
  id: SOURCE_ID,
  title: "史記·秦始皇本紀",
  origin: "中華書局點校本",
  usage_terms: "個人研究使用",
  version_count: 2,
  created_at: CREATED_AT,
};

export const sampleClaimOut = {
  id: CLAIM_ID,
  statement: "秦並天下在三十六年。",
  review_status: "unverified",
  created_at: CREATED_AT,
};

export const sampleClaimSummary = {
  ...sampleClaimOut,
  evidence_count: 1,
};

export const sampleEvidenceOut = {
  id: EVIDENCE_ID,
  claim_id: CLAIM_ID,
  version_id: VERSION_ID,
  source_id: SOURCE_ID,
  source_title: "史記·秦始皇本紀",
  source_origin: "中華書局點校本",
  version_label: "整理稿一",
  start: 0,
  end: 2,
  quote: "秦並",
  relation: "supports",
  note: "本紀正文",
  created_at: CREATED_AT,
};
