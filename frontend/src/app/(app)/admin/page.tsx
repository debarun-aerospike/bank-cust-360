"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  IngestStatus,
  Inventory,
  LoadStatus,
  MetricsPoint,
  fetchIngest,
  fetchInventory,
  fetchLoad,
  metricsWsUrl,
  putLoad,
  startIngest,
} from "@/lib/api";
import { INGEST_COUNTRIES } from "@/lib/countries";

const WINDOW_OPTIONS = [
  { label: "Last 1 min", seconds: 60 },
  { label: "Last 5 min", seconds: 300 },
  { label: "Last 15 min", seconds: 900 },
];

export default function AdminPage() {
  const [inventory, setInventory] = useState<Inventory | null>(null);
  const [load, setLoad] = useState<LoadStatus | null>(null);
  const [ingest, setIngest] = useState<IngestStatus | null>(null);
  const [readTps, setReadTps] = useState(50);
  const [writeTps, setWriteTps] = useState(10);
  const [ingestCount, setIngestCount] = useState(100);
  const [ingestCountry, setIngestCountry] = useState("India");
  const [windowSec, setWindowSec] = useState(300);
  const [series, setSeries] = useState<MetricsPoint[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    const [inv, ld, ig] = await Promise.all([
      fetchInventory(),
      fetchLoad(),
      fetchIngest(),
    ]);
    setInventory(inv);
    setLoad(ld);
    setIngest(ig);
    setReadTps(ld.targetReadTps || readTps);
    setWriteTps(ld.targetWriteTps || writeTps);
  }, [readTps, writeTps]);

  useEffect(() => {
    refresh().catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, [refresh]);

  useEffect(() => {
    let ws: WebSocket | null = null;
    let closed = false;
    let retry: ReturnType<typeof setTimeout> | null = null;

    const connect = () => {
      ws = new WebSocket(metricsWsUrl());
      ws.onmessage = (ev) => {
        try {
          const point = JSON.parse(ev.data) as MetricsPoint;
          setSeries((prev) => {
            const next = [...prev, point];
            const cutoff = Date.now() - windowSec * 1000;
            return next.filter((p) => p.ts >= cutoff).slice(-windowSec);
          });
        } catch {
          /* ignore */
        }
      };
      ws.onclose = () => {
        if (!closed) retry = setTimeout(connect, 1500);
      };
    };
    connect();
    return () => {
      closed = true;
      if (retry) clearTimeout(retry);
      ws?.close();
    };
  }, [windowSec]);

  useEffect(() => {
    if (ingest?.state !== "running") return;
    const t = setInterval(() => {
      fetchIngest()
        .then(setIngest)
        .catch(() => undefined);
      fetchInventory()
        .then(setInventory)
        .catch(() => undefined);
    }, 1500);
    return () => clearInterval(t);
  }, [ingest?.state]);

  const chartData = useMemo(
    () =>
      series.map((p) => ({
        t: new Date(p.ts).toLocaleTimeString(),
        readTps: p.readTps,
        writeTps: p.writeTps,
        targetRead: p.targetReadTps,
        targetWrite: p.targetWriteTps,
        p50: p.latencyMs.p50,
        p99: p.latencyMs.p99,
        p999: p.latencyMs.p99_9,
        errors: Math.round(p.errorRate * 1000) / 10,
      })),
    [series],
  );

  async function onLoadAction(
    action: "start" | "stop" | "pause" | "resume" | "set",
  ) {
    setBusy(true);
    setError(null);
    try {
      const ld = await putLoad({
        action,
        targetReadTps: readTps,
        targetWriteTps: writeTps,
      });
      setLoad(ld);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  async function onIngest(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const st = await startIngest(
        ingestCount,
        Math.max(100, Math.floor(ingestCount / 10)),
        ingestCountry.trim() || "India",
      );
      setIngest(st);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main>
      <div className="banner">Admin load lab · app-side latency & throughput</div>
      {error ? <p className="error">{error}</p> : null}

      <section className="admin-grid stats" style={{ marginBottom: "1.25rem" }}>
        <div className="stat">
          <div className="muted">Customers</div>
          <div className="n">{inventory?.custCnt.toLocaleString() ?? "—"}</div>
        </div>
        <div className="stat">
          <div className="muted">Accounts</div>
          <div className="n">{inventory?.acctCnt.toLocaleString() ?? "—"}</div>
        </div>
        <div className="stat">
          <div className="muted">S / F / L / C</div>
          <div className="n" style={{ fontSize: "1.1rem" }}>
            {inventory
              ? `${inventory.acctS} / ${inventory.acctF} / ${inventory.acctL} / ${inventory.acctC}`
              : "—"}
          </div>
        </div>
        <div className="stat">
          <div className="muted">Load state</div>
          <div className="n" style={{ fontSize: "1.4rem", textTransform: "capitalize" }}>
            {load?.state ?? "—"}
          </div>
        </div>
      </section>

      <section className="panel" style={{ marginBottom: "1.25rem" }}>
        <h2>Load control</h2>
        <div className="controls-row">
          <label className="control-field grow" htmlFor="rtps">
            <span className="label">Target Read TPS</span>
            <input
              id="rtps"
              className="field field-flush"
              type="number"
              min={0}
              max={5000}
              value={readTps}
              onChange={(e) => setReadTps(Number(e.target.value))}
            />
          </label>
          <label className="control-field grow" htmlFor="wtps">
            <span className="label">Target Write TPS</span>
            <input
              id="wtps"
              className="field field-flush"
              type="number"
              min={0}
              max={5000}
              value={writeTps}
              onChange={(e) => setWriteTps(Number(e.target.value))}
            />
          </label>
          <div className="toolbar" role="group" aria-label="Load control">
            <button
              className="btn load-action"
              data-active={load?.state === "running" ? "true" : "false"}
              disabled={busy || load?.state === "running"}
              type="button"
              onClick={() => onLoadAction("start")}
            >
              Start
            </button>
            <button
              className="btn load-action"
              data-active={load?.state === "paused" ? "true" : "false"}
              disabled={busy || load?.state !== "running"}
              type="button"
              onClick={() => onLoadAction("pause")}
            >
              Pause
            </button>
            <button
              className="btn load-action"
              data-active="false"
              disabled={busy || load?.state !== "paused"}
              type="button"
              onClick={() => onLoadAction("resume")}
            >
              Resume
            </button>
            <button
              className="btn load-action"
              data-active={
                !load?.state || load.state === "stopped" ? "true" : "false"
              }
              disabled={busy || load?.state === "stopped" || !load?.state}
              type="button"
              onClick={() => onLoadAction("stop")}
            >
              Stop
            </button>
          </div>
        </div>
        <p className="muted" style={{ margin: 0 }}>
          Achieved R/W: {load?.achievedReadTps ?? 0} / {load?.achievedWriteTps ?? 0} ·
          error {(load?.errorRate ?? 0) * 100}% · seeded max {load?.seededCustomerMax ?? "—"}
        </p>
      </section>

      <section className="panel" style={{ marginBottom: "1.25rem" }}>
        <h2>Ingestion simulation</h2>
        <form className="controls-row" onSubmit={onIngest}>
          <label className="control-field grow" htmlFor="ingest">
            <span className="label">Target customer count</span>
            <input
              id="ingest"
              className="field field-flush"
              type="number"
              min={1}
              max={9999999}
              value={ingestCount}
              onChange={(e) => setIngestCount(Number(e.target.value))}
            />
          </label>
          <label className="control-field grow" htmlFor="ingest-country">
            <span className="label">Country (names)</span>
            <select
              id="ingest-country"
              className="field field-flush control-select"
              value={ingestCountry}
              onChange={(e) => setIngestCountry(e.target.value)}
            >
              {INGEST_COUNTRIES.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </label>
          <button className="btn" disabled={busy || ingest?.state === "running"} type="submit">
            Run ingest
          </button>
        </form>
        <p className="muted" style={{ margin: 0 }}>
          Status: {ingest?.state ?? "idle"}
          {ingest?.message ? ` — ${ingest.message}` : ""}
        </p>
      </section>

      <div className="controls-row" style={{ marginBottom: "0.75rem" }}>
        <label className="control-field" htmlFor="win">
          <span className="label">Chart window</span>
          <select
            id="win"
            className="field field-flush control-select"
            value={windowSec}
            onChange={(e) => setWindowSec(Number(e.target.value))}
          >
            {WINDOW_OPTIONS.map((o) => (
              <option key={o.seconds} value={o.seconds}>
                {o.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      <section className="admin-grid controls">
        <div className="chart-panel">
          <h3>Throughput (TPS)</h3>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={chartData}>
              <CartesianGrid stroke="#d9d6cf" strokeDasharray="3 3" />
              <XAxis dataKey="t" hide />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="readTps" name="Read" stroke="#0D1B32" dot={false} isAnimationActive={false} />
              <Line type="monotone" dataKey="targetRead" name="Read target" stroke="#0D1B32" strokeDasharray="4 4" dot={false} isAnimationActive={false} />
              <Line type="monotone" dataKey="writeTps" name="Write" stroke="#F8F413" strokeWidth={2} dot={false} isAnimationActive={false} />
              <Line type="monotone" dataKey="targetWrite" name="Write target" stroke="#b3ad10" strokeDasharray="4 4" dot={false} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
        <div className="chart-panel">
          <h3>Latency (ms) · p50 / p99 / p99.9</h3>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={chartData}>
              <CartesianGrid stroke="#d9d6cf" strokeDasharray="3 3" />
              <XAxis dataKey="t" hide />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="p50" name="p50" stroke="#0D1B32" dot={false} isAnimationActive={false} />
              <Line type="monotone" dataKey="p99" name="p99" stroke="#5a6577" dot={false} isAnimationActive={false} />
              <Line type="monotone" dataKey="p999" name="p99.9" stroke="#F8F413" strokeWidth={2} dot={false} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </section>
    </main>
  );
}
