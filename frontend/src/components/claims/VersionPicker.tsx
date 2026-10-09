import { useId, useState } from "react";
import { getSource, listSources } from "../../api/workbench";
import type { VersionOut } from "../../domain/workbenchContract";
import { useLoad } from "../../hooks/useLoad";

export interface PickedVersion {
  versionId: string;
  versionLabel: string;
}

/** Pick a material, then one of its versions, when binding evidence manually. */
export function VersionPicker({ onChange }: { onChange: (picked: PickedVersion) => void }) {
  const [sourceId, setSourceId] = useState("");
  const pickerId = useId();
  const sourcesState = useLoad(() => listSources(), []);
  const detailState = useLoad(
    () => (sourceId === "" ? Promise.resolve(null) : getSource(sourceId)),
    [sourceId],
  );

  return (
    <>
      <label htmlFor={`${pickerId}-source`}>选择材料</label>
      <select
        id={`${pickerId}-source`}
        value={sourceId}
        onChange={(event) => setSourceId(event.target.value)}
      >
        <option value="">请选择材料</option>
        {sourcesState.status === "ok"
          ? sourcesState.data.map((source) => (
              <option key={source.id} value={source.id}>
                {source.title}
              </option>
            ))
          : null}
      </select>
      {detailState.status === "ok" && detailState.data !== null ? (
        <VersionSelect
          versions={detailState.data.versions}
          onChange={onChange}
          pickerId={pickerId}
        />
      ) : null}
    </>
  );
}

function VersionSelect({
  versions,
  onChange,
  pickerId,
}: {
  versions: VersionOut[];
  onChange: (picked: PickedVersion) => void;
  pickerId: string;
}) {
  return (
    <>
      <label htmlFor={`${pickerId}-version`}>选择版本</label>
      <select
        id={`${pickerId}-version`}
        onChange={(event) => {
          const version = versions.find((item) => item.id === event.target.value);
          if (version !== undefined) {
            onChange({ versionId: version.id, versionLabel: version.label });
          }
        }}
      >
        <option value="">请选择版本</option>
        {versions.map((version) => (
          <option key={version.id} value={version.id}>
            {version.label || "无说明"}
          </option>
        ))}
      </select>
    </>
  );
}
