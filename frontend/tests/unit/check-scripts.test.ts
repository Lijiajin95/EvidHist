import { execFileSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterAll, describe, expect, it } from "vitest";

const workdir = mkdtempSync(join(tmpdir(), "evidhist-check-scripts-"));

function runScript(script: string, args: string[]): { status: number; output: string } {
  try {
    const stdout = execFileSync(process.execPath, [script, ...args], {
      cwd: process.cwd(),
      encoding: "utf8",
      stdio: ["ignore", "pipe", "pipe"],
    });
    return { status: 0, output: stdout };
  } catch (error) {
    const failure = error as { status?: number; stdout?: string; stderr?: string };
    return {
      status: failure.status ?? 1,
      output: `${failure.stdout ?? ""}${failure.stderr ?? ""}`,
    };
  }
}

afterAll(() => {
  rmSync(workdir, { recursive: true, force: true });
});

describe("Stryker raw-state gate", () => {
  it("passes on a fully killed non-empty report", () => {
    const report = join(workdir, "clean.json");
    writeFileSync(
      report,
      JSON.stringify({ files: { "src/domain/a.ts": { mutants: [{ status: "Killed" }] } } }),
    );

    const result = runScript("scripts/check-stryker-stats.mjs", [report]);

    expect(result.status).toBe(0);
    expect(result.output).toContain("total 1, killed 1");
  });

  it("fails on survivors, no-coverage, timeouts, compile errors and empty reports", () => {
    for (const status of ["Survived", "NoCoverage", "Timeout", "CompileError"]) {
      const report = join(workdir, `${status}.json`);
      writeFileSync(
        report,
        JSON.stringify({ files: { "a.ts": { mutants: [{ status }, { status: "Killed" }] } } }),
      );
      const result = runScript("scripts/check-stryker-stats.mjs", [report]);
      expect(result.status, status).toBe(1);
      expect(result.output).toContain(status);
    }

    const empty = join(workdir, "empty.json");
    writeFileSync(empty, JSON.stringify({ files: {} }));
    expect(runScript("scripts/check-stryker-stats.mjs", [empty]).status).toBe(1);
  });

  it("fails when the report file is missing or malformed", () => {
    expect(
      runScript("scripts/check-stryker-stats.mjs", [join(workdir, "absent.json")]).status,
    ).toBe(1);

    const malformed = join(workdir, "broken.json");
    writeFileSync(malformed, "{oops", "utf8");
    expect(runScript("scripts/check-stryker-stats.mjs", [malformed]).status).toBe(1);
  });
});

describe("generated API types drift gate", () => {
  it("passes while the generated files match the OpenAPI snapshot", () => {
    const result = runScript("scripts/check-api-types.mjs", []);

    expect(result.status).toBe(0);
    expect(result.output).toContain("match the OpenAPI snapshot");
  });

  it("fails when the copied snapshot drifts from contracts/openapi.json", () => {
    const drifted = "src/generated/openapi.json";
    const original = readFileSync(drifted, "utf8");
    try {
      writeFileSync(drifted, original.replace('"0.0.1"', '"0.0.2"'), "utf8");
      const result = runScript("scripts/check-api-types.mjs", []);
      expect(result.status).toBe(1);
      expect(result.output).toContain("stale");
    } finally {
      writeFileSync(drifted, original, "utf8");
    }
  });
});
