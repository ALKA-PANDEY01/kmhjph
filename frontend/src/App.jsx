import { useState, useEffect } from 'react';
import DecisionView from './components/DecisionView';
import AccuracyView from './components/AccuracyView';
import { api } from './services/api';
import './App.css';

function App() {
  const [activeView, setActiveView] = useState('decision');
  const [health, setHealth] = useState(null);
  const [healthError, setHealthError] = useState(null);

  useEffect(() => {
    checkHealth();
  }, []);

  async function checkHealth() {
    try {
      const data = await api.getHealth();
      setHealth(data);
      setHealthError(null);
    } catch (err) {
      setHealthError(err.message);
    }
  }

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-content">
          <div className="brand">
            <h1>🌬️ UK Wind Forecast Accuracy</h1>
            <p className="brand-subtitle">Elexon BMRS • January 2026</p>
          </div>
          
          <div className="health-status">
            {healthError ? (
              <span className="status-badge error" title={healthError}>
                ⚠️ API Offline
              </span>
            ) : health ? (
              <span className="status-badge success" title={`${health.records_loaded} records loaded`}>
                ✓ Connected
              </span>
            ) : (
              <span className="status-badge loading">Connecting...</span>
            )}
          </div>
        </div>

        <nav className="nav-tabs">
          <button
            className={`nav-tab ${activeView === 'decision' ? 'active' : ''}`}
            onClick={() => setActiveView('decision')}
          >
            Decision View
          </button>
          <button
            className={`nav-tab ${activeView === 'accuracy' ? 'active' : ''}`}
            onClick={() => setActiveView('accuracy')}
          >
            Accuracy Analysis
          </button>
        </nav>
      </header>

      <main className="app-main">
        {activeView === 'decision' ? <DecisionView /> : <AccuracyView />}
      </main>

      <footer className="app-footer">
        <p>
          Data source: Elexon BMRS API (FUELHH + WINDFOR) • 
          Decision cutoff: 09:00 Europe/London D-1 •
          Built with React + FastAPI
        </p>
      </footer>
    </div>
  );
}

export default App;
