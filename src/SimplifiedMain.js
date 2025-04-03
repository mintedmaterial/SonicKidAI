// SimplifiedMain.js - A plain JavaScript entry point that doesn't use JSX syntax
// This helps avoid Vite's React plugin JSX detection issues

// Import React non-JSX style
import React from 'react';
import { createRoot } from 'react-dom/client';

// Log that the simplified main is running
console.log('[SimplifiedMain] Starting application in simplified mode');

// Function to dynamically import the real app
async function loadApp() {
  try {
    console.log('[SimplifiedMain] Attempting to load the main application');
    
    // Dynamically import the actual application
    // This separation helps avoid JSX detection issues at startup
    const { default: App } = await import('./App.tsx');
    
    // Standard React 18 rendering
    const container = document.getElementById('root');
    if (!container) {
      throw new Error('Root element not found');
    }
    
    const root = createRoot(container);
    root.render(React.createElement(App));
    
    console.log('[SimplifiedMain] Application loaded successfully');
  } catch (error) {
    console.error('[SimplifiedMain] Error loading application:', error);
    
    // Display a simple error message
    const container = document.getElementById('root');
    if (container) {
      container.innerHTML = `
        <div style="padding: 20px; font-family: system-ui, -apple-system, sans-serif;">
          <h2 style="color: #e11d48;">Application Error</h2>
          <p>Sorry, there was a problem loading the application.</p>
          <pre style="background: #f1f5f9; padding: 12px; border-radius: 4px; overflow: auto;">${error.message}</pre>
          <p>Please try reloading the page. If the problem persists, contact support.</p>
          <button onclick="window.location.reload()" style="background: #3b82f6; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer;">
            Reload Application
          </button>
        </div>
      `;
    }
  }
}

// Start loading the application
loadApp();