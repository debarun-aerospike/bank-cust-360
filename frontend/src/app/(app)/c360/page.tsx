"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import {
  AccountRow,
  Customer360,
  PRODUCT_LINE_LABELS,
  ProductLine,
  fetchCustomer360,
  formatMoney,
} from "@/lib/api";

const LINES: Array<ProductLine | "ALL"> = [
  "ALL",
  "SAVINGS_CURRENT",
  "TERM_DEPOSIT",
  "LOAN",
  "CARD",
];

export default function C360Page() {
  const router = useRouter();
  const [customerId, setCustomerId] = useState<string | null>(null);
  const [data, setData] = useState<Customer360 | null>(null);
  const [tab, setTab] = useState<(typeof LINES)[number]>("ALL");
  const [statusFilter, setStatusFilter] = useState("Active");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const id = sessionStorage.getItem("c360_customer_id");
    if (!id) {
      router.replace("/login");
      return;
    }
    setCustomerId(id);
  }, [router]);

  useEffect(() => {
    if (!customerId) return;
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await fetchCustomer360(customerId, statusFilter);
        if (!cancelled) setData(res);
      } catch (e) {
        if (!cancelled) {
          const msg = e instanceof Error ? e.message : String(e);
          setError(msg);
          setData(null);
          if (/dormant/i.test(msg) || /cannot use netbanking/i.test(msg)) {
            sessionStorage.removeItem("c360_customer_id");
            router.replace("/login");
          }
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [customerId, statusFilter, router]);

  const rows: AccountRow[] = useMemo(() => {
    if (!data) return [];
    if (tab === "ALL") return data.accounts;
    return data.accountsByProductLine[tab] ?? [];
  }, [data, tab]);

  if (!customerId) return null;

  return (
    <main>
      <div className="customer-head">
        <div className="customer-identity">
          {data ? (
            <>
              <div className="customer-title-row">
                <h1>
                  {data.customer.salutation} {data.customer.name}
                </h1>
                <span className="status-pill" title="Customer status">
                  Customer · {data.customer.status}
                </span>
              </div>
              <p className="muted customer-meta">
                Customer No. {data.customer.customerNo}
              </p>
            </>
          ) : (
            <h1>Accounts</h1>
          )}
        </div>

        <div className="customer-controls">
          <label className="control-field" htmlFor="acct-status">
            <span className="label">Account status</span>
            <select
              id="acct-status"
              className="field field-flush control-select"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <option value="Active">Active</option>
              <option value="Dormant">Dormant</option>
              <option value="Closed">Closed</option>
              <option value="Pledged">Pledged</option>
              <option value="Hidden">Hidden</option>
              <option value="*">All</option>
            </select>
          </label>
        </div>
      </div>

      {loading ? <p className="muted">Loading accounts…</p> : null}
      {error ? <p className="error">{error}</p> : null}

      {!loading && !error && data ? (
        <>
          <div className="tabs" role="tablist">
            {LINES.map((line) => (
              <button
                key={line}
                type="button"
                role="tab"
                data-active={tab === line ? "true" : "false"}
                onClick={() => setTab(line)}
              >
                {line === "ALL" ? "All" : PRODUCT_LINE_LABELS[line]}
              </button>
            ))}
          </div>

          {rows.length === 0 ? (
            <p className="muted">No accounts in this view.</p>
          ) : (
            <div className="table-wrap panel panel-table">
              <table className="accounts">
                <thead>
                  <tr>
                    <th>Product</th>
                    <th>Account</th>
                    <th>Status</th>
                    <th>Currency</th>
                    <th>Balance</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((a) => (
                    <tr key={a.accountId}>
                      <td>
                        <div>{a.productDescription}</div>
                        <div className="muted" style={{ fontSize: "0.85rem" }}>
                          {PRODUCT_LINE_LABELS[a.productLine]} · {a.ownership}
                        </div>
                      </td>
                      <td>{a.accountId}</td>
                      <td>
                        <span className="status-pill status-pill-sm">
                          {a.accountStatus}
                        </span>
                      </td>
                      <td>{a.currency}</td>
                      <td className="bal">{formatMoney(a.balance, a.currency)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      ) : null}
    </main>
  );
}
