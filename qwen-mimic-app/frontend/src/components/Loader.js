import React from "react";
import "../styles/Loader.css"; // Import CSS for Loader

const Loader = () => {
    return (
        <div className="dots-loader">
            <div className="dot"></div>
            <div className="dot"></div>
            <div className="dot"></div>
        </div>
    );
};

export default Loader;
