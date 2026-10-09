import type { VersionOut } from "../../domain/workbenchContract";

interface VersionListProps {
  versions: VersionOut[];
  openVersionId: string | null;
  onOpen: (id: string) => void;
}

/** Immutable version rows: label, short content hash and creation time. */
export function VersionList({ versions, openVersionId, onOpen }: VersionListProps) {
  if (versions.length === 0) {
    return <p>该材料还没有文本版本。</p>;
  }
  return (
    <ul data-testid="version-list">
      {versions.map((version) => (
        <li key={version.id}>
          <button
            type="button"
            aria-current={openVersionId === version.id ? "true" : undefined}
            onClick={() => onOpen(version.id)}
          >
            {version.label || "（无说明）"}
          </button>
          <span>
            {" "}
            散列 {version.content_sha256.slice(0, 12)} · {version.created_at}
          </span>
        </li>
      ))}
    </ul>
  );
}
