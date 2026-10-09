/**
 * Fetch client for POST /v1/quotes/locate with runtime response validation.
 *
 * Domain failures come back as HTTP 422 with {"detail": {"code": ...}}; anything
 * the schema cannot parse is reported as an invalid response, never displayed as
 * a located quote. Abort errors propagate unchanged so the task state machine
 * can treat them as cancellations. The shared mechanics live in ./client.
 */

import { requestJson } from "./client";
import { citationSchema, type LocateRequest, type QuoteLocation } from "../domain/locateContract";

export { apiBaseUrl } from "./client";

export async function locateQuote(
  request: LocateRequest,
  signal?: AbortSignal,
): Promise<QuoteLocation> {
  return requestJson("/v1/quotes/locate", citationSchema, {
    method: "POST",
    body: request,
    ...(signal === undefined ? {} : { signal }),
  });
}
