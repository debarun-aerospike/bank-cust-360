import { TopBar } from "@/components/TopBar";

export default function AppLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <div className="shell">
      <TopBar />
      {children}
    </div>
  );
}
