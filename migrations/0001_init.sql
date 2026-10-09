-- Initial EvidHist business schema: sources, immutable text versions, claims, evidence.
CREATE TABLE sources (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    title text NOT NULL,
    origin text NOT NULL DEFAULT '',
    usage_terms text NOT NULL DEFAULT '',
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE text_versions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id uuid NOT NULL REFERENCES sources(id),
    label text NOT NULL DEFAULT '',
    content text NOT NULL,
    content_sha256 text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT text_versions_source_content_unique UNIQUE (source_id, content_sha256)
);

CREATE TABLE claims (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    statement text NOT NULL,
    review_status text NOT NULL DEFAULT 'unverified',
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT claims_statement_unique UNIQUE (statement)
);

CREATE TABLE evidence (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_id uuid NOT NULL REFERENCES claims(id),
    version_id uuid NOT NULL REFERENCES text_versions(id),
    start integer NOT NULL CHECK (start >= 0),
    "end" integer NOT NULL CHECK ("end" > start),
    relation text NOT NULL
        CHECK (relation IN ('supports', 'contradicts', 'mentions', 'insufficient')),
    note text NOT NULL DEFAULT '',
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT evidence_natural_key_unique
        UNIQUE (claim_id, version_id, start, "end", relation, note)
);

CREATE INDEX idx_text_versions_source ON text_versions(source_id);
CREATE INDEX idx_evidence_claim ON evidence(claim_id);
CREATE INDEX idx_evidence_version ON evidence(version_id);
