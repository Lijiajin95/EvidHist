/**
 * Pure state transitions for the quote-locate task.
 *
 * A response may only update the state while its request is still the active
 * loading task, so a canceled or superseded request cannot turn the page into a
 * success state. Stryker mutates these rules; the property tests pin them down.
 */

import type { LocateRequest, QuoteLocation } from "./locateContract";

export type LocateFailureReason =
  { kind: "api"; code: string } | { kind: "invalid_response" } | { kind: "network" };

export type LocateTaskState =
  | { status: "idle" }
  | { status: "loading"; request: LocateRequest }
  | { status: "located"; request: LocateRequest; location: QuoteLocation }
  | { status: "failed"; request: LocateRequest; reason: LocateFailureReason };

export class LocateCallError extends Error {
  readonly failure: LocateFailureReason;

  constructor(failure: LocateFailureReason) {
    super(JSON.stringify(failure));
    this.failure = failure;
  }
}

export function beginTask(_state: LocateTaskState, request: LocateRequest): LocateTaskState {
  return { status: "loading", request };
}

export function resolveTask(
  state: LocateTaskState,
  request: LocateRequest,
  location: QuoteLocation,
): LocateTaskState {
  if (state.status !== "loading" || state.request !== request) {
    return state;
  }
  return { status: "located", request, location };
}

export function failTask(
  state: LocateTaskState,
  request: LocateRequest,
  reason: LocateFailureReason,
): LocateTaskState {
  if (state.status !== "loading" || state.request !== request) {
    return state;
  }
  return { status: "failed", request, reason };
}

export function cancelTask(state: LocateTaskState, request: LocateRequest): LocateTaskState {
  if (state.status !== "loading" || state.request !== request) {
    return state;
  }
  return { status: "idle" };
}

/** Classify a caught error and apply it: aborts cancel, API errors fail. */
export function rejectTask(
  state: LocateTaskState,
  request: LocateRequest,
  error: unknown,
): LocateTaskState {
  if (error instanceof DOMException && error.name === "AbortError") {
    return cancelTask(state, request);
  }
  if (error instanceof LocateCallError) {
    return failTask(state, request, error.failure);
  }
  return failTask(state, request, { kind: "network" });
}

export function resetTask(_state: LocateTaskState): LocateTaskState {
  return { status: "idle" };
}
