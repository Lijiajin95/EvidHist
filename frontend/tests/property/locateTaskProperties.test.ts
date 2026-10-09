import fc from "fast-check";
import { describe, it } from "vitest";
import type { LocateRequest, QuoteLocation } from "../../src/domain/locateContract";
import {
  beginTask,
  cancelTask,
  failTask,
  resolveTask,
  type LocateTaskState,
} from "../../src/domain/locateTask";
import { propertyParameters } from "./propertyParameters";

const requestArbitrary: fc.Arbitrary<LocateRequest> = fc.record({
  source: fc.record({
    version_id: fc.string({ minLength: 1, maxLength: 8 }),
    text: fc.string({ minLength: 1, maxLength: 20 }),
  }),
  citation: fc.record({
    version_id: fc.string({ minLength: 1, maxLength: 8 }),
    start: fc.nat(),
    end: fc.nat(),
    exact_quote: fc.string({ minLength: 1, maxLength: 5 }),
  }),
});

const locationArbitrary: fc.Arbitrary<QuoteLocation> = fc.record({
  version_id: fc.string({ minLength: 1, maxLength: 8 }),
  start: fc.nat(),
  end: fc.nat(),
  exact_quote: fc.string({ minLength: 1, maxLength: 5 }),
});

describe("locate task state properties", () => {
  it("a response from a superseded or finished request never changes the state", () => {
    fc.assert(
      fc.property(
        requestArbitrary,
        fc.option(requestArbitrary, { nil: undefined }),
        locationArbitrary,
        (current, stale, location) => {
          const state = beginTask({ status: "idle" }, current);
          const incoming = stale ?? current;
          const resolved = resolveTask(state, incoming, location);
          const failed = failTask(state, incoming, { kind: "network" });
          const canceled = cancelTask(state, incoming);
          if (incoming === current) {
            return true;
          }
          return (
            resolved === state &&
            failed === state &&
            canceled === state &&
            resolved.status === "loading"
          );
        },
      ),
      propertyParameters,
    );
  });

  it("canceling a request that is not loading leaves the state untouched", () => {
    fc.assert(
      fc.property(requestArbitrary, (request) => {
        const finished: LocateTaskState = { status: "idle" };
        return cancelTask(finished, request) === finished;
      }),
      propertyParameters,
    );
  });
});
