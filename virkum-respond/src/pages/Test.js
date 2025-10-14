import { useMemo, useState } from "react";
import styles from "./Test.module.css";
import Input from "../components/Input.js";

const seedCompanies = [
  { id: "c1", name: "Company 1" },
  { id: "c2", name: "Company 2" },
  { id: "c3", name: "Company 3" },
  { id: "c4", name: "Company 4" },
];

export default function TestPage() {
  const [companies] = useState(seedCompanies);
  const [selectedId, setSelectedId] = useState(companies[0].id);
  const selected = useMemo(() => companies.find(c => c.id === selectedId), [companies, selectedId]);

  const [emailCount, setEmailCount] = useState(5);
  const [concurrency, setConcurrency] = useState(2);
  const [logEnabled, setLogEnabled] = useState(true);
  const [log, setLog] = useState("");
  const [running, setRunning] = useState(false);

  function startTest() {
    if (running) return;
    setRunning(true);
    setLog("");
    const steps = [
      `Preparing test for ${selected.name}…`,
      `Spawning ${emailCount} emails at concurrency ${concurrency}…`,
      `Running …`,
      `Aggregating results …`,
      `Done. ✅`,
    ];
    let i = 0;
    const timer = setInterval(() => {
      setLog((s) => (logEnabled ? s + steps[i] + "\n" : s));
      i++;
      if (i >= steps.length) { clearInterval(timer); setRunning(false); }
    }, 600);
  }

  return (
    <div className={styles.wrap}>
      <section className={styles.listPane}>
        <h3>Companies</h3>
        <ul className={styles.list}>
          {companies.map((c) => (
            <li key={c.id}>
              <button
                className={c.id === selectedId ? styles.rowActive : styles.row}
                onClick={() => setSelectedId(c.id)}
              >
                {c.name}
              </button>
            </li>
          ))}
        </ul>
      </section>

      <section className={styles.detailPane}>
        <h3>Test settings</h3>
        <div className={styles.grid}>
          <Input label="Number of emails" type="number" value={emailCount} onChange={(v) => setEmailCount(Number(v))} />
          <Input label="Concurrency level" type="number" value={concurrency} onChange={(v) => setConcurrency(Number(v))} />
          <label className={styles.checkRow}>
            <input type="checkbox" checked={logEnabled} onChange={(e) => setLogEnabled(e.target.checked)} />
            <span>Log output</span>
          </label>
          <div className={styles.actions}>
            <button className={styles.startBtn} onClick={startTest} disabled={running}>
              {running ? "Running…" : "Start test"}
            </button>
          </div>
        </div>

        <div className={styles.logBox}>
          <pre>{log}</pre>
        </div>
      </section>
    </div>
  );
}
