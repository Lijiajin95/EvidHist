import { useId, useState } from "react";
import { bindEvidence } from "../../api/workbench";
import type { PendingQuote } from "../../domain/pendingQuote";
import {
  evidenceBindSchema,
  relationValues,
  type EvidenceBind,
} from "../../domain/workbenchContract";
import { FormFeedback, type FormFeedback as Feedback } from "../Feedback";
import { relationLabels, workbenchFailureMessage } from "../messages";
import { VersionPicker, type PickedVersion } from "./VersionPicker";

interface EvidenceBindFormProps {
  claimId: string;
  pendingQuote: PendingQuote | null;
  onQuoteConsumed: () => void;
  onBound: () => void;
}

/** Bind a citation to this claim: selection-prefilled or manually specified. */
export function EvidenceBindForm({
  claimId,
  pendingQuote,
  onQuoteConsumed,
  onBound,
}: EvidenceBindFormProps) {
  const [picked, setPicked] = useState<PickedVersion | null>(null);
  const [manual, setManual] = useState({ start: "", end: "", quote: "" });
  const [relation, setRelation] = useState("");
  const [note, setNote] = useState("");
  const formId = useId();
  const submission = useBindSubmission(
    () => buildBindRequest(pendingQuote, picked, manual, relation, note),
    { claimId, pendingQuote, onQuoteConsumed, onBound },
  );

  return (
    <form onSubmit={submission.submit} aria-label="绑定证据">
      {submission.feedback !== null ? (
        <FormFeedback feedback={submission.feedback} testId="evidence-feedback" />
      ) : null}
      <QuoteSourceSection
        pendingQuote={pendingQuote}
        onPicked={setPicked}
        manual={manual}
        onManual={setManual}
        formId={formId}
      />
      <RelationNoteFields
        relation={relation}
        onRelation={setRelation}
        note={note}
        onNote={setNote}
        formId={formId}
      />
      <button type="submit" disabled={submission.submitting}>
        绑定证据
      </button>
    </form>
  );
}

interface BindContext {
  claimId: string;
  pendingQuote: PendingQuote | null;
  onQuoteConsumed: () => void;
  onBound: () => void;
}

function useBindSubmission(buildRequest: () => EvidenceBind | null, context: BindContext) {
  const [feedback, setFeedback] = useState<Feedback | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const submit = (event: { preventDefault: () => void }): void => {
    event.preventDefault();
    const request = buildRequest();
    if (request === null) {
      setFeedback({ kind: "error", text: "请选择版本、关系，并填写位置与引文。" });
      return;
    }
    setSubmitting(true);
    bindEvidence(context.claimId, request)
      .then(({ created }) => {
        setFeedback({
          kind: "ok",
          text: created ? "已绑定证据。" : "相同证据已存在，已返回既有绑定。",
        });
        if (context.pendingQuote !== null) {
          context.onQuoteConsumed();
        }
        context.onBound();
      })
      .catch((error: unknown) =>
        setFeedback({ kind: "error", text: workbenchFailureMessage(error) }),
      )
      .finally(() => setSubmitting(false));
  };

  return { feedback, submitting, submit };
}

function buildBindRequest(
  pendingQuote: PendingQuote | null,
  picked: PickedVersion | null,
  manual: { start: string; end: string; quote: string },
  relation: string,
  note: string,
): EvidenceBind | null {
  const versionId = pendingQuote?.versionId ?? picked?.versionId;
  if (versionId === undefined) {
    return null;
  }
  const parsed = evidenceBindSchema.safeParse({
    version_id: versionId,
    start: pendingQuote === null ? Number(manual.start) : pendingQuote.start,
    end: pendingQuote === null ? Number(manual.end) : pendingQuote.end,
    relation,
    note,
    exact_quote: pendingQuote === null ? manual.quote : pendingQuote.quote,
  });
  return parsed.success ? parsed.data : null;
}

function RelationNoteFields({
  relation,
  onRelation,
  note,
  onNote,
  formId,
}: {
  relation: string;
  onRelation: (relation: string) => void;
  note: string;
  onNote: (note: string) => void;
  formId: string;
}) {
  return (
    <>
      <label htmlFor={`${formId}-relation`}>关系</label>
      <select
        id={`${formId}-relation`}
        value={relation}
        onChange={(event) => onRelation(event.target.value)}
      >
        <option value="">请选择关系</option>
        {relationValues.map((value) => (
          <option key={value} value={value}>
            {relationLabels[value]}
          </option>
        ))}
      </select>
      <label htmlFor={`${formId}-note`}>说明</label>
      <textarea
        id={`${formId}-note`}
        rows={2}
        value={note}
        onChange={(event) => onNote(event.target.value)}
      />
    </>
  );
}

interface QuoteSourceSectionProps {
  pendingQuote: PendingQuote | null;
  onPicked: (picked: PickedVersion) => void;
  manual: { start: string; end: string; quote: string };
  onManual: (manual: { start: string; end: string; quote: string }) => void;
  formId: string;
}

function QuoteSourceSection({
  pendingQuote,
  onPicked,
  manual,
  onManual,
  formId,
}: QuoteSourceSectionProps) {
  if (pendingQuote !== null) {
    return (
      <p data-testid="prefilled-quote">
        使用选中引文：版本「{pendingQuote.versionLabel || "无说明"}」，区间 [{pendingQuote.start},{" "}
        {pendingQuote.end})。
      </p>
    );
  }
  return (
    <>
      <VersionPicker onChange={onPicked} />
      <label htmlFor={`${formId}-start`}>起点（Unicode 码点，含）</label>
      <input
        id={`${formId}-start`}
        inputMode="numeric"
        value={manual.start}
        onChange={(event) => onManual({ ...manual, start: event.target.value })}
        autoComplete="off"
      />
      <label htmlFor={`${formId}-end`}>终点（Unicode 码点，不含）</label>
      <input
        id={`${formId}-end`}
        inputMode="numeric"
        value={manual.end}
        onChange={(event) => onManual({ ...manual, end: event.target.value })}
        autoComplete="off"
      />
      <label htmlFor={`${formId}-quote`}>引文</label>
      <textarea
        id={`${formId}-quote`}
        rows={2}
        value={manual.quote}
        onChange={(event) => onManual({ ...manual, quote: event.target.value })}
      />
    </>
  );
}
