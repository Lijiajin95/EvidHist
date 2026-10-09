import { describe, expect, it } from "vitest";
import type { LocateRequest } from "../../src/domain/locateContract";
import {
  beginTask,
  LocateCallError,
  cancelTask,
  rejectTask,
  resolveTask,
} from "../../src/domain/locateTask";

const request: LocateRequest = {
  source: { version_id: "v1", text: "甲乙" },
  citation: { version_id: "v1", start: 0, end: 1, exact_quote: "甲" },
};

const other: LocateRequest = {
  source: { version_id: "v2", text: "丙" },
  citation: { version_id: "v2", start: 0, end: 1, exact_quote: "丙" },
};

const location = { version_id: "v1", start: 0, end: 1, exact_quote: "甲" };

const loading = beginTask({ status: "idle" }, request);

describe("resolveTask transitions", () => {
  it("marks the task located with the resolved citation", () => {
    expect(resolveTask(loading, request, location)).toEqual({
      status: "located",
      request,
      location,
    });
  });

  it("a late success response cannot overwrite a finished task", () => {
    const failed = rejectTask(loading, request, new TypeError("socket"));
    expect(resolveTask(failed, request, location)).toBe(failed);
    expect(resolveTask(resolveTask(loading, request, location), request, location)).toEqual({
      status: "located",
      request,
      location,
    });
  });
});

describe("rejectTask classification", () => {
  it("cancels the task when the fetch was aborted", () => {
    const abort = new DOMException("Aborted", "AbortError");
    expect(rejectTask(loading, request, abort)).toEqual({ status: "idle" });
  });

  it("treats a non-abort DOMException as a network failure, not a cancellation", () => {
    const strange = new DOMException("malformed payload", "SyntaxError");
    expect(rejectTask(loading, request, strange)).toEqual({
      status: "failed",
      request,
      reason: { kind: "network" },
    });
  });

  it("fails with the API failure carried by the call error", () => {
    const error = new LocateCallError({ kind: "api", code: "version_mismatch" });
    expect(rejectTask(loading, request, error)).toEqual({
      status: "failed",
      request,
      reason: { kind: "api", code: "version_mismatch" },
    });
  });

  it("fails with a network reason for unexpected errors", () => {
    expect(rejectTask(loading, request, new TypeError("socket"))).toEqual({
      status: "failed",
      request,
      reason: { kind: "network" },
    });
  });

  it("ignores errors that belong to another request or a finished task", () => {
    expect(rejectTask(loading, other, new LocateCallError({ kind: "network" }))).toBe(loading);
    const located = resolveTask(loading, request, location);
    expect(rejectTask(located, request, new TypeError("late"))).toBe(located);
    expect(cancelTask(located, request)).toBe(located);
  });
});
