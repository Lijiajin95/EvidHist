import fc from "fast-check";

const extended = process.env.EVIDHIST_PROPERTY_PROFILE === "extended";

/**
 * Property-run budget per the quality policy: local 100, CI 300, extended 1000.
 * The time-limit plugin fails an interrupted run (fast-check 4.x supports
 * failOnInterrupt), so an interruption is reported as unfinished rather than
 * silently passing with fewer runs; 4000ms leaves headroom below the 5s
 * Vitest test timeout that would otherwise kill the run without a report.
 */
export const propertyParameters = {
  numRuns: extended ? 1000 : process.env.CI ? 300 : 100,
  plugins: [fc.interruptAfterTimeLimit(4000, { failOnInterrupt: true })],
};
