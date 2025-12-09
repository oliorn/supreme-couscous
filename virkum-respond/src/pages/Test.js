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

  const [logEnabled, setLogEnabled] = useState(true);
  const [log, setLog] = useState("");
  const [running, setRunning] = useState(false);
  const [openaiKey, setOpenaiKey] = useState("");
  
  // State for email response feature
  const [mockEmail, setMockEmail] = useState("");
  const [emailSubject, setEmailSubject] = useState("");
  const [emailResponse, setEmailResponse] = useState("");
  const [generatingResponse, setGeneratingResponse] = useState(false);
  const [sendingEmail, setSendingEmail] = useState(false);
  const [recipientEmail, setRecipientEmail] = useState("");
  const [autoSend, setAutoSend] = useState(true);
  const [generatedSubject, setGeneratedSubject] = useState("");
  const [generatedBody, setGeneratedBody] = useState("");
  const [generatedGrade, setGeneratedGrade] = useState(null);


  const [numRequests, setNumRequests] = useState(10);
  const [isTesting, setIsTesting] = useState(false);
  const [useRandomCompany, setUseRandomCompany] = useState(false);
  const [selectedConcurrency, setSelectedConcurrency] = useState(1);

  // Helper function to detect if email is for a different company
  function appearsToBeForOtherCompany(emailText, companyName) {
    const emailLower = emailText.toLowerCase();
    const companyNameLower = companyName.toLowerCase();
    
    const recipientGreetings = [
      "dear", "to", "hello", "hi", "greetings", "attn:", "attention:",
      "for the attention of", "re:", "subject:", "query for"
    ];
    
    const commonCompanies = [
      "youtube", "google", "netflix", "amazon", "apple", "microsoft",
      "facebook", "twitter", "instagram", "linkedin", "spotify",
      "uber", "airbnb", "tesla", "nike", "adidas", "starbucks"
    ];
    
    for (const greeting of recipientGreetings) {
      for (const company of commonCompanies) {
        if (company === companyNameLower) continue;
        
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

  // Function to extract subject from mock email
  function extractSubjectFromMockEmail(emailText) {
    if (!emailText) return "";
    
    // Look for common subject patterns
    const lines = emailText.split('\n');
    for (let i = 0; i < Math.min(lines.length, 5); i++) {
      const line = lines[i].trim();
      
      // Check for "Subject:" pattern
      if (line.toLowerCase().startsWith('subject:')) {
        return line.substring(8).trim();
      }
      
      // Check for "Re:" pattern (reply)
      if (line.toLowerCase().startsWith('re:')) {
        return line.trim();
      }
      
      // Check for lines that look like subjects (not too long, not greetings)
      if (line.length > 0 && line.length < 100 && 
          !line.toLowerCase().includes('dear') &&
          !line.toLowerCase().includes('hello') &&
          !line.toLowerCase().includes('hi ') &&
          !line.toLowerCase().includes('to ') &&
          !line.toLowerCase().includes('attn:')) {
        return line;
      }
    }
    
    return "";
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

  // Auto-extract subject when mock email changes
  useEffect(() => {
    if (mockEmail.trim()) {
      const extractedSubject = extractSubjectFromMockEmail(mockEmail);
      if (extractedSubject) {
        setEmailSubject(extractedSubject);
      } else {
        // Generate a default subject
        setEmailSubject(`Regarding your message`);
      }
    } else {
      setEmailSubject("");
    }
  }, [mockEmail]);

  async function generateEmailWithOpenAI(company, context = null) {
    if (!openaiKey) {
      throw new Error("OpenAI API key is required");
    }

    let prompt;
    if (context) {
      const isForOtherCompany = appearsToBeForOtherCompany(context, company.name);
      
      if (isForOtherCompany) {
        prompt = `You are a representative from ${company.name}. 

You received the following email, but it appears to be intended for a different company or service. Please write a polite, professional response that:

1. Acknowledges the email was received
2. Gently points out that it seems to be directed at another company/service
3. Explains that you cannot help with this specific inquiry
4. Offers to assist with matters relevant to ${company.name}
5. Maintains a friendly, helpful tone

IMPORTANT: 
- Do NOT use placeholders like [Your Name], [Your Company Name], [Your Title], etc.
- Do NOT include company description or "Company Information" sections in the email
- If you need to sign the email, use a professional signature like "Best regards" or "Sincerely"
- Write as if you are an actual employee of ${company.name}
- The response should be natural and human-like, not formulaic
- Only write the email body, no subject line needed

EMAIL TO RESPOND TO:
${context}

Please write a diplomatic response that helps the sender while clarifying the misunderstanding.`;
      } else {
        prompt = `You are a representative from ${company.name}. 

You received the following email. Please write a professional but friendly response:

IMPORTANT: 
- Do NOT use placeholders like [Your Name], [Your Company Name], [Your Title], etc.
- Do NOT include company description or "Company Information" sections in the email
- If you need to sign the email, use a professional signature like "Best regards" or "Sincerely"
- Write as if you are an actual employee of ${company.name}
- The response should be natural and human-like, not formulaic
- Only write the email body, no subject line needed

EMAIL TO RESPOND TO:
${context}

Please write an appropriate response that reflects the company's professionalism and values.`;
      }
    } else {
      prompt = `Generate a business outreach email from ${company.name}. 

IMPORTANT: 
- Do NOT use placeholders like [Your Name], [Your Company Name], [Your Title], etc.
- Do NOT include company description or "Company Information" sections in the email
- The email should be written as if coming from an actual representative of ${company.name}
- If you need to include a name, use a realistic name or just use a professional signature without a specific name
- The email should be professional but approachable, about 2-3 paragraphs long.
- It should introduce the company and its services naturally in the flow of the email
- Make it sound like a human wrote it, not an AI.
- Only write the email body, no subject line needed`;
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
        temperature: 0.8,
      }),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(`OpenAI API error: ${errorData.error?.message || 'Unknown error'}`);
    }

    const data = await response.json();
    let emailContent = data.choices[0].message.content;
    
    // Clean up any remaining placeholders that might have slipped through
    emailContent = cleanEmailContent(emailContent, company.name);
    
    return emailContent;
  }

  // Function to clean up placeholders in email content
  function cleanEmailContent(content, companyName) {
    // Remove common placeholders
    const placeholders = [
      /\[Your Name\]/gi,
      /\[Your Company Name\]/gi,
      /\[Company Name\]/gi,
      /\[Your Title\]/gi,
      /\[Your Position\]/gi,
      /\[Your Role\]/gi,
      /\[Date\]/gi,
      /\[Recipient's Name\]/gi,
      /\[Specific details about the recipient's business\]/gi,
      /\[Your Contact Information\]/gi,
      /company information:/gi,
      /company description:/gi,
      /about the company:/gi
    ];
    
    let cleaned = content;
    placeholders.forEach(pattern => {
      cleaned = cleaned.replace(pattern, '');
    });
    
    // Replace [Your Name] with professional signature
    if (cleaned.includes('[Your Name]')) {
      cleaned = cleaned.replace(/\[Your Name\]/gi, `Best regards,\nThe ${companyName} Team`);
    }
    
    // Remove any double line breaks caused by placeholder removal
    cleaned = cleaned.replace(/\n\s*\n\s*\n/g, '\n\n');
    
    // Trim extra whitespace
    cleaned = cleaned.trim();
    
    return cleaned;
  }

  // Function to generate appropriate subject
  function generateEmailSubject() {
    if (!emailSubject.trim()) {
      if (selected) {
        return `Message from ${selected.name}`;
      }
      return "Response to your inquiry";
    }
    
    // If subject doesn't start with Re:, add it for replies
    const cleanSubject = emailSubject.trim();
    if (!cleanSubject.toLowerCase().startsWith('re:') && 
        !cleanSubject.toLowerCase().startsWith('fw:')) {
      return `Re: ${cleanSubject}`;
    }
    
    return cleanSubject;
  }

  // Function to send actual email via FastAPI backend
  async function sendGeneratedEmail(emailContent) {
    if (!recipientEmail) {
      alert("Please enter a recipient email address first");
      return { success: false, error: "No recipient email" };
    }

    if (!selected) {
      alert("Please select a company first");
      return { success: false, error: "No company selected" };
    }

    setSendingEmail(true);
    
    try {
      addToLog(`Sending email to: ${recipientEmail}`);
      addToLog(`Subject: ${generateEmailSubject()}`);
      addToLog("Connecting to email server...");

      // Call FastAPI backend to send email
      const response = await fetch('https://backend-737530900569.europe-west2.run.app/send-email', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          to: recipientEmail,
          subject: generateEmailSubject(),
          content: emailContent,
          company_name: selected.name,
          company_description: "", // Empty to not include in email
          company_info: "" // Empty to not include in email
        }),
      });

      const result = await response.json();

      if (result.success) {
        addToLog(`✅ Email sent successfully to ${recipientEmail}`);
        return { success: true, message: result.message };
      } else {
        throw new Error(result.error || 'Failed to send email');
      }
    } catch (error) {
      console.error("Error sending email:", error);
      addToLog(`❌ Error sending email: ${error.message}`);
      return { success: false, error: error.message };
    } finally {
      setSendingEmail(false);
    }
  }

  // Function to generate email response and optionally send it
  async function generateEmailResponse() {
    if (!selected || !mockEmail.trim()) {
      alert("Please select a company and enter a mock email first");
      return;
    }

    // openaiKey er ekki lengur notað á frontend
    if (autoSend && !recipientEmail) {
      alert("Auto-send is enabled. Please enter a recipient email address");
      return;
    }

    setGeneratingResponse(true);
    setEmailResponse("");

    try {
      addToLog(`Generating response for ${selected.name}...`);

      // 1) Kalla á backend: /manual-generate
      const resp = await fetch("https://backend-737530900569.europe-west2.run.app/manual-generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          company_name: selected.name,
          to: recipientEmail || "test@example.com", // notað bara sem metadata
          input_email: mockEmail,
        }),
      });

      if (!resp.ok) {
        const text = await resp.text();
        throw new Error(`HTTP ${resp.status}: ${text}`);
      }

      const data = await resp.json();
      const body = data.generated_body || "";
      const subject = data.generated_subject || "";
      const grade = data.grade;

      // birtum svarið í UI
      setEmailResponse(body);

      // logg um gæði + test
      const gradeText =
        grade != null ? (grade * 10).toFixed(1) + " %" : "N/A";
      addToLog(
        `✅ Response generated for ${selected.name} (grade: ${gradeText})`
      );

      if (data.test_summary?.test_id) {
        addToLog(
          `Stored as Test #${data.test_summary.test_id} in history (1 email, concurrency 1).`
        );
      }

      const isForOtherCompany = appearsToBeForOtherCompany(
        mockEmail,
        selected.name
      );
      if (isForOtherCompany) {
        addToLog(
          `Note: Email appears to be directed at a different company. Response will clarify this.`
        );
      }

      // 2) Ef auto-send er virkt → kalla á /send-email
      if (autoSend && recipientEmail && body) {
        addToLog(`Auto-sending email to ${recipientEmail}...`);

        const sendResp = await fetch("https://backend-737530900569.europe-west2.run.app/send-email", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            to: recipientEmail,
            subject: subject || "Response",
            content: body,
            company_name: selected.name,
          }),
        });

        if (!sendResp.ok) {
          const text = await sendResp.text();
          addToLog(
            `⚠️ Generated response ready, but email sending failed: HTTP ${sendResp.status}: ${text}`
          );
        } else {
          const sendData = await sendResp.json();
          if (sendData.success) {
            addToLog(`✅ Email successfully sent to ${recipientEmail}`);
          } else {
            addToLog(
              `⚠️ Generated response ready, but email sending failed: ${
                sendData.error || "Unknown error"
              }`
            );
          }
        }
      } else if (!autoSend) {
        addToLog(
          "✅ Response generated and stored (EmailTestRuns/tests). Auto-send is disabled."
        );
      }
    } catch (error) {
      console.error("Error generating response:", error);
      setEmailResponse(`Error: ${error.message}`);
      addToLog(`❌ Error generating response: ${error.message}`);
    } finally {
      setGeneratingResponse(false);
    }
  }


  // Manual send function for when auto-send is disabled
  async function sendEmailManually() {
    if (!emailResponse) {
      alert("No email response generated yet");
      return;
    }

    if (!recipientEmail) {
      alert("Please enter a recipient email address");
      return;
    }

    const sendResult = await sendGeneratedEmail(emailResponse);
    
    if (sendResult.success) {
      alert(`Email sent successfully to ${recipientEmail}`);
    } else {
      alert(`Failed to send email: ${sendResult.error}`);
    }
  }

  async function runSimulatedTest() {
  if (!useRandomCompany && !selected) {
    alert("Please select a company or enable Random company");
    return;
  }
  if (!recipientEmail) {
    alert("Settu inn móttakanda (recipient email) fyrst");
    return;
  }
  if (numRequests <= 0) {
    alert("Number of requests must be > 0");
    return;
  }

  setIsTesting(true);
  addToLog(
    `Starting simulated test for ${
      useRandomCompany ? "RANDOM companies" : selected.name
    } (${numRequests} requests, concurrency ${selectedConcurrency})...`
  );

  try {
    // Build payload for /run-simulated-test
    const payload = {
      num_emails: numRequests,
      concurrency_level: selectedConcurrency,       // e.g. 1, 5, 10…
      to: recipientEmail,
    };

    // Only send company_name if *not* random
    if (!useRandomCompany && selected?.name) {
      payload.company_name = selected.name;
    }

    const resp = await fetch("https://backend-737530900569.europe-west2.run.app/run-simulated-test", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!resp.ok) {
      const text = await resp.text();
      throw new Error(`HTTP ${resp.status}: ${text}`);
    }

    const summary = await resp.json();

    const companies = Array.isArray(summary.companies)
      ? summary.companies.join(", ")
      : "N/A";

    // avg_reply_grade is 0–10 in your backend; *10 → percent
    const avgGrade =
      summary.avg_reply_grade != null
        ? (summary.avg_reply_grade * 10).toFixed(1) + " %"
        : "N/A";

    addToLog(
      `✅ Batch Test #${summary.test_id} created – companies: ${companies}, ` +
        `total_requests: ${summary.total_requests}, ` +
        `concurrency: ${summary.concurrency_level}, avg grade: ${avgGrade}`
    );

    // If you want, you can also log run_ids if you return them from backend:
    // addToLog(`Run IDs: ${summary.run_ids.join(", ")}`);

    // Optionally refresh your History view here if this page owns that:
    // await loadHistory();

  } catch (err) {
    console.error(err);
    addToLog(`❌ Error during simulated test: ${err.message}`);
  } finally {
    setIsTesting(false);
  }
}


  

  function addToLog(message) {
    if (logEnabled) {
      setLog(prev => prev + message + "\n\n");
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
    setEmailSubject("");
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
        <h3>Email Response System</h3>
        
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
            Your API key is used only for this session and is not stored
          </small>
        </div>

        {/* Recipient Email and Auto-send Settings */}
        <div className={styles.section}>
          <h4>Email Settings</h4>
          <div className={styles.grid}>
            <Input 
              label="Recipient Email" 
              value={recipientEmail} 
              onChange={setRecipientEmail} 
              type="email"
              placeholder="recipient@gmail.com"
              required={autoSend}
            />
            
            
            <label className={styles.checkRow}>
              <input 
                type="checkbox" 
                checked={autoSend} 
                onChange={(e) => setAutoSend(e.target.checked)} 
              />
              <span>Auto-send email when generated</span>
            </label>
            
            <small className={styles.helperText}>
              {autoSend ? 
                "Emails will be sent automatically after generation" : 
                "You'll need to manually send emails after generation"}
            </small>
          </div>
        </div>

        {/* Email Response Section */}
        <div className={styles.section}>
          <h4>Generate Email Response</h4>
          <div className={styles.mockEmailSection}>
            <label className={styles.textareaWrap}>
              <span>Mock Email to Respond To:</span>
              <textarea
                value={mockEmail}
                onChange={(e) => setMockEmail(e.target.value)}
                placeholder="Paste or type the email you want to respond to...
                
                          Example:
                          Subject: Inquiry about your services
                          Dear Team,

                          I'm interested in learning more about your products..."

                rows={8}
              />
              <small className={styles.helperText}>
                Tip: Include "Subject:" on the first line for better results
              </small>
            </label>
            
            <div className={styles.responseActions}>
              <button
                className={styles.respondBtn}
                onClick={generateEmailResponse}
                disabled={generatingResponse || !selected || !mockEmail.trim() || (autoSend && !recipientEmail)}
              >
                {generatingResponse ? "Generating Response..." : "Generate & Send Response"}
              </button>
              
              {!autoSend && emailResponse && (
                <button
                  className={styles.sendBtn}
                  onClick={sendEmailManually}
                  disabled={sendingEmail || !recipientEmail}
                >
                  {sendingEmail ? "Sending..." : "Send Email"}
                </button>
              )}
              
              <button
                className={styles.clearBtn}
                onClick={clearMockEmail}
                disabled={generatingResponse || sendingEmail}
              >
                Clear
              </button>
            </div>

            {emailResponse && (
              <div className={styles.responseOutput}>
                <div className={styles.responseHeader}>
                  <h5>Generated Response</h5>
                  <div className={styles.subjectPreview}>
                    <strong>Subject:</strong> {generateEmailSubject()}
                  </div>
                </div>
                <div className={styles.responseContent}>
                  {emailResponse}
                </div>
                <div className={styles.responseMeta}>
                  <small>
                    {autoSend && recipientEmail ? 
                      `This email was ${sendingEmail ? 'being sent' : 'sent'} to ${recipientEmail}` : 
                      "Ready to send. Click 'Send Email' above."}
                  </small>
                </div>
              </div>
            )}
          </div>
        </div>
        {/* Simulated Load Test */}
        <div className={styles.section}>
          <h4>Simulated Load Test</h4>
          <div className={styles.grid}>
            <Input
              label="Number of requests"
              type="number"
              value={numRequests}
              onChange={(v) => setNumRequests(Number(v) || 0)}
            />
            <Input
              label="Concurrency level"
              type="number"
              min={1}
              max={50}
              value={selectedConcurrency}
              onChange={(v) => setSelectedConcurrency(Number(v) || 1)}
            />

            <label className={styles.checkRow}>
              <input
                type="checkbox"
                checked={useRandomCompany}
                onChange={(e) => setUseRandomCompany(e.target.checked)}
              />
              <span>Use random company for each request</span>
            </label>

            <button
              className={styles.respondBtn}
              onClick={runSimulatedTest}
              disabled={isTesting || (!useRandomCompany && !selected) || !recipientEmail}
            >
              {isTesting ? "Running test..." : "Run simulated test"}
            </button>
          </div>

          <small className={styles.helperText}>
            This will call /simulate-email on the backend and log latency for each
            request. If "Use random company" is checked, the backend will pick a random
            company from the database each time.
          </small>
        </div>
        <label>Concurrency level</label>
        



        {/* Log Settings and Output */}
        <div className={styles.section}>
          <div className={styles.logHeader}>
            <h4>Activity Log</h4>
            <label className={styles.checkRow}>
              <input 
                type="checkbox" 
                checked={logEnabled} 
                onChange={(e) => setLogEnabled(e.target.checked)} 
              />
              <span>Enable Log</span>
            </label>
          </div>
          
          <div className={styles.logActions}>
            <button 
              className={styles.clearBtn} 
              onClick={clearLog}
              disabled={generatingResponse || sendingEmail}
            >
              Clear Log
            </button>
          </div>
          
          <div className={styles.logBox}>
            <pre>{log || "Activity log will appear here..."}</pre>
          </div>
          
          <small className={styles.helperText}>
            Log shows email generation and sending activity
          </small>
        </div>
      </section>
    </div>
  );
}