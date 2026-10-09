import { z } from "zod";
import { describe, expect, it } from "vitest";
import openapiSnapshot from "../../src/generated/openapi.json";
import {
  citationSchema,
  failureCodes,
  locateErrorDetailSchema,
  locateRequestSchema,
  textVersionSchema,
} from "../../src/domain/locateContract";
import {
  claimCreateSchema,
  locateVersionSchema,
  quoteLocationOutSchema,
  claimCreatedSchema,
  claimDetailSchema,
  claimOutSchema,
  claimSummarySchema,
  evidenceBindSchema,
  evidenceOutSchema,
  relationValues,
  sourceCreateSchema,
  sourceDetailSchema,
  sourceOutSchema,
  sourceSummarySchema,
  sourceWithVersionSchema,
  versionContentSchema,
  versionCreateSchema,
  versionOutSchema,
} from "../../src/domain/workbenchContract";

function propertyKeys(schema: z.ZodType): string[] {
  const jsonSchema = z.toJSONSchema(schema) as { properties?: Record<string, unknown> };
  return Object.keys(jsonSchema.properties ?? {});
}

/**
 * Real API contract case: the copied OpenAPI snapshot (drift-checked against
 * contracts/openapi.json by npm run check:api-types) and the frontend's runtime
 * Zod schemas must describe the same request and response shapes, so MSW-based
 * tests and the live service cannot drift apart silently.
 */

const openapi = openapiSnapshot as {
  components: {
    schemas: Record<string, { required?: string[]; properties: Record<string, unknown> }>;
  };
  paths: Record<
    string,
    Record<string, { requestBody?: unknown; responses?: Record<string, unknown> }>
  >;
};

const schemas = openapi.components.schemas;

function expectSameFields(schema: z.ZodType, openapiName: string): void {
  expect(propertyKeys(schema).sort()).toEqual(
    Object.keys(schemas[openapiName]?.properties ?? {}).sort(),
  );
  expect(propertyKeys(schema).sort()).toEqual([...(schemas[openapiName]?.required ?? [])].sort());
}

