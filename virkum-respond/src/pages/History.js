import { useState, useEffect } from "react";
import styles from "./History.module.css";
import Modal from "../components/Modal.js";
import { fetchTests } from "../api/tests";

function formatDateTime(isoString) {
  if (!isoString) return "N/A";
  const d = new Date(isoString);
  if (Number.isNaN(d.getTime())) return isoString;
  return d.toLocaleString();
}

function TestDetailsModal({ test, onClose }) {
  return (
    <Modal title={`Test #${test.test_id}`} onClose={onClose}>
      <div className={styles.detailsGrid}>
        <p>
          <strong>Companies:</strong>{" "}
          {Array.isArray(test.companies) && test.companies.length > 0
            ? test.companies.join(", ")
            : "N/A"}
        </p>
        <p>
          <strong>Started:</strong> {formatDateTime(test.started_at)}
        </p>
        <p>
          <strong>Finished:</strong> {formatDateTime(test.finished_at)}
        </p>
        <p>
          <strong>Total requests:</strong> {test.total_requests ?? 0}
        </p>
        <p>
          <strong>Number of emails:</strong> {test.num_emails ?? "N/A"}
        </p>
        <p>
          <strong>Concurrency level:</strong>{" "}
          {test.concurrency_level ?? "N/A"}
        </p>
        <p>
          <strong>Average reply grade:</strong>{" "}
          {test.avg_reply_grade != null
            ? `${(test.avg_reply_grade * 100).toFixed(1)} %`
            : "N/A"}
        </p>
      </div>
    </Modal>
  );
}

export default function HistoryPage() {
  const [tests, setTests] = useState([]);
  const [selected, setSelected] = useState(null); // like editing/creating in Companies
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadHistory() {
      try {
        setLoading(true);
        setError("");

        const data = await fetchTests();
        setTests(data);
      } catch (err) {
        console.error(err);
        setError("Failed to load test history from server");
      } finally {
        setLoading(false);
      }
    }

    loadHistory();
  }, []);

  return (
    <div className={styles.wrap}>
      <h2>History</h2>

      {loading && <p>Loading test history...</p>}
      {error && <p className={styles.error}>{error}</p>}

      {!loading && !error && tests.length === 0 && (
        <p>No tests in database yet.</p>
      )}

      {!loading && !error && tests.length > 0 && (
        <ul className={styles.list}>
          {tests.map((t) => (
            <li key={t.test_id} className={styles.row}>
              <button
                className={styles.rowBtn}
                onClick={() => setSelected(t)}
              >
                <span className={styles.name}>
                  Test #{t.test_id} –{" "}
                  {Array.isArray(t.companies) && t.companies.length > 0
                    ? t.companies.join(", ")
                    : "Unknown companies"}
                </span>
                <span className={styles.meta}>
                  Performed at{" "}
                  {formatDateTime(t.finished_at || t.started_at)}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}

      {selected && (
        <TestDetailsModal
          test={selected}
          onClose={() => setSelected(null)}
        />
      )}
    </div>
  );
}
