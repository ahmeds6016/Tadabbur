/* Enhanced Tafsir Application Styles */

:root {
  --background: #ffffff;
  --foreground: #171717;
  --primary-color: #4a90e2;
  --secondary-color: #eaf1fd;
  --error-color: #ff4d4f;
  --success-color: #52c41a;
  --warning-color: #faad14;
  --border-color: #d1d5db;
  --shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06);
  --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
  --shadow-xl: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
  --gradient-primary: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  --gradient-secondary: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
  --gradient-success: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%);
}

@media (prefers-color-scheme: dark) {
  :root {
    --background: #0a0a0a;
    --foreground: #ededed;
    --secondary-color: #1a1a1a;
    --border-color: #374151;
    --primary-color: #6bb6ff;
  }
}

/* Base Styles */
html, body {
  max-width: 100vw;
  overflow-x: hidden;
  scroll-behavior: smooth;
}

body {
  color: var(--foreground);
  background: var(--background);
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 
               'Oxygen', 'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 
               'Helvetica Neue', sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  line-height: 1.6;
  font-size: 16px;
}

* {
  box-sizing: border-box;
  padding: 0;
  margin: 0;
}

a {
  color: inherit;
  text-decoration: none;
}

/* Container and Cards */
.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
  animation: fadeIn 0.6s ease-out;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

.card {
  background: var(--background);
  border-radius: 16px;
  padding: 32px;
  box-shadow: var(--shadow-lg);
  border: 1px solid var(--border-color);
  margin-bottom: 24px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
}

.card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: var(--gradient-primary);
  transform: scaleX(0);
  transition: transform 0.3s ease;
}

.card:hover::before {
  transform: scaleX(1);
}

.card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-xl);
}

.main-app {
  max-width: none;
  padding: 40px;
}

/* Header Enhancements */
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 40px;
  padding-bottom: 24px;
  border-bottom: 2px solid var(--border-color);
  position: relative;
}

.header::after {
  content: '';
  position: absolute;
  bottom: -2px;
  left: 0;
  width: 100px;
  height: 2px;
  background: var(--gradient-primary);
}

.header h1 {
  font-size: 2.5rem;
  font-weight: 800;
  background: var(--gradient-primary);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin: 0;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 16px;
  font-size: 14px;
  color: #666;
  background: var(--secondary-color);
  padding: 12px 20px;
  border-radius: 25px;
  border: 1px solid var(--border-color);
}

/* Suggestions Section */
.suggestions-section {
  margin-bottom: 32px;
}

.suggestions-toggle {
  background: var(--secondary-color);
  border: 2px solid var(--border-color);
  border-radius: 12px;
  padding: 12px 20px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
  color: var(--primary-color);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
}

.suggestions-toggle::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,0.4), transparent);
  transition: left 0.5s;
}

.suggestions-toggle:hover::before {
  left: 100%;
}

.suggestions-toggle:hover {
  background: var(--primary-color);
  color: white;
  transform: translateY(-2px);
  box-shadow: var(--shadow-lg);
}

.suggestions-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 12px;
  margin-top: 20px;
  padding: 24px;
  background: linear-gradient(135deg, var(--secondary-color) 0%, rgba(74, 144, 226, 0.05) 100%);
  border-radius: 16px;
  border: 1px solid var(--border-color);
  animation: slideDown 0.4s ease-out;
}

@keyframes slideDown {
  from { opacity: 0; transform: translateY(-10px); }
  to { opacity: 1; transform: translateY(0); }
}

.suggestion-chip {
  background: white;
  border: 2px solid var(--border-color);
  border-radius: 25px;
  padding: 10px 16px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  text-align: center;
  position: relative;
  overflow: hidden;
}

.suggestion-chip::before {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  width: 0;
  height: 0;
  background: var(--primary-color);
  border-radius: 50%;
  transform: translate(-50%, -50%);
  transition: all 0.3s ease;
  z-index: 0;
}

.suggestion-chip:hover::before {
  width: 200%;
  height: 200%;
}

.suggestion-chip:hover {
  color: white;
  transform: translateY(-3px);
  box-shadow: var(--shadow-lg);
  border-color: var(--primary-color);
}

.suggestion-chip span {
  position: relative;
  z-index: 1;
}

/* Enhanced Form Styling */
.form {
  margin-bottom: 24px;
}

.tafsir-form {
  display: flex;
  gap: 16px;
  margin-bottom: 32px;
  flex-wrap: wrap;
  align-items: stretch;
}

.tafsir-form select,
.tafsir-form input {
  padding: 16px 20px;
  border: 2px solid var(--border-color);
  border-radius: 12px;
  font-size: 16px;
  font-weight: 500;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  background: var(--background);
  color: var(--foreground);
}

.tafsir-form input {
  flex: 1;
  min-width: 320px;
}

