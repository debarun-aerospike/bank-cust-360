"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { fetchCustomer360 } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<"customer" | "admin">("customer");
  const [customerId, setCustomerId] = useState("0000001");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (mode === "admin") {
      router.push("/admin");
      return;
    }
    const id = customerId.trim();
    if (!/^\d{7}$/.test(id)) {
      setError("Enter a 7-digit Customer ID (e.g. 0000001).");
      return;
    }
    setBusy(true);
    try {
      await fetchCustomer360(id, "Active");
      sessionStorage.setItem("c360_customer_id", id);
      router.push("/c360");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-frame">
      <aside className="login-brand">
        <div className="brand login-brand-mark">
          Aerospike Bank<span>C360</span>
        </div>
        <h1>Netbanking sign-in</h1>
        <p>
          Separate login for the Customer 360 demo. Use a seeded Customer ID for
          accounts, or continue to the Admin load lab.
        </p>
      </aside>

      <main className="login-card">
        <div className="login-mode" role="tablist" aria-label="Login type">
          <button
            type="button"
            role="tab"
            data-active={mode === "customer"}
            onClick={() => setMode("customer")}
          >
            Customer
          </button>
          <button
            type="button"
            role="tab"
            data-active={mode === "admin"}
            onClick={() => setMode("admin")}
          >
            Admin
          </button>
        </div>

        <form onSubmit={onSubmit}>
          <h2>{mode === "customer" ? "Customer login" : "Admin login"}</h2>
          {mode === "customer" ? (
            <>
              <label className="label" htmlFor="cid">
                Customer ID
              </label>
              <input
                id="cid"
                className="field field-flush"
                value={customerId}
                onChange={(e) => setCustomerId(e.target.value)}
                placeholder="0000001"
                inputMode="numeric"
                autoComplete="username"
              />
              <button className="btn btn-block" type="submit" disabled={busy}>
                {busy ? "Signing in…" : "Sign in to accounts"}
              </button>
            </>
          ) : (
            <>
              <p className="muted login-admin-hint">
                Admin uses the API credential configured on the server
                (<code>admin:admin</code> by default). No customer session is
                created.
              </p>
              <button className="btn btn-block" type="submit">
                Continue to Admin lab
              </button>
            </>
          )}
          {error ? <p className="error">{error}</p> : null}
        </form>

        <p className="login-footnote muted">
          Demo only ·{" "}
          <Link href="/admin" className="login-inline-link">
            skip to Admin
          </Link>
        </p>
      </main>
    </div>
  );
}
