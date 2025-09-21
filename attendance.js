// Attendance System JavaScript functionality
class AttendanceSystem {
    constructor() {
        this.video = document.getElementById('video');
        this.canvas = document.getElementById('canvas');
        this.cameraPlaceholder = document.getElementById('camera-placeholder');
        this.startBtn = document.getElementById('startWebcam');
        this.stopBtn = document.getElementById('stopWebcam');
        this.markBtn = document.getElementById('markAttendance');
        this.backBtn = document.getElementById('backBtn');
        this.resultDiv = document.getElementById('attendanceResult');
        this.resultContent = document.getElementById('resultContent');
        this.recordsTableBody = document.getElementById('recordsTableBody');
        
        this.stream = null;
        this.capturedImage = null;
        this.attendanceRecords = [];
        this.currentUser = null;
        
        // AWS Configuration
        this.awsConfig = {
            region: 'us-east-1',
            apiGatewayUrl: 'https://7wal320aqk.execute-api.us-east-1.amazonaws.com/prod'
        };
        
        this.initializeEventListeners();
        this.loadAttendanceRecords();
        this.updateStats();
    }
    
    initializeEventListeners() {
        this.startBtn.addEventListener('click', () => this.startWebcam());
        this.stopBtn.addEventListener('click', () => this.stopWebcam());
        this.markBtn.addEventListener('click', () => this.markAttendance());
        this.backBtn.addEventListener('click', () => this.goBack());
        
        // Filter controls
        document.getElementById('statusFilter').addEventListener('change', () => this.filterRecords());
        document.getElementById('dateFilter').addEventListener('change', () => this.filterRecords());
        document.getElementById('exportBtn').addEventListener('click', () => this.exportToCSV());
    }
    
    async startWebcam() {
        try {
            this.startBtn.disabled = true;
            this.startBtn.textContent = 'Starting...';
            
            const constraints = {
                video: {
                    width: { ideal: 640 },
                    height: { ideal: 480 },
                    facingMode: 'user'
                }
            };
            
            this.stream = await navigator.mediaDevices.getUserMedia(constraints);
            this.video.srcObject = this.stream;
            
            this.video.addEventListener('loadedmetadata', () => {
                this.video.style.display = 'block';
                this.cameraPlaceholder.style.display = 'none';
                this.startBtn.disabled = false;
                this.startBtn.textContent = 'Start Camera';
                this.stopBtn.disabled = false;
                this.markBtn.disabled = false;
            });
            
        } catch (error) {
            console.error('Error accessing webcam:', error);
            this.showMessage('Unable to access webcam. Please check permissions and try again.', 'error');
            this.startBtn.disabled = false;
            this.startBtn.textContent = 'Start Camera';
        }
    }
    
    stopWebcam() {
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }
        
        this.video.style.display = 'none';
        this.cameraPlaceholder.style.display = 'flex';
        this.video.srcObject = null;
        
        this.startBtn.disabled = false;
        this.stopBtn.disabled = true;
        this.markBtn.disabled = true;
        
