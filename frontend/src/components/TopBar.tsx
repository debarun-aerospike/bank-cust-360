"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { clearSession, getSessionRole, SessionRole } from "@/lib/session";

export function TopBar() {
  const pathname = usePathname();
  const router = useRouter();
  const [role, setRole] = useState<SessionRole | null>(null);

  useEffect(() => {
    setRole(getSessionRole());
  }, [pathname]);

  function signOut() {
    clearSession();
    router.push("/login");
  }

  const isAdmin = role === "admin";
  const isCustomer = role === "customer";

  return (
    <header className="topbar">
      <Link href="/login" className="brand">
        Aerospike Bank<span>C360</span>
      </Link>
      <nav className="nav">
        {isCustomer ? (
          <Link
            href="/c360"
            data-active={pathname?.startsWith("/c360") ? "true" : "false"}
          >
            Accounts
          </Link>
        ) : null}
        {isAdmin ? (
          <Link
            href="/admin"
            data-active={pathname?.startsWith("/admin") ? "true" : "false"}
          >
            Admin
          </Link>
        ) : null}
        <button type="button" className="btn secondary btn-compact" onClick={signOut}>
          Sign out
        </button>
      </nav>
    </header>
  );
}
