module.exports = {
  forbidden: [
    { name: "no-runtime-cycles", severity: "error", from: {}, to: { circular: true } },
    {
      name: "domain-does-not-import-ui-or-api",
      severity: "error",
      from: { path: "^src/domain(/|$)" },
      to: { path: "^src/(components|pages|api)(/|$)" },
    },
  ],
  options: {
    tsPreCompilationDeps: false,
    tsConfig: { fileName: "tsconfig.json" },
    doNotFollow: { path: "node_modules" },
    includeOnly: "^src/|^tests/",
  },
};
