import { HttpResponse, http } from "msw";
import {
  VERSION_ID,
  sampleClaimOut,
  sampleClaimSummary,
  sampleEvidenceOut,
  sampleSourceOut,
  sampleSourceSummary,
  sampleVersionOut,
} from "./workbenchFixtures";

/**
 * Workbench handlers. Default handlers answer with empty lists so the App
 * shell renders cleanly; tests override specific endpoints with the factories
 * below to exercise loading, empty, failure and idempotent-retry behavior.
 */

export const emptyWorkbenchHandlers = [
  http.get("/v1/sources", () => HttpResponse.json([])),
  http.get("/v1/claims", () => HttpResponse.json([])),
];

export const sourcesListHandler = http.get("/v1/sources", ({ request }) => {
  const query = new URL(request.url).searchParams.get("q") ?? "";
  const items = query === "" ? [sampleSourceSummary] : [];
  return HttpResponse.json(items);
});

export const networkFailureSourcesHandler = http.get("/v1/sources", () => HttpResponse.error());

export const networkFailureClaimsHandler = http.get("/v1/claims", () => HttpResponse.error());

export const createSourceHandler = http.post("/v1/sources", async ({ request }) => {
  const body = (await request.json()) as { title: string };
  return HttpResponse.json(
    {
      source: { ...sampleSourceOut, title: body.title },
      version: sampleVersionOut,
      created: true,
    },
    { status: 201 },
  );
});

export const createSourceExistingHandler = http.post("/v1/sources", () =>
  HttpResponse.json(
    { source: sampleSourceOut, version: sampleVersionOut, created: false },
    { status: 200 },
  ),
);

export const sourceDetailHandler = (versions = [sampleVersionOut]) =>
  http.get("/v1/sources/:id", () => HttpResponse.json({ source: sampleSourceOut, versions }));

export const sourceNotFoundHandler = http.get("/v1/sources/:id", () =>
  HttpResponse.json({ detail: { code: "source_not_found" } }, { status: 404 }),
);

export const addVersionHandler = http.post("/v1/sources/:id/versions", () =>
  HttpResponse.json(sampleVersionOut, { status: 201 }),
);

export const addVersionExistingHandler = http.post("/v1/sources/:id/versions", () =>
  HttpResponse.json(sampleVersionOut, { status: 200 }),
);

export const versionContentHandler = (content: string) =>
  http.get("/v1/versions/:id", () => HttpResponse.json({ ...sampleVersionOut, content }));

export const versionNotFoundHandler = http.get("/v1/versions/:id", () =>
  HttpResponse.json({ detail: { code: "version_not_found" } }, { status: 404 }),
);

export const locateVersionHandler = http.post("/v1/versions/:id/locate", async ({ request }) => {
  const body = (await request.json()) as { start: number; end: number; exact_quote: string };
  return HttpResponse.json({ version_id: VERSION_ID, ...body });
});

export const locateVersionMismatchHandler = http.post("/v1/versions/:id/locate", () =>
  HttpResponse.json({ detail: { code: "quote_mismatch" } }, { status: 422 }),
);

export const claimsListHandler = http.get("/v1/claims", () =>
  HttpResponse.json([sampleClaimSummary]),
);

export const createClaimHandler = http.post("/v1/claims", async ({ request }) => {
  const body = (await request.json()) as { statement: string };
  return HttpResponse.json(
    { claim: { ...sampleClaimOut, statement: body.statement }, created: true },
    { status: 201 },
  );
});

export const createClaimExistingHandler = http.post("/v1/claims", () =>
  HttpResponse.json({ claim: sampleClaimOut, created: false }, { status: 200 }),
);

export const claimDetailHandler = (evidence = [sampleEvidenceOut]) =>
  http.get("/v1/claims/:id", () => HttpResponse.json({ claim: sampleClaimOut, evidence }));

export const claimNotFoundHandler = http.get("/v1/claims/:id", () =>
  HttpResponse.json({ detail: { code: "claim_not_found" } }, { status: 404 }),
);

export const bindEvidenceHandler = http.post("/v1/claims/:id/evidence", async ({ request }) => {
  const body = (await request.json()) as {
    version_id: string;
    start: number;
    end: number;
    exact_quote: string;
    relation: string;
    note: string;
  };
  return HttpResponse.json(
    {
      evidence: {
        ...sampleEvidenceOut,
        version_id: body.version_id,
        start: body.start,
        end: body.end,
        quote: body.exact_quote,
        relation: body.relation,
        note: body.note,
      },
      created: true,
    },
    { status: 201 },
  );
});

export const bindEvidenceExistingHandler = http.post("/v1/claims/:id/evidence", () =>
  HttpResponse.json({ evidence: sampleEvidenceOut, created: false }, { status: 200 }),
);

export const bindEvidenceInvalidRangeHandler = http.post("/v1/claims/:id/evidence", () =>
  HttpResponse.json({ detail: { code: "invalid_range" } }, { status: 422 }),
);

export const networkFailureBindHandler = http.post("/v1/claims/:id/evidence", () =>
  HttpResponse.error(),
);

export const bindVersionNotFoundHandler = http.post("/v1/claims/:id/evidence", () =>
  HttpResponse.json({ detail: { code: "version_not_found" } }, { status: 404 }),
);
