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

function CreateCompanyModal({ onSave, onClose, onBack, existingCompanies }) {
  const [url, setUrl] = useState("");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [info, setInfo] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [duplicateWarning, setDuplicateWarning] = useState("");

  // Check for duplicates when name changes
  useEffect(() => {
    if (name.trim()) {
      const isDuplicate = existingCompanies.some(
        company => company.name.toLowerCase() === name.toLowerCase()
      );
      setDuplicateWarning(
        isDuplicate ? "⚠️ A company with this name already exists" : ""
      );
    } else {
      setDuplicateWarning("");
    }
  }, [name, existingCompanies]);

  async function handleScrape() {
    if (!url.trim()) return alert("Please enter a URL first");
    setLoading(true);
    setError("");
    setDuplicateWarning("");

    try {
      const data = await scrapeWebsite(url);
      const scraped = data.scraped || data;

      console.log("SCRAPED FROM BACKEND:", scraped);

      const companyName = scraped.company_name || "";
      
      // Check for duplicates
      const isDuplicate = existingCompanies.some(
        company => company.name.toLowerCase() === companyName.toLowerCase()
      );
      
      if (isDuplicate) {
        setDuplicateWarning("⚠️ This company already exists in the database");
      }

      setName(companyName);
      setDescription(scraped.company_description || "");
      setInfo(scraped.company_information || "");
    } catch (err) {
      console.error(err);
      setError("❌ Failed to scrape website. Please check the backend or URL.");
    } finally {
      setLoading(false);
    }
  }

  function handleSave() {
    if (duplicateWarning) {
      setError("Cannot save: Company already exists");
      return;
    }
    
    if (!name.trim()) {
      setError("Company name is required");
      return;
    }
    
    onSave({
      id: crypto.randomUUID(),
      name,
      description,
      info,
    });
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
          <Input 
            label="Company name" 
            value={name} 
            onChange={setName} 
          />
          {duplicateWarning && <p style={{color: 'orange', margin: '0', fontSize: '14px'}}>{duplicateWarning}</p>}
          
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
              onClick={handleSave}
              disabled={!!duplicateWarning || !name.trim()}
            />
          </div>
        </section>
      </div>
    </Modal>
  );
}

export default function CompaniesPage() {
  const [companies, setCompanies] = useState([]);
  const [editing, setEditing] = useState(null);
  const [creating, setCreating] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Load from backend when the page mounts
  useEffect(() => {
    async function loadCompanies() {
      try {
        setLoading(true);
        setError("");

        const data = await fetchCompanies();
        
        // Client-side duplicate removal as backup
        const uniqueCompanies = removeDuplicates(data);
        
        const mapped = uniqueCompanies.map((c, index) => ({
          id: c.id ?? String(index),
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

  // Helper function to remove duplicates client-side
  function removeDuplicates(companies) {
    const seen = new Set();
    return companies.filter(company => {
      const name = company.CompanyName?.toLowerCase().trim();
      if (!name || seen.has(name)) {
        return false;
      }
      seen.add(name);
      return true;
    });
  }

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
              {/* Pen icon - you can add your icon here */}
              ✏️
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
        {/* Plus icon - you can add your icon here */}
        +
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
          existingCompanies={companies}
        />
      )}
    </div>
  );
}