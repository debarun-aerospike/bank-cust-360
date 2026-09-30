/** Session keys for the Customer 360 demo login. */

export const SESSION_CUSTOMER_ID = "c360_customer_id";
export const SESSION_ROLE = "c360_role";

export type SessionRole = "customer" | "admin";

export function getSessionRole(): SessionRole | null {
  if (typeof window === "undefined") return null;
  const role = sessionStorage.getItem(SESSION_ROLE);
  if (role === "customer" || role === "admin") return role;
  // Legacy sessions only stored the customer id.
  if (sessionStorage.getItem(SESSION_CUSTOMER_ID)) return "customer";
  return null;
}

export function setCustomerSession(customerId: string): void {
  sessionStorage.setItem(SESSION_ROLE, "customer");
  sessionStorage.setItem(SESSION_CUSTOMER_ID, customerId);
}

export function setAdminSession(): void {
  sessionStorage.setItem(SESSION_ROLE, "admin");
  sessionStorage.removeItem(SESSION_CUSTOMER_ID);
}

export function clearSession(): void {
  sessionStorage.removeItem(SESSION_ROLE);
  sessionStorage.removeItem(SESSION_CUSTOMER_ID);
}