.tafsir-form select:focus,
.tafsir-form input:focus {
  outline: none;
  border-color: var(--primary-color);
  box-shadow: 0 0 0 4px rgba(74, 144, 226, 0.1);
  transform: translateY(-1px);
}

.tafsir-form button {
  background: var(--gradient-primary);
  color: white;
  border: none;
  border-radius: 12px;
  padding: 16px 32px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
  min-width: 140px;
}

.tafsir-form button::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent);
  transition: left 0.5s;
}

.tafsir-form button:hover:not(:disabled)::before {
  left: 100%;
}

.tafsir-form button:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: var(--shadow-xl);
}

.tafsir-form button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

/* Enhanced Buttons */
button {
  background: var(--primary-color);
  color: white;
  border: none;
  border-radius: 8px;
  padding: 12px 24px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
}

button:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: var(--shadow-lg);
}

.logout-button {
  background: var(--gradient-secondary);
  font-size: 13px;
  padding: 8px 16px;
  border-radius: 20px;
}

.toggle-auth {
  background: transparent;
  color: var(--primary-color);
  border: 2px solid var(--primary-color);
  margin-top: 16px;
}

.toggle-auth:hover {
  background: var(--primary-color);
  color: white;
}

/* Loading States */
.loading-spinner {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 40px;
}

.loading-spinner::after {
  content: '';
  width: 40px;
  height: 40px;
  border: 4px solid var(--border-color);
  border-top: 4px solid var(--primary-color);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* Alert States */
.error {
  color: var(--error-color);
  background: rgba(255, 77, 79, 0.1);
  border: 1px solid var(--error-color);
  border-radius: 8px;
  padding: 12px 16px;
  margin: 16px 0;
  font-weight: 500;
}

.rate-limit-warning {
  background: rgba(250, 173, 20, 0.1);
  border: 1px solid var(--warning-color);
  color: var(--warning-color);
  border-radius: 12px;
  padding: 16px 20px;
  margin: 20px 0;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
}

/* Onboarding Styles */
.level-buttons {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
  margin: 24px 0;
}

.level-buttons button {
  padding: 20px 24px;
  font-size: 16px;
  font-weight: 600;
  border-radius: 12px;
  background: var(--secondary-color);
  color: var(--foreground);
  border: 2px solid var(--border-color);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.level-buttons button:hover {
  background: var(--primary-color);
  color: white;
  transform: translateY(-3px);
  box-shadow: var(--shadow-lg);
}

/* Results Display */
.results-container {
  margin-top: 32px;
  animation: fadeInUp 0.6s ease-out;
}

@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(30px); }
  to { opacity: 1; transform: translateY(0); }
}

.result-section {
  margin-bottom: 40px;
  padding: 32px;
  background: linear-gradient(135deg, rgba(74, 144, 226, 0.02) 0%, rgba(74, 144, 226, 0.05) 100%);
  border-radius: 16px;
  border: 1px solid var(--border-color);
  position: relative;
}

.result-section::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 4px;
  height: 100%;
  background: var(--gradient-primary);
  border-radius: 4px;
}

.result-section h2 {
  color: var(--primary-color);
  font-size: 1.5rem;
  font-weight: 700;
  margin-bottom: 24px;
  padding-bottom: 12px;
  border-bottom: 2px solid var(--border-color);
  position: relative;
}

.result-section h2::after {
  content: '';
  position: absolute;
  bottom: -2px;
  left: 0;
  width: 60px;
  height: 2px;
  background: var(--gradient-primary);
}

/* Verse Cards */
.verse-card {
  background: white;
  border-radius: 12px;
  padding: 24px;
  margin-bottom: 20px;
  box-shadow: var(--shadow);
  border: 1px solid var(--border-color);
  transition: all 0.3s ease;
}

.verse-card.enhanced {
  background: linear-gradient(135deg, #ffffff 0%, rgba(74, 144, 226, 0.02) 100%);
  border-left: 4px solid var(--primary-color);
}

.verse-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-lg);
}

.verse-ref {
  font-size: 1.1rem;
  color: var(--primary-color);
  margin-bottom: 16px;
}

.arabic-text {
  font-size: 1.8rem;
  line-height: 1.8;
  margin: 20px 0;
  padding: 20px;
  background: rgba(74, 144, 226, 0.05);
  border-radius: 12px;
  text-align: center;
  font-family: 'Amiri', 'Scheherazade New', serif;
  border: 1px solid rgba(74, 144, 226, 0.1);
}

.translation {
  font-style: italic;
  font-size: 1.1rem;
  line-height: 1.7;
  color: #555;
  padding: 16px;
  background: rgba(0, 0, 0, 0.02);
  border-radius: 8px;
  border-left: 4px solid var(--primary-color);
}

