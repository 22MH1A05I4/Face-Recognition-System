// Verify Face JavaScript functionality with AWS integration
class FaceVerify {
    constructor() {
        this.video = document.getElementById('video');
        this.canvas = document.getElementById('canvas');
        this.cameraPlaceholder = document.getElementById('camera-placeholder');
        this.startBtn = document.getElementById('startWebcam');
        this.stopBtn = document.getElementById('stopWebcam');
        this.verifyBtn = document.getElementById('verifyImage');
        this.clearBtn = document.getElementById('clearImage');
        this.backBtn = document.getElementById('backBtn');
        this.resultDiv = document.getElementById('verificationResult');
        this.resultContent = document.getElementById('resultContent');
        
        this.stream = null;
        this.capturedImage = null;
        
        // AWS Configuration
        this.awsConfig = {
            region: 'us-east-1',
            apiGatewayUrl: 'https://58z5i6ahil.execute-api.us-east-1.amazonaws.com/prod' // Replace with your actual API Gateway URL
        };
        
        this.initializeEventListeners();
    }
    
    initializeEventListeners() {
        this.startBtn.addEventListener('click', () => this.startWebcam());
        this.stopBtn.addEventListener('click', () => this.stopWebcam());
        this.verifyBtn.addEventListener('click', () => this.verifyImage());
        this.clearBtn.addEventListener('click', () => this.clearImage());
        this.backBtn.addEventListener('click', () => this.goBack());
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
                this.verifyBtn.disabled = false;
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
        this.verifyBtn.disabled = true;
        
        // Hide result when stopping webcam
        this.resultDiv.style.display = 'none';
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
    }
    
    async verifyImage() {
        if (!this.stream) {
            this.showMessage('Please start the webcam first.', 'error');
            return;
        }
        
        // Capture image first
        this.captureImage();
        
        if (!this.capturedImage) {
            return;
        }
        
        try {
            this.showMessage('Verifying face...', 'info');
            this.setLoading(true);
            
            // Call AWS API Gateway
            const result = await this.verifyFaceAPI(this.capturedImage);
            
            this.displayResult(result);
            
        } catch (error) {
            console.error('Verification error:', error);
            this.showMessage('Verification failed. Please try again.', 'error');
        } finally {
            this.setLoading(false);
        }
    }
    
    clearImage() {
        this.capturedImage = null;
        const context = this.canvas.getContext('2d');
        context.clearRect(0, 0, this.canvas.width, this.canvas.height);
        
        this.showMessage('Image cleared.', 'info');
        this.resultDiv.style.display = 'none';
    }
    
    async verifyFaceAPI(imageData) {
        console.log('🔍 Calling real API...');
        console.log('API URL:', this.awsConfig.apiGatewayUrl);
        
        try {
            const response = await fetch(`${this.awsConfig.apiGatewayUrl}/verify`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ image: imageData })
            });
            
            console.log('Response status:', response.status);
            
            if (!response.ok) {
                const errorText = await response.text();
                console.error('API Error Response:', errorText);
                throw new Error(`HTTP error! status: ${response.status}, message: ${errorText}`);
            }
            
            const result = await response.json();
            console.log('API Response:', result);
            
            return result;
            
        } catch (error) {
            console.error('API call failed:', error);
            return {
                success: false,
                match: false,
                confidence: 0,
                message: error.message
            };
        }
    }
    
    displayResult(result) {
        this.resultDiv.style.display = 'block';
        
        // Ensure confidence is always a number
        const confidence = typeof result.confidence === 'number' ? result.confidence : 0;
        
        if (result.match) {
            this.resultContent.innerHTML = `
                <div class="result-success">
                    <h4 style="color: #28a745; margin-bottom: 15px;">✅ Face Verified Successfully!</h4>
                    <div class="result-details">
                        <p><strong>Confidence:</strong> ${confidence.toFixed(1)}%</p>
                        <p><strong>Face ID:</strong> ${result.faceId || 'N/A'}</p>
                        <hr style="margin: 15px 0; border: none; border-top: 1px solid #dee2e6;">
                        <h5 style="color: #2c3e50; margin-bottom: 10px;">Person Details:</h5>
                        <p><strong>Name:</strong> ${(result.person?.firstName || 'Unknown')} ${(result.person?.lastName || '')}</p>
                        <p><strong>Date of Birth:</strong> ${result.person?.dateOfBirth || 'Unknown'}</p>
                        <p><strong>Phone:</strong> ${result.person?.phoneNumber || 'Unknown'}</p>
                        ${result.message ? `<p style="margin-top: 10px; font-style: italic; color: #6c757d;">${result.message}</p>` : ''}
                    </div>
                </div>
            `;
        } else {
            this.resultContent.innerHTML = `
                <div class="result-error">
                    <h4 style="color: #dc3545; margin-bottom: 15px;">❌ Face Not Recognized</h4>
                    <div class="result-details">
                        <p><strong>Confidence:</strong> ${confidence.toFixed(1)}%</p>
                        <p><strong>Message:</strong> ${result.message || 'No match found'}</p>
                        <p style="margin-top: 15px; color: #6c757d;">
                            Please ensure your face is clearly visible and well-lit, then try again.
                        </p>
                    </div>
                </div>
            `;
        }
    }
    
    showMessage(message, type) {
        const existingMessage = document.querySelector('.message');
        if (existingMessage) {
            existingMessage.remove();
        }
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `message message-${type}`;
        messageDiv.textContent = message;
        
        const cameraControls = document.querySelector('.camera-controls');
        cameraControls.parentNode.insertBefore(messageDiv, cameraControls);
        
        setTimeout(() => {
            if (messageDiv.parentNode) {
                messageDiv.remove();
            }
        }, 5000);
    }
    
    setLoading(loading) {
        const buttons = [this.startBtn, this.stopBtn, this.verifyBtn, this.clearBtn, this.backBtn];
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
    new FaceVerify();
});
