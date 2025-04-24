import React from 'react';
import '../styles/ThemeToggle.css';

const ThemeToggle = ({ isDarkTheme, toggleTheme }) => {
  return (
    <div className="theme-toggle">
      <label className="switch">
        <input 
          type="checkbox" 
          checked={isDarkTheme}
          onChange={toggleTheme}
        />
        <span className="slider round">
          <div className="toggle-icons">
            <span className="moon">🌙</span>
            <span className="sun">☀️</span>
          </div>
        </span>
      </label>
    </div>
  );
};

export default ThemeToggle; 
