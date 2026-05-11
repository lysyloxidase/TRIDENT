import Link from "next/link";
import { Download } from "lucide-react";
import { MoleculeViewer } from "@/components/MoleculeViewer";
import { molecules } from "@/lib/mockData";

export default async function MoleculesPage({
  params
}: {
  params: Promise<{ id: string; gene: string }>;
}) {
  const { id, gene } = await params;
  return (
    <>
      <div className="topbar">
        <div>
          <h1 className="page-title">{gene} Molecules</h1>
          <p className="muted">Boltz-2 pocket, validated candidates, ADMET, and synthesis scores.</p>
        </div>
        <div className="form-row">
          <button className="button secondary" type="button">
            <Download size={16} aria-hidden /> Export SDF
          </button>
          <button className="button secondary" type="button">
            <Download size={16} aria-hidden /> Export SMILES
          </button>
        </div>
      </div>
      <div className="grid two">
        <MoleculeViewer gene={gene} />
        <section className="panel">
          <h2>Top Pocket</h2>
          <table className="table">
            <tbody>
              <tr>
                <th>Volume</th>
                <td>536 A3</td>
              </tr>
              <tr>
                <th>Hydrophobicity</th>
                <td>0.68</td>
              </tr>
              <tr>
                <th>Druggability</th>
                <td>0.91</td>
              </tr>
              <tr>
                <th>Return</th>
                <td>
                  <Link href={`/run/${id}/targets`}>Targets</Link>
                </td>
              </tr>
            </tbody>
          </table>
        </section>
      </div>
      <div className="band">
        <h2>Candidate Gallery</h2>
        <div className="molecule-grid">
          {molecules.map((molecule) => (
            <article className="molecule-card" key={molecule.smiles}>
              <div className="mol-sketch" aria-hidden>
                <span />
                <span />
                <span />
              </div>
              <p className="smiles">{molecule.smiles}</p>
              <dl className="metrics">
                <div>
                  <dt>Affinity</dt>
                  <dd>{molecule.affinity.toFixed(2)} kcal/mol</dd>
                </div>
                <div>
                  <dt>ADMET</dt>
                  <dd>{molecule.admet.toFixed(2)}</dd>
                </div>
                <div>
                  <dt>Synthesis</dt>
                  <dd>{molecule.synthesis.toFixed(2)}</dd>
                </div>
              </dl>
            </article>
          ))}
        </div>
      </div>
    </>
  );
}
