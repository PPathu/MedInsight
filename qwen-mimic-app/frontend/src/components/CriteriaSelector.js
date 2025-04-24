import React, { useState, useEffect } from 'react';
import { getCriteriaList, setActiveCriteria, addCustomCriteria, deleteCustomCriteria } from '../api';

const CriteriaSelector = ({ isOpen, onClose, onCriteriaChange, onSave }) => {
    const [criteriaList, setCriteriaList] = useState([]);
    const [activeCriteria, setActiveCriteria] = useState('');
    const [selectedCriteriaKey, setSelectedCriteriaKey] = useState('');
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [showAddForm, setShowAddForm] = useState(false);
    
    // Form state for adding custom criteria
    const [formData, setFormData] = useState({
        key: '',
        name: '',
        description: '',
        criteria: [''],
        threshold: ''
    });

    // Load criteria list on component mount
    useEffect(() => {
        if (isOpen) {
            fetchCriteriaList();
        }
    }, [isOpen]);

    // Fetch criteria list from API
    const fetchCriteriaList = async () => {
        if (!isOpen) return;
        
        setLoading(true);
        setError(null);
        
        try {
            const data = await getCriteriaList();
            console.log('CriteriaSelector: Fetched criteria list:', data);
            
            if (data.error) {
                setError(data.error);
            } else {
                // Log the exact format of each criteria in the list to debug key issues
                if (data.criteria && data.criteria.length > 0) {
                    console.log('CriteriaSelector: All available criteria:');
                    data.criteria.forEach(c => {
                        console.log(`Criteria - key: "${c.key}", name: "${c.name}", description: "${c.description}"`);
                    });
                }
                
                setCriteriaList(data.criteria || []);
                
                // Store the active criteria name
                const activeName = data.active || '';
                setActiveCriteria(activeName);
                console.log('CriteriaSelector: Current active criteria name:', activeName);
                
                // Find the criteria object with matching name to get its key
                const activeItem = data.criteria?.find(c => c.name === activeName);
                if (activeItem) {
                    console.log(`CriteriaSelector: Found active criteria with key ${activeItem.key}`);
                    setSelectedCriteriaKey(activeItem.key);
                } else if (data.criteria?.length > 0) {
                    console.log(`CriteriaSelector: No matching active criteria found, defaulting to first item: ${data.criteria[0].key}`);
                    setSelectedCriteriaKey(data.criteria[0].key);
                }
            }
        } catch (error) {
            setError('Failed to load criteria list');
            console.error('CriteriaSelector: Error fetching criteria:', error);
        } finally {
            setLoading(false);
        }
    };

    // Handle selecting a criteria (not saving yet)
    const handleCriteriaSelect = (event) => {
        const criteriaKey = event.target.value;
        console.log(`CriteriaSelector: Criteria selected: ${criteriaKey}`);
        
        // Find the selected criteria in the list to verify key and name match
        const selectedCriteria = criteriaList.find(c => c.key === criteriaKey);
        if (selectedCriteria) {
            console.log(`CriteriaSelector: Selected criteria details - key: "${selectedCriteria.key}", name: "${selectedCriteria.name}"`);
        } else {
            console.warn(`CriteriaSelector: Could not find criteria with key "${criteriaKey}" in the list`);
        }
        
        setSelectedCriteriaKey(criteriaKey);
    };

    // Handle saving the selected criteria
    const handleSaveCriteria = async () => {
        if (!selectedCriteriaKey) {
            console.error('CriteriaSelector: No criteria key selected');
            return;
        }
        
        // Double check that we have the correct key format before saving
        console.log(`CriteriaSelector: Criteria selected for saving - key: "${selectedCriteriaKey}"`);
        const selectedCriteria = criteriaList.find(c => c.key === selectedCriteriaKey);
        if (selectedCriteria) {
            console.log(`CriteriaSelector: Selected criteria details - key: "${selectedCriteria.key}", name: "${selectedCriteria.name}"`);
        } else {
            console.warn(`CriteriaSelector: Could not find criteria with key "${selectedCriteriaKey}" in the list - this may cause issues`);
        }
        
        setError(null);
        console.log(`CriteriaSelector: Attempting to save criteria with key: ${selectedCriteriaKey}`);
        
        try {
            // Force a browser cache-busting approach
            const timestamp = Date.now();
            console.log(`CriteriaSelector: Adding timestamp to request: ${timestamp}`);
            
            // Try a direct POST with fetch to the server
            const response = await fetch(`${window.location.origin.replace('3000', '8000')}/criteria/active?t=${timestamp}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Cache-Control': 'no-cache, no-store, must-revalidate',
                    'Pragma': 'no-cache',
                    'Expires': '0'
                },
                body: JSON.stringify({ key: selectedCriteriaKey })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const result = await response.json();
            console.log('CriteriaSelector: Direct fetch response:', result);
            
            if (result && result.error) {
                setError(result.error);
                console.error('CriteriaSelector: Error from API:', result.error);
            } else {
                // Success! Notify parent components
                console.log('CriteriaSelector: Successfully saved criteria');
                
                // Notify parent component about the criteria change
                if (onCriteriaChange) {
                    console.log('CriteriaSelector: Calling onCriteriaChange callback');
                    onCriteriaChange();
                } else {
                    console.warn('CriteriaSelector: onCriteriaChange callback is not defined');
                }
                
                // Call onSave if provided
                if (onSave) {
                    console.log('CriteriaSelector: Calling onSave callback');
                    onSave();
                }
                
                // Close the modal
                console.log('CriteriaSelector: Closing criteria modal');
                onClose();
            }
        } catch (error) {
            setError('Failed to change criteria');
            console.error('CriteriaSelector: Error changing criteria:', error);
        }
    };

    // Handle form input changes
    const handleFormChange = (e, index = null) => {
        const { name, value } = e.target;
        
        if (name === 'criterion' && index !== null) {
            // Handle criteria array updates
            const updatedCriteria = [...formData.criteria];
            updatedCriteria[index] = value;
            setFormData({ ...formData, criteria: updatedCriteria });
        } else {
            // Handle other form fields
            setFormData({ ...formData, [name]: value });
        }
    };

    // Add a new criterion field
    const addCriterionField = () => {
        setFormData({
            ...formData,
            criteria: [...formData.criteria, '']
        });
    };

    // Remove a criterion field
    const removeCriterionField = (index) => {
        const updatedCriteria = formData.criteria.filter((_, i) => i !== index);
        setFormData({
            ...formData,
            criteria: updatedCriteria
        });
    };

    // Submit the form to add a custom criteria
    const handleSubmit = async () => {
        // Validate the form data
        if (!formData.key || !formData.name || formData.criteria.some(c => !c.trim())) {
            setError('Key, name, and criteria fields are required');
            return;
        }
        
        try {
            const result = await addCustomCriteria(formData);
            
            if (result && result.error) {
                setError(result.error);
            } else {
                // Reset form and hide it
                setFormData({
                    key: '',
                    name: '',
                    description: '',
                    criteria: [''],
                    threshold: ''
                });
                setShowAddForm(false);
                
                // Refresh the criteria list
                fetchCriteriaList();
            }
        } catch (error) {
            setError('Failed to add custom criteria');
            console.error('Error adding criteria:', error);
        }
    };

    // Delete a custom criteria
    const handleDelete = async (key) => {
        if (window.confirm(`Are you sure you want to delete "${key}" criteria?`)) {
            try {
                const result = await deleteCustomCriteria(key);
                
                if (result && result.error) {
                    setError(result.error);
                } else {
                    // Refresh the list
                    fetchCriteriaList();
                    
                    // Notify parent component about the criteria change
                    if (onCriteriaChange) {
                        onCriteriaChange();
                    }
                }
            } catch (error) {
                setError('Failed to delete criteria');
                console.error('Error deleting criteria:', error);
            }
        }
    };

    if (!isOpen) return null;

    return (
        <div className="modal-overlay">
            <div className="criteria-modal">
                <div className="criteria-header">
                    <h3>Assessment Criteria</h3>
                    <div className="header-buttons">
                        {!showAddForm && (
                            <button 
                                className="add-criteria-btn"
                                onClick={() => setShowAddForm(true)}
                            >
                                Add Custom Criteria
                            </button>
                        )}
                        <button 
                            className="close-modal-btn"
                            onClick={onClose}
                        >
                            ✕
                        </button>
                    </div>
                </div>
                
                {error && <div className="error-message">{error}</div>}
                
                {loading ? (
                    <div className="loading-indicator">Loading criteria...</div>
                ) : (
                    <>
                        {/* Show criteria selection only when not adding custom criteria */}
                        {!showAddForm && (
                            <div className="criteria-select-container">
                                <label htmlFor="criteria-select">Select Criteria:</label>
                                <select 
                                    id="criteria-select"
                                    value={selectedCriteriaKey}
                                    onChange={handleCriteriaSelect}
                                >
                                    {criteriaList.map(criteria => (
                                        <option key={criteria.key} value={criteria.key}>
                                            {criteria.name} - {criteria.description}
                                        </option>
                                    ))}
                                </select>
                                
                                <div className="criteria-actions">
                                    <button 
                                        className="save-criteria-btn"
                                        onClick={handleSaveCriteria}
                                        disabled={!selectedCriteriaKey}
                                    >
                                        Save Selection
                                    </button>
                                    <div className="debug-info">
                                        <small>Selected key: {selectedCriteriaKey}</small>
                                    </div>
                                </div>
                            </div>
                        )}
                
                        {/* Show the form for adding custom criteria */}
                        {showAddForm && (
                            <div className="add-criteria-form-container">
                                <h4>Add Custom Assessment Criteria</h4>
                                
                                <div className="form-group">
                                    <label htmlFor="key">Unique Key:</label>
                                    <input
                                        type="text"
                                        id="key"
                                        name="key"
                                        value={formData.key}
                                        onChange={handleFormChange}
                                        placeholder="e.g., custom-sepsis"
                                    />
                                </div>
                                
                                <div className="form-group">
                                    <label htmlFor="name">Display Name:</label>
                                    <input
                                        type="text"
                                        id="name"
                                        name="name"
                                        value={formData.name}
                                        onChange={handleFormChange}
                                        placeholder="e.g., Custom Sepsis Criteria"
                                    />
                                </div>
                                
                                <div className="form-group">
                                    <label htmlFor="description">Description:</label>
                                    <input
                                        type="text"
                                        id="description"
                                        name="description"
                                        value={formData.description}
                                        onChange={handleFormChange}
                                        placeholder="e.g., My custom sepsis assessment criteria"
                                    />
                                </div>
                                
                                <div className="form-group">
                                    <label>Criteria Points:</label>
                                    {formData.criteria.map((criterion, index) => (
                                        <div key={index} className="criterion-row">
                                            <input
                                                type="text"
                                                name="criterion"
                                                value={criterion}
                                                onChange={(e) => handleFormChange(e, index)}
                                                placeholder="e.g., - Temperature >38°C"
                                            />
                                            <button 
                                                type="button" 
                                                className="remove-btn"
                                                onClick={() => removeCriterionField(index)}
                                                disabled={formData.criteria.length <= 1}
                                            >
                                                Remove
                                            </button>
                                        </div>
                                    ))}
                                    <button 
                                        type="button" 
                                        className="add-btn"
                                        onClick={addCriterionField}
                                    >
                                        Add Criterion
                                    </button>
                                    <div className="info-message">
                                        <small>You can add any number of criteria points. The system will evaluate based on exactly what you specify.</small>
                                    </div>
                                </div>
                                
                                <div className="form-group">
                                    <label htmlFor="threshold">Threshold Rule (Optional):</label>
                                    <input
                                        type="text"
                                        id="threshold"
                                        name="threshold"
                                        value={formData.threshold}
                                        onChange={handleFormChange}
                                        placeholder="e.g., If any 2 criteria met => Positive"
                                    />
                                    <div className="info-message">
                                        <small>If provided, this threshold will be used. If left blank, the AI will use its medical knowledge to assess the criteria.</small>
                                    </div>
                                </div>
                                
                                <div className="modal-footer">
                                    <button 
                                        type="button" 
                                        className="cancel-btn"
                                        onClick={() => setShowAddForm(false)}
                                    >
                                        Cancel
                                    </button>
                                    <button 
                                        type="button" 
                                        className="save-criteria-btn"
                                        onClick={handleSubmit}
                                    >
                                        Add Criteria
                                    </button>
                                </div>
                            </div>
                        )}
                    </>
                )}
            </div>
        </div>
    );
};

export default CriteriaSelector; 
