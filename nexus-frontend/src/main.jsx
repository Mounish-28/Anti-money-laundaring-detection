import React, { StrictMode, Component } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'

class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('QuantumAML Nexus Caught Runtime Error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          minHeight: '100vh',
          backgroundColor: '#05070a',
          color: '#f1f5f9',
          fontFamily: 'monospace',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '24px',
          textAlign: 'center'
        }}>
          <div style={{
            maxWidth: '640px',
            backgroundColor: '#0b0f17',
            border: '1px solid #f43f5e',
            borderRadius: '16px',
            padding: '32px',
            boxShadow: '0 20px 25px -5px rgba(244, 63, 94, 0.2)'
          }}>
            <div style={{ fontSize: '40px', marginBottom: '16px' }}>🔴</div>
            <h1 style={{ fontSize: '20px', fontWeight: 'bold', color: '#fda4af', marginBottom: '8px' }}>
              QUANTUM AML NEXUS // RUNTIME RECOVERY
            </h1>
            <p style={{ fontSize: '13px', color: '#94a3b8', marginBottom: '20px' }}>
              The surveillance workspace intercepted an unexpected UI event.
            </p>
            <pre style={{
              backgroundColor: '#020408',
              padding: '12px',
              borderRadius: '8px',
              color: '#f87171',
              fontSize: '11px',
              overflowX: 'auto',
              textAlign: 'left',
              marginBottom: '24px',
              maxHeight: '140px'
            }}>
              {String(this.state.error?.message || this.state.error || 'Unknown Error')}
            </pre>
            <button
              onClick={() => {
                this.setState({ hasError: false, error: null });
                window.location.reload();
              }}
              style={{
                backgroundColor: '#e11d48',
                color: '#ffffff',
                border: 'none',
                borderRadius: '10px',
                padding: '10px 24px',
                fontSize: '13px',
                fontWeight: 'bold',
                cursor: 'pointer'
              }}
            >
              Reload Surveillance Console
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </StrictMode>,
)
