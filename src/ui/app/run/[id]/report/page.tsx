import Link from "next/link";
import { Download, Share2 } from "lucide-react";
import { CaveatBanner } from "@/components/CaveatBanner";
import { mandatoryCaveats } from "@/lib/caveats";
import { targets } from "@/lib/mockData";

export default async function ReportPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <>
      <div className="topbar">
        <div>
          <h1 className="page-title">TRIDENT Report</h1>
          <p className="muted">Publication-ready markdown preview for run {id}.</p>
        </div>
        <div className="form-row">
          <button className="button secondary" type="button">
            <Download size={16} aria-hidden /> Markdown
          </button>
          <button className="button secondary" type="button">
            <Download size={16} aria-hidden /> PDF
          </button>
          <button className="button secondary" type="button">
            <Share2 size={16} aria-hidden /> Share
          </button>
        </div>
      </div>
      <article className="report panel">
        <h2>Executive Summary</h2>
        <p>
          TRIDENT ranked {targets.length} targets for idiopathic pulmonary fibrosis. The top two
          targets occupy the high-novelty, high-confidence quadrant and retain patent white-space.
        </p>
        <h2>Evidence Triangulation</h2>
        <table className="table">
          <thead>
            <tr>
              <th>Target</th>
              <th>MR</th>
              <th>LBD</th>
              <th>Patent</th>
              <th>Trial</th>
            </tr>
          </thead>
          <tbody>
            {targets.slice(0, 5).map((target) => (
              <tr key={target.gene}>
                <td>{target.gene}</td>
                <td>{target.confidence > 0.98 ? "supportive" : "mixed"}</td>
                <td>{target.evidence[0]}</td>
                <td>legal_review_required=True</td>
                <td>pipeline gap retained</td>
              </tr>
            ))}
          </tbody>
        </table>
        <h2>Molecule Design</h2>
        <p>Top candidates passed Boltz-ABFE2, ADMET, and synthesis-route filters.</p>
        <h2>Perturbation Predictions</h2>
        <p>
          KRAS/MAPK pathway genes are predicted to downregulate; high-variance genes are flagged
          as experimental readouts.
        </p>
        <h2>Caveats & Limitations</h2>
        <ul>
          {mandatoryCaveats.map((caveat) => (
            <li key={caveat}>{caveat}</li>
          ))}
        </ul>
        <h2>References</h2>
        <ol>
          {Array.from({ length: 10 }, (_, index) => (
            <li key={index}>
              <Link href={`https://pubmed.ncbi.nlm.nih.gov/${10000000 + index}/`}>
                PMID:{10000000 + index}
              </Link>{" "}
              source_url timestamp agent_name
            </li>
          ))}
        </ol>
      </article>
      <div className="band">
        <CaveatBanner />
      </div>
    </>
  );
}
