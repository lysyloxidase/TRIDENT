import Link from "next/link";
import { ScoreBadge } from "@/components/ScoreBadge";
import { targets } from "@/lib/mockData";

export default async function TargetsPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <>
      <div className="topbar">
        <div>
          <h1 className="page-title">Ranked Targets</h1>
          <p className="muted">N, C, and N x C scores for run {id}.</p>
        </div>
        <Link className="button secondary" href={`/run/${id}/report`}>
          Report
        </Link>
      </div>
      <table className="table">
        <thead>
          <tr>
            <th>Rank</th>
            <th>Target</th>
            <th>TDL</th>
            <th>Novelty</th>
            <th>Confidence</th>
            <th>TRIDENT</th>
            <th>Evidence</th>
            <th>Next</th>
          </tr>
        </thead>
        <tbody>
          {targets.map((target) => (
            <tr key={target.gene}>
              <td>{target.rank}</td>
              <td>
                <strong>{target.gene}</strong>
                <br />
                <span className="muted">{target.uniprot}</span>
              </td>
              <td>
                <ScoreBadge tdl={target.tdl} />
              </td>
              <td>{target.novelty.toFixed(3)}</td>
              <td>{target.confidence.toFixed(3)}</td>
              <td>
                <strong>{target.trident.toFixed(3)}</strong>
              </td>
              <td>
                <details>
                  <summary>Trace</summary>
                  <ul>
                    {target.evidence.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                  <p className="muted">MR forest plot and LBD paths are stored with provenance.</p>
                </details>
              </td>
              <td className="action-stack">
                <Link href={`/run/${id}/targets/${target.gene}/molecules`}>Molecules</Link>
                <Link href={`/run/${id}/targets/${target.gene}/perturbation`}>Perturbation</Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}
