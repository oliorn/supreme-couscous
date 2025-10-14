import styles from "./Sidebar.module.css";

const items = [
  { key: "home", label: "Home" },
  { key: "test", label: "Test" },
  { key: "companies", label: "Companies" },
  { key: "history", label: "History" },
  { key: "settings", label: "Settings" },
];

export default function Sidebar({ route, onNavigate }) {
  return (
    <aside className={styles.sidebar}>
      <div className={styles.logo}>Virkum Tools</div>
      <nav className={styles.nav}>
        {items.map((it) => (
          <button
            key={it.key}
            className={it.key === route ? styles.active : styles.item}
            onClick={() => onNavigate(it.key)}
          >
            {it.label}
          </button>
        ))}
      </nav>
    </aside>
  );
}