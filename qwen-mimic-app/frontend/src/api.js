import axios from "axios";

const BASE_URL = "http://127.0.0.1:8000";
const QUERY_URL = `${BASE_URL}/query`; 
const DIAGNOSE_URL = `${BASE_URL}/diagnose`;
const PROVIDE_INFO_URL = `${BASE_URL}/provide_info`;

// Configure axios with longer timeout and retry capability
const apiClient = axios.create({
    baseURL: BASE_URL,
    timeout: 30000, // 30 seconds timeout
    headers: {
        'Content-Type': 'application/json',
    }
});

// Retry logic for API calls
const retryAxios = async (axiosCall, maxRetries = 3, delayMs = 1000) => {
    let lastError;
    for (let retry = 0; retry < maxRetries; retry++) {
        try {
            if (retry > 0) {
                console.log(`Retry attempt ${retry} of ${maxRetries}...`);
            }
            return await axiosCall();
        } catch (error) {
            console.error(`Attempt ${retry + 1} failed:`, error.message);
            lastError = error;
            // Only wait if we're going to retry again
            if (retry < maxRetries - 1) {
                await new Promise(resolve => setTimeout(resolve, delayMs));
            }
        }
    }
    throw lastError;
};

// Original query endpoint for database queries
export const sendQuery = async (userQuery) => {
    try {
        const response = await retryAxios(() => apiClient.post(QUERY_URL, { user_query: userQuery }));
        return response.data;
    } catch (error) {
        console.error("Query error:", error);
        return { error: "Failed to fetch response from server. Please check if the backend server is running." };
    }
};

// Start a diagnosis session with the database-first approach
export const startDiagnosis = async (query) => {
    try {
        // First check if the server is reachable with our test endpoint
        const testResponse = await retryAxios(() => apiClient.get(`/diagnose-test`));
        console.log("Test endpoint response:", testResponse.data);
        
        // Create a custom promise with progress callback support
        let progressCallback = null;
        
        const customPromise = new Promise((resolve, reject) => {
            const eventSource = new EventSource(`${BASE_URL}/diagnose?query=${encodeURIComponent(query)}`);
            const result = {
                status: [],
                thinking: "",
                search_query: "",
                answer: "",
                database_info: "",
                full_response: "",
                model_progress: [],  // Array to store model loading progress updates
                conversation_history: []
            };
            
            eventSource.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    console.log("Stream data:", data);
                    
                    // Handle different types of responses
                    if (data.type === 'status') {
                        result.status.push(data.content);
                    } else if (data.type === 'thinking') {
                        result.thinking = data.content;
                    } else if (data.type === 'search') {
                        result.search_query = data.content;
                    } else if (data.type === 'answer') {
                        result.answer = data.content;
                    } else if (data.type === 'database') {
                        result.database_info = data.content;
                    } else if (data.type === 'full') {
                        result.full_response = data.content;
                    } else if (data.type === 'model_progress') {
                        // Store progress data in array
                        result.model_progress.push(data.content);
                        // Call progress callback if registered
                        if (progressCallback) {
                            progressCallback(data.content);
                        }
                    } else if (data.type === 'conversation') {
                        // This handles conversation history updates from the server
                        result.conversation_history = data.content;
                        console.log(`Received conversation history with ${data.content.length} messages`);
                    } else if (data.type === 'error') {
                        eventSource.close();
                        reject({ error: data.content });
                    } else if (data.type === 'done') {
                        eventSource.close();
                        
                        // If no conversation history was received, create one from the exchange
                        if (!result.conversation_history || result.conversation_history.length === 0) {
                            result.conversation_history = [
                                { role: "user", content: query },
                                { role: "assistant", content: result.full_response }
                            ];
                            console.log("Created conversation history from query and response");
                        }
                        
                        resolve(result);
                    }
                } catch (error) {
                    console.error("Error parsing SSE data:", error, event.data);
                    eventSource.close();
                    reject({ error: "Error processing server response" });
                }
            };
            
            eventSource.onerror = (error) => {
                console.error("EventSource error:", error);
                eventSource.close();
                reject({ 
                    error: "Connection to server failed or was interrupted", 
                    details: "Check if the backend server is still running."
                });
            };
        });
        
        // Add the setProgressCallback method to the promise
        customPromise.setProgressCallback = (callback) => {
            progressCallback = callback;
            return customPromise;
        };
        
        return customPromise;
    } catch (error) {
        console.error("Error starting diagnosis:", error);
        // Provide more detailed error information
        if (error.code === 'ECONNREFUSED' || error.message.includes('Network Error')) {
            return { 
                error: "Failed to connect to server. Please make sure the backend is running at http://localhost:8000 and you have no CORS issues.", 
                details: `Technical details: ${error.message}`
            };
        }
        return { 
            error: "Failed to start diagnosis session.", 
            details: error.response?.data?.detail || error.message 
        };
    }
};

