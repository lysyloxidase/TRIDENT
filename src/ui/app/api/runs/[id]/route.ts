import { NextResponse } from "next/server";
import { targets } from "@/lib/mockData";

export async function GET(_: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return NextResponse.json({
    id,
    disease: "Idiopathic pulmonary fibrosis",
    status: "complete",
    targets,
    provenance: {
      source_url: `trident://run/${id}`,
      retrieval_timestamp: new Date().toISOString(),
      agent_name: "ui-api"
    }
  });
}
