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
  const [openaiKey, setOpenaiKey] = useState("");

  async function generateEmailWithOpenAI(company) {
    if (!openaiKey) {
      throw new Error("OpenAI API key is required");
    }

    const prompt = `Generate a business email about ${company.name}. The email should be professional but slightly informal, about 2-3 paragraphs long.`;

    const response = await fetch('https://api.openai.com/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${openaiKey}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        model: "gpt-3.5-turbo",
        messages: [
          {
            role: "user",
            content: prompt
          }
        ],
        max_tokens: 500,
        temperature: 0.7,
      }),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(`OpenAI API error: ${errorData.error?.message || 'Unknown error'}`);
    }

    const data = await response.json();
    return data.choices[0].message.content;
  }

  async function startTest() {
    if (running || !selected) return;
    
    setRunning(true);
    setLog("");
    
    try {
      addToLog(`Starting test for: ${selected.name}`);
      addToLog(`Emails to generate: ${emailCount}`);
      addToLog(`Concurrency: ${concurrency}`);
      addToLog("---");
      
      if (!openaiKey) {
        throw new Error("Please enter your OpenAI API key first");
      }

      // Generate emails with OpenAI
      for (let i = 1; i <= emailCount; i++) {
        addToLog(`Generating email ${i}/${emailCount}...`);
        
        const emailContent = await generateEmailWithOpenAI(selected);
        addToLog(`Email ${i} generated:`);
        addToLog(`--- Email ${i} Content ---`);
        addToLog(emailContent);
        addToLog(`--- End Email ${i} ---`);
        
        // Simulate concurrency delay
        if (i % concurrency === 0) {
          addToLog(` Waiting for batch completion...`);
          await new Promise(resolve => setTimeout(resolve, 1000));
        }
      }
      
      addToLog("---");
      addToLog("Test completed successfully!");
      addToLog(`Generated ${emailCount} semi-coherent emails`);
      
    } catch (error) {
      addToLog(`Error: ${error.message}`);
      addToLog("Make sure your OpenAI API key is valid and has credits");
    } finally {
      setRunning(false);
    }
  }

  function addToLog(message) {
    if (logEnabled) {
      setLog(prev => prev + message + "\n\n");
    }
  }

  function clearLog() {
    setLog("");
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
        <h3>Email Test Settings</h3>
        
        {/* OpenAI API Key Input */}
        <div className={styles.apiKeySection}>
          <Input 
            label="OpenAI API Key" 
            value={openaiKey} 
            onChange={setOpenaiKey} 
            type="password"
            placeholder="sk-..."
          />
          <small className={styles.helperText}>
            Your API key is used only for this test and is not stored
          </small>
        </div>

        <div className={styles.grid}>
          <Input 
            label="Number of emails" 
            type="number" 
            value={emailCount} 
            onChange={(v) => setEmailCount(Number(v))} 
            min="1"
            max="20"
          />
          <Input 
            label="Concurrency level" 
            type="number" 
            value={concurrency} 
            onChange={(v) => setConcurrency(Number(v))} 
            min="1"
            max="5"
          />
          <label className={styles.checkRow}>
            <input 
              type="checkbox" 
              checked={logEnabled} 
              onChange={(e) => setLogEnabled(e.target.checked)} 
            />
            <span>Show detailed log</span>
          </label>
          
          <div className={styles.actions}>
            <button 
              className={styles.startBtn} 
              onClick={startTest} 
              disabled={running || !selected || !openaiKey}
            >
              {running ? "Generating Emails..." : "Generate Test Emails"}
            </button>
            <button 
              className={styles.clearBtn} 
              onClick={clearLog}
              disabled={running}
            >
              Clear Log
            </button>
          </div>
        </div>

        <div className={styles.logSection}>
          <h4>Test Output Log</h4>
          <div className={styles.logBox}>
            <pre>{log || "Log will appear here when you run the test..."}</pre>
          </div>
        </div>
      </section>
    </div>
  );
}