// Send user-provided information when the model asks for additional details
export const provideInfo = async (userResponse, conversationHistory) => {
    try {
        // Ensure conversation_history is always an array
        let history = [];
        
        if (Array.isArray(conversationHistory)) {
            // Filter to ensure only valid message objects are included
            history = conversationHistory.filter(msg => 
                msg && typeof msg === 'object' && 
                'role' in msg && 
                'content' in msg
            );
            
            console.log(`Validated conversation history: ${history.length} of ${conversationHistory.length} messages are valid`);
        }
        
        // Check if we have any valid conversation history
        if (!history.length) {
            console.error("No valid conversation history found");
            return {
                error: "No valid conversation history found",
                details: "Cannot continue without previous conversation context"
            };
        }
        
        // Log the full conversation history for debugging (limit output size)
        console.log("First message in history:", history[0]);
        console.log("Last message in history:", history[history.length - 1]);
        console.log("Total conversation history length:", history.length);
        
        // First check if the server is reachable with a test request
        const testResponse = await retryAxios(() => apiClient.get(`/diagnose-test`));
        console.log("Server is reachable, proceeding with request");
        
        // Create a custom promise with progress callback support
        let progressCallback = null;
        
        // Use the POST endpoint only for providing information, as GET doesn't support sending complex objects
        const customPromise = new Promise((resolve, reject) => {
            // Send the POST request containing both the user response and conversation history
            console.log(`Sending POST request to ${PROVIDE_INFO_URL} with ${history.length} messages`);
            
            apiClient.post(PROVIDE_INFO_URL, {
                user_response: userResponse,
                conversation_history: history
            })
            .then(response => {
                console.log("Successfully received provide_info response");
                
                // Process and return the response data
                const responseData = response.data;
                
                // Create a result object with the received data
                const result = {
                    status: responseData.status || [],
                    thinking: responseData.thinking || "",
                    search_query: responseData.search_query || "",
                    answer: responseData.answer || "",
                    full_response: responseData.full_response || "",
                    conversation_history: Array.isArray(responseData.conversation_history) ? 
                        responseData.conversation_history : history,
                    model_progress: []
                };
                
                // Log information about the received conversation history
                if (Array.isArray(responseData.conversation_history)) {
                    console.log(`Received updated conversation history with ${responseData.conversation_history.length} messages`);
                } else {
                    console.log("No conversation history returned from backend");
                }
                
                resolve(result);
            })
            .catch(error => {
                console.error("Error in provide_info request:", error);
                
                // Add more detailed error handling
                let errorMessage = "Failed to send additional information.";
                let errorDetails = "";
                
                if (error.response) {
                    // The request was made and the server responded with a status code
                    // that falls out of the range of 2xx
                    errorDetails = `Server responded with status ${error.response.status}: ${error.response.data?.detail || error.message}`;
                    console.error("Server error response:", error.response.data);
                } else if (error.request) {
                    // The request was made but no response was received
                    errorDetails = "No response received from server. Server might be down.";
                } else {
                    // Something happened in setting up the request that triggered an Error
                    errorDetails = error.message;
                }
                
                reject({ 
                    error: errorMessage, 
                    details: errorDetails
                });
            });
        });
        
        // Add the setProgressCallback method to the promise
        customPromise.setProgressCallback = (callback) => {
            progressCallback = callback;
            return customPromise;
        };
        
        return customPromise;
    } catch (error) {
        console.error("Error sending additional information:", error);
        // Provide more detailed error information
        if (error.code === 'ECONNREFUSED' || error.message.includes('Network Error')) {
            return { 
                error: "Failed to connect to server. Please make sure the backend is running at http://localhost:8000 and you have no CORS issues.", 
                details: `Technical details: ${error.message}`
            };
        }
        return { 
            error: "Failed to send additional information.", 
            details: error.response?.data?.detail || error.message 
        };
    }
};
