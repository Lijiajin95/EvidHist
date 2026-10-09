/**
 * Shared fetch client: JSON requests with runtime Zod validation and a stable
 * error classification. Non-OK responses are parsed as {"detail": {"code"}};
 * unknown codes or unparseable bodies surface as an invalid response, never as
 * a silent success. Interceptor layers do not guarantee a DOMException for
 * aborted requests, so the signal state is the authoritative cancellation
 * signal (see src/api/locateQuote.ts for the original pattern).
 */

import type { ZodType } from "zod";
import { LocateCallError } from "../domain/locateTask";
import { locateErrorDetailSchema } from "../domain/locateContract";

export function apiBaseUrl(): string {
  const configured: unknown = import.meta.env.VITE_API_BASE_URL;
  return typeof configured === "string" ? configured : "";
}

export interface RequestInitLike {
  method?: "GET" | "POST";
  body?: unknown;
  signal?: AbortSignal;
}

export async function requestJson<T>(
  path: string,
  schema: ZodType<T>,
  init: RequestInitLike = {},
): Promise<T> {
  return (await requestJsonWithStatus(path, schema, init)).data;
}

/** Same as requestJson, but surfaces the HTTP status for 200-vs-201 semantics. */
export async function requestJsonWithStatus<T>(
  path: string,
  schema: ZodType<T>,
  init: RequestInitLike = {},
): Promise<{ data: T; status: number }> {
  let response: Response;
  const request: RequestInit = {
    method: init.method ?? "GET",
    signal: init.signal ?? null,
  };
  if (init.body !== undefined) {
    request.headers = { "Content-Type": "application/json" };
    request.body = JSON.stringify(init.body);
  }
  try {
    response = await fetch(`${apiBaseUrl()}${path}`, request);
  } catch {
    if (init.signal?.aborted) {
      throw new DOMException("The request was canceled.", "AbortError");
    }
    throw new LocateCallError({ kind: "network" });
  }
  if (!response.ok) {
    throw new LocateCallError(await failureFrom(response));
  }
  const payload: unknown = await response.json();
  const parsed = schema.safeParse(payload);
  if (!parsed.success) {
    throw new LocateCallError({ kind: "invalid_response" });
  }
  return { data: parsed.data, status: response.status };
}

async function failureFrom(response: Response): Promise<LocateCallError["failure"]> {
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
