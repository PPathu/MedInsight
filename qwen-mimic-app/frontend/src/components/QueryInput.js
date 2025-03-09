import React, { useState, useRef } from "react";
import "../styles/QueryInput.css"; 

const QueryInput = ({ onQuerySubmit }) => {
    const [query, setQuery] = useState("");
    const textareaRef = useRef(null);

    const adjustTextareaHeight = () => {
        const textarea = textareaRef.current;
        if (!textarea) return;

        textarea.style.height = "auto"; 
        if (textarea.scrollHeight > textarea.clientHeight) {
            textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`; 
        }
    };

    const handleChange = (e) => {
        setQuery(e.target.value);
        adjustTextareaHeight();
    };

    const handleKeyDown = (e) => {
        if (e.key === "Enter") {
            if (e.shiftKey) {
                // Shift + Enter → Add a new line
                e.preventDefault(); 
                setQuery((prev) => prev + "\n");
                setTimeout(() => adjustTextareaHeight(), 0); 
            } else {
                // Enter → Submit the form
                e.preventDefault(); 
                handleSubmit(e);
            }
        }
    };

    const handleSubmit = (e) => {
        e.preventDefault();
        if (!query.trim()) return;
        onQuerySubmit(query);
        setQuery(""); // Clear input after submission
        textareaRef.current.style.height = "50px"; // Reset height after submit
    };

    return (
        <form id="query-form" onSubmit={handleSubmit}>
            <div id="query-container">
                <textarea
                    ref={textareaRef}
                    className="query-input"
                    value={query}
                    onChange={handleChange}
                    onKeyDown={handleKeyDown}
                    placeholder="Ask a question..."
                    rows="1"
                />
                <button type="submit" className="submit-btn">
                    <span className="circle1"></span>
                    <span className="circle2"></span>
                    <span className="circle3"></span>
                    <span className="circle4"></span>
                    <span className="circle5"></span>
                    <span className="text">Submit</span>
                </button>
            </div>
        </form>
    );
};

export default QueryInput;
