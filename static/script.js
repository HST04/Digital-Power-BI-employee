document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const fileDetails = document.getElementById('file-details');
    const selectedFileName = document.getElementById('selected-file-name');
    const selectedFileSize = document.getElementById('selected-file-size');
    const btnClear = document.getElementById('btn-clear');
    
    const profileCard = document.getElementById('profile-card');
    const sheetList = document.getElementById('sheet-list');
    const btnViewProfile = document.getElementById('btn-view-profile');
    
    const promptCard = document.getElementById('prompt-card');
    const promptInput = document.getElementById('prompt-input');
    const btnRun = document.getElementById('btn-run');
    
    const outputPlaceholder = document.getElementById('output-placeholder');
    const runProgressCard = document.getElementById('run-progress-card');
    const statusMessage = document.getElementById('status-message');
    const progressBarFill = document.getElementById('progress-bar-fill');
    
    const reportResultCard = document.getElementById('report-result-card');
    const markdownOutput = document.getElementById('markdown-output');
    const btnCopyMd = document.getElementById('btn-copy-md');
    const btnDownloadMd = document.getElementById('btn-download-md');
    const btnDownloadPbip = document.getElementById('btn-download-pbip');
    
    const profileModal = document.getElementById('profile-modal');
    const modalBodyContent = document.getElementById('modal-body-content');
    const modalCloseBtn = document.getElementById('modal-close-btn');

    // Global App State variables
    let currentFileId = null;
    let currentProfileData = null;
    let currentProfileMarkdown = '';
    let compiledReportMarkdown = '';

    // Agent list and their progress mappings
    const agentsList = [
        'data_profiler',
        'model_architect',
        'dax_engineer',
        'tmdl_specialist',
        'ux_advisor',
        'final_compiler'
    ];

    const agentProgressPercent = {
        'data_profiler': 15,
        'model_architect': 35,
        'dax_engineer': 55,
        'tmdl_specialist': 70,
        'ux_advisor': 85,
        'final_compiler': 95
    };

    // 1. Drag & Drop File Handlers
    dropZone.addEventListener('click', () => fileInput.click());

    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => dropZone.classList.remove('dragover'));
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        if (e.dataTransfer.files.length > 0) {
            handleFileUpload(e.dataTransfer.files[0]);
        }
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFileUpload(e.target.files[0]);
        }
    });

    // Clear Selected File
    btnClear.addEventListener('click', (e) => {
        e.stopPropagation();
        resetUploadState();
    });

    // Upload & Profile File API Call
    async function handleFileUpload(file) {
        if (!file.name.endsWith('.xlsx') && !file.name.endsWith('.xls')) {
            alert('Please upload an Excel workbook (.xlsx or .xls).');
            return;
        }

        // Show uploading feedback
        dropZone.style.display = 'none';
        fileDetails.style.display = 'flex';
        selectedFileName.textContent = file.name;
        selectedFileSize.textContent = formatBytes(file.size);
        
        const formData = new FormData();
        formData.append('file', file);

        try {
            selectedFileName.textContent = "Profiling spreadsheet...";
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail || 'Profiling failed');
            }

            const data = await response.json();
            
            // Set App State
            currentFileId = data.file_id;
            currentProfileData = data.profile_data;
            currentProfileMarkdown = data.profile_markdown;
            
            // Update Details Name
            selectedFileName.textContent = file.name;

            // Render Sheet Badges
            sheetList.innerHTML = '';
            data.sheet_names.forEach(sheet => {
                const badge = document.createElement('span');
                badge.className = 'badge-sheet';
                badge.innerHTML = `<i class="fa-solid fa-table"></i> ${sheet}`;
                sheetList.appendChild(badge);
            });

            // Unlock Steps
            profileCard.style.display = 'block';
            promptCard.classList.remove('disabled-card');
            promptInput.disabled = false;
            btnRun.disabled = false;
            promptInput.focus();

        } catch (err) {
            alert(`Error loading file: ${err.message}`);
            resetUploadState();
        }
    }

    function resetUploadState() {
        currentFileId = null;
        currentProfileData = null;
        currentProfileMarkdown = '';
        fileInput.value = '';
        
        dropZone.style.display = 'flex';
        fileDetails.style.display = 'none';
        profileCard.style.display = 'none';
        
        promptCard.classList.add('disabled-card');
        promptInput.disabled = true;
        promptInput.value = '';
        btnRun.disabled = true;
        
        resetWorkflowProgress();
        outputPlaceholder.style.display = 'flex';
        runProgressCard.style.display = 'none';
        reportResultCard.style.display = 'none';
    }

    // 2. View Metadata Profile Modal Handler
    btnViewProfile.addEventListener('click', () => {
        if (currentProfileMarkdown) {
            modalBodyContent.innerHTML = marked.parse(currentProfileMarkdown);
            profileModal.classList.add('open');
        }
    });

    modalCloseBtn.addEventListener('click', () => profileModal.classList.remove('open'));
    window.addEventListener('click', (e) => {
        if (e.target === profileModal) {
            profileModal.classList.remove('open');
        }
    });

    // 3. Multi-Agent Runner Integration
    btnRun.addEventListener('click', async () => {
        const userPrompt = promptInput.value.trim();
        if (!userPrompt) {
            alert('Please enter your business goals/instructions.');
            return;
        }

        if (!currentFileId || !currentProfileData) {
            alert('Please upload a file first.');
            return;
        }

        // Lock form during execution
        promptInput.disabled = true;
        btnRun.disabled = true;
        btnClear.disabled = true;
        
        // Toggle view containers
        outputPlaceholder.style.display = 'none';
        reportResultCard.style.display = 'none';
        runProgressCard.style.display = 'block';
        
        resetWorkflowProgress();
        statusMessage.textContent = "Bootstrapping agents...";
        progressBarFill.style.width = '5%';

        const formData = new FormData();
        formData.append('file_id', currentFileId);
        formData.append('user_prompt', userPrompt);
        formData.append('profile_data_str', JSON.stringify(currentProfileData));

        try {
            const response = await fetch('/analyze', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error('Analysis failed to start.');
            }

            // Stream response chunk reader
            const reader = response.body.getReader();
            const decoder = new TextDecoder('utf-8');
            let buffer = '';

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop(); // Keep last partial line

                for (const line of lines) {
                    const cleanLine = line.trim();
                    if (cleanLine.startsWith('data: ')) {
                        try {
                            const eventData = JSON.parse(cleanLine.slice(6));
                            handleAgentEvent(eventData);
                        } catch (e) {
                            console.error('Failed to parse line:', cleanLine, e);
                        }
                    }
                }
            }

        } catch (err) {
            statusMessage.innerHTML = `<span style="color: #EF4444;"><i class="fa-solid fa-triangle-exclamation"></i> Error: ${err.message}</span>`;
            progressBarFill.style.backgroundColor = '#EF4444';
            promptInput.disabled = false;
            btnRun.disabled = false;
            btnClear.disabled = false;
        }
    });

    // 4. Update Node chart states based on events
    function handleAgentEvent(event) {
        if (event.status === 'started') {
            statusMessage.textContent = event.message;
            progressBarFill.style.width = '8%';
        } 
        else if (event.status === 'agent_change') {
            statusMessage.textContent = event.message;
            const activeAgent = event.agent;
            
            // Mark active agent node and complete previous nodes
            let pastActive = true;
            agentsList.forEach(agent => {
                const node = document.getElementById(`node-${agent}`);
                if (!node) return;
                
                if (agent === activeAgent) {
                    node.className = 'node-wrapper active';
                    node.querySelector('.node-status').textContent = 'Active';
                    pastActive = false;
                } else if (pastActive) {
                    node.className = 'node-wrapper completed';
                    node.querySelector('.node-status').textContent = 'Done';
                } else {
                    node.className = 'node-wrapper';
                    node.querySelector('.node-status').textContent = 'Pending';
                }
            });

            // Update progress bar
            const percent = agentProgressPercent[activeAgent] || 10;
            progressBarFill.style.width = `${percent}%`;
        } 
        else if (event.status === 'completed') {
            // Update all to completed
            agentsList.forEach(agent => {
                const node = document.getElementById(`node-${agent}`);
                if (node) {
                    node.className = 'node-wrapper completed';
                    node.querySelector('.node-status').textContent = 'Done';
                }
            });
            
            progressBarFill.style.width = '100%';
            statusMessage.textContent = "Analysis completed. Compiling final output...";
            
            compiledReportMarkdown = event.report;
            
            if (event.pbip_url) {
                btnDownloadPbip.href = event.pbip_url;
                btnDownloadPbip.style.display = 'inline-block';
            } else {
                btnDownloadPbip.style.display = 'none';
            }
            
            // Render Report using marked.js
            setTimeout(() => {
                markdownOutput.innerHTML = marked.parse(compiledReportMarkdown);
                runProgressCard.style.display = 'none';
                reportResultCard.style.display = 'block';
                
                // Unlock form
                promptInput.disabled = false;
                btnRun.disabled = false;
                btnClear.disabled = false;
            }, 800);
        } 
        else if (event.status === 'error') {
            statusMessage.innerHTML = `<span style="color: #EF4444;"><i class="fa-solid fa-circle-exclamation"></i> ${event.message}</span>`;
            progressBarFill.style.backgroundColor = '#EF4444';
            
            // Unlock form
            promptInput.disabled = false;
            btnRun.disabled = false;
            btnClear.disabled = false;
        }
    }

    function resetWorkflowProgress() {
        agentsList.forEach(agent => {
            const node = document.getElementById(`node-${agent}`);
            if (node) {
                node.className = 'node-wrapper';
                node.querySelector('.node-status').textContent = 'Pending';
            }
        });
        progressBarFill.style.width = '0%';
        progressBarFill.style.backgroundColor = '';
    }

    // 5. Action Buttons Event Listeners
    btnCopyMd.addEventListener('click', () => {
        if (compiledReportMarkdown) {
            navigator.clipboard.writeText(compiledReportMarkdown).then(() => {
                btnCopyMd.innerHTML = `<i class="fa-solid fa-check"></i> Copied!`;
                setTimeout(() => {
                    btnCopyMd.innerHTML = `<i class="fa-regular fa-copy"></i> Copy MD`;
                }, 2000);
            }).catch(err => {
                alert('Failed to copy text: ' + err);
            });
        }
    });

    btnDownloadMd.addEventListener('click', () => {
        if (compiledReportMarkdown) {
            const blob = new Blob([compiledReportMarkdown], { type: 'text/markdown;charset=utf-8;' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'PowerBI_Developer_Handbook.md';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }
    });

    // Utility: Format bytes
    function formatBytes(bytes, decimals = 1) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const dm = decimals < 0 ? 0 : decimals;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
    }
});
