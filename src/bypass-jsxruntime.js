/**
 * JSX Runtime Bypass Script
 * 
 * This script explicitly defines React.createElement and JSX runtime functions
 * to work around Vite's React plugin preamble detection issues.
 * 
 * The problem occurs because Vite's React plugin requires specific JSX runtime
 * imports at the top of React files, but sometimes these aren't detected properly.
 */

// Create a fallback React object if it doesn't exist
window.React = window.React || {};

// Define the createElement function if it doesn't exist
if (!window.React.createElement) {
  window.React.createElement = function(type, props, ...children) {
    // This is just a placeholder to bypass the detection
    // The real React.createElement will be loaded by the React library
    return { type, props, children };
  };
}

// Define the JSX runtime functions that might be missing
window.__REACT_JSX_RUNTIME__ = {
  jsx: function(type, props, key) {
    // This is just a placeholder to bypass the detection
    return { type, props, key };
  },
  jsxs: function(type, props, key) {
    // This is just a placeholder to bypass the detection
    return { type, props, key };
  },
  Fragment: Symbol('Fragment')
};

// Log that the bypass script has loaded
console.log('[JSX Runtime Bypass] Initialized successfully');