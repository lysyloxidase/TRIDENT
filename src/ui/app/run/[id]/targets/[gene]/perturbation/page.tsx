import { PredictionHeatmap } from "@/components/PredictionHeatmap";
import { VolcanoPlot } from "@/components/VolcanoPlot";

export default async function PerturbationPage({
  params
}: {
  params: Promise<{ id: string; gene: string }>;
}) {
  const { id, gene } = await params;
  return (
    <>
      <div className="topbar">
        <div>
          <h1 className="page-title">{gene} Perturbation</h1>
          <p className="muted">Run {id}: ensemble response in tumor epithelial cells.</p>
        </div>
        <span className="badge warn">observational_only</span>
      </div>
      <div className="grid two">
        <VolcanoPlot />
        <section className="panel">
          <h2>Patient Cell-Type UMAP</h2>
          <div className="umap" aria-label="Patient UMAP colored by predicted response">
            {Array.from({ length: 34 }, (_, index) => (
              <span
                key={index}
                style={{
                  left: `${12 + ((index * 17) % 72)}%`,
                  top: `${14 + ((index * 23) % 70)}%`,
                  opacity: 0.42 + ((index % 5) * 0.1)
                }}
              />
            ))}
          </div>
        </section>
      </div>
      <div className="band">
        <h2>Per-Model Predictions</h2>
        <PredictionHeatmap />
      </div>
      <section className="caveats">
        <strong>Disagreement readout</strong>
        <p>
          ETV4 and ETV5 exceed the ensemble variance threshold and should be prioritized as
          wet-lab response markers.
        </p>
      </section>
    </>
  );
}
