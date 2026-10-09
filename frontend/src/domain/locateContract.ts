/**
 * Runtime contract for POST /v1/quotes/locate, mirroring contracts/openapi.json.
 *
 * The generated TypeScript types cover compile-time compatibility; these Zod
 * schemas validate runtime responses. A contract test keeps the two in sync so
 * the frontend and the API snapshot cannot drift apart silently.
 */

import { z } from "zod";

/**
 * Stable error codes across the API: the citation domain rejects with
 * version_mismatch / invalid_range / quote_mismatch (422), the workbench adds
 * source_not_found / version_not_found / claim_not_found (404). Codes that the
 * backend has not documented must surface as an invalid response, never as a
 * silent success.
 */
export const failureCodes = [
  "version_mismatch",
  "invalid_range",
  "quote_mismatch",
  "source_not_found",
  "version_not_found",
  "claim_not_found",
] as const;

export const textVersionSchema = z.object({
  version_id: z.string().min(1).max(128),
  text: z.string().min(1),
});

export const citationSchema = z.object({
  version_id: z.string().min(1).max(128),
  start: z.number().int().min(0),
  end: z.number().int().min(0),
  exact_quote: z.string().min(1),
});

export const locateRequestSchema = z.object({
  source: textVersionSchema,
  citation: citationSchema,
});

export const locateErrorDetailSchema = z.object({
  detail: z.object({ code: z.enum(failureCodes) }),
});

export type QuoteLocation = z.infer<typeof citationSchema>;
export type LocateRequest = z.infer<typeof locateRequestSchema>;
