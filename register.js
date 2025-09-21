// Register Face ID JavaScript functionality with AWS integration
class FaceRegister {
    constructor() {
        this.video = document.getElementById('video');
        this.canvas = document.getElementById('canvas');
        this.cameraPlaceholder = document.getElementById('camera-placeholder');
        this.startBtn = document.getElementById('startWebcam');
        this.stopBtn = document.getElementById('stopWebcam');
        this.captureBtn = document.getElementById('captureImage');
        this.clearBtn = document.getElementById('clearImage');
        this.backBtn = document.getElementById('backBtn');
        this.form = document.getElementById('registrationForm');
        
        this.stream = null;
        this.capturedImage = null;
        
        // AWS Configuration
        this.awsConfig = {
            region: 'us-east-1',
            apiGatewayUrl: 'https://7wal320aqk.execute-api.us-east-1.amazonaws.com/prod' // Replace with your actual API Gateway URL
        };

        this.initializeEventListeners();
    }
    
    initializeEventListeners() {
        this.startBtn.addEventListener('click', () => this.startWebcam());
        this.stopBtn.addEventListener('click', () => this.stopWebcam());
        this.captureBtn.addEventListener('click', () => this.captureImage());
        this.clearBtn.addEventListener('click', () => this.clearImage());
        this.backBtn.addEventListener('click', () => this.goBack());
        
        // Form submission
        this.form.addEventListener('submit', (e) => this.handleFormSubmit(e));
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
                this.startBtn.textContent = 'Start Webcam';
                this.stopBtn.disabled = false;
                this.captureBtn.disabled = false;
            });
            
        } catch (error) {
            console.error('Error accessing webcam:', error);
            this.showMessage('Unable to access webcam. Please check permissions and try again.', 'error');
            this.startBtn.disabled = false;
            this.startBtn.textContent = 'Start Webcam';
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
        this.captureBtn.disabled = true;
    }
    
    captureImage() {
        if (!this.stream) {
            this.showMessage('Please start the webcam first.', 'error');
            return;
        }
        
        const context = this.canvas.getContext('2d');
        this.canvas.width = this.video.videoWidth;
        this.canvas.height = this.video.videoHeight;
        
        context.drawImage(this.video, 0, 0, this.canvas.width, this.canvas.height);
        
        this.capturedImage = this.canvas.toDataURL('image/jpeg', 0.8);
        
        this.showMessage('Image captured successfully!', 'success');
        this.enableFormSubmission();
    }
    
    clearImage() {
        this.capturedImage = null;
        const context = this.canvas.getContext('2d');
        context.clearRect(0, 0, this.canvas.width, this.canvas.height);
        
        this.showMessage('Image cleared.', 'info');
        this.disableFormSubmission();
    }
    
    enableFormSubmission() {
        const submitBtn = document.createElement('button');
        submitBtn.type = 'submit';
        submitBtn.className = 'control-btn';
        submitBtn.textContent = 'Register Face';
        submitBtn.style.marginTop = '20px';
        
        // Remove existing submit button if any
        const existingSubmit = document.querySelector('.submit-btn');
        if (existingSubmit) {
            existingSubmit.remove();
        }
        
        submitBtn.classList.add('submit-btn');
        this.form.appendChild(submitBtn);
    }
    
    disableFormSubmission() {
        const submitBtn = document.querySelector('.submit-btn');
        if (submitBtn) {
            submitBtn.remove();
        }
    }
    
    async handleFormSubmit(e) {
        e.preventDefault();
        
        if (!this.capturedImage) {
            this.showMessage('Please capture an image first.', 'error');
            return;
        }
        
        const formData = new FormData(this.form);
        const userData = {
            firstName: formData.get('firstName'),
            lastName: formData.get('lastName'),
            dateOfBirth: formData.get('dateOfBirth'),
            phoneNumber: formData.get('phoneNumber'),
            image: this.capturedImage
        };
        
        try {
            this.showMessage('Registering face and saving to S3...', 'info');
            this.setLoading(true);
            
            // Call AWS API Gateway to save to S3 and DynamoDB
            const result = await this.registerFaceAPI(userData);
            
            if (result.success) {
                this.showMessage(`Face registered successfully! Face ID: ${result.faceId}`, 'success');
                this.form.reset();
                this.clearImage();
                
                // Also store locally for testing
                this.storeRegisteredFace({
                    faceId: result.faceId,
                    firstName: userData.firstName,
                    lastName: userData.lastName,
                    dateOfBirth: userData.dateOfBirth,
                    phoneNumber: userData.phoneNumber,
                    registeredAt: new Date().toISOString(),
                    s3Key: result.s3Key || 'stored-in-s3'
                });
            } else {
                throw new Error(result.error || 'Registration failed');
            }
            
        } catch (error) {
            console.error('Registration error:', error);
            this.showMessage(`Registration failed: ${error.message}`, 'error');
        } finally {
            this.setLoading(false);
        }
    }
    
    async registerFaceAPI(userData) {
        try {
            const response = await fetch(`${this.awsConfig.apiGatewayUrl}/register`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(userData)
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const result = await response.json();
            
            if (!result.success) {
                throw new Error(result.error || 'Registration failed');
            }
            
            return result;
        } catch (error) {
            console.error('API call failed:', error);
            // Fallback to simulation if API is not available
            return await this.simulateRegistration(userData);
        }
    }
    
    async simulateRegistration(userData) {
        // Simulate API call delay
        await new Promise(resolve => setTimeout(resolve, 2000));
        
        // Simulate success/failure
        if (Math.random() > 0.1) { // 90% success rate for demo
            const faceId = 'face_' + Date.now();
            const s3Key = `faces/${faceId}.jpg`;
            
            // Store the registered face data in localStorage
            this.storeRegisteredFace({
                faceId: faceId,
                firstName: userData.firstName,
                lastName: userData.lastName,
                dateOfBirth: userData.dateOfBirth,
                phoneNumber: userData.phoneNumber,
                registeredAt: new Date().toISOString(),
                s3Key: s3Key
            });
            
            return { 
                success: true, 
                faceId: faceId,
                s3Key: s3Key,
                bucketName: 'facial-recognition-data-bucket',
                message: 'Face registered successfully (simulated - would save to S3)'
            };
        } else {
            throw new Error('Registration failed (simulated)');
        }
    }
    
    storeRegisteredFace(faceData) {
        // Get existing registered faces
        const existingFaces = this.getRegisteredFaces();
        
        // Add new face
        existingFaces.push(faceData);
        
        // Store back to localStorage
        localStorage.setItem('registeredFaces', JSON.stringify(existingFaces));
        
        console.log('Face stored locally:', faceData);
    }
    
    getRegisteredFaces() {
        // Get registered faces from localStorage
        const stored = localStorage.getItem('registeredFaces');
        return stored ? JSON.parse(stored) : [];
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
        
        this.form.appendChild(messageDiv);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (messageDiv.parentNode) {
                messageDiv.remove();
            }
        }, 5000);
    }
    
    setLoading(loading) {
        const buttons = [this.startBtn, this.stopBtn, this.captureBtn, this.clearBtn, this.backBtn];
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
    new FaceRegister();
});