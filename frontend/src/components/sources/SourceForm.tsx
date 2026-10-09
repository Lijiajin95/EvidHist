import { useId, useState, type ChangeEvent } from "react";
import { createSource } from "../../api/workbench";
import { sourceCreateSchema } from "../../domain/workbenchContract";
import { FormFeedback, type FormFeedback as Feedback } from "../Feedback";
import { workbenchFailureMessage } from "../messages";

const EMPTY_VALUES = {
  title: "",
  origin: "",
  usage_terms: "",
  initial_label: "",
  initial_text: "",
};

type Values = typeof EMPTY_VALUES;
type FieldEvent = ChangeEvent<HTMLInputElement | HTMLTextAreaElement>;

/** Add a material with its immutable first text version; .txt import is UTF-8. */
export function SourceForm({ onSaved }: { onSaved: () => void }) {
  const [values, setValues] = useState<Values>(EMPTY_VALUES);
  const [feedback, setFeedback] = useState<Feedback | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const formId = useId();

  const update = (field: keyof Values) => (event: FieldEvent) => {
    setValues((previous) => ({ ...previous, [field]: event.target.value }));
  };

  const importText = (file: File | undefined): void => {
    if (file === undefined) {
      return;
    }
    file
      .text()
      .then((text) => {
        if (text.includes("\uFFFD")) {
          setFeedback({ kind: "error", text: "文件不是有效的 UTF-8 文本，请转换编码后重试。" });
          return;
        }
        setValues((previous) => ({ ...previous, initial_text: text }));
      })
      .catch(() => setFeedback({ kind: "error", text: "无法读取所选文件。" }));
  };

  const handleSubmit = (event: { preventDefault: () => void }): void => {
    event.preventDefault();
    const parsed = sourceCreateSchema.safeParse(values);
    if (!parsed.success) {
      setFeedback({ kind: "error", text: "请填写标题和初始文本；各字段不超过长度上限。" });
      return;
    }
    setSubmitting(true);
    createSource(parsed.data)
      .then((result) => {
        if (result.created) {
          setValues(EMPTY_VALUES);
          setFeedback({ kind: "ok", text: "已保存材料与初始版本。" });
        } else {
          setFeedback({ kind: "ok", text: "同题材料已存在，已返回既有材料与初始版本。" });
        }
        onSaved();
      })
      .catch((error: unknown) =>
        setFeedback({ kind: "error", text: workbenchFailureMessage(error) }),
      )
      .finally(() => setSubmitting(false));
  };

  return (
    <form onSubmit={handleSubmit} aria-label="添加材料">
      {feedback !== null ? <FormFeedback feedback={feedback} testId="source-feedback" /> : null}
      <SourceFormFields values={values} update={update} formId={formId} onImport={importText} />
      <button type="submit" disabled={submitting}>
        保存材料
      </button>
    </form>
  );
}

interface SourceFormFieldsProps {
  values: Values;
  update: (
    field: keyof Values,
  ) => (event: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => void;
  formId: string;
  onImport: (file: File | undefined) => void;
}

function SourceFormFields({ values, update, formId, onImport }: SourceFormFieldsProps) {
  return (
    <>
      <label htmlFor={`${formId}-title`}>标题</label>
      <input
        id={`${formId}-title`}
        value={values.title}
        onChange={update("title")}
        autoComplete="off"
      />
      <label htmlFor={`${formId}-origin`}>来源说明</label>
      <input
        id={`${formId}-origin`}
        value={values.origin}
        onChange={update("origin")}
        autoComplete="off"
      />
      <label htmlFor={`${formId}-terms`}>材料使用条件</label>
      <input
        id={`${formId}-terms`}
        value={values.usage_terms}
        onChange={update("usage_terms")}
        autoComplete="off"
      />
      <label htmlFor={`${formId}-label`}>初始版本说明</label>
      <input
        id={`${formId}-label`}
        value={values.initial_label}
        onChange={update("initial_label")}
        autoComplete="off"
      />
      <label htmlFor={`${formId}-text`}>初始文本</label>
      <textarea
        id={`${formId}-text`}
        rows={6}
        value={values.initial_text}
        onChange={update("initial_text")}
      />
      <label htmlFor={`${formId}-file`}>导入 .txt 文件（UTF-8）</label>
      <input
        id={`${formId}-file`}
        type="file"
        accept=".txt,text/plain"
        onChange={(event) => onImport(event.target.files?.[0])}
      />
    </>
  );
}
