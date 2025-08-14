document.addEventListener('DOMContentLoaded', function() {
    const socket = io();
    const progressBar = document.getElementById('progressBar');
    const progressText = document.getElementById('progressText');
    const progressPercentage = document.getElementById('progressPercentage');
    const connectionStatus = document.getElementById('connectionStatus');
    const connectionText = document.getElementById('connectionText');
    const errorAlert = document.getElementById('errorAlert');
    const errorText = document.getElementById('errorText');
    const retryBtn = document.getElementById('retryBtn');

    let currentStep = '';
    let transcriptionStarted = false;

    // Update progress bar
    function updateProgress(percentage, text) {
        progressBar.style.width = percentage + '%';
        progressBar.setAttribute('aria-valuenow', percentage);
        progressPercentage.textContent = percentage + '%';
        progressText.textContent = text;
    }

    // Update step status
    function updateStepStatus(stepName, status) {
        const stepElement = document.getElementById(`step-${stepName}`);
        if (!stepElement) return;

        const spinner = stepElement.querySelector('.spinner-border');
        const checkmark = stepElement.querySelector('.fa-check');

        // Reset all statuses first
        stepElement.classList.remove('active', 'completed');
        if (spinner) spinner.classList.add('d-none');
        if (checkmark) checkmark.classList.add('d-none');

        if (status === 'active') {
            stepElement.classList.add('active');
            if (spinner) spinner.classList.remove('d-none');
        } else if (status === 'completed') {
            stepElement.classList.add('completed');
            if (checkmark) checkmark.classList.remove('d-none');
        }
    }

    // Mark previous steps as completed
    function markPreviousStepsCompleted(currentStepName) {
        const steps = ['starting', 'extracting', 'cleaning', 'transcribing', 'translating', 'completed'];
        const currentIndex = steps.indexOf(currentStepName);
        
        for (let i = 0; i < currentIndex; i++) {
            updateStepStatus(steps[i], 'completed');
        }
    }

    // Socket connection handlers
    socket.on('connect', function() {
        console.log('Connected to server');
        connectionText.textContent = 'Connected to server';
        connectionStatus.className = 'alert alert-success';
        
        // Start transcription automatically if we have a session ID
        if (window.sessionId && !transcriptionStarted) {
            transcriptionStarted = true;
            setTimeout(() => {
                socket.emit('start_transcription', { session_id: window.sessionId });
            }, 1000);
        }
    });

    socket.on('disconnect', function() {
        console.log('Disconnected from server');
        connectionText.textContent = 'Disconnected from server. Attempting to reconnect...';
        connectionStatus.className = 'alert alert-warning';
    });

    socket.on('connect_error', function(error) {
        console.error('Connection error:', error);
        connectionText.textContent = 'Connection failed. Please refresh the page.';
        connectionStatus.className = 'alert alert-danger';
        retryBtn.classList.remove('d-none');
    });

    // Progress update handler
    socket.on('progress', function(data) {
        console.log('Progress update:', data);
        
        updateProgress(data.percentage, data.message);
        
        // Update step status
        if (data.step && data.step !== currentStep) {
            if (currentStep) {
                updateStepStatus(currentStep, 'completed');
            }
            updateStepStatus(data.step, 'active');
            markPreviousStepsCompleted(data.step);
            currentStep = data.step;
        }

        // Hide error alert if progress is being made
        if (!errorAlert.classList.contains('d-none')) {
            errorAlert.classList.add('d-none');
        }
    });

    // Transcription complete handler
    socket.on('transcription_complete', function(data) {
        console.log('Transcription complete:', data);
        
        updateProgress(100, 'Processing completed successfully!');
        updateStepStatus('completed', 'completed');
        markPreviousStepsCompleted('completed');
        
        // Redirect to results page after a short delay
        setTimeout(() => {
            window.location.href = data.redirect_url;
        }, 2000);
    });

    // Error handler
    socket.on('error', function(data) {
        console.error('Server error:', data);
        
        errorText.textContent = data.message;
        errorAlert.classList.remove('d-none');
        retryBtn.classList.remove('d-none');
        
        // Stop progress animation
        progressBar.classList.remove('progress-bar-animated');
        
        // Mark current step as failed
        if (currentStep) {
            updateStepStatus(currentStep, '');
        }
    });

    // Retry functionality
    retryBtn.addEventListener('click', function() {
        location.reload();
    });

    // Auto-start transcription if session exists
    if (window.sessionId) {
        updateProgress(0, 'Connecting to server...');
    } else {
        errorText.textContent = 'No active session found. Please upload a file first.';
        errorAlert.classList.remove('d-none');
        retryBtn.classList.remove('d-none');
    }

    // Handle page visibility changes
    document.addEventListener('visibilitychange', function() {
        if (!document.hidden && socket.disconnected) {
            console.log('Page became visible, attempting to reconnect...');
            socket.connect();
        }
    });

    // Prevent page reload during processing
    window.addEventListener('beforeunload', function(e) {
        if (transcriptionStarted && currentStep !== 'completed') {
            e.preventDefault();
            e.returnValue = 'Transcription in progress. Are you sure you want to leave?';
        }
    });
});
