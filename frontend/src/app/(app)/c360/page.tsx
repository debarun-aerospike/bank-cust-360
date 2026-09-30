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
import {
  SESSION_CUSTOMER_ID,
  clearSession,
  getSessionRole,
} from "@/lib/session";

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
    if (getSessionRole() !== "customer") {
      router.replace("/login");
      return;
    }
    const id = sessionStorage.getItem(SESSION_CUSTOMER_ID);
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
            clearSession();
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

  const lineCounts = useMemo(() => {
    if (!data) return [];
    return (Object.keys(PRODUCT_LINE_LABELS) as ProductLine[]).map((line) => ({
      line,
      label: PRODUCT_LINE_LABELS[line],
      count: data.accountsByProductLine[line]?.length ?? 0,
    }));
  }, [data]);

  if (!customerId) return null;

  return (
    <main className="c360-page">
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

          <section className="home-below" aria-label="Account insights">
            <div className="home-snapshot">
              <h2>Your portfolio at a glance</h2>
              <p className="muted">
                Linked products in this view · {data.accounts.length} account
                {data.accounts.length === 1 ? "" : "s"}
              </p>
              <ul className="home-line-strip">
                {lineCounts.map((item) => (
                  <li key={item.line}>
                    <span className="home-line-label">{item.label}</span>
                    <span className="home-line-count">{item.count}</span>
                    <span
                      className="home-line-bar"
                      style={{
                        width: `${Math.max(8, item.count * 28)}%`,
                      }}
                    />
                  </li>
                ))}
              </ul>
            </div>

            <div className="home-spotlight">
              <div className="home-spotlight-copy">
                <p className="home-kicker">Aerospike Bank</p>
                <h2>Banking that keeps up with you</h2>
                <p>
                  Balances on this screen are assembled in real time from
                  customer, account, product, and booking data — the same
                  Customer 360 path powering netbanking demos.
                </p>
              </div>
              <div className="home-spotlight-art" aria-hidden="true">
                <svg viewBox="0 0 420 240" xmlns="http://www.w3.org/2000/svg">
                  <defs>
                    <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#1a2a44" />
                      <stop offset="100%" stopColor="#0d1b32" />
                    </linearGradient>
                  </defs>
                  <rect width="420" height="240" fill="url(#sky)" />
                  <circle cx="330" cy="54" r="28" fill="#F8F413" opacity="0.9" />
                  <g fill="#F2F1ED" opacity="0.88">
                    <rect x="36" y="120" width="42" height="100" />
                    <rect x="88" y="88" width="54" height="132" />
                    <rect x="152" y="108" width="48" height="112" />
                    <rect x="210" y="72" width="62" height="148" />
                    <rect x="284" y="100" width="44" height="120" />
                    <rect x="338" y="128" width="50" height="92" />
                  </g>
                  <g fill="#0D1B32" opacity="0.35">
                    <rect x="96" y="100" width="8" height="8" />
                    <rect x="112" y="100" width="8" height="8" />
                    <rect x="96" y="116" width="8" height="8" />
                    <rect x="112" y="116" width="8" height="8" />
                    <rect x="224" y="88" width="8" height="8" />
                    <rect x="240" y="88" width="8" height="8" />
                    <rect x="224" y="104" width="8" height="8" />
                    <rect x="240" y="104" width="8" height="8" />
                  </g>
                  <rect y="210" width="420" height="30" fill="#F8F413" opacity="0.85" />
                </svg>
              </div>
            </div>

            <div className="home-tips">
              <article>
                <h3>Stay secure</h3>
                <p className="muted">
                  Never share OTPs or passwords. Sign out when you finish on a
                  shared device.
                </p>
              </article>
              <article>
                <h3>Read your balances</h3>
                <p className="muted">
                  Savings available balance is ledger minus holds and float.
                  Loans and cards show outstanding principal plus interest.
                </p>
              </article>
              <article>
                <h3>Need another view?</h3>
                <p className="muted">
                  Use the product-line tabs and account-status filter above to
                  focus Active, Dormant, or Closed accounts.
                </p>
              </article>
            </div>
          </section>
        </>
      ) : null}
    </main>
  );
}
