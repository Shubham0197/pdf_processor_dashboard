document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('process-form');
    const overlay = document.getElementById('processing-overlay');
    const resultsDiv = document.getElementById('process-results');
    const viewResultsBtn = document.getElementById('view-results-btn');
    const processAnotherBtn = document.getElementById('process-another-btn');
    let processingRequestId = null;
    
    if (form) {
        form.addEventListener('submit', function(e) {
            e.preventDefault(); // Prevent the default form submission
            
            // Show the processing overlay
            overlay.style.display = 'flex';
            
            // Submit the form using fetch API
            fetch(form.action || window.location.href, {
                method: 'POST',
                body: new FormData(form),
                headers: {
                    'Accept': 'application/json'
                }
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                console.log('Processing request created:', data);
                
                if (data.id) {
                    processingRequestId = data.id;
                    // Poll for processing status
                    pollProcessingStatus(data.id);
                } else {
                    throw new Error('No processing request ID returned');
                }
            })
            .catch(error => {
                console.error('Error submitting form:', error);
                showError(error.message || 'Failed to process document');
            });
        });
    }
    
    function pollProcessingStatus(requestId) {
        const statusUrl = `/api/v1/processing/${requestId}/status`;
        
        // Check the status every 3 seconds
        const statusCheck = setInterval(() => {
            fetch(statusUrl)
            .then(response => response.json())
            .then(data => {
                console.log('Processing status:', data);
                
                if (data.status === 'completed') {
                    clearInterval(statusCheck);
                    showProcessingComplete(requestId);
                } else if (data.status === 'failed') {
                    clearInterval(statusCheck);
                    showError(data.error || 'Processing failed');
                }
                // If it's still processing, we continue polling
            })
            .catch(error => {
                console.error('Error checking status:', error);
                clearInterval(statusCheck);
                showError('Failed to check processing status');
            });
        }, 3000);
    }
    
    function showProcessingComplete(requestId) {
        // Show the results
        resultsDiv.classList.remove('d-none');
        
        // Set up the View Results button link
        viewResultsBtn.href = `/dashboard/documents/processing/${requestId}`;
        
        // Set up the Process Another button
        processAnotherBtn.addEventListener('click', function(e) {
            e.preventDefault();
            overlay.style.display = 'none';
            resultsDiv.classList.add('d-none');
        });
    }
    
    function showError(message) {
        resultsDiv.innerHTML = `
            <div class="alert alert-danger">
                <h6 class="alert-heading mb-2">Processing Error</h6>
                <p class="mb-2">${message}</p>
                <button id="dismiss-error-btn" class="btn btn-sm btn-outline-secondary mt-2">Dismiss</button>
            </div>
        `;
        resultsDiv.classList.remove('d-none');
        
        // Add event listener to dismiss button
        document.getElementById('dismiss-error-btn').addEventListener('click', function() {
            overlay.style.display = 'none';
            resultsDiv.classList.add('d-none');
        });
    }
});
