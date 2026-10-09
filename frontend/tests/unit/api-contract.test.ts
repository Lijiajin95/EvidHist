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

describe("frontend schemas track the OpenAPI snapshot", () => {
  it("exposes the same fields as the TextVersion, Citation and QuoteLocation components", () => {
    expect(propertyKeys(textVersionSchema).sort()).toEqual(
      Object.keys(schemas["TextVersion"]?.properties ?? {}).sort(),
    );
    expect(propertyKeys(citationSchema).sort()).toEqual(
      Object.keys(schemas["Citation"]?.properties ?? {}).sort(),
    );
    expect(propertyKeys(citationSchema).sort()).toEqual(
      Object.keys(schemas["QuoteLocation"]?.properties ?? {}).sort(),
    );
    expect(propertyKeys(citationSchema).sort()).toEqual(
      [...(schemas["Citation"]?.required ?? [])].sort(),
    );
    expect(propertyKeys(citationSchema).sort()).toEqual(
      [...(schemas["QuoteLocation"]?.required ?? [])].sort(),
    );
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
});