/* Tafsir Explanations */
.tafsir-details {
  margin-bottom: 24px;
  border: 1px solid var(--border-color);
  border-radius: 12px;
  background: white;
  overflow: hidden;
  transition: all 0.3s ease;
}

.tafsir-details.enhanced {
  box-shadow: var(--shadow);
}

.tafsir-details:hover {
  box-shadow: var(--shadow-lg);
}

.tafsir-details summary {
  padding: 20px 24px;
  cursor: pointer;
  background: var(--secondary-color);
  font-weight: 600;
  font-size: 1.1rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  transition: all 0.3s ease;
  border-bottom: 1px solid var(--border-color);
}

.tafsir-details summary:hover {
  background: rgba(74, 144, 226, 0.1);
  color: var(--primary-color);
}

.tafsir-details[open] summary {
  background: var(--primary-color);
  color: white;
}

.limited-content-badge {
  background: var(--warning-color);
  color: white;
  font-size: 11px;
  padding: 4px 8px;
  border-radius: 12px;
  font-weight: 600;
  margin-left: 12px;
}

.explanation-content {
  padding: 24px;
  line-height: 1.8;
  background: white;
}

.explanation-content p {
  margin-bottom: 16px;
}

/* Cross References */
.cross-references {
  display: grid;
  gap: 16px;
}

.cross-ref-item {
  padding: 16px 20px;
  background: white;
  border-radius: 10px;
  border: 1px solid var(--border-color);
  border-left: 4px solid var(--primary-color);
  transition: all 0.3s ease;
}

.cross-ref-item:hover {
  transform: translateX(4px);
  box-shadow: var(--shadow);
}

/* Lessons List */
.lessons-list {
  list-style: none;
  padding: 0;
}

.lesson-item {
  padding: 16px 20px;
  margin-bottom: 12px;
  background: white;
  border-radius: 10px;
  border: 1px solid var(--border-color);
  border-left: 4px solid var(--success-color);
  position: relative;
  transition: all 0.3s ease;
}

.lesson-item::before {
  content: '✓';
  position: absolute;
  left: -12px;
  top: 50%;
  transform: translateY(-50%);
  background: var(--success-color);
  color: white;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: bold;
}

.lesson-item:hover {
  transform: translateX(4px);
  box-shadow: var(--shadow);
}

/* Summary */
.summary-content {
  background: linear-gradient(135deg, rgba(74, 144, 226, 0.05) 0%, rgba(116, 75, 162, 0.05) 100%);
  border-radius: 12px;
  padding: 24px;
  border: 1px solid var(--border-color);
  font-size: 1.1rem;
  line-height: 1.8;
}

/* Export Section */
.export-section {
  margin-top: 40px;
  padding: 32px;
  background: var(--secondary-color);
  border-radius: 16px;
  border: 1px solid var(--border-color);
}

.export-section h3 {
  color: var(--primary-color);
  margin-bottom: 20px;
  font-size: 1.3rem;
}

.export-controls {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}

.export-btn {
  background: var(--gradient-success);
  padding: 12px 20px;
  border-radius: 10px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: all 0.3s ease;
}

.export-btn:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-lg);
}

/* Responsive Design */
@media (max-width: 768px) {
  .container {
    padding: 16px;
  }
  
  .card {
    padding: 20px;
    margin-bottom: 16px;
  }
  
  .main-app {
    padding: 24px;
  }
  
  .header {
    flex-direction: column;
    gap: 16px;
    text-align: center;
  }
  
  .header h1 {
    font-size: 2rem;
  }
  
  .tafsir-form {
    flex-direction: column;
    gap: 12px;
  }
  
  .tafsir-form input {
    min-width: auto;
  }
  
  .suggestions-grid {
    grid-template-columns: repeat(auto-fit, minmax(100px, 1fr));
    gap: 8px;
    padding: 16px;
  }
  
  .level-buttons {
    grid-template-columns: 1fr;
    gap: 12px;
  }
  
  .export-controls {
    flex-direction: column;
  }
  
  .arabic-text {
    font-size: 1.4rem;
    padding: 16px;
  }
}

@media (max-width: 480px) {
  .header h1 {
    font-size: 1.8rem;
  }
  
  .result-section {
    padding: 20px;
  }
  
  .verse-card {
    padding: 16px;
  }
  
  .arabic-text {
    font-size: 1.2rem;
  }
}

/* Accessibility Improvements */
@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}

/* Focus Styles for Accessibility */
button:focus-visible,
input:focus-visible,
select:focus-visible,
summary:focus-visible {
  outline: 2px solid var(--primary-color);
  outline-offset: 2px;
}

/* Print Styles */
@media print {
  .suggestions-section,
  .export-section,
  .header .user-info,
  button {
    display: none !important;
  }
  
  .card {
    box-shadow: none;
    border: 1px solid #ccc;
  }
  
  .result-section {
    break-inside: avoid;
    page-break-inside: avoid;
  }
}
