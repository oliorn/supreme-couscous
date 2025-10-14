import styles from "./Input.module.css";

export default function Input({ label, value, onChange, type = "text", placeholder, rightAdornment }) {
  return (
    <label className={styles.wrap}>
      <span className={styles.label}>{label}</span>
      <div className={styles.fieldWrap}>
        <input
          className={styles.input}
          type={type}
          value={value}
          onChange={(e) => onChange?.(e.target.value)}
          placeholder={placeholder}
        />
        {rightAdornment && <div className={styles.right}>{rightAdornment}</div>}
      </div>
    </label>
  );
}