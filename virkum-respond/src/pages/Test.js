import { useMemo, useState, useEffect } from "react";
import styles from "./Test.module.css";
import Input from "../components/Input.js";
import { fetchCompanies } from "../api/scraper";

export default function TestPage() {
  const [companies, setCompanies] = useState([]);
  const [selectedId, setSelectedId] = useState("");
  const [loadingCompanies, setLoadingCompanies] = useState(true);
  
  const selected = useMemo(() => 
    companies.find(c => c.id === selectedId), [companies, selectedId]
  );

  const [emailCount, setEmailCount] = useState(5);
  const [concurrency, setConcurrency] = useState(2);
  const [logEnabled, setLogEnabled] = useState(true);
  const [log, setLog] = useState("");
  const [running, setRunning] = useState(false);
  const [openaiKey, setOpenaiKey] = useState("");
  
  // New state for email response feature
  const [mockEmail, setMockEmail] = useState("");
  const [emailResponse, setEmailResponse] = useState("");
  const [generatingResponse, setGeneratingResponse] = useState(false);

  // Helper function to detect if email is for a different company
  function appearsToBeForOtherCompany(emailText, companyName) {
    const emailLower = emailText.toLowerCase();
    const companyNameLower = companyName.toLowerCase();
    
    // List of common greetings that indicate the intended recipient
    const recipientGreetings = [
      "dear", "to", "hello", "hi", "greetings", "attn:", "attention:",
      "for the attention of", "re:", "subject:", "query for"
    ];
    
    // Common company names to check for
    const commonCompanies = [
      "youtube", "google", "netflix", "amazon", "apple", "microsoft",
      "facebook", "twitter", "instagram", "linkedin", "spotify",
      "uber", "airbnb", "tesla", "nike", "adidas", "starbucks"
    ];
    
    // Check if email mentions a different company in greeting/salutation
    for (const greeting of recipientGreetings) {
      for (const company of commonCompanies) {
        if (company === companyNameLower) continue; // Skip if it's our own company
        
        const pattern1 = `${greeting} ${company}`;
        const pattern2 = `${greeting} ${company} team`;
        const pattern3 = `${greeting} ${company} support`;
        const pattern4 = `${greeting} ${company} customer service`;
        
        if (emailLower.includes(pattern1) || 
            emailLower.includes(pattern2) || 
            emailLower.includes(pattern3) || 
            emailLower.includes(pattern4)) {
          return true;
        }
      }
    }
    
    // Check for phrases like "I'm contacting YouTube about..."
    for (const company of commonCompanies) {
      if (company === companyNameLower) continue;
      
      const patterns = [
        `contacting ${company}`,
        `writing to ${company}`,
        `emailing ${company}`,
        `reaching out to ${company}`,
        `${company} account`,
        `${company} service`,
        `${company} platform`
      ];
      
      if (patterns.some(pattern => emailLower.includes(pattern))) {
        return true;
      }
    }
    
    return false;
  }

  // Load companies from database
  useEffect(() => {
    async function loadCompanies() {
      try {
        setLoadingCompanies(true);
        const data = await fetchCompanies();
        
        const mapped = data.map((c, index) => ({
          id: c.id ?? String(index),
          name: c.CompanyName,
          description: c.CompanyDescription,
          info: c.CompanyInfo,
        }));

        setCompanies(mapped);
        if (mapped.length > 0) {
          setSelectedId(mapped[0].id);
        }
      } catch (err) {
        console.error("Failed to load companies:", err);
        addToLog(`Error loading companies: ${err.message}`);
      } finally {
        setLoadingCompanies(false);
      }
    }

    loadCompanies();
  }, []);

  async function generateEmailWithOpenAI(company, context = null) {
    if (!openaiKey) {
      throw new Error("OpenAI API key is required");
    }

    let prompt;
    if (context) {
      // Check if email appears to be directed at a different company
      const isForOtherCompany = appearsToBeForOtherCompany(context, company.name);
      
      if (isForOtherCompany) {
        prompt = `You are a representative from ${company.name}. 

Company Information:
- Description: ${company.description || "Not specified"}
- About: ${company.info || "Not specified"}

You received the following email, but it appears to be intended for a different company or service. Please write a polite, professional response that:

1. Acknowledges the email was received
2. Gently points out that it seems to be directed at another company/service
3. Explains that you cannot help with this specific inquiry
4. Offers to assist with matters relevant to ${company.name}
5. Maintains a friendly, helpful tone

EMAIL TO RESPOND TO:
${context}

Please write a diplomatic response that helps the sender while clarifying the misunderstanding.`;
      } else {
        // Generate normal response to mock email
        prompt = `You are a representative from ${company.name}. 
        
Company Information:
- Description: ${company.description || "Not specified"}
- About: ${company.info || "Not specified"}

You received the following email. Please write a professional but friendly response:

EMAIL TO RESPOND TO:
${context}

Please write an appropriate response that reflects the company's professionalism and values.`;
      }
    } else {
      // Generate initial outreach email
      prompt = `Generate a business outreach email from ${company.name}. 

Company Information:
- Description: ${company.description || "Not specified"}
- About: ${company.info || "Not specified"}

The email should be professional but approachable, about 2-3 paragraphs long. It should introduce the company and its services in a way that matches the company description above.`;
    }

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
      addToLog(`Company description: ${selected.description || "Not available"}`);
      addToLog(`Company info: ${selected.info || "Not available"}`);
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
      addToLog(`Generated ${emailCount} emails for ${selected.name}`);
      
    } catch (error) {
      addToLog(`Error: ${error.message}`);
      addToLog("Make sure your OpenAI API key is valid and has credits");
    } finally {
      setRunning(false);
    }
  }

  // New function to generate response to mock email
  async function generateEmailResponse() {
    if (!selected || !mockEmail.trim()) {
      alert("Please select a company and enter a mock email first");
      return;
    }

    if (!openaiKey) {
      alert("Please enter your OpenAI API key first");
      return;
    }

    setGeneratingResponse(true);
    setEmailResponse("");

    try {
      const response = await generateEmailWithOpenAI(selected, mockEmail);
      setEmailResponse(response);
      addToLog(`Generated response for ${selected.name} to mock email`);
      
      // Check if it was detected as wrong company
      const isForOtherCompany = appearsToBeForOtherCompany(mockEmail, selected.name);
      if (isForOtherCompany) {
        addToLog(`Note: Email appears to be directed at a different company. Response will clarify this.`);
      }
    } catch (error) {
      console.error("Error generating response:", error);
      setEmailResponse(`Error: ${error.message}`);
    } finally {
      setGeneratingResponse(false);
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

  function clearMockEmail() {
    setMockEmail("");
    setEmailResponse("");
  }

  return (
    <div className={styles.wrap}>
      <section className={styles.listPane}>
        <h3>Companies from Database</h3>
        {loadingCompanies ? (
          <p>Loading companies...</p>
        ) : (
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
        )}
        {companies.length === 0 && !loadingCompanies && (
          <p>No companies in database</p>
        )}
      </section>

      <section className={styles.detailPane}>
        <h3>Email Testing</h3>
        
        {/* Selected Company Info */}
        {selected && (
          <div className={styles.companyInfo}>
            <h4>Selected: {selected.name}</h4>
            {selected.description && (
              <p><strong>Description:</strong> {selected.description}</p>
            )}
            {selected.info && (
              <p><strong>Info:</strong> {selected.info}</p>
            )}
          </div>
        )}

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

        {/* Email Response Section */}
        <div className={styles.section}>
          <h4>Email Response Test</h4>
          <div className={styles.mockEmailSection}>
            <label className={styles.textareaWrap}>
              <span>Mock Email to Respond To:</span>
              <textarea
                value={mockEmail}
                onChange={(e) => setMockEmail(e.target.value)}
                placeholder="Paste an email here that you want the AI to respond to..."
                rows={6}
              />
            </label>
            
            <div className={styles.responseActions}>
              <button
                className={styles.respondBtn}
                onClick={generateEmailResponse}
                disabled={generatingResponse || !selected || !mockEmail.trim() || !openaiKey}
              >
                {generatingResponse ? "Generating Response..." : "Generate Response"}
              </button>
              <button
                className={styles.clearBtn}
                onClick={clearMockEmail}
                disabled={generatingResponse}
              >
                Clear
              </button>
            </div>

            {emailResponse && (
              <div className={styles.responseOutput}>
                <h5>Generated Response:</h5>
                <div className={styles.responseContent}>
                  {emailResponse}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Bulk Email Generation Section */}
        <div className={styles.section}>
          <h4>Bulk Email Generation</h4>
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