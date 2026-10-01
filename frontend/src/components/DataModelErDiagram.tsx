"use client";

type BinRow = { name: string; type: string; note?: string };

type Entity = {
  id: string;
  x: number;
  y: number;
  w: number;
  title: string;
  pk: string;
  bins: BinRow[];
  accent?: "core" | "aux";
};

const ENTITIES: Entity[] = [
  {
    id: "customers",
    x: 40,
    y: 48,
    w: 220,
    title: "customers",
    pk: "PK  7-digit ID (0000001)",
    accent: "core",
    bins: [
      { name: "salutation", type: "str" },
      { name: "name", type: "str" },
      { name: "status", type: "Active | Dormant" },
      { name: "lastTouchAt", type: "int ms", note: "W1" },
    ],
  },
  {
    id: "cust_accts",
    x: 340,
    y: 48,
    w: 220,
    title: "cust_accts",
    pk: "PK  same as customer ID",
    accent: "core",
    bins: [
      { name: "acctIds", type: "list<str>", note: "max 5" },
    ],
  },
  {
    id: "accounts",
    x: 340,
    y: 280,
    w: 260,
    title: "accounts",
    pk: "PK  {S|F|L|C} + 12 digits",
    accent: "core",
    bins: [
      { name: "productLine", type: "enum ×4" },
      { name: "currency", type: "INR" },
      { name: "acctStatus", type: "str" },
      { name: "productCode", type: "str" },
      { name: "productDesc", type: "str", note: "denorm" },
      { name: "ownership", type: "PRIMARY | JOINT" },
      { name: "ownerIds", type: "list<str>", note: "max 3" },
      { name: "openedAt", type: "YYYY-MM-DD" },
    ],
  },
  {
    id: "booking",
    x: 680,
    y: 280,
    w: 240,
    title: "booking",
    pk: "PK  same as account ID",
    accent: "core",
    bins: [
      { name: "ledger / hold / float", type: "paise", note: "S|F" },
      { name: "principal / interest", type: "paise", note: "L|C" },
      { name: "hist", type: "list", note: "max 20" },
    ],
  },
  {
    id: "products",
    x: 40,
    y: 280,
    w: 220,
    title: "products",
    pk: "PK  product code",
    accent: "aux",
    bins: [
      { name: "description", type: "str" },
      { name: "productLine", type: "enum" },
      { name: "active", type: "bool" },
    ],
  },
  {
    id: "inventory",
    x: 680,
    y: 48,
    w: 240,
    title: "inventory",
    pk: "PK  totals (± totals:wN)",
    accent: "aux",
    bins: [
      { name: "custCnt / acctCnt", type: "int" },
      { name: "acctS/F/L/C", type: "int" },
      { name: "prodCnt", type: "int" },
      { name: "updatedAt", type: "int ms" },
    ],
  },
];

function entityHeight(bins: BinRow[]) {
  return 54 + bins.length * 22 + 10;
}

function EntityBox({ e }: { e: Entity }) {
  const h = entityHeight(e.bins);
  const headerFill = e.accent === "aux" ? "#F2F1ED" : "#F8F413";
  return (
    <g transform={`translate(${e.x}, ${e.y})`}>
      <rect
        width={e.w}
        height={h}
        fill="#ffffff"
        stroke="#0D1B32"
        strokeWidth={1.25}
      />
      <rect width={e.w} height={32} fill={headerFill} stroke="#0D1B32" strokeWidth={1.25} />
      <text x={12} y={21} className="er-title">
        {e.title}
      </text>
      <text x={12} y={48} className="er-pk">
        {e.pk}
      </text>
      <line x1={0} y1={56} x2={e.w} y2={56} stroke="#d9d6cf" />
      {e.bins.map((b, i) => {
        const y = 74 + i * 22;
        return (
          <g key={b.name}>
            <text x={12} y={y} className="er-bin">
              {b.name}
            </text>
            <text x={e.w - 12} y={y} className="er-type" textAnchor="end">
              {b.note ? `${b.type} · ${b.note}` : b.type}
            </text>
          </g>
        );
      })}
    </g>
  );
}

/** Midpoints on entity edges for connectors */
function edge(
  e: Entity,
  side: "top" | "bottom" | "left" | "right",
  frac = 0.5,
): { x: number; y: number } {
  const h = entityHeight(e.bins);
  switch (side) {
    case "top":
      return { x: e.x + e.w * frac, y: e.y };
    case "bottom":
      return { x: e.x + e.w * frac, y: e.y + h };
    case "left":
      return { x: e.x, y: e.y + h * frac };
    case "right":
      return { x: e.x + e.w, y: e.y + h * frac };
  }
}

function byId(id: string) {
  const e = ENTITIES.find((x) => x.id === id);
  if (!e) throw new Error(`unknown entity ${id}`);
  return e;
}

type Rel = {
  from: string;
  fromSide: "top" | "bottom" | "left" | "right";
  fromFrac?: number;
  to: string;
  toSide: "top" | "bottom" | "left" | "right";
  toFrac?: number;
  label: string;
  dashed?: boolean;
  labelDx?: number;
  labelDy?: number;
  labelW?: number;
};