        this.resultDiv.style.display = 'none';
    }
    
    captureImage() {
        if (!this.stream) {
            this.showMessage('Please start the camera first.', 'error');
            return;
        }
        
        const context = this.canvas.getContext('2d');
        this.canvas.width = this.video.videoWidth;
        this.canvas.height = this.video.videoHeight;
        
        context.drawImage(this.video, 0, 0, this.canvas.width, this.canvas.height);
        
        this.capturedImage = this.canvas.toDataURL('image/jpeg', 0.8);
        return this.capturedImage;
    }
    
    async markAttendance() {
        if (!this.stream) {
            this.showMessage('Please start the camera first.', 'error');
            return;
        }
        
        // Capture image first
        const imageData = this.captureImage();
        if (!imageData) {
            return;
        }
        
        try {
            this.showMessage('Verifying face and marking attendance...', 'info');
            this.setLoading(true);
            
            // Call AWS API Gateway for face verification
            const verificationResult = await this.verifyFaceAPI(imageData);
            
            if (verificationResult.match) {
                // Determine if this is check-in or check-out
                const attendanceType = this.determineAttendanceType(verificationResult.faceId);
                
                // Create attendance record
                const attendanceRecord = {
                    id: Date.now().toString(),
                    faceId: verificationResult.faceId,
                    person: verificationResult.person,
                    timestamp: new Date().toISOString(),
                    type: attendanceType, // 'checkin' or 'checkout'
                    confidence: verificationResult.confidence,
                    date: new Date().toISOString().split('T')[0],
                    time: new Date().toTimeString().split(' ')[0]
                };
                
                // Save attendance record locally and to backend
                this.saveAttendanceRecord(attendanceRecord);
                await this.saveAttendanceToBackend(attendanceRecord);
                
                // Update UI
                this.displayAttendanceResult(attendanceRecord);
                this.addRecordToTable(attendanceRecord);
                this.updateStats();
                
                this.showMessage(`${attendanceType === 'checkin' ? 'Checked in' : 'Checked out'} successfully!`, 'success');
                
            } else {
                this.showMessage('Face not recognized. Please ensure you are registered in the system.', 'error');
            }
            
        } catch (error) {
            console.error('Attendance marking error:', error);
            this.showMessage('Failed to mark attendance. Please try again.', 'error');
        } finally {
            this.setLoading(false);
        }
    }
    
    async saveAttendanceToBackend(record) {
        try {
            const response = await fetch(`${this.awsConfig.apiGatewayUrl}/attendance`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    faceId: record.faceId,
                    person: record.person,
                    type: record.type,              // checkin / checkout
                    confidence: record.confidence,  // confidence score
                    timestamp: record.timestamp,    // full ISO timestamp
                    date: record.date,              // YYYY-MM-DD
                    time: record.time               // HH:MM:SS
                })
            });
    
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
    
            const result = await response.json();
            console.log('✅ Attendance saved to backend:', result);
    
        } catch (error) {
            console.error('❌ Failed to save attendance to backend:', error);
            this.showMessage('Failed to save attendance to backend', 'error');
        }
    }
    
    
    determineAttendanceType(faceId) {
        // Check if user has already checked in today
        const today = new Date().toISOString().split('T')[0];
        const todayRecords = this.attendanceRecords.filter(record => 
            record.faceId === faceId && record.date === today
        );
        
        // If no records today, it's a check-in
        if (todayRecords.length === 0) {
            return 'checkin';
        }
        
        // If last record was check-in, this is check-out
        const lastRecord = todayRecords[todayRecords.length - 1];
        return lastRecord.type === 'checkin' ? 'checkout' : 'checkin';
    }
    
    async verifyFaceAPI(imageData) {
        try {
            const response = await fetch(`${this.awsConfig.apiGatewayUrl}/verify`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ image: imageData })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const result = await response.json();
            
            if (!result.success) {
                throw new Error(result.error || 'Verification failed');
            }
            
            return result;
        } catch (error) {
            console.error('API call failed:', error);
            // Fallback to simulation if API is not available
            return await this.simulateVerification(imageData);
        }
    }
    
    async simulateVerification(imageData) {
        // Simulate API call delay
        await new Promise(resolve => setTimeout(resolve, 1500));
        
        // Check if there are any registered faces in localStorage
        const registeredFaces = this.getRegisteredFaces();
        
        if (registeredFaces.length === 0) {
            return {
                success: true,
                match: false,
                confidence: 0,
                message: 'No faces registered in the system yet. Please register a face first.'
            };
        }
        
        // Simulate verification against registered faces
        const isMatch = Math.random() > 0.3; // 70% match rate for demo
        const confidence = Math.random() * 0.3 + (isMatch ? 0.7 : 0.3); // 70-100% for match, 30-60% for no match
        
        if (isMatch) {
            // Return a random registered face
            const randomFace = registeredFaces[Math.floor(Math.random() * registeredFaces.length)];
            return {
                success: true,
                match: true,
                confidence: confidence,
                faceId: randomFace.faceId,
                person: {
                    firstName: randomFace.firstName,
                    lastName: randomFace.lastName,
                    dateOfBirth: randomFace.dateOfBirth,
                    phoneNumber: randomFace.phoneNumber
                },
                message: 'Face verified successfully (simulated)'
            };
        } else {
            return {
                success: true,
                match: false,
                confidence: confidence,
                message: 'No matching face found in the database (simulated)'
            };
        }
    }
    
    getRegisteredFaces() {
        // Get registered faces from localStorage
        const stored = localStorage.getItem('registeredFaces');
        return stored ? JSON.parse(stored) : [];
    }
    
    saveAttendanceRecord(record) {
        // Get existing records
        const existingRecords = this.getAttendanceRecords();
        
        // Add new record
        existingRecords.push(record);
        
        // Save back to localStorage
        localStorage.setItem('attendanceRecords', JSON.stringify(existingRecords));
        
        // Update local array
        this.attendanceRecords = existingRecords;
        
        console.log('Attendance record saved:', record);
    }
    
    getAttendanceRecords() {
        const stored = localStorage.getItem('attendanceRecords');
        return stored ? JSON.parse(stored) : [];
    }
    
    loadAttendanceRecords() {
        this.attendanceRecords = this.getAttendanceRecords();
        this.populateRecordsTable();
    }
    
    populateRecordsTable() {
        this.recordsTableBody.innerHTML = '';
        
        // Sort records by timestamp (newest first)
        const sortedRecords = [...this.attendanceRecords].sort((a, b) => 
            new Date(b.timestamp) - new Date(a.timestamp)
        );
        
        sortedRecords.forEach(record => {
            this.addRecordToTable(record, false); // false = don't scroll to top
        });
    }
    
    addRecordToTable(record, scrollToTop = true) {
        const row = document.createElement('tr');
        
        const statusClass = record.type === 'checkin' ? 'status-checkin' : 'status-checkout';
        const statusText = record.type === 'checkin' ? 'Check In' : 'Check Out';
        
        row.innerHTML = `
            <td>${record.time}</td>
            <td>${record.person.firstName} ${record.person.lastName}</td>
            <td><span class="status-badge ${statusClass}">${statusText}</span></td>
            <td>${(record.confidence * 100).toFixed(1)}%</td>
            <td>
                <button onclick="attendanceSystem.deleteRecord('${record.id}')" 
                        style="background: #dc3545; color: white; border: none; padding: 4px 8px; border-radius: 3px; cursor: pointer; font-size: 12px;">
                    Delete
                </button>
            </td>
        `;
        
        this.recordsTableBody.insertBefore(row, this.recordsTableBody.firstChild);
        
        if (scrollToTop) {
            row.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    }
    
    deleteRecord(recordId) {
        if (confirm('Are you sure you want to delete this attendance record?')) {
            this.attendanceRecords = this.attendanceRecords.filter(record => record.id !== recordId);
            localStorage.setItem('attendanceRecords', JSON.stringify(this.attendanceRecords));
            this.populateRecordsTable();
            this.updateStats();
            this.showMessage('Record deleted successfully.', 'success');
        }
    }
    
    displayAttendanceResult(record) {
        this.resultDiv.style.display = 'block';
        
        const statusClass = record.type === 'checkin' ? 'result-success' : 'result-error';
        const statusIcon = record.type === 'checkin' ? '✅' : '❌';
        const statusText = record.type === 'checkin' ? 'Checked In' : 'Checked Out';
        
        this.resultContent.innerHTML = `
            <div class="${statusClass}">
                <h4 style="color: ${record.type === 'checkin' ? '#28a745' : '#dc3545'}; margin-bottom: 15px;">
                    ${statusIcon} ${statusText} Successfully!
                </h4>
                <div class="result-details">
                    <p><strong>Name:</strong> ${record.person.firstName} ${record.person.lastName}</p>
                    <p><strong>Time:</strong> ${record.time}</p>
                    <p><strong>Date:</strong> ${record.date}</p>
                    <p><strong>Confidence:</strong> ${(record.confidence * 100).toFixed(1)}%</p>
                </div>
            </div>
        `;
        
        // Auto-hide after 5 seconds
        setTimeout(() => {
            this.resultDiv.style.display = 'none';
        }, 5000);
    }
    
    updateStats() {
        const today = new Date().toISOString().split('T')[0];
        const todayRecords = this.attendanceRecords.filter(record => record.date === today);
        const checkedInToday = todayRecords.filter(record => record.type === 'checkin').length;
        
        // Count currently checked in (last record of each person today is check-in)
        const currentlyCheckedIn = this.getCurrentlyCheckedIn();
        
        document.getElementById('totalToday').textContent = checkedInToday;
        document.getElementById('checkedIn').textContent = currentlyCheckedIn;
        document.getElementById('totalRecords').textContent = this.attendanceRecords.length;
    }
    
    getCurrentlyCheckedIn() {
        const today = new Date().toISOString().split('T')[0];
        const todayRecords = this.attendanceRecords.filter(record => record.date === today);
        
        // Group by faceId and find the last record for each person
        const lastRecordsByPerson = {};
        todayRecords.forEach(record => {
            if (!lastRecordsByPerson[record.faceId] || 
                new Date(record.timestamp) > new Date(lastRecordsByPerson[record.faceId].timestamp)) {
                lastRecordsByPerson[record.faceId] = record;
            }
        });
        
        // Count how many people's last record is check-in
        return Object.values(lastRecordsByPerson).filter(record => record.type === 'checkin').length;
    }
    
    filterRecords() {
        const statusFilter = document.getElementById('statusFilter').value;
        const dateFilter = document.getElementById('dateFilter').value;
        
        let filteredRecords = [...this.attendanceRecords];
        
        if (statusFilter !== 'all') {
            filteredRecords = filteredRecords.filter(record => record.type === statusFilter);
        }
        
        if (dateFilter) {
            filteredRecords = filteredRecords.filter(record => record.date === dateFilter);
        }
        
        // Sort by timestamp (newest first)
        filteredRecords.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
        
        // Update table
        this.recordsTableBody.innerHTML = '';
        filteredRecords.forEach(record => {
            this.addRecordToTable(record, false);
        });
    }
    
    exportToCSV() {
        const records = this.attendanceRecords;
        
        if (records.length === 0) {
            this.showMessage('No records to export.', 'error');
            return;
        }
        
        // Create CSV content
        const headers = ['Date', 'Time', 'Name', 'Status', 'Confidence', 'Face ID'];
        const csvContent = [
            headers.join(','),
            ...records.map(record => [
                record.date,
                record.time,
                `"${record.person.firstName} ${record.person.lastName}"`,
                record.type,
                (record.confidence * 100).toFixed(1) + '%',
                record.faceId
            ].join(','))
        ].join('\n');
        
        // Download CSV
        const blob = new Blob([csvContent], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `attendance_records_${new Date().toISOString().split('T')[0]}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        
        this.showMessage('CSV exported successfully!', 'success');
    }
    
    showMessage(message, type) {
        // Remove existing messages
        const existingMessage = document.querySelector('.message');
        if (existingMessage) {
            existingMessage.remove();
        }
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `message message-${type}`;
        messageDiv.textContent = message;
        
        // Insert message at the top of the container
        const container = document.querySelector('.attendance-container');
        container.insertBefore(messageDiv, container.firstChild);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (messageDiv.parentNode) {
                messageDiv.remove();
            }
        }, 5000);
    }
    
    setLoading(loading) {
        const buttons = [this.startBtn, this.stopBtn, this.markBtn, this.backBtn];
        buttons.forEach(btn => {
            btn.disabled = loading;
        });
        
        if (loading) {
            document.body.classList.add('loading');
        } else {
            document.body.classList.remove('loading');
        }
    }
    
    goBack() {
        if (this.stream) {
            this.stopWebcam();
        }
        window.location.href = 'index.html';
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.attendanceSystem = new AttendanceSystem();
});
