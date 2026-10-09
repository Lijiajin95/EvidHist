import { HttpResponse, http } from "msw";
import type { LocateRequest } from "../../src/domain/locateContract";

/**
 * Default handler: echo a valid location for the requested citation. Individual
 * tests override these with HttpResponse.error(), delayed responses or invalid
 * payloads to exercise the UI's failure, empty, cancel and stale-response paths.
 */
export const locateQuoteHandler = http.post("/v1/quotes/locate", async ({ request }) => {
  const body = (await request.json()) as LocateRequest;
  return HttpResponse.json(body.citation);
});

export const versionMismatchHandler = http.post("/v1/quotes/locate", () =>
  HttpResponse.json({ detail: { code: "version_mismatch" } }, { status: 422 }),
);

export const invalidResponseHandler = http.post("/v1/quotes/locate", () =>
  HttpResponse.json({ unexpected: "shape" }),
);

export const emptyResultHandler = http.post("/v1/quotes/locate", () =>
  HttpResponse.json({
    version_id: "v1",
    start: 2,
    end: 2,
    exact_quote: "甲",
  }),
);

export const networkFailureHandler = http.post("/v1/quotes/locate", () => HttpResponse.error());

export const unknownCodeHandler = http.post("/v1/quotes/locate", () =>
  HttpResponse.json({ detail: { code: "unforeseen_failure" } }, { status: 422 }),
);

export const nonJsonErrorHandler = http.post("/v1/quotes/locate", () =>
  HttpResponse.text("gateway problem", { status: 422 }),
);

export const delayedSuccessHandler = (delayMs: number) =>
  http.post("/v1/quotes/locate", async () => {
    await new Promise((resolve) => setTimeout(resolve, delayMs));
    return HttpResponse.json({
      version_id: "v1",
      start: 0,
      end: 1,
      exact_quote: "甲",
    });
  });