describe("frontend schemas track the OpenAPI snapshot", () => {
  it("exposes the same fields as the TextVersion, Citation and QuoteLocation components", () => {
    expect(propertyKeys(textVersionSchema).sort()).toEqual(
      Object.keys(schemas["TextVersion"]?.properties ?? {}).sort(),
    );
    expect(propertyKeys(citationSchema).sort()).toEqual(
      Object.keys(schemas["Citation"]?.properties ?? {}).sort(),
    );
    expect(propertyKeys(citationSchema).sort()).toEqual(
      [...(schemas["Citation"]?.required ?? [])].sort(),
    );
  });

  it("exposes the same fields for every workbench request and response schema", () => {
    expectSameFields(sourceCreateSchema, "SourceCreateRequest");
    expectSameFields(sourceOutSchema, "SourceOut");
    expectSameFields(sourceSummarySchema, "SourceSummaryOut");
    expectSameFields(sourceDetailSchema, "SourceDetailOut");
    expectSameFields(sourceWithVersionSchema, "SourceWithVersionOut");
    expectSameFields(versionCreateSchema, "VersionCreateRequest");
    expectSameFields(versionOutSchema, "VersionOut");
    expectSameFields(versionContentSchema, "VersionContentOut");
    expectSameFields(claimCreateSchema, "ClaimCreateRequest");
    expectSameFields(claimOutSchema, "ClaimOut");
    expectSameFields(claimSummarySchema, "ClaimSummaryOut");
    expectSameFields(claimCreatedSchema, "ClaimCreatedOut");
    expectSameFields(claimDetailSchema, "ClaimDetailOut");
    expectSameFields(evidenceBindSchema, "EvidenceBindRequest");
    expectSameFields(evidenceOutSchema, "EvidenceOut");
  });

  it("keeps the documented relation enum", () => {
    const relation = schemas["EvidenceBindRequest"]?.properties["relation"] as { enum?: string[] };
    expect([...(relation.enum ?? [])].sort()).toEqual([...relationValues].sort());
  });

  it("wraps the same request body as the locate operation", () => {
    const locate = openapi.paths["/v1/quotes/locate"]?.["post"];
    const requestBody = locate?.requestBody as {
      content: { "application/json": { schema: { $ref: string } } };
    };
    expect(requestBody.content["application/json"].schema.$ref).toBe(
      "#/components/schemas/LocateQuoteRequest",
    );
    expect(propertyKeys(locateRequestSchema).sort()).toEqual(
      Object.keys(schemas["LocateQuoteRequest"]?.properties ?? {}).sort(),
    );
    expect(propertyKeys(locateRequestSchema).sort()).toEqual(
      [...(schemas["LocateQuoteRequest"]?.required ?? [])].sort(),
    );
  });

  it("accepts exactly the documented failure codes", () => {
    const locate = openapi.paths["/v1/quotes/locate"]?.["post"];
    expect(Object.keys(locate?.responses ?? {})).toContain("422");
    for (const code of failureCodes) {
      expect(locateErrorDetailSchema.safeParse({ detail: { code } }).success).toBe(true);
    }
    expect(locateErrorDetailSchema.safeParse({ detail: { code: "not_a_code" } }).success).toBe(
      false,
    );
  });

  it("enforces the documented field constraints, not just the field names", () => {
    const validCitation = {
      version_id: "史記-001",
      start: 0,
      end: 2,
      exact_quote: "甲乙",
    };
    expect(citationSchema.safeParse(validCitation).success).toBe(true);
    expect(
      citationSchema.safeParse({ ...validCitation, version_id: "v".repeat(129) }).success,
    ).toBe(false);
    expect(citationSchema.safeParse({ ...validCitation, start: -1 }).success).toBe(false);
    expect(citationSchema.safeParse({ ...validCitation, start: 1.5 }).success).toBe(false);
    expect(citationSchema.safeParse({ ...validCitation, exact_quote: "" }).success).toBe(false);
    expect(textVersionSchema.safeParse({ version_id: "v".repeat(129), text: "甲" }).success).toBe(
      false,
    );
  });

  it("enforces the workbench field constraints", () => {
    const validSource = {
      title: "史記",
      origin: "",
      usage_terms: "",
      initial_text: "甲",
      initial_label: "",
    };
    expect(sourceCreateSchema.safeParse(validSource).success).toBe(true);
    expect(sourceCreateSchema.safeParse({ ...validSource, title: "史".repeat(201) }).success).toBe(
      false,
    );
    expect(sourceCreateSchema.safeParse({ ...validSource, initial_text: "" }).success).toBe(false);
    expect(sourceCreateSchema.safeParse({ ...validSource, origin: "来".repeat(501) }).success).toBe(
      false,
    );
    expect(
      sourceCreateSchema.safeParse({ ...validSource, initial_label: "稿".repeat(101) }).success,
    ).toBe(false);

    const validClaim = { statement: "秦並天下。" };
    expect(claimCreateSchema.safeParse(validClaim).success).toBe(true);
    expect(claimCreateSchema.safeParse({ statement: "字".repeat(501) }).success).toBe(false);
    expect(claimCreateSchema.safeParse({ statement: "" }).success).toBe(false);

    const validVersion = { label: "", text: "甲" };
    expect(versionCreateSchema.safeParse(validVersion).success).toBe(true);
    expect(versionCreateSchema.safeParse({ label: "稿".repeat(101), text: "甲" }).success).toBe(
      false,
    );
    expect(versionCreateSchema.safeParse({ label: "", text: "" }).success).toBe(false);
  });

  it("enforces the version-locate and location constraints", () => {
    const validLocate = { start: 5, end: 7, exact_quote: "甲乙" };
    expect(locateVersionSchema.safeParse(validLocate).success).toBe(true);
    expect(locateVersionSchema.safeParse({ ...validLocate, start: -1 }).success).toBe(false);
    expect(locateVersionSchema.safeParse({ ...validLocate, start: 1.5 }).success).toBe(false);
    expect(locateVersionSchema.safeParse({ ...validLocate, exact_quote: "" }).success).toBe(false);

    const validLocation = {
      version_id: "123e4567-e89b-12d3-a456-426614174000",
      start: 0,
      end: 2,
      exact_quote: "甲乙",
    };
    expect(quoteLocationOutSchema.safeParse(validLocation).success).toBe(true);
    expect(quoteLocationOutSchema.safeParse({ ...validLocation, exact_quote: "" }).success).toBe(
      false,
    );
    expect(quoteLocationOutSchema.safeParse({ ...validLocation, version_id: "nope" }).success).toBe(
      false,
    );
    expect(quoteLocationOutSchema.safeParse({ ...validLocation, end: -1 }).success).toBe(false);
  });

  it("enforces the evidence-bind constraints", () => {
    const validEvidence = {
      version_id: "123e4567-e89b-12d3-a456-426614174000",
      start: 0,
      end: 2,
      relation: "supports",
      note: "",
      exact_quote: "甲乙",
    };
    expect(evidenceBindSchema.safeParse(validEvidence).success).toBe(true);
    expect(evidenceBindSchema.safeParse({ ...validEvidence, relation: "unrelated" }).success).toBe(
      false,
    );
    expect(evidenceBindSchema.safeParse({ ...validEvidence, note: "字".repeat(501) }).success).toBe(
      false,
    );
    expect(evidenceBindSchema.safeParse({ ...validEvidence, exact_quote: "" }).success).toBe(false);
  });

  it("validates id formats and ISO timestamps in responses", () => {
    const uuid = "123e4567-e89b-12d3-a456-426614174000";
    const base = {
      id: uuid,
      title: "史記",
      origin: "",
      usage_terms: "",
      created_at: "2026-10-10T08:00:00+08:00",
      updated_at: "2026-10-10T08:00:00+08:00",
    };
    expect(sourceOutSchema.safeParse(base).success).toBe(true);
    expect(sourceOutSchema.safeParse({ ...base, id: "not-a-uuid" }).success).toBe(false);
    expect(sourceOutSchema.safeParse({ ...base, created_at: "2026-10-10 08:00" }).success).toBe(
      false,
    );
  });
});
