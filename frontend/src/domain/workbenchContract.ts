/**
 * Runtime contract for the v0.1 workbench endpoints (sources, versions,
 * claims, evidence), mirroring contracts/openapi.json. The generated
 * TypeScript types cover compile-time compatibility; these Zod schemas
 * validate runtime payloads. The contract test keeps both in sync.
 */

import { z } from "zod";

const id = z.uuid();
const timestamp = z.iso.datetime({ offset: true });

export const relationValues = ["supports", "contradicts", "mentions", "insufficient"] as const;

export const sourceCreateSchema = z.object({
  title: z.string().min(1).max(200),
  origin: z.string().max(500),
  usage_terms: z.string().max(500),
  initial_text: z.string().min(1),
  initial_label: z.string().max(100),
});

export const sourceOutSchema = z.object({
  id,
  title: z.string(),
  origin: z.string(),
  usage_terms: z.string(),
  created_at: timestamp,
  updated_at: timestamp,
});

export const sourceSummarySchema = z.object({
  id,
  title: z.string(),
  origin: z.string(),
  usage_terms: z.string(),
  version_count: z.number().int().min(0),
  created_at: timestamp,
});

export const versionOutSchema = z.object({
  id,
  source_id: id,
  label: z.string().max(100),
  content_sha256: z.string(),
  created_at: timestamp,
});

export const versionContentSchema = versionOutSchema.extend({
  content: z.string(),
});

export const sourceWithVersionSchema = z.object({
  source: sourceOutSchema,
  version: versionOutSchema,
  created: z.boolean(),
});

export const sourceDetailSchema = z.object({
  source: sourceOutSchema,
  versions: z.array(versionOutSchema),
});

export const versionCreateSchema = z.object({
  label: z.string().max(100),
  text: z.string().min(1),
});

export const locateVersionSchema = z.object({
  start: z.number().int().min(0),
  end: z.number().int().min(0),
  exact_quote: z.string().min(1),
});

export const quoteLocationOutSchema = z.object({
  version_id: id,
  start: z.number().int().min(0),
  end: z.number().int().min(0),
  exact_quote: z.string().min(1),
});

export const claimCreateSchema = z.object({
  statement: z.string().min(1).max(500),
});

export const claimOutSchema = z.object({
  id,
  statement: z.string(),
  review_status: z.string(),
  created_at: timestamp,
});

export const claimSummarySchema = claimOutSchema.extend({
  evidence_count: z.number().int().min(0),
});

export const claimCreatedSchema = z.object({
  claim: claimOutSchema,
  created: z.boolean(),
});

export const evidenceOutSchema = z.object({
  id,
  claim_id: id,
  version_id: id,
  source_id: id,
  source_title: z.string(),
  source_origin: z.string(),
  version_label: z.string(),
  start: z.number().int().min(0),
  end: z.number().int().min(0),
  quote: z.string(),
  relation: z.enum(relationValues),
  note: z.string(),
  created_at: timestamp,
});

export const claimDetailSchema = z.object({
  claim: claimOutSchema,
  evidence: z.array(evidenceOutSchema),
});

export const evidenceBindSchema = z.object({
  version_id: id,
  start: z.number().int().min(0),
  end: z.number().int().min(0),
  relation: z.enum(relationValues),
  note: z.string().max(500),
  exact_quote: z.string().min(1),
});

export const evidenceCreatedSchema = z.object({
  evidence: evidenceOutSchema,
  created: z.boolean(),
});

export type SourceCreate = z.infer<typeof sourceCreateSchema>;
export type SourceSummary = z.infer<typeof sourceSummarySchema>;
export type SourceDetail = z.infer<typeof sourceDetailSchema>;
export type SourceWithVersion = z.infer<typeof sourceWithVersionSchema>;
export type VersionOut = z.infer<typeof versionOutSchema>;
export type VersionContent = z.infer<typeof versionContentSchema>;
export type VersionCreate = z.infer<typeof versionCreateSchema>;
export type QuoteLocationOut = z.infer<typeof quoteLocationOutSchema>;
export type ClaimSummary = z.infer<typeof claimSummarySchema>;
export type ClaimCreated = z.infer<typeof claimCreatedSchema>;
export type ClaimDetail = z.infer<typeof claimDetailSchema>;
export type EvidenceBind = z.infer<typeof evidenceBindSchema>;
export type EvidenceOut = z.infer<typeof evidenceOutSchema>;
export type EvidenceCreated = z.infer<typeof evidenceCreatedSchema>;
