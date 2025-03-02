import React, { useState, useEffect, useRef } from "react";
import QueryInput from "./QueryInput";
import { sendQuery } from "../api";

const Layout = () => {
    const [history, setHistory] = useState([]);
    const messagesEndRef = useRef(null);

    const handleQuerySubmit = async (userQuery) => {
        if (!userQuery.trim()) return;

        const response = await sendQuery(userQuery);

        const timestamp = new Date().toLocaleString(); // Format: "MM/DD/YYYY, HH:MM:SS AM/PM"

        setHistory(prevHistory => [
            ...prevHistory,
            {
                userQuery,
                generatedCode: response.generated_code || "Error generating SQL",
                queryResult: response.result || [],
                timestamp, // Store timestamp
            }
        ]);
    };

    // Auto-scroll to latest message
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [history]);

    return (
        <div className="app-layout">
            {/* Left Panel: User Input */}
            <div className="left-panel">
                <QueryInput onQuerySubmit={handleQuerySubmit} />
            </div>

            {/* Right Panel: Chat-Style Responses */}
            <div className="chat-panel">
                <div className="chat-messages">
                    {history.map((entry, index) => (
                        <div key={index} className="chat-bubble-container">
                            {/* Timestamp */}
                            <span className="timestamp">{entry.timestamp}</span>

                            {/* User Query */}
                            <div className="chat-bubble user-query">
                                {entry.userQuery}
                            </div>

                            {/* AI Response */}
                            <div className="chat-bubble bot-response">
                                <strong>SQL Code:</strong>
                                <pre>{entry.generatedCode}</pre>
                                <strong>Query Result:</strong>
                                <pre>{JSON.stringify(entry.queryResult, null, 2)}</pre>
                            </div>
                        </div>
                    ))}
                    <div ref={messagesEndRef} />
                </div>
            </div>
        </div>
    );
};

export default Layout;
