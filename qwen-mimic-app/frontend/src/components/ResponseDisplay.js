import React from "react";

const ResponseDisplay = ({ sqlCode, queryResult }) => {
    return (
        <div className="response-display">
            <div className="sql-section">
                <h3>Generated SQL Code:</h3>
                <pre>{sqlCode || "No SQL code generated yet."}</pre>
            </div>
            <div className="result-section">
                <h3>Query Result:</h3>
                <pre>{queryResult.length > 0 ? JSON.stringify(queryResult, null, 2) : "No results yet."}</pre>
            </div>
        </div>
    );
};

export default ResponseDisplay;
