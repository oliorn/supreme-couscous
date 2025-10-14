import { useState } from "react";
import styles from "./History.module.css";
import Modal from "../components/Modal.js";

const initial = [
  { id: "t1", name: "Test 1", performed: "2025-03-12 12:30" },
  { id: "t2", name: "Test 2", performed: "2025-03-13 09:10" },
  { id: "t3", name: "Test 3", performed: "2025-03-14 18:45" },
];

export default function HistoryPage() {
  const [items] = useState(initial);
  const [open, setOpen] = useState(null);
  return (
    <div className={styles.wrap}>
      <h2>History</h2>
      <ul className={styles.list}>
        {items.map((it) => (
          <li key={it.id}>
            <button className={styles.row} onClick={() => setOpen(it)}>
              <span className={styles.name}>{it.name}</span>
              <span className={styles.meta}>Performed at {it.performed}</span>
            </button>
          </li>
        ))}
      </ul>

      {open && (
        <Modal
          title={`Results for ${open.name} performed on ${open.performed}`}
          onBack={() => setOpen(null)}
          onClose={() => setOpen(null)}
        >
          <p>Example results content. Replace with your data.</p>
          <ul>
            <li>Sent: 50 emails</li>
            <li>Success: 48</li>
            <li>Failures: 2</li>
          </ul>
        </Modal>
      )}
    </div>
  );
}