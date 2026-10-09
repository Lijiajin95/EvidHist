import { afterEach, describe, expect, it, vi } from "vitest";
import { apiBaseUrl, locateQuote } from "../../src/api/locateQuote";
import { locateRequestSchema, type LocateRequest } from "../../src/domain/locateContract";

const request: LocateRequest = locateRequestSchema.parse({
  source: { version_id: "v1", text: "甲" },
  citation: { version_id: "v1", start: 0, end: 1, exact_quote: "甲" },
});

afterEach(() => {
  vi.unstubAllEnvs();
});

describe("locateQuote client", () => {
  it("uses the configured API base URL when provided", () => {
    vi.stubEnv("VITE_API_BASE_URL", "https://api.example.test");

    expect(apiBaseUrl()).toBe("https://api.example.test");
  });
  it("validates a successful response against the runtime schema", async () => {
    const location = await locateQuote(request);

    expect(location).toEqual({ version_id: "v1", start: 0, end: 1, exact_quote: "甲" });
  });

  it("propagates abort errors so cancellations stay cancellations", async () => {
    const controller = new AbortController();
    controller.abort();

    await expect(locateQuote(request, controller.signal)).rejects.toSatisfy(
      (error: unknown) => error instanceof DOMException && error.name === "AbortError",
    );
  });
});
