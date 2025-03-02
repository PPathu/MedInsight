import axios from "axios";

const API_URL = "http://localhost:8000/query"; 
export const sendQuery = async (userQuery) => {
    try {
        const response = await axios.post(API_URL, { user_query: userQuery });
        return response.data;
    } catch (error) {
        return { error: "Failed to fetch response from server." };
    }
};
