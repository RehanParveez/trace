import { useQuery } from "@tanstack/react-query";
import { getHealth } from "../../shared/api/system.api";

export function HomePage() {
  const health = useQuery({
    queryKey: ["system", "health"],
    queryFn: getHealth,
    refetchInterval: 30_000,
  });

  const connected = health.isSuccess && health.data.status === "healthy";

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <div className="mx-auto flex min-h-screen max-w-5xl flex-col justify-center px-6 py-16">
        <div className="mb-10">
          <p className="text-sm font-semibold uppercase tracking-[0.3em] text-slate-400">
            Trace
          </p>
          <h1 className="mt-3 text-5xl font-semibold tracking-tight">
            Construction Intelligence
          </h1>
          <p className="mt-4 max-w-2xl text-lg text-slate-400">
            Phase 0 foundation is running. The visual product system will be
            defined before the application modules are built.
          </p>
        </div>

        <section className="grid gap-4 sm:grid-cols-3">
          <StatusCard label="Frontend" value="Running" />
          <StatusCard label="Backend API" value={health.isPending ? "Checking..." : connected ? "Connected" : "Offline"} />
          <StatusCard label="Version" value={health.data?.version ?? "—"} />
        </section>
      </div>
    </main>
  );
}

function StatusCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
      <p className="text-sm text-slate-500">{label}</p>
      <p className="mt-2 text-lg font-medium">{value}</p>
    </div>
  );
}
