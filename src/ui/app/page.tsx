import Link from "next/link";
import { Play, Search } from "lucide-react";
import { recentRuns } from "@/lib/mockData";

const mondoSuggestions = [
  "Idiopathic pulmonary fibrosis",
  "Dry age-related macular degeneration",
  "Non-small cell lung cancer",
  "Raynaud disease",
  "Migraine disorder"
];

export default function DashboardPage() {
  return (
    <>
      <div className="topbar">
        <div>
          <h1 className="page-title">Disease to target to molecule to response</h1>
          <p className="muted">Run a closed-loop TRIDENT discovery workflow.</p>
        </div>
      </div>

      <section className="panel">
        <form className="form-row" action="/run/demo">
          <Search size={20} aria-hidden />
          <input
            className="input"
            name="disease"
            list="mondo"
            defaultValue="Idiopathic pulmonary fibrosis"
            aria-label="Disease"
          />
          <datalist id="mondo">
            {mondoSuggestions.map((disease) => (
              <option value={disease} key={disease} />
            ))}
          </datalist>
          <button className="button" type="submit">
            <Play size={16} aria-hidden /> Run TRIDENT
          </button>
        </form>
      </section>

      <div className="band">
        <h2>Recent Runs</h2>
        <table className="table">
          <thead>
            <tr>
              <th>Disease</th>
              <th>Status</th>
              <th>Targets</th>
              <th>Open</th>
            </tr>
          </thead>
          <tbody>
            {recentRuns.map((run) => (
              <tr key={run.id}>
                <td>{run.disease}</td>
                <td>
                  <span className="badge tchem">{run.status}</span>
                </td>
                <td>{run.targets}</td>
                <td>
                  <Link className="button secondary" href={`/run/${run.id}`}>
                    View Graph
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
