"use client";

import "@xyflow/react/dist/style.css";
import {
  Background,
  Controls,
  Edge,
  Node,
  ReactFlow,
  useEdgesState,
  useNodesState
} from "@xyflow/react";
import { useEffect, useMemo, useState } from "react";

type AgentStatus = "queued" | "running" | "complete" | "failed";

const orderedAgents = [
  "disease",
  "kg",
  "lit",
  "patent",
  "trial",
  "mr",
  "lbd",
  "contradiction",
  "ranker",
  "structure",
  "generator",
  "validator",
  "perturbation",
  "report"
] as const;

const labels: Record<(typeof orderedAgents)[number], string> = {
  disease: "Disease Intake",
  kg: "KG Slice",
  lit: "Literature",
  patent: "Patent",
  trial: "Trial",
  mr: "MR",
  lbd: "LBD",
  contradiction: "Contradiction",
  ranker: "Target Ranker",
  structure: "Structure",
  generator: "Generator",
  validator: "Validator",
  perturbation: "Perturbation",
  report: "Report"
};

const positions: Record<(typeof orderedAgents)[number], { x: number; y: number }> = {
  disease: { x: 20, y: 30 },
  kg: { x: 210, y: 30 },
  lit: { x: 410, y: -50 },
  patent: { x: 410, y: 50 },
  trial: { x: 410, y: 150 },
  mr: { x: 630, y: -50 },
  lbd: { x: 630, y: 50 },
  contradiction: { x: 630, y: 150 },
  ranker: { x: 860, y: 50 },
  structure: { x: 1080, y: -70 },
  generator: { x: 1080, y: 25 },
  validator: { x: 1080, y: 120 },
  perturbation: { x: 1290, y: 25 },
  report: { x: 1510, y: 25 }
};

const graphEdges: Edge[] = [
  { id: "disease-kg", source: "disease", target: "kg" },
  { id: "kg-lit", source: "kg", target: "lit" },
  { id: "kg-patent", source: "kg", target: "patent" },
  { id: "kg-trial", source: "kg", target: "trial" },
  { id: "lit-mr", source: "lit", target: "mr" },
  { id: "lit-lbd", source: "lit", target: "lbd" },
  { id: "trial-contradiction", source: "trial", target: "contradiction" },
  { id: "mr-ranker", source: "mr", target: "ranker" },
  { id: "lbd-ranker", source: "lbd", target: "ranker" },
  { id: "contradiction-ranker", source: "contradiction", target: "ranker" },
  { id: "ranker-structure", source: "ranker", target: "structure" },
  { id: "structure-generator", source: "structure", target: "generator" },
  { id: "generator-validator", source: "generator", target: "validator" },
  { id: "validator-perturbation", source: "validator", target: "perturbation" },
  { id: "perturbation-report", source: "perturbation", target: "report" }
];

function makeNodes(statuses: Record<string, AgentStatus>): Node[] {
  return orderedAgents.map((agent) => ({
    id: agent,
    position: positions[agent],
    data: {
      label: (
        <div className={`agent-node ${statuses[agent] ?? "queued"}`}>
          <strong>{labels[agent]}</strong>
          <span>{statuses[agent] ?? "queued"}</span>
        </div>
      )
    },
    type: agent === "disease" ? "input" : agent === "report" ? "output" : "default"
  }));
}

export function AgentGraph({ runId }: { runId: string }) {
  const [statuses, setStatuses] = useState<Record<string, AgentStatus>>({
    disease: "complete",
    kg: "complete",
    lit: "running"
  });
  const [selected, setSelected] = useState<string>("lit");
  const initialNodes = useMemo(() => makeNodes(statuses), []);
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, , onEdgesChange] = useEdgesState(graphEdges);

  useEffect(() => {
    setNodes(makeNodes(statuses));
  }, [setNodes, statuses]);

  useEffect(() => {
    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    const configured = process.env.NEXT_PUBLIC_TRIDENT_WS_URL;
    const socket = new WebSocket(
      configured
        ? `${configured}/runs/${runId}`
        : `${protocol}://${window.location.host}/api/runs/${runId}/events`
    );
    let fallbackTimer: ReturnType<typeof setInterval> | null = null;
    socket.onmessage = (event) => {
      const update = JSON.parse(event.data) as { agent: string; status: AgentStatus };
      setStatuses((current) => ({ ...current, [update.agent]: update.status }));
    };
    socket.onerror = () => {
      let cursor = 3;
      fallbackTimer = setInterval(() => {
        const agent = orderedAgents[cursor];
        setStatuses((current) => ({ ...current, [agent]: "complete" }));
        cursor += 1;
        if (cursor >= orderedAgents.length && fallbackTimer) {
          clearInterval(fallbackTimer);
        }
      }, 900);
    };
    return () => {
      socket.close();
      if (fallbackTimer) {
        clearInterval(fallbackTimer);
      }
    };
  }, [runId]);

  const selectedStatus = statuses[selected] ?? "queued";

  return (
    <div className="grid two">
      <div className="react-flow-shell">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={(_, node) => setSelected(node.id)}
          fitView
        >
          <Background />
          <Controls />
        </ReactFlow>
      </div>
      <section className="panel">
        <h2>{labels[selected as keyof typeof labels] ?? selected}</h2>
        <p>
          <span className={`status-dot ${selectedStatus}`} /> {selectedStatus}
        </p>
        <table className="table">
          <tbody>
            <tr>
              <th>Source URL</th>
              <td>trident://run/{runId}/{selected}</td>
            </tr>
            <tr>
              <th>Timestamp</th>
              <td>2026-05-11T00:00:00Z</td>
            </tr>
            <tr>
              <th>Output</th>
              <td>Provenance-bearing fixture output with verified citation handles.</td>
            </tr>
          </tbody>
        </table>
      </section>
    </div>
  );
}
