import React, { useState, useRef } from "react";
import "../styles.css"; // Ensure this is imported

const QueryInput = ({ onQuerySubmit }) => {
    const [query, setQuery] = useState("");
    const textAreaRef = useRef(null);

    const handleSubmit = (e) => {
        e.preventDefault();
        if (query.trim() === "") return;
        onQuerySubmit(query);
        setQuery(""); 
        if (textAreaRef.current) {
            textAreaRef.current.style.height = "30px"; // Reset height after submission
        }
    };

    const handleInputChange = (e) => {
        setQuery(e.target.value);
        if (textAreaRef.current) {
            textAreaRef.current.style.height = "30px"; // Reset to default
            if (textAreaRef.current.scrollHeight > textAreaRef.current.clientHeight) {
                textAreaRef.current.style.height = `${textAreaRef.current.scrollHeight}px`;
            }
        }
    };

    return (
        <div className="query-input">
            <div className="query-container">
                <textarea
                    ref={textAreaRef}
                    className="query-textarea"
                    placeholder="Ask a data-related question..."
                    value={query}
                    onChange={handleInputChange}
                    rows={1}
                />
                <button type="submit" className="query-submit-btn" onClick={handleSubmit}>
                    Submit
                </button>
            </div>
        </div>
    );
};

export default QueryInput;
