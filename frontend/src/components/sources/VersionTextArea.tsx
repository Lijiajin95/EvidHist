import { useRef } from "react";
import { utf16IndexFromCodePoint, utf16IndexToCodePoint } from "../../domain/offsets";
import type { TextSelection } from "./SelectedQuotePanel";

interface VersionTextAreaProps {
  content: string;
  onSelection: (selection: TextSelection | null) => void;
}

/**
 * Read-only version text. Selection boundaries arrive as UTF-16 indices and
 * are converted here into Unicode code-point offsets — the unit the API uses.
 */
export function VersionTextArea({ content, onSelection }: VersionTextAreaProps) {
  const areaRef = useRef<HTMLTextAreaElement | null>(null);

  const handleSelect = () => {
    const area = areaRef.current;
    if (area === null) {
      return;
    }
    // Align the quote to whole code points so a selection boundary landing
    // inside a surrogate pair can never emit a lone surrogate to the API.
    const start = utf16IndexToCodePoint(area.value, area.selectionStart);
    const end = utf16IndexToCodePoint(area.value, area.selectionEnd);
    const quote = area.value.slice(
      utf16IndexFromCodePoint(area.value, start),
      utf16IndexFromCodePoint(area.value, end),
    );
    onSelection(quote === "" ? null : { quote, start, end });
  };

  return (
    <textarea
      ref={areaRef}
      data-testid="version-text"
      readOnly
      rows={8}
      value={content}
      onSelect={handleSelect}
    />
  );
}
