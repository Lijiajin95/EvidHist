export type View = "sources" | "claims" | "tool";

const viewNames: Record<View, string> = {
  sources: "材料",
  claims: "论断",
  tool: "引文定位工具",
};

const viewOrder: View[] = ["sources", "claims", "tool"];

export function Nav({ view, onChange }: { view: View; onChange: (view: View) => void }) {
  return (
    <nav aria-label="主导航">
      {viewOrder.map((name) => (
        <button
          key={name}
          type="button"
          aria-current={view === name ? "page" : undefined}
          className={view === name ? "active" : undefined}
          onClick={() => onChange(name)}
        >
          {viewNames[name]}
        </button>
      ))}
    </nav>
  );
}
