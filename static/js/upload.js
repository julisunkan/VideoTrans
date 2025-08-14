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

        uploadInProgress = true;

        // Create XMLHttpRequest for progress tracking
        const xhr = new XMLHttpRequest();
        
        // Update modal content for upload progress
        const modalBody = document.querySelector('#loadingModal .modal-body');
        modalBody.innerHTML = `
            <div class="text-center p-4">
                <div class="mb-3">
                    <div class="progress" style="height: 25px;">
                        <div id="uploadProgress" class="progress-bar progress-bar-striped progress-bar-animated" 
                             role="progressbar" style="width: 0%" aria-valuenow="0" aria-valuemin="0" aria-valuemax="100">
                        </div>
                    </div>
                    <small class="text-muted mt-2 d-block" id="uploadStatus">Preparing upload...</small>
                </div>
                <h5 id="uploadText">Uploading file...</h5>
                <p class="text-muted mb-0">Please wait while we upload and process your file</p>
            </div>
        `;
        
        const uploadProgressBar = document.getElementById('uploadProgress');
        const uploadStatus = document.getElementById('uploadStatus');
        const uploadText = document.getElementById('uploadText');

        // Track upload progress
        xhr.upload.addEventListener('progress', function(e) {
            if (e.lengthComputable) {
                const percentComplete = Math.round((e.loaded / e.total) * 100);
                uploadProgressBar.style.width = percentComplete + '%';
                uploadProgressBar.textContent = percentComplete + '%';
                uploadStatus.textContent = `Uploaded ${formatFileSize(e.loaded)} of ${formatFileSize(e.total)}`;
            }
        });

        // Handle completion
        xhr.addEventListener('load', function() {
            uploadInProgress = false;
            if (xhr.status === 200) {
                try {
                    const data = JSON.parse(xhr.responseText);
                    if (data.success) {
                        uploadText.textContent = 'Upload completed! Redirecting...';
                        uploadProgressBar.style.width = '100%';
                        uploadProgressBar.textContent = '100%';
                        uploadStatus.textContent = 'Upload successful';
                        
                        setTimeout(() => {
                            loadingModal.hide();
                            window.location.href = data.redirect_url;
                        }, 1000);
                    } else {
                        loadingModal.hide();
                        alert(data.error || 'Upload failed. Please try again.');
                    }
                } catch (e) {
                    loadingModal.hide();
                    alert('Upload failed. Invalid response from server.');
                }
            } else {
                loadingModal.hide();
                alert('Upload failed. Server error: ' + xhr.status);
            }
        });

        // Handle errors
        xhr.addEventListener('error', function() {
            uploadInProgress = false;
            loadingModal.hide();
            alert('Upload failed. Please check your connection and try again.');
        });

        // Start upload
        xhr.open('POST', '/upload');
        xhr.send(formData);
    });

    // Prevent page unload during upload
    let uploadInProgress = false;
});
