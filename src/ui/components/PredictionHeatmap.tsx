const rows = [
  { gene: "KRAS", cpa: -0.92, scgpt: -0.71, geneformer: -0.82, gears: -0.88 },
  { gene: "MAPK1", cpa: -0.44, scgpt: -0.32, geneformer: -0.48, gears: -0.41 },
  { gene: "MYC", cpa: -0.63, scgpt: -0.35, geneformer: -0.58, gears: -0.71 },
  { gene: "DUSP6", cpa: 0.74, scgpt: 0.51, geneformer: 0.82, gears: 0.68 },
  { gene: "ETV4", cpa: -0.82, scgpt: -0.11, geneformer: -0.52, gears: -0.69 }
];

const columns = ["cpa", "scgpt", "geneformer", "gears"] as const;

function heatColor(value: number) {
  const magnitude = Math.min(1, Math.abs(value));
  if (value < 0) {
    return `rgba(23, 105, 170, ${0.18 + magnitude * 0.62})`;
  }
  return `rgba(22, 135, 93, ${0.18 + magnitude * 0.62})`;
}

export function PredictionHeatmap() {
  return (
    <table className="table heatmap">
      <thead>
        <tr>
          <th>Gene</th>
          <th>CPA</th>
          <th>scGPT</th>
          <th>Geneformer</th>
          <th>GEARS</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={row.gene}>
            <th>{row.gene}</th>
            {columns.map((column) => (
              <td key={column} style={{ background: heatColor(row[column]) }}>
                {row[column].toFixed(2)}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
