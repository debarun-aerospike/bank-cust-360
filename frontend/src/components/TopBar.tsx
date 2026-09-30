"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

export function TopBar() {
  const pathname = usePathname();
  const router = useRouter();

  function signOut() {
    sessionStorage.removeItem("c360_customer_id");
    router.push("/login");
  }

  return (
    <header className="topbar">
      <Link href="/login" className="brand">
        Aerospike Bank<span>C360</span>
      </Link>
      <nav className="nav">
        <Link href="/c360" data-active={pathname?.startsWith("/c360") ? "true" : "false"}>
          Accounts
        </Link>
        <Link href="/admin" data-active={pathname?.startsWith("/admin") ? "true" : "false"}>
          Admin
        </Link>
        <button type="button" className="btn secondary btn-compact" onClick={signOut}>
          Sign out
        </button>
      </nav>
    </header>
  );
}
