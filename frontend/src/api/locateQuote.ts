/**
 * Fetch client for POST /v1/quotes/locate with runtime response validation.
 *
 * Domain failures come back as HTTP 422 with {"detail": {"code": ...}}; anything
 * the schema cannot parse is reported as an invalid response, never displayed as
 * a located quote. Abort errors propagate unchanged so the task state machine
 * can treat them as cancellations.
 */

import { LocateCallError } from "../domain/locateTask";
import {
  locateErrorDetailSchema,
  citationSchema,
  type LocateRequest,
  type QuoteLocation,
} from "../domain/locateContract";

export function apiBaseUrl(): string {
  const configured: unknown = import.meta.env.VITE_API_BASE_URL;
  return typeof configured === "string" ? configured : "";
}

export async function locateQuote(
  request: LocateRequest,
  signal?: AbortSignal,
): Promise<QuoteLocation> {
  let response: Response;
  try {
    response = await fetch(`${apiBaseUrl()}/v1/quotes/locate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
      signal: signal ?? null,
    });
  } catch {
    // Interceptor layers do not guarantee a DOMException for aborted requests,
    // so the signal state is the authoritative cancellation signal.
    if (signal?.aborted) {
      throw new DOMException("The locate request was canceled.", "AbortError");
    }
    throw new LocateCallError({ kind: "network" });
  }
  if (!response.ok) {
    throw new LocateCallError(await apiFailure(response));
  }
  const payload: unknown = await response.json();
  const parsed = citationSchema.safeParse(payload);
  if (!parsed.success) {
    throw new LocateCallError({ kind: "invalid_response" });
  }
  return parsed.data;
}

async function apiFailure(response: Response): Promise<LocateCallError["failure"]> {
  try {
    const payload: unknown = await response.json();
    const parsed = locateErrorDetailSchema.safeParse(payload);
    if (parsed.success) {
      return { kind: "api", code: parsed.data.detail.code };
    }
  } catch {
    // fall through to invalid_response below
  }
  return { kind: "invalid_response" };
}
