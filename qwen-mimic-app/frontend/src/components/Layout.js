import React, { useState, useEffect, useRef } from "react";
import QueryInput from "./QueryInput";
import { sendQuery, startDiagnosis, provideInfo, checkBackendStatus } from "../api";
import Loader from "./Loader";
import CriteriaSelector from "./CriteriaSelector";
import Header from "./Header";
import ThemeToggle from "./ThemeToggle";
import jsPDF from 'jspdf';

// Progress bar component for model loading
const ProgressBar = ({ progress, label }) => {
    return (
        <div className="progress-container">
            <div className="progress-label">{label}</div>
            <div className="progress-bar-container">
                <div 
                    className="progress-bar" 
                    style={{ width: `${Math.min(progress, 100)}%` }}
                ></div>
                <div className="progress-percentage">{Math.round(progress)}%</div>
            </div>
        </div>
    );
};

// Model loading progress display component
const ModelLoadingProgress = ({ progressData }) => {
    if (!progressData || !progressData.files || Object.keys(progressData.files).length === 0) {
        return null;
    }
    
    return (
        <div className="model-loading-progress">
            <h4>Model Loading Progress</h4>
            <ProgressBar 
                progress={progressData.overall_progress} 
                label="Overall Progress" 
            />
            {Object.entries(progressData.files).map(([fileName, data]) => (
                <ProgressBar 
                    key={fileName} 
                    progress={data.percentage} 
                    label={fileName} 
                />
            ))}
        </div>
    );
};

