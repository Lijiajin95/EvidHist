import { readFileSync } from "node:fs";

/**
 * Gate on Stryker's raw mutant states for the critical domain scope: no
 * unexplained survivors, no untested mutants, no timeouts and no compile errors.
 * A missing or malformed report is a failed check, never a pass.
 */
const reportPath = process.argv[2] ?? "reports/mutation/mutation.json";

let report;
try {
  report = JSON.parse(readFileSync(reportPath, "utf8"));
} catch (error) {
  console.error(`FAIL: cannot read Stryker report ${reportPath}: ${error.message}`);
  process.exit(1);
}

const files = report.files ?? {};
const mutants = Object.entries(files).flatMap(([file, data]) =>
  data.mutants.map((mutant) => ({ file, ...mutant })),
);

const byStatus = {};
for (const mutant of mutants) {
  byStatus[mutant.status] = (byStatus[mutant.status] ?? 0) + 1;
}

const failures = [];
if (mutants.length === 0) {
  failures.push("report contains no mutants; the mutation scope is empty");
}
for (const status of ["Survived", "NoCoverage", "Timeout", "CompileError"]) {
  const count = byStatus[status] ?? 0;
  if (count > 0) {
    const details = mutants
      .filter((mutant) => mutant.status === status)
      .map((mutant) => `${mutant.file}:${mutant.location?.start?.line} ${mutant.mutatorName}`)
      .join("; ");
    failures.push(`${count} mutant(s) in state ${status}: ${details}`);
  }
}

for (const failure of failures) {
  console.error(`FAIL: ${failure}`);
}
const killed = byStatus["Killed"] ?? 0;
console.log(
  `Stryker raw states: total ${mutants.length}, killed ${killed}, ` +
    `survived ${byStatus["Survived"] ?? 0}, noCoverage ${byStatus["NoCoverage"] ?? 0}, ` +
    `timeout ${byStatus["Timeout"] ?? 0}, compileError ${byStatus["CompileError"] ?? 0}, ` +
    `ignored ${byStatus["Ignored"] ?? 0}.`,
);
process.exit(failures.length > 0 ? 1 : 0);
