document.addEventListener('DOMContentLoaded', function() {
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    const uploadForm = document.getElementById('uploadForm');
    const uploadBtn = document.getElementById('uploadBtn');
    const fileInfo = document.getElementById('fileInfo');
    const fileName = document.getElementById('fileName');
    const fileSize = document.getElementById('fileSize');
    const loadingModal = new bootstrap.Modal(document.getElementById('loadingModal'));
    const toggleMoreLanguages = document.getElementById('toggleMoreLanguages');
    const moreLanguages = document.getElementById('moreLanguages');

    // File size formatter
    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    // Validate file type and size
    function validateFile(file) {
        const allowedTypes = [
            'audio/mpeg', 'audio/wav', 'audio/flac', 'audio/m4a', 'audio/aac',
            'video/mp4', 'video/x-msvideo', 'video/quicktime', 'video/x-matroska', 'video/webm'
        ];
        
        const allowedExtensions = [
            'mp3', 'wav', 'flac', 'm4a', 'aac',
            'mp4', 'avi', 'mov', 'mkv', 'webm', 'flv'
        ];

        const fileExtension = file.name.split('.').pop().toLowerCase();
        const maxSize = 1024 * 1024 * 1024; // 1GB

        if (!allowedExtensions.includes(fileExtension)) {
            return { valid: false, error: 'Invalid file type. Please select an audio or video file.' };
        }

        if (file.size > maxSize) {
            return { valid: false, error: 'File size exceeds 1GB limit.' };
        }

        return { valid: true };
    }

    // Handle file selection
    function handleFileSelect(file) {
        const validation = validateFile(file);
        
        if (!validation.valid) {
            alert(validation.error);
            return;
        }

        fileName.textContent = file.name;
        fileSize.textContent = formatFileSize(file.size);
        fileInfo.classList.remove('d-none');
        uploadBtn.disabled = false;
        
        // Update drop zone appearance
        dropZone.classList.add('border-success');
        dropZone.querySelector('h5').textContent = 'File selected successfully!';
        dropZone.querySelector('p').textContent = 'Click "Start Processing" to continue';
    }

    // Drag and drop handlers
    dropZone.addEventListener('dragover', function(e) {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });

    dropZone.addEventListener('dragleave', function(e) {
        e.preventDefault();
        dropZone.classList.remove('dragover');
    });

    dropZone.addEventListener('drop', function(e) {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            fileInput.files = files;
            handleFileSelect(files[0]);
        }
    });

    // Click to upload
    dropZone.addEventListener('click', function() {
        fileInput.click();
    });

    // File input change
    fileInput.addEventListener('change', function() {
        if (this.files.length > 0) {
            handleFileSelect(this.files[0]);
        }
    });

    // Toggle more languages
    toggleMoreLanguages.addEventListener('click', function() {
        const isHidden = moreLanguages.classList.contains('d-none');
        
        if (isHidden) {
            moreLanguages.classList.remove('d-none');
            this.innerHTML = 'Show fewer languages <i class="fas fa-chevron-up"></i>';
        } else {
            moreLanguages.classList.add('d-none');
            this.innerHTML = 'Show more languages <i class="fas fa-chevron-down"></i>';
        }
    });

    // Ensure at least one target language is selected
    function validateTargetLanguages() {
        const checkedBoxes = document.querySelectorAll('input[name="target_languages"]:checked');
        return checkedBoxes.length > 0;
    }

    // Add change listeners to target language checkboxes
    document.querySelectorAll('input[name="target_languages"]').forEach(checkbox => {
        checkbox.addEventListener('change', function() {
            if (!validateTargetLanguages()) {
                this.checked = true; // Prevent unchecking the last checkbox
                alert('At least one target language must be selected.');
            }
        });
    });

    // Form submission
    uploadForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        if (!fileInput.files.length) {
            alert('Please select a file first.');
            return;
        }

        if (!validateTargetLanguages()) {
            alert('Please select at least one target language.');
            return;
        }

        // Show loading modal
        loadingModal.show();

        // Create FormData
        const formData = new FormData(uploadForm);

        // Upload file
        fetch('/upload', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            loadingModal.hide();
            
            if (data.success) {
                window.location.href = data.redirect_url;
            } else {
                alert(data.error || 'Upload failed. Please try again.');
            }
        })
        .catch(error => {
            loadingModal.hide();
            console.error('Upload error:', error);
            alert('Upload failed. Please check your connection and try again.');
        });
    });

    // Prevent page unload during upload
    let uploadInProgress = false;
    
    uploadForm.addEventListener('submit', function() {
        uploadInProgress = true;
    });

    window.addEventListener('beforeunload', function(e) {
        if (uploadInProgress) {
            e.preventDefault();
            e.returnValue = 'Upload in progress. Are you sure you want to leave?';
        }
    });
});
