import Link from "next/link";
import { AgentGraph } from "@/components/AgentGraph";

export default async function RunPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <>
      <div className="topbar">
        <div>
          <h1 className="page-title">Agent Graph</h1>
          <p className="muted">Run {id}: live DAG state and evidence outputs.</p>
        </div>
        <Link className="button secondary" href={`/run/${id}/targets`}>
          Targets
        </Link>
      </div>
      <AgentGraph runId={id} />
    </>
  );
}
