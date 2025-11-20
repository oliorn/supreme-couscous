import { useState, useEffect } from "react";
import styles from "./Companies.module.css";
import Modal from "../components/Modal.js";
import Input from "../components/Input.js";
import SaveIconButton from "../components/SaveIconButton.js";
import { scrapeWebsite, fetchCompanies } from "../api/scraper";


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
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </label>
        <label className={styles.textareaWrap}>
          <span>Company information</span>
          <textarea
            value={info}
            onChange={(e) => setInfo(e.target.value)}
          />
        </label>
        <div className={styles.footerRight}>
          <SaveIconButton
            onClick={() => onSave({ ...company, name, description, info })}
          />
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
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // ✅ Uses the new scraper API helper
  async function handleScrape() {
  if (!url.trim()) return alert("Please enter a URL first");
  setLoading(true);
  setError("");

  try {
    const data = await scrapeWebsite(url);
    const scraped = data.scraped || data;

    // DEBUG 
    console.log("SCRAPED FROM BACKEND:", scraped);

    setName(scraped.company_name || "");
    setDescription(scraped.company_description || "");
    setInfo(scraped.company_information || "");
  } catch (err) {
    console.error(err);
    setError("❌ Failed to scrape website. Please check the backend or URL.");
  } finally {
    setLoading(false);
  }
}


  return (
    <Modal title="Create a new company" onBack={onBack} onClose={onClose}>
      <div className={styles.formGrid}>
        <section className={styles.section}>
          <h4>Web scrape</h4>
          <div className={styles.scrapeRow}>
            <Input
              label="URL"
              value={url}
              onChange={setUrl}
              placeholder="https://example.com"
            />
            <button
              className={styles.scrapeBtn}
              onClick={handleScrape}
              disabled={loading}
            >
              {loading ? "Loading..." : "Start"}
            </button>
          </div>
          {error && <p className={styles.error}>{error}</p>}
        </section>

        <section className={styles.section}>
          <h4>Details</h4>
          <Input label="Company name" value={name} onChange={setName} />
          <label className={styles.textareaWrap}>
            <span>Company description</span>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </label>
          <label className={styles.textareaWrap}>
            <span>Company information</span>
            <textarea
              value={info}
              onChange={(e) => setInfo(e.target.value)}
            />
          </label>
          <div className={styles.footerRight}>
            <SaveIconButton
              onClick={() =>
                onSave({
                  id: crypto.randomUUID(),
                  name,
                  description,
                  info,
                })
              }
            />
          </div>
        </section>
      </div>
    </Modal>
  );
}

export default function CompaniesPage() {
  const [companies, setCompanies] = useState([]);        // 🔹 start empty
  const [editing, setEditing] = useState(null);
  const [creating, setCreating] = useState(false);
  const [loading, setLoading] = useState(false);         // 🔹 NEW
  const [error, setError] = useState("");               // 🔹 NEW

  // 🔹 Load from backend when the page mounts
  useEffect(() => {
    async function loadCompanies() {
      try {
        setLoading(true);
        setError("");

        const data = await fetchCompanies();
        // data is whatever your FastAPI /companies returns.
        // assuming backend returns:
        // [{ CompanyName, CompanyDescription, CompanyInfo }, ...]
        const mapped = data.map((c, index) => ({
          id: c.id ?? String(index), // use DB id if you have it
          name: c.CompanyName,
          description: c.CompanyDescription,
          info: c.CompanyInfo,
        }));

        setCompanies(mapped);
      } catch (err) {
        console.error(err);
        setError("Failed to load companies from server");
      } finally {
        setLoading(false);
      }
    }

    loadCompanies();
  }, []);

  function saveEdited(updated) {
    setCompanies((arr) => arr.map((c) => (c.id === updated.id ? updated : c)));
    setEditing(null);
  }

  // For now this still only updates local state.
  // (The actual saving to DB happens when you scrape, since /scrape writes to DB.)
  function saveCreated(newCompany) {
    setCompanies((arr) => [...arr, newCompany]);
    setCreating(false);
  }

  return (
    <div className={styles.wrap}>
      <h2>Companies</h2>

      {loading && <p>Loading companies...</p>}
      {error && <p className={styles.error}>{error}</p>}

      <ul className={styles.list}>
        {companies.map((c) => (
          <li key={c.id} className={styles.row}>
            <span>{c.name}</span>
            <button
              className={styles.editBtn}
              onClick={() => setEditing(c)}
              title="Edit"
            >
              {/* Pen icon ... */}
            </button>
          </li>
        ))}
      </ul>

      {!loading && !error && companies.length === 0 && (
        <p>No companies in database yet.</p>
      )}

      <button
        className={styles.plusFloat}
        onClick={() => setCreating(true)}
        aria-label="Create company"
        title="Create company"
      >
        {/* plus icon ... */}
      </button>

      {editing && (
        <EditCompanyModal
          company={editing}
          onSave={saveEdited}
          onClose={() => setEditing(null)}
        />
      )}
      {creating && (
        <CreateCompanyModal
          onSave={saveCreated}
          onClose={() => setCreating(false)}
          onBack={() => setCreating(false)}
        />
      )}
    </div>
  );
}