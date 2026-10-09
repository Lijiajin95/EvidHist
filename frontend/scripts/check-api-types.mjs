import { execFileSync } from "node:child_process";
import { copyFileSync, mkdtempSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

/**
 * Fail when the generated TypeScript contract types or the copied OpenAPI
 * snapshot drift from the backend's contracts/openapi.json; regeneration must
 * be an explicit, reviewable step. Tests import the sandbox-local copy so the
 * contract suite also runs inside Stryker's sandbox.
 */
const generatedTypes = "src/generated/api-types.ts";
const copiedSnapshot = "src/generated/openapi.json";
const checker = join("node_modules", ".bin", "openapi-typescript");
const temporary = mkdtempSync(join(tmpdir(), "evidhist-api-types-"));

try {
  execFileSync(checker, ["../contracts/openapi.json", "-o", join(temporary, "api-types.ts")], {
    stdio: "pipe",
  });
} catch (error) {
  console.error(`FAIL: openapi-typescript failed: ${error.message}`);
  process.exit(1);
}

let failures = 0;
if (
  readFileSync(generatedTypes, "utf8") !== readFileSync(join(temporary, "api-types.ts"), "utf8")
) {
  console.error(
    `FAIL: ${generatedTypes} is out of date with contracts/openapi.json; ` +
      "run npm run generate:api-types and review compatibility.",
  );
  failures += 1;
}
const snapshot = readFileSync("../contracts/openapi.json", "utf8");
if (readFileSync(copiedSnapshot, "utf8") !== snapshot) {
  copyFileSync("../contracts/openapi.json", copiedSnapshot);
  console.error(
    `FAIL: ${copiedSnapshot} was stale; it has been refreshed from ` +
      "contracts/openapi.json. Rerun the check.",
  );
  failures += 1;
}
if (failures === 0) {
  console.log("Generated API types match the OpenAPI snapshot.");
}
process.exit(failures > 0 ? 1 : 0);
