import { execFileSync } from "node:child_process";
import { copyFileSync, existsSync, mkdtempSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";

/**
 * Fail when the generated TypeScript contract types or the copied OpenAPI
 * snapshot drift from the backend's contracts/openapi.json; regeneration must
 * be an explicit, reviewable step. Tests import the sandbox-local copy so the
 * contract suite also runs inside Stryker's sandbox (whose working directory
 * sits below frontend/), so the contracts file is located by walking up from
 * the working directory instead of assuming one fixed relative path.
 */

const generatedTypes = "src/generated/api-types.ts";
const copiedSnapshot = "src/generated/openapi.json";
const checker = join("node_modules", ".bin", "openapi-typescript");
const temporary = mkdtempSync(join(tmpdir(), "evidhist-api-types-"));

function findContractsPath() {
  let directory = process.cwd();
  for (let depth = 0; depth < 4; depth += 1) {
    const candidate = join(directory, "contracts", "openapi.json");
    if (existsSync(candidate)) {
      return candidate;
    }
    const parent = dirname(directory);
    if (parent === directory) {
      break;
    }
    directory = parent;
  }
  return null;
}

const contractsPath = findContractsPath();
if (contractsPath === null) {
  console.error("FAIL: contracts/openapi.json not found above the working directory.");
  process.exit(1);
}

try {
  execFileSync(checker, [contractsPath, "-o", join(temporary, "api-types.ts")], {
    stdio: "pipe",
  });
} catch (error) {
  console.error(`FAIL: openapi-typescript failed: ${error.message}`);
  process.exit(1);
}

let failures = 0;
// Stryker prepends `// @ts-nocheck` to copied TypeScript files in its sandbox;
// normalize it away so the byte comparison stays meaningful in both contexts.
const normalize = (content) =>
  content
    .split("\n")
    .filter((line) => line.trim() !== "" && line !== "// @ts-nocheck")
    .join("\n");
if (
  normalize(readFileSync(generatedTypes, "utf8")) !==
  normalize(readFileSync(join(temporary, "api-types.ts"), "utf8"))
) {
  console.error(
    `FAIL: ${generatedTypes} is out of date with ${contractsPath}; ` +
      "run npm run generate:api-types and review compatibility.",
  );
  failures += 1;
}
if (readFileSync(copiedSnapshot, "utf8") !== readFileSync(contractsPath, "utf8")) {
  copyFileSync(contractsPath, copiedSnapshot);
  console.error(
    `FAIL: ${copiedSnapshot} was stale; it has been refreshed from ` +
      `${contractsPath}. Rerun the check.`,
  );
  failures += 1;
}
if (failures === 0) {
  console.log("Generated API types match the OpenAPI snapshot.");
}
process.exit(failures > 0 ? 1 : 0);
