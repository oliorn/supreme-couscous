import { useState } from "react";
import styles from "./Companies.module.css";
import Modal from "../components/Modal.js";
import Input from "../components/Input.js";
import SaveIconButton from "../components/SaveIconButton.js";

const initial = [
  { id: "c1", name: "Company 1", description: "", info: "" },
  { id: "c2", name: "Company 2", description: "", info: "" },
  { id: "c3", name: "Company 3", description: "", info: "" },
];

function EditCompanyModal({ company, onSave, onClose }) {
  const [name, setName] = useState(company.name);
  const [description, setDescription] = useState(company.description ?? "");
  const [info, setInfo] = useState(company.info ?? "");
  return (
    <Modal title={`Edit ${company.name}`} onClose={onClose}>
      <div className={styles.formGrid}>
        <Input label="Company name" value={name} onChange={setName} />
        <label className={styles.textareaWrap}>
          <span>Company description</span>
          <textarea value={description} onChange={(e)=>setDescription(e.target.value)} />
        </label>
        <label className={styles.textareaWrap}>
          <span>Company information</span>
          <textarea value={info} onChange={(e)=>setInfo(e.target.value)} />
        </label>
        <div className={styles.footerRight}>
          <SaveIconButton onClick={() => onSave({ ...company, name, description, info })} />
        </div>
      </div>
    </Modal>
  );
}

function CreateCompanyModal({ onSave, onClose, onBack }) {
  const [url, setUrl] = useState("");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [info, setInfo] = useState("");

  return (
    <Modal title="Create a new company" onBack={onBack} onClose={onClose}>
      <div className={styles.formGrid}>
        <section className={styles.section}>
          <h4>Web scrape</h4>
          <div className={styles.scrapeRow}>
            <Input label="URL" value={url} onChange={setUrl} placeholder="https://example.com" />
            <button className={styles.scrapeBtn}>Start</button>
          </div>
        </section>
        <section className={styles.section}>
          <h4>Details</h4>
          <Input label="Company name" value={name} onChange={setName} />
          <label className={styles.textareaWrap}>
            <span>Company description</span>
            <textarea value={description} onChange={(e)=>setDescription(e.target.value)} />
          </label>
          <label className={styles.textareaWrap}>
            <span>Company information</span>
            <textarea value={info} onChange={(e)=>setInfo(e.target.value)} />
          </label>
          <div className={styles.footerRight}>
            <SaveIconButton onClick={() => onSave({ id: crypto.randomUUID(), name, description, info })} />
          </div>
        </section>
      </div>
    </Modal>
  );
}

export default function CompaniesPage() {
  const [companies, setCompanies] = useState(initial);
  const [editing, setEditing] = useState(null);
  const [creating, setCreating] = useState(false);

  function saveEdited(updated) {
    setCompanies((arr) => arr.map((c) => (c.id === updated.id ? updated : c)));
    setEditing(null);
  }

  function saveCreated(newCompany) {
    setCompanies((arr) => [...arr, newCompany]);
    setCreating(false);
  }

  return (
    <div className={styles.wrap}>
      <h2>Companies</h2>
      <ul className={styles.list}>
        {companies.map((c) => (
          <li key={c.id} className={styles.row}>
            <span>{c.name}</span>
            <button className={styles.editBtn} onClick={() => setEditing(c)} title="Edit">
              {/* Pen icon */}
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 1 1 3 3L7 19l-4 1 1-4 12.5-12.5z"/></svg>
            </button>
          </li>
        ))}
      </ul>

      <button className={styles.plusFloat} onClick={() => setCreating(true)} aria-label="Create company" title="Create company">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
      </button>

      {editing && (
        <EditCompanyModal company={editing} onSave={saveEdited} onClose={() => setEditing(null)} />
      )}
      {creating && (
        <CreateCompanyModal onSave={saveCreated} onClose={() => setCreating(false)} onBack={() => setCreating(false)} />
      )}
    </div>
  );
}
