import { Runner } from '../lib/api';

interface Props {
  selections: Runner[];
}

export const SelectionTable: React.FC<Props> = ({ selections }) => {
  if (!selections.length) {
    return <p>No selections at the current settings.</p>;
  }

  return (
    <div className="table-wrapper">
      <table>
        <thead>
          <tr>
            <th>Date</th>
            <th>Track</th>
            <th>Race</th>
            <th>Runner</th>
            <th>Odds</th>
            <th>Prob%</th>
            <th>Imp%</th>
            <th>Edge%</th>
            <th>Value%</th>
          </tr>
        </thead>
        <tbody>
          {selections.map((row) => (
            <tr key={`${row.win_market_id}-${row.selection_id}`}>
              <td>{new Date(row.event_date).toLocaleDateString()}</td>
              <td>{row.track}</td>
              <td>{row.race_no}</td>
              <td>{row.selection_name}</td>
              <td>{row.win_odds.toFixed(2)}</td>
              <td>{(row.model_prob * 100).toFixed(1)}</td>
              <td>{(row.implied_prob * 100).toFixed(1)}</td>
              <td>{((row.model_prob - row.implied_prob) * 100).toFixed(1)}</td>
              <td>{row.value_pct !== undefined ? (row.value_pct * 100).toFixed(1) : '-'}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <style jsx>{`
        .table-wrapper {
          overflow-x: auto;
          border-radius: 12px;
          border: 1px solid rgba(148, 163, 184, 0.4);
          background: rgba(15, 23, 42, 0.8);
        }
        table {
          width: 100%;
          border-collapse: collapse;
        }
        th,
        td {
          padding: 0.75rem 1rem;
          text-align: left;
          border-bottom: 1px solid rgba(148, 163, 184, 0.2);
        }
        th {
          font-size: 0.85rem;
          text-transform: uppercase;
          letter-spacing: 0.08em;
          color: rgba(148, 163, 184, 0.9);
        }
      `}</style>
    </div>
  );
};
