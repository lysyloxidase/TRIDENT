import { perturbationGenes } from "@/lib/mockData";

export function VolcanoPlot() {
  return (
    <svg className="plot" viewBox="0 0 620 420" role="img" aria-label="Volcano plot">
      <line x1="70" y1="350" x2="570" y2="350" className="axis" />
      <line x1="310" y1="60" x2="310" y2="350" className="axis faint" />
      <line x1="70" y1="350" x2="70" y2="60" className="axis" />
      <text x="260" y="392" className="plot-label">
        log2 fold-change
      </text>
      <text x="18" y="210" className="plot-label vertical">
        -log10(p)
      </text>
      {perturbationGenes.map((point) => {
        const x = 310 + point.log2fc * 210;
        const y = 350 - point.neglog10p * 42;
        const high = point.variance > 0.04;
        return (
          <g key={point.gene}>
            <circle cx={x} cy={y} r={high ? 8 : 6} className={high ? "dot warn" : "dot"} />
            <text x={x + 9} y={y - 8} className="plot-label">
              {point.gene}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