const Layout = () => {
    const [history, setHistory] = useState([]);
    const [waitingForUserInput, setWaitingForUserInput] = useState(false);
    const [currentQuestion, setCurrentQuestion] = useState("");
    const [displayedAnswer, setDisplayedAnswer] = useState('');
    const [thinking, setThinking] = useState('');
    const [conversationHistory, setConversationHistory] = useState([]);
    const [isDarkTheme, setIsDarkTheme] = useState(true); // Start with dark theme
    const [modelProgress, setModelProgress] = useState(null);
    const [showDebugPanel, setShowDebugPanel] = useState(false); // State for toggling debug panel
    const [showCriteriaModal, setShowCriteriaModal] = useState(false);
    const [criteriaRefreshKey, setCriteriaRefreshKey] = useState(0); // Used to force header to refresh
    const [useSqlRetriever, setUseSqlRetriever] = useState(false); // State for SQL retriever toggle
    const [backendAvailable, setBackendAvailable] = useState(true); // Track backend availability
    const messagesEndRef = useRef(null);

    // Toggle between dark and light themes
    const toggleTheme = () => {
        setIsDarkTheme(!isDarkTheme);
    };

    // Toggle debug panel
    const toggleDebugPanel = () => {
        setShowDebugPanel(!showDebugPanel);
    };
    
    // Toggle criteria modal
    const toggleCriteriaModal = () => {
        setShowCriteriaModal(!showCriteriaModal);
    };
    
    // Toggle SQL retriever
    const toggleSqlRetriever = () => {
        const newState = !useSqlRetriever;
        console.log(`Toggling SQL retriever: ${useSqlRetriever} → ${newState}`);
        setUseSqlRetriever(newState);
    };
    
    // Handle criteria change (force header to refresh)
    const handleCriteriaChange = () => {
        // Force Header component to re-render by updating the key
        const newKey = `criteria_refresh_${Date.now()}`;
        console.log('Layout: Updating criteria refresh key:', newKey);
        
        // Briefly delay to ensure backend has time to update
        setTimeout(() => {
            setCriteriaRefreshKey(newKey);
            console.log('Layout: Criteria refresh key updated');
        }, 300);
    };

    // Apply theme to body element
    useEffect(() => {
        if (isDarkTheme) {
            document.body.classList.add('dark-theme');
            document.body.classList.remove('light-theme');
        } else {
            document.body.classList.add('light-theme');
            document.body.classList.remove('dark-theme');
        }
    }, [isDarkTheme]);

    // Check backend availability
    useEffect(() => {
        const checkBackend = async () => {
            const isAvailable = await checkBackendStatus();
            setBackendAvailable(isAvailable);
            
            // If not available, check again every 10 seconds
            if (!isAvailable) {
                const intervalId = setInterval(async () => {
                    const available = await checkBackendStatus();
                    setBackendAvailable(available);
                    if (available) {
                        clearInterval(intervalId);
                    }
                }, 10000);
                
                return () => clearInterval(intervalId);
            }
        };
        
        checkBackend();
    }, []);

    // Handle initial query from user
    const handleQuerySubmit = async (userQuery) => {
        if (!userQuery.trim()) return;
        const newMessageId = Date.now();
        const timestamp = new Date().toLocaleString();

        // Add user query to history
        const newEntry = {
            id: newMessageId,
            type: "user-query",
            content: userQuery,
            timestamp
        };
        setHistory((prev) => [...prev, newEntry]);

        // Add loading indicator
        const loadingId = Date.now() + 1;
        setHistory((prev) => [...prev, {
            id: loadingId,
            type: "loading",
            timestamp
        }]);

        try {
            // Clear previous model progress
            setModelProgress(null);
            
            // Start the diagnostic process and register progress callback
            const diagnosisPromise = startDiagnosis(userQuery, useSqlRetriever);
            
            // Register progress callback if available
            if (typeof diagnosisPromise.setProgressCallback === 'function') {
                diagnosisPromise.setProgressCallback((progress) => {
                    setModelProgress(progress);
                });
            }
            
            // Wait for the response
            const response = await diagnosisPromise;
            
            // Remove loading indicator
            setHistory((prev) => prev.filter(entry => entry.id !== loadingId));
            
            // Process the response
            if (response.error) {
                addSystemMessage("Error", response.error + (response.details ? `\n\nDetails: ${response.details}` : ""));
                
                // Special handling for connectivity errors - more visible warning
                if (response.error.includes("Failed to connect to server")) {
                    addSystemMessage("Connection Troubleshooting", 
                        "1. Check if the backend server is running (cd qwen-mimic-app/backend && uvicorn app.main:app --host 0.0.0.0 --port 8000)\n" +
                        "2. Check if you can access http://localhost:8000 in your browser\n" +
                        "3. If using localhost, try using 127.0.0.1 instead in api.js\n" +
                        "4. Check your firewall/network settings\n" +
                        "5. Check for browser console errors"
                    );
                }
                return;
            }
            
            // Display status messages
            if (response.status && response.status.length > 0) {
                addSystemMessage("Processing Status", response.status.join("\n"));
            }
            
            // Add database information to the chat
            if (response.database_info && response.database_info.trim() !== "DATABASE INFORMATION:\n") {
                addSystemMessage("Database Information", response.database_info);
            }
            
            // Add thinking if available
            if (response.thinking) {
                addSystemMessage("Reasoning", response.thinking);
            }
            
            // If there's an answer, display it
            if (response.answer) {
                addSystemMessage("Diagnosis", response.answer);
            }
            
            // If there's a search query (question), ask user for more info
            if (response.search_query) {
                setCurrentQuestion(response.search_query);
                setWaitingForUserInput(true);
                
                // Store conversation history in both state and localStorage for persistence
                const historyToStore = Array.isArray(response.conversation_history) ? 
                    response.conversation_history : [];
                    
                setConversationHistory(historyToStore);
                
                // Also save to localStorage as a backup
                if (historyToStore.length > 0) {
                    localStorage.setItem('conversationHistory', JSON.stringify(historyToStore));
                    console.log("Saved conversation history with", historyToStore.length, "messages");
                }
            }
            
            // Always ensure conversation history is stored, regardless of whether we received a search query
            if (response.conversation_history && Array.isArray(response.conversation_history)) {
                console.log("Setting conversation history from initial diagnosis with", 
                    response.conversation_history.length, "messages");
                    
                // Store in state
                setConversationHistory(response.conversation_history);
                
                // Store in localStorage for backup
                localStorage.setItem('conversationHistory', JSON.stringify(response.conversation_history));
            } else {
                // If no conversation history is returned, create one manually with the query and response
                const manualHistory = [
                    { role: "user", content: userQuery },
                    { role: "assistant", content: response.full_response || "" }
                ];
                console.log("Created manual conversation history with", manualHistory.length, "messages");
                
                // Store in state and localStorage
                setConversationHistory(manualHistory);
                localStorage.setItem('conversationHistory', JSON.stringify(manualHistory));
            }
            
            // Clear model progress when complete
            setModelProgress(null);
            
            setThinking(response.thinking || "");
            setDisplayedAnswer(response.answer || "");
            setConversationHistory(Array.isArray(response.conversation_history) ? 
                response.conversation_history : []);
            
        } catch (error) {
            console.error("Error in diagnosis:", error);
            addSystemMessage("Error", "Error connecting to the diagnostic system.");
            
            // Remove loading indicator
            setHistory((prev) => prev.filter(entry => entry.id !== loadingId));
            
            // Clear model progress
            setModelProgress(null);
        }
    };
    
    // Handle user providing additional information
    const handleFollowUpSubmit = async (additionalInfo) => {
        if (!additionalInfo.trim()) return;
        
        // Add user response to history
        const responseEntry = {
            id: Date.now(),
            type: "user-response",
            content: additionalInfo,
            timestamp: new Date().toLocaleString()
        };
        setHistory((prev) => [...prev, responseEntry]);
        
        // Reset state but keep the question
        setWaitingForUserInput(false);
        
        // Add loading indicator
        const loadingId = Date.now() + 1;
        setHistory((prev) => [...prev, {
            id: loadingId,
            type: "loading",
            timestamp: new Date().toLocaleString()
        }]);
        
        try {
            // Log the current state of conversation history to help debug
            console.log("Current conversation history state:", conversationHistory);
            
            // Try to get conversation history from multiple sources in order of preference:
            // 1. From component state
            // 2. From localStorage
            // 3. Create an empty one as last resort
            let history = [];
            
            if (conversationHistory && conversationHistory.length > 0) {
                // Use the history from component state
                history = [...conversationHistory];
                console.log("Using conversation history from state with", history.length, "messages");
            } else {
                // Try to load from localStorage
                try {
                    console.log("Checking for saved conversation history in localStorage...");
                    const savedHistory = localStorage.getItem('conversationHistory');
                    
                    if (savedHistory) {
                        console.log("Found saved history in localStorage");
                        try {
                            const parsedHistory = JSON.parse(savedHistory);
                            
                            if (Array.isArray(parsedHistory) && parsedHistory.length > 0) {
                                // Validate that the items have the correct structure
                                const validItems = parsedHistory.filter(msg => 
                                    msg && typeof msg === 'object' && 
                                    'role' in msg && 
                                    'content' in msg
                                );
                                
                                if (validItems.length > 0) {
                                    console.log(`Loaded ${validItems.length} valid messages from localStorage`);
                                    history = validItems;
                                } else {
                                    console.error("No valid messages in saved history");
                                }
                            } else {
                                console.error("Saved history is not a non-empty array");
                            }
                        } catch (parseError) {
                            console.error("Error parsing saved history:", parseError);
                        }
                    } else {
                        console.log("No saved conversation history found in localStorage");
                    }
                } catch (error) {
                    console.error("Error loading saved conversation history:", error);
                }
                
                // If still empty, show error
                if (history.length === 0) {
                    console.error("No conversation history available from any source");
                    addSystemMessage("Error", "Missing conversation history. Please start a new query.");
                    
                    // Remove loading indicator
                    setHistory((prev) => prev.filter(entry => entry.id !== loadingId));
                    return;
                }
            }
            
            // Clear previous model progress
            setModelProgress(null);
            
            // Send the additional information to the backend with progress callback
            const infoPromise = provideInfo(additionalInfo, history, useSqlRetriever);
            
            // Register progress callback if available
            if (typeof infoPromise.setProgressCallback === 'function') {
                infoPromise.setProgressCallback((progress) => {
                    setModelProgress(progress);
                });
            }
            
            // Wait for the response
            const response = await infoPromise;
            
            // Remove loading indicator
            setHistory((prev) => prev.filter(entry => entry.id !== loadingId));
            
            // Process the response
            if (response.error) {
                addSystemMessage("Error", response.error + (response.details ? `\n\nDetails: ${response.details}` : ""));
                return;
            }
            
            // Display status messages
            if (response.status && response.status.length > 0) {
                addSystemMessage("Processing Status", response.status.join("\n"));
            }
            
            // Update conversation history if available
            if (response.conversation_history && response.conversation_history.length > 0) {
                setConversationHistory(response.conversation_history);
                // Also update localStorage
                localStorage.setItem('conversationHistory', JSON.stringify(response.conversation_history));
                console.log("Updated conversation history with", response.conversation_history.length, "messages");
            } else {
                // Manually update the conversation history if server didn't return it
                const updatedHistory = [
                    ...history,
                    { role: "user", content: additionalInfo },
                    { role: "assistant", content: response.full_response || "" }
                ];
                setConversationHistory(updatedHistory);
                // Also update localStorage
                localStorage.setItem('conversationHistory', JSON.stringify(updatedHistory));
                console.log("Manually updated conversation history with", updatedHistory.length, "messages");
            }
            
            // Add thinking if available
            if (response.thinking) {
                addSystemMessage("Reasoning", response.thinking);
            }
            
            // If there's an answer, display it
            if (response.answer) {
                addSystemMessage("Diagnosis", response.answer);
            }
            
            // If there's another search query (question), ask user for more info
            if (response.search_query) {
                setCurrentQuestion(response.search_query);
                setWaitingForUserInput(true);
            }
            
            // Clear model progress when complete
            setModelProgress(null);
            
            setThinking(response.thinking || "");
            setDisplayedAnswer(response.answer || "");
            
        } catch (error) {
            console.error("Error sending additional info:", error);
            addSystemMessage("Error", "Error connecting to the diagnostic system.");
            
            // Remove loading indicator
            setHistory((prev) => prev.filter(entry => entry.id !== loadingId));
            
            // Clear model progress
            setModelProgress(null);
        }
    };

    // Helper function to add system messages to the chat
    const addSystemMessage = (title, content) => {
        const newEntry = {
            id: Date.now(),
            type: "system-message",
            title,
            content,
            timestamp: new Date().toLocaleString()
        };
        setHistory((prev) => [...prev, newEntry]);
    };

    // Scroll to bottom on new messages - use smooth scrolling
    useEffect(() => {
        if (messagesEndRef.current) {
            // Use a slight delay to ensure all content is rendered before scrolling
            setTimeout(() => {
                messagesEndRef.current.scrollIntoView({ 
                    behavior: "smooth",
                    block: "end"
                });
            }, 100);
        }
    }, [history]);

    // Scroll to bottom on initial render to show the input field
    useEffect(() => {
        // Scroll to bottom on initial load
        window.scrollTo(0, document.body.scrollHeight);
    }, []);

    // In useEffect, add code to load conversation history from localStorage on component mount
    useEffect(() => {
        // Try to load conversation history from localStorage
        try {
            console.log("Checking for saved conversation history in localStorage...");
            const savedHistory = localStorage.getItem('conversationHistory');
            
            if (savedHistory) {
                console.log("Found saved history in localStorage");
                try {
                    const parsedHistory = JSON.parse(savedHistory);
                    
                    if (Array.isArray(parsedHistory) && parsedHistory.length > 0) {
                        // Validate that the items have the correct structure
                        const validItems = parsedHistory.filter(msg => 
                            msg && typeof msg === 'object' && 
                            'role' in msg && 
                            'content' in msg
                        );
                        
                        if (validItems.length > 0) {
                            console.log(`Loaded ${validItems.length} valid messages from localStorage`);
                            setConversationHistory(validItems);
                        } else {
                            console.error("No valid messages in saved history");
                        }
                    } else {
                        console.error("Saved history is not a non-empty array");
                    }
                } catch (parseError) {
                    console.error("Error parsing saved history:", parseError);
                }
            } else {
                console.log("No saved conversation history found in localStorage");
            }
        } catch (error) {
            console.error("Error loading saved conversation history:", error);
        }
    }, []);

    // Function to generate and download PDF from chat history
    const downloadChatHistory = () => {
        const doc = new jsPDF();
        const pageWidth = doc.internal.pageSize.getWidth();
        const margin = 20;
        const contentWidth = pageWidth - (margin * 2);
        const lineHeight = 7;
        let yPosition = 20;
        
        // Add title
        doc.setFontSize(18);
        doc.setFont('helvetica', 'bold');
        doc.text('Chat History', margin, yPosition);
        yPosition += lineHeight * 2;
        
        // Format the conversation history as pretty JSON
        const jsonString = JSON.stringify(conversationHistory, null, 2);
        
        // Set monospace font for code
        doc.setFont('courier', 'normal');
        doc.setFontSize(9); // Smaller font size for JSON
        doc.setCharSpace(0);
        
        // Split content into lines that fit the page width
        const textLines = doc.splitTextToSize(jsonString, contentWidth);
        
        // Add lines to the PDF
        textLines.forEach(line => {
            // Check if we need a new page
            if (yPosition > doc.internal.pageSize.getHeight() - 30) {
                doc.addPage();
                yPosition = 20;
            }
            
            doc.text(line, margin, yPosition);
            yPosition += lineHeight;
        });
        
        // Save the PDF
        doc.save('chat-history.pdf');
    };

    return (
        <div className={`app-container ${isDarkTheme ? 'dark' : 'light'}`}>
            <Header 
                key={criteriaRefreshKey} // Add key to force re-render when criteria changes
                forceUpdate={criteriaRefreshKey} // Pass the key as a prop to trigger useEffect
                isDarkTheme={isDarkTheme}
                toggleDebugPanel={toggleDebugPanel} 
                showDebugPanel={showDebugPanel}
                toggleCriteriaModal={toggleCriteriaModal}
                downloadChatHistory={downloadChatHistory} // Add the download function as a prop
                useSqlRetriever={useSqlRetriever}
                toggleSqlRetriever={toggleSqlRetriever}
            />

            <main className="app-main">
                <div className="sidebar">
                    <h3>Session History</h3>
                    <ul className="session-list">
                        {history
                            .filter(entry => entry.type === "user-query")
                            .map((entry) => (
                                <li key={entry.id} className="history-item">
                                    {entry.content.substring(0, 30)}
                                    {entry.content.length > 30 ? "..." : ""}
                                </li>
                            ))}
                    </ul>
                </div>
                
                <div className="chat-container">
                    {/* Debug panel */}
                    {showDebugPanel && (
                        <div className="debug-panel">
                            <h3>Conversation History</h3>
                            <pre className="debug-content">
                                {JSON.stringify(conversationHistory, null, 2)}
                            </pre>
                            
                            <h3>Current Thinking Process</h3>
                            <pre className="debug-content">
                                {thinking || 'No thinking process available'}
                            </pre>
                            
                            <h3>Current Answer</h3>
                            <pre className="debug-content">
                                {displayedAnswer || 'No answer available'}
                            </pre>
                        </div>
                    )}
                    
                    {/* Backend connection warning */}
                    {!backendAvailable && (
                        <div className="backend-warning">
                            <strong>Backend server is not running!</strong>
                            <p>Start the backend server with:</p>
                            <pre>cd qwen-mimic-app/backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000</pre>
                            <button onClick={() => checkBackendStatus().then(setBackendAvailable)}>
                                Check Connection
                            </button>
                        </div>
                    )}
                    
                    <div className="chat-messages">
                        {history.map((entry) => (
                            <div key={entry.id} className="chat-bubble-container">
                                <span className="timestamp">{entry.timestamp}</span>

                                {entry.type === "user-query" && (
                                    <div className="chat-bubble user-query">
                                        <strong>Patient Query:</strong>
                                        <p>{entry.content}</p>
                                    </div>
                                )}
                                
                                {entry.type === "user-response" && (
                                    <div className="chat-bubble user-response">
                                        <strong>Additional Information:</strong>
                                        <p>{entry.content}</p>
                                    </div>
                                )}
                                
                                {entry.type === "system-message" && (
                                    <div className="chat-bubble system-message">
                                        <strong>{entry.title}:</strong>
                                        {entry.title === "Reasoning" ? (
                                            <div className="thinking-content">
                                                <pre className="thinking-text">{entry.content}</pre>
                                            </div>
                                        ) : entry.title === "Diagnosis" ? (
                                            <div className="answer-content">
                                                <pre className={`answer-text ${entry.content.toLowerCase().includes('not met') || 
                                                                      entry.content.toLowerCase().includes('negative') || 
                                                                      entry.content.toLowerCase().includes('no ') || 
                                                                      entry.content.toLowerCase().includes('normal') ? 
                                                                      'negative-result' : ''}`}>
                                                    {entry.content}
                                                </pre>
                                            </div>
                                        ) : (
                                            <pre className="system-content">{entry.content}</pre>
                                        )}
                                    </div>
                                )}

                                {entry.type === "loading" && (
                                    <div className="chat-bubble loading">
                                        <div className="loading-dots">
                                            <span className="dot"></span>
                                            <span className="dot"></span>
                                            <span className="dot"></span>
                                        </div>
                                    </div>
                                )}
                                
                                {/* Show model loading progress if available */}
                                {modelProgress && (
                                    <ModelLoadingProgress progressData={modelProgress} />
                                )}
                            </div>
                        ))}
                        <div ref={messagesEndRef} />
                    </div>
                    
                    {/* Input Field Fixed at Bottom */}
                    <div className="chat-input">
                        {waitingForUserInput ? (
                            <>
                                <div className="question-prompt">
                                    <p><strong>Question:</strong> {currentQuestion}</p>
                                </div>
                                <QueryInput 
                                    onQuerySubmit={handleFollowUpSubmit} 
                                    placeholder="Type your answer here..."
                                    buttonText="Send Response"
                                />
                            </>
                        ) : (
                            <QueryInput 
                                onQuerySubmit={handleQuerySubmit} 
                                placeholder="Ask a medical question about a patient..."
                                buttonText="Diagnose"
                            />
                        )}
                    </div>
                </div>
            </main>
            
            {/* Theme toggle in bottom left corner */}
            <div className="theme-toggle-container">
                <ThemeToggle isDarkTheme={isDarkTheme} toggleTheme={toggleTheme} />
            </div>
            
            {/* Criteria Modal */}
            {showCriteriaModal && (
                <CriteriaSelector 
                    isOpen={showCriteriaModal}
                    onClose={toggleCriteriaModal}
                    onCriteriaChange={handleCriteriaChange}
                />
            )}
        </div>
    );
};

export default Layout;
