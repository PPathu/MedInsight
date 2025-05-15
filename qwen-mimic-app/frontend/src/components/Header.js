import React, { useState, useEffect } from 'react';
import { getActiveCriteria } from '../api';

const Header = ({ toggleDebugPanel, showDebugPanel, toggleCriteriaModal, forceUpdate, downloadChatHistory, useSqlRetriever, toggleSqlRetriever }) => {
    const [activeCriteria, setActiveCriteria] = useState(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchActiveCriteria = async () => {
            try {
                setIsLoading(true);
                console.log("Header: Fetching active criteria...", Date.now());
                
                // Add cache-busting parameter to avoid browser caching
                const timestamp = Date.now();
                const criteria = await getActiveCriteria(timestamp);
                
                console.log("Header: Received active criteria:", criteria);
                
                if (criteria && criteria.name) {
                    console.log(`Header: Successfully fetched criteria: ${criteria.name}`);
                    document.title = `Qwen Medical - ${criteria.name}`;
                } else {
                    console.log("Header: No criteria name in response");
                }
                
                // Check if criteria has an error property
                if (criteria && criteria.error) {
                    console.error("Header: Error from API:", criteria.error);
                    setError(criteria.error);
                    setActiveCriteria(null);
                } else {
                    console.log("Header: Setting active criteria:", criteria.name);
                    setActiveCriteria(criteria);
                    setError(null);
                }
            } catch (err) {
                console.error("Header: Error fetching active criteria:", err);
                setError("Failed to load active criteria");
                setActiveCriteria(null);
            } finally {
                setIsLoading(false);
            }
        };

        console.log("Header: forceUpdate changed, value:", forceUpdate);
        fetchActiveCriteria();
    }, [forceUpdate]);

    // Inline styles for header components
    const headerStyles = {
        content: {
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            width: '100%',
            maxWidth: '1400px',
            margin: '0 auto'
        },
        left: {
            flex: '0 0 auto',
            textAlign: 'left',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'flex-start'
        },
        title: {
            margin: 0,
            fontSize: '1.8rem',
            color: 'var(--dark-text-color, #ecf0f1)',
            whiteSpace: 'nowrap',
            textAlign: 'left'
        },
        center: {
            flex: '1 1 auto',
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center'
        },
        right: {
            flex: '0 0 auto',
            display: 'flex',
            justifyContent: 'flex-end',
            alignItems: 'center'
        }
    };

    return (
        <header className="app-header">
            <div style={headerStyles.content}>
                <div style={headerStyles.left}>
                    <h1 style={headerStyles.title}>Qwen Medical Assistant</h1>
                </div>
                
                <div style={headerStyles.center}>
                    <div className="active-criteria">
                        <span className="criteria-label">Active Criteria:</span>
                        {isLoading ? (
                            <span className="loading-text">Loading...</span>
                        ) : error ? (
                            <span className="error-text" title={error}>Connection Error</span>
                        ) : activeCriteria ? (
                            <div className="criteria-list">
                                <span className="criteria-name">
                                    {activeCriteria.name}
                                </span>
                            </div>
                        ) : (
                            <span className="active-criteria-placeholder">Connect to backend server</span>
                        )}
                        <button onClick={toggleCriteriaModal} className="criteria-btn">
                            Change
                        </button>
                        <button 
                            onClick={toggleSqlRetriever} 
                            className={`model-toggle-btn ${useSqlRetriever ? 'active' : ''}`}
                            title={useSqlRetriever ? "Using SQL database retriever (click to disable)" : "Using only conversation (click to enable SQL mode)"}
                        >
                            <span className="sql-indicator"></span>
                            {useSqlRetriever ? "SQL: ON" : "SQL: OFF"}
                        </button>
                    </div>
                </div>
                
                <div style={headerStyles.right}>
                    <button 
                        onClick={toggleDebugPanel} 
                        className="debug-toggle"
                    >
                        {showDebugPanel ? "Hide Debug" : "Show Debug"}
                    </button>
                    
                    <button 
                        onClick={downloadChatHistory} 
                        className="download-pdf-btn"
                        title="Download chat history as PDF"
                    >
                        Download PDF
                    </button>
                </div>
            </div>
        </header>
    );
};

export default Header; 
