/**
 * Workbench API calls for sources, versions, claims and evidence. Every call
 * validates its response against the Zod contract and classifies failures the
 * same way as the locate tool (LocateCallError with api / invalid_response /
 * network reasons). Idempotent creates rely on the returned `created` flag or
 * on the 200-vs-201 status, both surfaced to the caller.
 */

import { z } from "zod";
import { requestJson, requestJsonWithStatus, type RequestInitLike } from "./client";
import {
  claimCreatedSchema,
  claimDetailSchema,
  claimSummarySchema,
  evidenceCreatedSchema,
  locateVersionSchema,
  quoteLocationOutSchema,
  sourceDetailSchema,
  sourceSummarySchema,
  sourceWithVersionSchema,
  versionContentSchema,
  versionOutSchema,
  type ClaimCreated,
  type ClaimDetail,
  type ClaimSummary,
  type EvidenceBind,
  type EvidenceCreated,
  type QuoteLocationOut,
  type SourceCreate,
  type SourceDetail,
  type SourceSummary,
  type SourceWithVersion,
  type VersionContent,
  type VersionCreate,
  type VersionOut,
} from "../domain/workbenchContract";

const post = <T>(path: string, schema: z.ZodType<T>, body: unknown, init: RequestInitLike = {}) =>
  requestJson(path, schema, { method: "POST", body, ...init });

export async function listSources(
  q?: string,
  init: RequestInitLike = {},
): Promise<SourceSummary[]> {
  const query = q === undefined || q === "" ? "" : `?q=${encodeURIComponent(q)}`;
  return requestJson(`/v1/sources${query}`, z.array(sourceSummarySchema), init);
}

export function createSource(
  request: SourceCreate,
  init: RequestInitLike = {},
): Promise<SourceWithVersion> {
  return post("/v1/sources", sourceWithVersionSchema, request, init);
}

export function getSource(id: string, init: RequestInitLike = {}): Promise<SourceDetail> {
  return requestJson(`/v1/sources/${encodeURIComponent(id)}`, sourceDetailSchema, init);
}

/** Add a version; identical content answers 200 with the stored version. */
export async function addVersion(
  sourceId: string,
  request: VersionCreate,
  init: RequestInitLike = {},
): Promise<{ version: VersionOut; created: boolean }> {
  const { data, status } = await requestJsonWithStatus(
    `/v1/sources/${encodeURIComponent(sourceId)}/versions`,
    versionOutSchema,
    { method: "POST", body: request, ...init },
  );
  return { version: data, created: status === 201 };
}

export function getVersion(id: string, init: RequestInitLike = {}): Promise<VersionContent> {
  return requestJson(`/v1/versions/${encodeURIComponent(id)}`, versionContentSchema, init);
}

export function locateInVersion(
  versionId: string,
  request: z.infer<typeof locateVersionSchema>,
  init: RequestInitLike = {},
): Promise<QuoteLocationOut> {
  return post(
    `/v1/versions/${encodeURIComponent(versionId)}/locate`,
    quoteLocationOutSchema,
    request,
    init,
  );
}

export function listClaims(init: RequestInitLike = {}): Promise<ClaimSummary[]> {
  return requestJson("/v1/claims", z.array(claimSummarySchema), init);
}

export function createClaim(statement: string, init: RequestInitLike = {}): Promise<ClaimCreated> {
  return post("/v1/claims", claimCreatedSchema, { statement }, init);
}

export function getClaim(id: string, init: RequestInitLike = {}): Promise<ClaimDetail> {
  return requestJson(`/v1/claims/${encodeURIComponent(id)}`, claimDetailSchema, init);
}

export function bindEvidence(
  claimId: string,
  request: EvidenceBind,
  init: RequestInitLike = {},
): Promise<EvidenceCreated> {
  return post(
    `/v1/claims/${encodeURIComponent(claimId)}/evidence`,
    evidenceCreatedSchema,
    request,
    init,
  );
}