const RELS: Rel[] = [
  {
    from: "customers",
    fromSide: "right",
    to: "cust_accts",
    toSide: "left",
    label: "1 : 1  shared key",
    labelDy: -18,
  },
  {
    from: "cust_accts",
    fromSide: "bottom",
    to: "accounts",
    toSide: "top",
    label: "1 : N  acctIds (≤5)",
    labelDx: 70,
  },
  {
    from: "accounts",
    fromSide: "right",
    fromFrac: 0.28,
    to: "booking",
    toSide: "left",
    toFrac: 0.28,
    label: "1 : 1  same account ID",
    labelDy: -16,
    labelW: 168,
  },
  {
    from: "accounts",
    fromSide: "left",
    fromFrac: 0.62,
    to: "customers",
    toSide: "bottom",
    toFrac: 0.62,
    label: "N : M  ownerIds (≤3)",
    labelDx: -40,
    labelDy: 8,
  },
  {
    from: "products",
    fromSide: "right",
    fromFrac: 0.35,
    to: "accounts",
    toSide: "left",
    toFrac: 0.18,
    label: "ingest copy → productDesc",
    dashed: true,
    labelDy: -22,
    labelW: 178,
  },
];

function Connector({ r }: { r: Rel }) {
  const a = edge(byId(r.from), r.fromSide, r.fromFrac ?? 0.5);
  const b = edge(byId(r.to), r.toSide, r.toFrac ?? 0.5);
  const mx = (a.x + b.x) / 2 + (r.labelDx ?? 0);
  const my = (a.y + b.y) / 2 + (r.labelDy ?? 0);
  const lw = r.labelW ?? 156;
  let d: string;
  if (r.fromSide === "right" && r.toSide === "left") {
    const mid = (a.x + b.x) / 2;
    d = `M ${a.x} ${a.y} H ${mid} V ${b.y} H ${b.x}`;
  } else if (r.fromSide === "bottom" && r.toSide === "top") {
    const mid = (a.y + b.y) / 2;
    d = `M ${a.x} ${a.y} V ${mid} H ${b.x} V ${b.y}`;
  } else if (r.fromSide === "left" && r.toSide === "bottom") {
    d = `M ${a.x} ${a.y} H ${a.x - 36} V ${b.y + 28} H ${b.x} V ${b.y}`;
  } else {
    d = `M ${a.x} ${a.y} L ${b.x} ${b.y}`;
  }

  return (
    <g className={r.dashed ? "er-rel dashed" : "er-rel"}>
      <path d={d} fill="none" stroke="#0D1B32" strokeWidth={1.35} />
      <circle cx={a.x} cy={a.y} r={3.5} fill="#0D1B32" />
      <circle cx={b.x} cy={b.y} r={3.5} fill="#0D1B32" />
      <rect
        x={mx - lw / 2}
        y={my - 11}
        width={lw}
        height={20}
        fill="#F2F1ED"
        stroke="#d9d6cf"
      />
      <text x={mx} y={my + 3} textAnchor="middle" className="er-rel-label">
        {r.label}
      </text>
    </g>
  );
}

export default function DataModelErDiagram() {
  const width = 960;
  const height = 620;

  return (
    <section className="panel er-panel" aria-labelledby="er-heading">
      <div className="er-header">
        <div>
          <h2 id="er-heading">Aerospike data model</h2>
          <p className="muted er-sub">
            Namespace <code>bank</code> · sets as entities · relationships by
            primary key and bounded ID lists (not server joins)
          </p>
        </div>
        <ul className="er-legend" aria-label="Legend">
          <li>
            <span className="er-swatch core" /> Core C360 path
          </li>
          <li>
            <span className="er-swatch aux" /> Admin / ingest
          </li>
          <li>
            <span className="er-swatch dashed" /> Copy at ingest only
          </li>
        </ul>
      </div>

      <div className="er-canvas" role="img" aria-label="Entity relationship diagram of Aerospike sets">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          width="100%"
          height="auto"
          className="er-svg"
        >
          <defs>
            <style>{`
              .er-title { font: 700 13px var(--font-display, Georgia, serif); fill: #0D1B32; }
              .er-pk { font: 600 10px var(--font-body, system-ui, sans-serif); fill: #5a6577; }
              .er-bin { font: 600 11px var(--font-body, system-ui, sans-serif); fill: #0D1B32; }
              .er-type { font: 500 10px var(--font-body, system-ui, sans-serif); fill: #5a6577; }
              .er-rel-label { font: 600 10px var(--font-body, system-ui, sans-serif); fill: #0D1B32; }
              .er-rel.dashed path { stroke-dasharray: 5 4; stroke: #5a6577; }
              .er-ns { font: 700 12px var(--font-display, Georgia, serif); fill: #0D1B32; }
            `}</style>
          </defs>

          <rect
            x={16}
            y={12}
            width={width - 32}
            height={height - 24}
            fill="none"
            stroke="#d9d6cf"
            strokeDasharray="6 4"
          />
          <text x={28} y={34} className="er-ns">
            namespace · bank
          </text>

          {RELS.map((r) => (
            <Connector key={`${r.from}-${r.to}-${r.label}`} r={r} />
          ))}
          {ENTITIES.map((e) => (
            <EntityBox key={e.id} e={e} />
          ))}
        </svg>
      </div>

      <ol className="er-readpath muted">
        <li>
          <strong>C360 read:</strong> get customers → get cust_accts → batch
          accounts (≤5) → batch booking (≤5) → assemble balances in app
        </li>
        <li>
          <strong>Indexes:</strong> none on routine paths · caps: acctIds 5,
          ownerIds 3, hist 20
        </li>
      </ol>
    </section>
  );
}
