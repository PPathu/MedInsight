import React, { useState, useEffect, useRef } from "react";
import QueryInput from "./QueryInput";
import { sendQuery } from "../api";
import Loader from "./Loader"; 

const Layout = () => {
    const [history, setHistory] = useState([]);
    const messagesEndRef = useRef(null);

    const handleQuerySubmit = async (userQuery) => {
        if (!userQuery.trim()) return;
        const newMessageId = Date.now();
        const timestamp = new Date().toLocaleString();

        // Insert a loading entry into history
        const loadingEntry = {
            id: newMessageId,
            userQuery,
            generatedCode: null,
            queryResult: null,
            timestamp,
            loading: true,
        };

        setHistory((prevHistory) => [...prevHistory, loadingEntry]);

        try {
            const response = await sendQuery(userQuery);
            setHistory((prevHistory) =>
                prevHistory.map((entry) =>
                    entry.id === newMessageId
                        ? {
                              ...entry,
                              generatedCode:
                                  response.generated_code || "Error generating SQL",
                              queryResult: response.result || [],
                              loading: false,
                          }
                        : entry
                )
            );
        } catch (error) {
            console.error("Error in sendQuery:", error);
            setHistory((prevHistory) =>
                prevHistory.map((entry) =>
                    entry.id === newMessageId
                        ? {
                              ...entry,
                              generatedCode: "Error generating SQL",
                              queryResult: [],
                              loading: false,
                          }
                        : entry
                )
            );
        }
    };

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [history]);

    return (
        <div className="app-container">
            {/* Sidebar for chat history */}
            <aside className="sidebar">
                <h2>Chat History</h2>
                <ul>
                    {history.map((entry) => (
                        <li key={entry.id} className="history-item">
                            {entry.userQuery}
                        </li>
                    ))}
                </ul>
            </aside>

            {/* Main Chat Window */}
            <main className="chat-container">
                <div className="chat-messages">
                    {history.map((entry) => (
                        <div key={entry.id} className="chat-bubble-container">
                            <span className="timestamp">{entry.timestamp}</span>

                            <div className="chat-bubble user-query">
                                {entry.userQuery}
                            </div>

                            <div className="chat-bubble bot-response">
                                {entry.loading ? (
                                    <Loader />
                                ) : (
                                    <>
                                        <strong>SQL Code:</strong>
                                        <pre>{entry.generatedCode}</pre>
                                        <strong>Query Result:</strong>
                                        <pre>
                                            {JSON.stringify(entry.queryResult, null, 2)}
                                        </pre>
                                    </>
                                )}
                            </div>
                        </div>
                    ))}
                    <div ref={messagesEndRef} />
                </div>

                {/* Input Field Fixed at Bottom */}
                <div className="chat-input">
                    <QueryInput onQuerySubmit={handleQuerySubmit} />
                </div>
            </main>
        </div>
    );
};

export default Layout;
