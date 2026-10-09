import { useId, useState } from "react";
import { addVersion } from "../../api/workbench";
import { versionCreateSchema } from "../../domain/workbenchContract";
import { FormFeedback, type FormFeedback as Feedback } from "../Feedback";
import { workbenchFailureMessage } from "../messages";

/** Add a new immutable text version; identical content returns the stored one. */
export function VersionForm({ sourceId, onSaved }: { sourceId: string; onSaved: () => void }) {
  const [label, setLabel] = useState("");
  const [text, setText] = useState("");
  const [feedback, setFeedback] = useState<Feedback | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const formId = useId();

  const handleSubmit = (event: { preventDefault: () => void }): void => {
    event.preventDefault();
    const parsed = versionCreateSchema.safeParse({ label, text });
    if (!parsed.success) {
      setFeedback({ kind: "error", text: "请填写文本；版本说明不超过 100 字。" });
      return;
    }
    setSubmitting(true);
    addVersion(sourceId, parsed.data)
      .then(({ created }) => {
        setFeedback({
          kind: "ok",
          text: created ? "已新增版本。" : "相同文本已有版本，已返回该既有版本。",
        });
        setLabel("");
        setText("");
        onSaved();
      })
      .catch((error: unknown) =>
        setFeedback({ kind: "error", text: workbenchFailureMessage(error) }),
      )
      .finally(() => setSubmitting(false));
  };

  return (
    <form onSubmit={handleSubmit} aria-label="新增版本">
      {feedback !== null ? <FormFeedback feedback={feedback} testId="version-feedback" /> : null}
      <VersionFormFields
        label={label}
        text={text}
        onLabel={setLabel}
        onText={setText}
        formId={formId}
      />
      <button type="submit" disabled={submitting}>
        保存版本
      </button>
    </form>
  );
}

function VersionFormFields({
  label,
  text,
  onLabel,
  onText,
  formId,
}: {
  label: string;
  text: string;
  onLabel: (label: string) => void;
  onText: (text: string) => void;
  formId: string;
}) {
  return (
    <>
      <label htmlFor={`${formId}-label`}>版本说明</label>
      <input
        id={`${formId}-label`}
        value={label}
        onChange={(event) => onLabel(event.target.value)}
        autoComplete="off"
      />
      <label htmlFor={`${formId}-text`}>新版本文本</label>
      <textarea
        id={`${formId}-text`}
        rows={6}
        value={text}
        onChange={(event) => onText(event.target.value)}
      />
    </>
  );
}
