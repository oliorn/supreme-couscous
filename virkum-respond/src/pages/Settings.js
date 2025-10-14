import { useState } from "react";
import styles from "./Settings.module.css";
import Input from "../components/Input.js";
import SaveIconButton from "../components/SaveIconButton.js";

export default function SettingsPage() {
  const [api, setApi] = useState("");
  const [dbKey, setDbKey] = useState("");

  function saveApi() { alert("Saved Virkum API"); }
  function saveDb() { alert("Saved DB key"); }

  return (
    <div className={styles.wrap}>
      <h2>Settings</h2>
      <div className={styles.card}>
        <div className={styles.row}>
          <Input label="Virkum API" value={api} onChange={setApi} />
          <SaveIconButton onClick={saveApi} />
        </div>
        <div className={styles.row}>
          <Input label="DB Key" value={dbKey} onChange={setDbKey} />
          <SaveIconButton onClick={saveDb} />
        </div>
      </div>
    </div>
  );
}
