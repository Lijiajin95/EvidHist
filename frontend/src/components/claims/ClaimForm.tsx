import { useId, useState } from "react";
import { createClaim } from "../../api/workbench";
import { claimCreateSchema } from "../../domain/workbenchContract";
import { FormFeedback, type FormFeedback as Feedback } from "../Feedback";
import { workbenchFailureMessage } from "../messages";

/** Create a short claim; identical statements return the stored claim. */
export function ClaimForm({ onSaved }: { onSaved: () => void }) {
  const [statement, setStatement] = useState("");
  const [feedback, setFeedback] = useState<Feedback | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const inputId = useId();

  const handleSubmit = (event: { preventDefault: () => void }): void => {
    event.preventDefault();
    const parsed = claimCreateSchema.safeParse({ statement });
    if (!parsed.success) {
      setFeedback({ kind: "error", text: "请填写 1–500 字的论断描述。" });
      return;
    }
    setSubmitting(true);
    createClaim(statement)
      .then(({ created }) => {
        setFeedback({
          kind: "ok",
          text: created ? "已创建论断（默认未核查）。" : "相同论断已存在，已返回既有论断。",
        });
        setStatement("");
        onSaved();
      })
      .catch((error: unknown) =>
        setFeedback({ kind: "error", text: workbenchFailureMessage(error) }),
      )
      .finally(() => setSubmitting(false));
  };

  return (
    <form onSubmit={handleSubmit} aria-label="新建论断">
      {feedback !== null ? <FormFeedback feedback={feedback} testId="claim-feedback" /> : null}
      <label htmlFor={inputId}>论断描述</label>
      <textarea
        id={inputId}
        rows={3}
        value={statement}
        onChange={(event) => setStatement(event.target.value)}
      />
      <button type="submit" disabled={submitting}>
        保存论断
      </button>
    </form>
  );
}
