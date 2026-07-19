import { useMemo, useState } from "react";
import { NODE_PALETTE } from "./palette";

type Props = {
  onAdd: (type: string, name: string, defaults?: Record<string, unknown>) => void;
};

export function NodePalette({ onAdd }: Props) {
  const [query, setQuery] = useState("");
  const grouped = useMemo(() => {
    const filtered = NODE_PALETTE.filter(
      (n) =>
        n.name.toLowerCase().includes(query.toLowerCase()) ||
        n.type.toLowerCase().includes(query.toLowerCase()) ||
        n.category.toLowerCase().includes(query.toLowerCase()),
    );
    return filtered.reduce<Record<string, typeof NODE_PALETTE>>((acc, item) => {
      acc[item.category] = acc[item.category] || [];
      acc[item.category].push(item);
      return acc;
    }, {});
  }, [query]);

  return (
    <aside className="palette">
      <div className="palette-header">Nodes</div>
      <div className="palette-search">
        <input
          placeholder="Search nodes..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
      </div>
      {Object.entries(grouped).map(([category, items]) => (
        <div className="category" key={category}>
          <h4>{category}</h4>
          {items.map((item) => (
            <button
              key={item.type + item.name}
              className="node-chip"
              draggable
              onDragStart={(e) => {
                e.dataTransfer.setData(
                  "application/oneopen-node",
                  JSON.stringify(item),
                );
              }}
              onClick={() => onAdd(item.type, item.name, item.defaults)}
            >
              {item.name}
            </button>
          ))}
        </div>
      ))}
    </aside>
  );
}
