import { useId, useState, type ChangeEvent, type FormEvent } from "react";
import { locateRequestSchema, type LocateRequest } from "../domain/locateContract";

export interface FormValues {
  text_version: string;
  citation_version: string;
  text: string;
  start: string;
  end: string;
  exact_quote: string;
}

interface FieldDefinition {
  key: keyof FormValues;
  label: string;
  multiline?: boolean;
}

const FIELDS: FieldDefinition[] = [
  { key: "text_version", label: "文本版本编号" },
  { key: "citation_version", label: "引文版本编号" },
  { key: "text", label: "文本（本界面只校验此文本）", multiline: true },
  { key: "start", label: "起点（Unicode 码点，含）" },
  { key: "end", label: "终点（Unicode 码点，不含）" },
  { key: "exact_quote", label: "引文" },
];

interface FormFieldProps {
  id: string;
  label: string;
  value: string;
  multiline: boolean;
  onChange: (event: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => void;
}

function FormField({ id, label, value, multiline, onChange }: FormFieldProps) {
  return (
    <div>
      <label htmlFor={id}>{label}</label>
      {multiline ? (
        <textarea id={id} rows={5} value={value} onChange={onChange} />
      ) : (
        <input id={id} value={value} onChange={onChange} autoComplete="off" />
      )}
    </div>
  );
}

interface LocateFormProps {
  onSubmit: (request: LocateRequest) => void;
  onCancel: () => void;
  loading: boolean;
}

/** Input form for the explicit-text citation location check. */
export function LocateForm({ onSubmit, onCancel, loading }: LocateFormProps) {
  const [values, setValues] = useState<FormValues>({
    text_version: "",
    citation_version: "",
    text: "",
    start: "",
    end: "",
    exact_quote: "",
  });
  const [formError, setFormError] = useState<string | null>(null);
  const formId = useId();

  const update =
    (field: keyof FormValues) => (event: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
      setValues((previous) => ({ ...previous, [field]: event.target.value }));
    };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const parsed = locateRequestSchema.safeParse(toRequest(values));
    if (!parsed.success) {
      setFormError("请完整填写版本号、原文、非负整数起止位置和引文。");
      return;
    }
    setFormError(null);
    onSubmit(parsed.data);
  };

  return (
    <form onSubmit={handleSubmit} aria-labelledby={`${formId}-heading`}>
      <h2 id={`${formId}-heading`}>引用定位</h2>
      {formError ? <p role="alert">{formError}</p> : null}
      {FIELDS.map((field) => (
        <FormField
          key={field.key}
          id={`${formId}-${field.key}`}
          label={field.label}
          value={values[field.key]}
          multiline={field.multiline === true}
          onChange={update(field.key)}
        />
      ))}
      <button type="submit" disabled={loading}>
        校验位置
      </button>
      {loading ? (
        <button type="button" onClick={onCancel}>
          取消
        </button>
      ) : null}
    </form>
  );
}

function toRequest(values: FormValues): LocateRequest {
  return {
    source: { version_id: values.text_version.trim(), text: values.text },
    citation: {
      version_id: values.citation_version.trim(),
      start: Number(values.start),
      end: Number(values.end),
      exact_quote: values.exact_quote,
    },
  };
}
