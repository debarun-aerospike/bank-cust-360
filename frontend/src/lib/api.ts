export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE?.replace(/\/$/, "") || "http://127.0.0.1:8000";

export const ADMIN_TOKEN =
  process.env.NEXT_PUBLIC_ADMIN_TOKEN || "admin:admin";

export type ProductLine =
  | "SAVINGS_CURRENT"
  | "TERM_DEPOSIT"
  | "LOAN"
  | "CARD";

export const PRODUCT_LINE_LABELS: Record<ProductLine, string> = {
  SAVINGS_CURRENT: "Savings / Current",
  TERM_DEPOSIT: "Fixed / Term Deposits",
  LOAN: "Loans",
  CARD: "Cards",
};

export type AccountRow = {
  accountId: string;
  productLine: ProductLine;
  currency: string;
  accountStatus: string;
  productDescription: string;
  balance: number;
  ownership: "PRIMARY" | "JOINT";
};

export type Customer360 = {
  customer: {
    customerId: string;
    customerNo: string;
    salutation: string;
    name: string;
    status: string;
  };
  accounts: AccountRow[];
  accountsByProductLine: Record<string, AccountRow[]>;
};

export type Inventory = {
  custCnt: number;
  acctCnt: number;
  acctS: number;
  acctF: number;
  acctL: number;
  acctC: number;
  prodCnt: number;
  updatedAt?: number | null;
};

export type LoadStatus = {
  state: "stopped" | "running" | "paused";
  targetReadTps: number;
  targetWriteTps: number;
  achievedReadTps: number;
  achievedWriteTps: number;
  errorRate: number;
  latencyMs: { p50: number; p99: number; p99_9: number };
  seededCustomerMax: number;
};

export type MetricsPoint = {
  ts: number;
  readTps: number;
  writeTps: number;
  errorRate: number;
  latencyMs: { p50: number; p99: number; p99_9: number };
  targetReadTps: number;
  targetWriteTps: number;
};

export type IngestStatus = {
  state: "idle" | "running" | "failed" | "completed";
  targetCustomerCount: number | null;
  country?: string | null;
  message: string | null;
  lastExitCode: number | null;
};

async function parseError(res: Response): Promise<string> {
  try {
    const j = await res.json();
    if (typeof j.detail === "string") return j.detail;
    return JSON.stringify(j.detail ?? j);
  } catch {
    return res.statusText;
  }
}

export function mockToken(customerId: string): string {
  return `mock:${customerId}`;
}

export async function fetchCustomer360(
  customerId: string,
  accountStatus = "Active",
): Promise<Customer360> {
  const q =
    accountStatus === "*"
      ? "?account_status=*"
      : `?account_status=${encodeURIComponent(accountStatus)}`;
  const res = await fetch(`${API_BASE}/api/v1/customers/${customerId}/360${q}`, {
    headers: { Authorization: `Bearer ${mockToken(customerId)}` },
    cache: "no-store",
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function fetchInventory(): Promise<Inventory> {
  const res = await fetch(`${API_BASE}/api/v1/admin/inventory`, {
    headers: { Authorization: `Bearer ${ADMIN_TOKEN}` },
    cache: "no-store",
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function fetchLoad(): Promise<LoadStatus> {
  const res = await fetch(`${API_BASE}/api/v1/admin/load`, {
    headers: { Authorization: `Bearer ${ADMIN_TOKEN}` },
    cache: "no-store",
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function putLoad(body: {
  action: "start" | "stop" | "pause" | "resume" | "set";
  targetReadTps?: number;
  targetWriteTps?: number;
}): Promise<LoadStatus> {
  const res = await fetch(`${API_BASE}/api/v1/admin/load`, {
    method: "PUT",
    headers: {
      Authorization: `Bearer ${ADMIN_TOKEN}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function startIngest(
  targetCustomerCount: number,
  checkpointEvery = 1000,
  country = "India",
): Promise<IngestStatus> {
  const res = await fetch(`${API_BASE}/api/v1/admin/ingest`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${ADMIN_TOKEN}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ targetCustomerCount, checkpointEvery, country }),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function fetchIngest(): Promise<IngestStatus> {
  const res = await fetch(`${API_BASE}/api/v1/admin/ingest`, {
    headers: { Authorization: `Bearer ${ADMIN_TOKEN}` },
    cache: "no-store",
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export function metricsWsUrl(): string {
  const base = API_BASE.replace(/^http/, "ws");
  return `${base}/api/v1/admin/metrics/stream?token=${encodeURIComponent(ADMIN_TOKEN)}`;
}

export function formatMoney(n: number, currency = "INR"): string {
  const code = (currency || "INR").toUpperCase();
  try {
    return new Intl.NumberFormat(undefined, {
      style: "currency",
      currency: code,
      minimumFractionDigits: code === "JPY" ? 0 : 2,
      maximumFractionDigits: code === "JPY" ? 0 : 2,
    }).format(n);
  } catch {
    return `${code} ${n.toFixed(2)}`;
  }
}

/** @deprecated Prefer formatMoney(n, currency) */
export function formatInr(n: number): string {
  return formatMoney(n, "INR");
}
