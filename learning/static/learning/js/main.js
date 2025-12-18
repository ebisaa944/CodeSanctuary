// Therapeutic Coding - Main JavaScript File

// Wait for DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('Therapeutic Coding JS loaded');
    
    // Initialize all components
    initializeTheme();
    initializeMoodSelector();
    initializeProgressBars();
    initializeBreathingExercise();
    initializeFormValidation();
    initializeNotifications();
    initializeSmoothScrolling();
    initializeActivityTracking();
});

// Theme Management
function initializeTheme() {
    const themeToggle = document.getElementById('themeToggle');
    const prefersDarkScheme = window.matchMedia('(prefers-color-scheme: dark)');
    
    // Check for saved theme preference
    const savedTheme = localStorage.getItem('theme');
    const currentTheme = savedTheme || (prefersDarkScheme.matches ? 'dark' : 'light');
    
    // Apply theme
    if (currentTheme === 'dark') {
        document.body.classList.add('dark-theme');
    }
    
    // Toggle theme
    if (themeToggle) {
        themeToggle.addEventListener('click', function() {
            document.body.classList.toggle('dark-theme');
            const theme = document.body.classList.contains('dark-theme') ? 'dark' : 'light';
            localStorage.setItem('theme', theme);
            
            // Show theme change notification
            showNotification(`Theme changed to ${theme} mode`, 'success');
        });
    }
}

// Mood Tracking
function initializeMoodSelector() {
    const moodButtons = document.querySelectorAll('.mood-btn');
    const moodInput = document.getElementById('moodInput');
    
    moodButtons.forEach(button => {
        button.addEventListener('click', function() {
            // Remove active class from all buttons
            moodButtons.forEach(btn => btn.classList.remove('active'));
            
            // Add active class to clicked button
            this.classList.add('active');
            
            // Get mood value
            const mood = this.dataset.mood;
            
            // Update hidden input if exists
            if (moodInput) {
                moodInput.value = mood;
            }
            
            // Save mood to localStorage
            saveMood(mood);
            
            // Show feedback based on mood
            showMoodFeedback(mood);
        });
    });
    
    // Load last saved mood
    const lastMood = localStorage.getItem('lastMood');
    if (lastMood) {
        const lastMoodBtn = document.querySelector(`.mood-btn[data-mood="${lastMood}"]`);
        if (lastMoodBtn) {
            lastMoodBtn.classList.add('active');
            if (moodInput) moodInput.value = lastMood;
        }
    }
}

function saveMood(mood) {
    // Save to localStorage
    localStorage.setItem('lastMood', mood);
    localStorage.setItem('lastMoodTime', new Date().toISOString());
    
    // You could also send to server
    console.log('Mood saved:', mood);
}

function showMoodFeedback(mood) {
    const messages = {
        'happy': '😊 Great to see you\'re happy! Keep that positive energy!',
        'neutral': '😐 It\'s okay to feel neutral. Take a deep breath and continue.',
        'stressed': '😰 Stress is temporary. Remember to breathe and take breaks.',
        'sad': '😔 It\'s okay to feel sad. Be gentle with yourself today.',
        'excited': '🎉 Exciting! Channel that energy into learning!'
    };
    
    if (messages[mood]) {
        showNotification(messages[mood], 'info');
    }
}

// Progress Tracking
function initializeProgressBars() {
    const progressBars = document.querySelectorAll('.progress-fill');
    
    progressBars.forEach(bar => {
        const targetWidth = bar.dataset.progress || '0';
        
        // Animate progress bar
        setTimeout(() => {
            bar.style.width = targetWidth + '%';
        }, 300);
        
        // Add percentage text
        const percentageText = document.createElement('span');
        percentageText.className = 'progress-text';
        percentageText.textContent = targetWidth + '%';
        bar.parentElement.appendChild(percentageText);
    });
}

// Breathing Exercise
function initializeBreathingExercise() {
    const breathingBtn = document.getElementById('startBreathing');
    const breathingCircle = document.querySelector('.breathing-circle');
    
    if (breathingBtn && breathingCircle) {
        let isBreathing = false;
        let breathInterval;
        
        breathingBtn.addEventListener('click', function() {
            if (!isBreathing) {
                // Start breathing exercise
                isBreathing = true;
                this.textContent = 'Stop Breathing Exercise';
                breathingCircle.style.animation = 'breathe 4s infinite ease-in-out';
                
                // Add instructions
                const instructions = document.createElement('div');
                instructions.className = 'breathing-instructions mt-2';
                instructions.innerHTML = `
                    <p>Breathe in as the circle expands...</p>
                    <p>Breathe out as the circle contracts...</p>
                    <p>Repeat for 1 minute...</p>
                `;
                breathingCircle.parentElement.appendChild(instructions);
                
                // Stop after 1 minute
                breathInterval = setTimeout(() => {
                    stopBreathingExercise();
                }, 60000);
            } else {
                stopBreathingExercise();
            }
        });
        
        function stopBreathingExercise() {
            isBreathing = false;
            breathingBtn.textContent = 'Start Breathing Exercise';
            breathingCircle.style.animation = 'none';
            
            const instructions = document.querySelector('.breathing-instructions');
            if (instructions) instructions.remove();
            
            if (breathInterval) clearTimeout(breathInterval);
            
            showNotification('Great job! Take a moment to notice how you feel.', 'success');
        }
    }
}

// Form Validation
function initializeFormValidation() {
    const forms = document.querySelectorAll('.needs-validation');
    
    forms.forEach(form => {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
                
                // Highlight invalid fields
                const invalidFields = form.querySelectorAll(':invalid');
                invalidFields.forEach(field => {
                    field.classList.add('is-invalid');
                    
                    // Add error message
                    const feedback = document.createElement('div');
                    feedback.className = 'invalid-feedback';
                    feedback.textContent = field.validationMessage;
                    field.parentElement.appendChild(feedback);
                });
            } else {
                // Form is valid - show loading state
                const submitBtn = form.querySelector('[type="submit"]');
                if (submitBtn) {
                    submitBtn.disabled = true;
                    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
                }
            }
            
            form.classList.add('was-validated');
        }, false);
    });
    
    // Real-time validation
    const inputs = document.querySelectorAll('.form-control');
    inputs.forEach(input => {
        input.addEventListener('input', function() {
            if (this.classList.contains('is-invalid')) {
                this.classList.remove('is-invalid');
                const feedback = this.parentElement.querySelector('.invalid-feedback');
                if (feedback) feedback.remove();
            }
        });
    });
}

// Notifications System
function initializeNotifications() {
    // Create notification container if it doesn't exist
    if (!document.getElementById('notification-container')) {
        const container = document.createElement('div');
        container.id = 'notification-container';
        container.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 9999;
            max-width: 300px;
        `;
        document.body.appendChild(container);
    }
}

function showNotification(message, type = 'info') {
    const container = document.getElementById('notification-container');
    const notification = document.createElement('div');
    
    const icons = {
        'success': '✅',
        'error': '❌',
        'warning': '⚠️',
        'info': 'ℹ️'
    };
    
    notification.className = `alert alert-${type} fade-in`;
    notification.innerHTML = `
        ${icons[type] || 'ℹ️'} ${message}
    `;
    
    container.appendChild(notification);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        notification.style.opacity = '0';
        notification.style.transform = 'translateX(100%)';
        setTimeout(() => notification.remove(), 300);
    }, 5000);
    
    // Allow click to dismiss
    notification.addEventListener('click', () => {
        notification.style.opacity = '0';
        notification.style.transform = 'translateX(100%)';
        setTimeout(() => notification.remove(), 300);
    });
}

// Smooth Scrolling
function initializeSmoothScrolling() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            
            const targetId = this.getAttribute('href');
            if (targetId === '#') return;
            
            const targetElement = document.querySelector(targetId);
            if (targetElement) {
                window.scrollTo({
                    top: targetElement.offsetTop - 80,
                    behavior: 'smooth'
                });
            }
        });
    });
}

// Activity Tracking
function initializeActivityTracking() {
    // Track time spent on page
    let startTime = new Date();
    let activeTime = 0;
    
    // Update active time every minute
    setInterval(() => {
        activeTime++;
        
        // Save to localStorage
        const today = new Date().toDateString();
        const storedTime = parseInt(localStorage.getItem(`activeTime_${today}`)) || 0;
        localStorage.setItem(`activeTime_${today}`, storedTime + 1);
        
        // Show encouragement every 15 minutes
        if (activeTime % 15 === 0) {
            const encouragements = [
                "Great focus! You've been learning for a while. Consider taking a short break.",
                "Amazing dedication! Remember to stay hydrated.",
                "You're doing great! How about a quick stretch?",
                "Keep up the good work! Learning takes time and patience."
            ];
            const randomEncouragement = encouragements[Math.floor(Math.random() * encouragements.length)];
            showNotification(randomEncouragement, 'info');
        }
    }, 60000); // Every minute
    
    // Mark activity as complete
    const completeButtons = document.querySelectorAll('.mark-complete');
    completeButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            
            if (confirm('Mark this activity as complete?')) {
                const activityId = this.dataset.activityId;
                
                // Show loading
                this.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Completing...';
                this.disabled = true;
                
                // Simulate API call
                setTimeout(() => {
                    this.innerHTML = '<i class="fas fa-check"></i> Completed!';
                    showNotification('Activity marked as complete! Great job!', 'success');
                    
                    // Update progress
                    updateProgressBar(activityId);
                }, 1000);
            }
        });
    });
}

function updateProgressBar(activityId) {
    // Find and update the relevant progress bar
    const progressBar = document.querySelector(`.progress-fill[data-activity="${activityId}"]`);
    if (progressBar) {
        const currentProgress = parseInt(progressBar.style.width) || 0;
        const newProgress = Math.min(currentProgress + 25, 100);
        
        progressBar.style.width = newProgress + '%';
        progressBar.textContent = newProgress + '%';
        
        // Update overall progress if exists
        const overallProgress = document.querySelector('.overall-progress');
        if (overallProgress) {
            const overallCurrent = parseInt(overallProgress.dataset.progress) || 0;
            const overallNew = Math.min(overallCurrent + 5, 100);
            overallProgress.dataset.progress = overallNew;
            overallProgress.style.width = overallNew + '%';
            overallProgress.textContent = overallNew + '%';
        }
    }
}

// Session Timer
class SessionTimer {
    constructor(duration = 25) {
        this.duration = duration * 60; // Convert to seconds
        this.remaining = this.duration;
        this.isRunning = false;
        this.timerInterval = null;
        this.init();
    }
    
    init() {
        const timerContainer = document.getElementById('sessionTimer');
        if (!timerContainer) return;
        
        timerContainer.innerHTML = `
            <div class="timer-display">
                <span class="timer-minutes">${Math.floor(this.duration / 60)}</span>:<span class="timer-seconds">00</span>
            </div>
            <div class="timer-controls">
                <button class="btn btn-primary" id="startTimer">Start Session</button>
                <button class="btn btn-secondary" id="pauseTimer">Pause</button>
                <button class="btn btn-outline" id="resetTimer">Reset</button>
            </div>
            <div class="timer-status">Ready to start your focus session</div>
        `;
        
        this.bindEvents();
    }
    
    bindEvents() {
        document.getElementById('startTimer')?.addEventListener('click', () => this.start());
        document.getElementById('pauseTimer')?.addEventListener('click', () => this.pause());
        document.getElementById('resetTimer')?.addEventListener('click', () => this.reset());
    }
    
    start() {
        if (!this.isRunning) {
            this.isRunning = true;
            this.timerInterval = setInterval(() => this.tick(), 1000);
            showNotification('Focus session started!', 'success');
        }
    }
    
    pause() {
        this.isRunning = false;
        if (this.timerInterval) {
            clearInterval(this.timerInterval);
            showNotification('Session paused', 'warning');
        }
    }
    
    reset() {
        this.pause();
        this.remaining = this.duration;
        this.updateDisplay();
        showNotification('Session reset', 'info');
    }
    
    tick() {
        this.remaining--;
        this.updateDisplay();
        
        if (this.remaining <= 0) {
            this.complete();
        }
    }
    
    updateDisplay() {
        const minutes = Math.floor(this.remaining / 60);
        const seconds = this.remaining % 60;
        
        const minDisplay = document.querySelector('.timer-minutes');
        const secDisplay = document.querySelector('.timer-seconds');
        
        if (minDisplay) minDisplay.textContent = minutes.toString().padStart(2, '0');
        if (secDisplay) secDisplay.textContent = seconds.toString().padStart(2, '0');
    }
    
    complete() {
        this.pause();
        showNotification('🎉 Session complete! Time for a break!', 'success');
        
        // Play notification sound if available
        this.playCompletionSound();
    }
    
    playCompletionSound() {
        // Simple beep sound
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const oscillator = audioContext.createOscillator();
        const gainNode = audioContext.createGain();
        
        oscillator.connect(gainNode);
        gainNode.connect(audioContext.destination);
        
        oscillator.frequency.value = 800;
        oscillator.type = 'sine';
        
        gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 1);
        
        oscillator.start(audioContext.currentTime);
        oscillator.stop(audioContext.currentTime + 1);
    }
}

// Initialize timer when page loads
document.addEventListener('DOMContentLoaded', function() {
    const timer = new SessionTimer(25); // 25-minute Pomodoro timer
    
    // Add keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        // Ctrl/Cmd + Shift + T to toggle timer
        if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'T') {
            e.preventDefault();
            if (timer.isRunning) {
                timer.pause();
            } else {
                timer.start();
            }
        }
        
        // Escape to close notifications
        if (e.key === 'Escape') {
            const notifications = document.querySelectorAll('.alert');
            notifications.forEach(notification => {
                notification.style.opacity = '0';
                setTimeout(() => notification.remove(), 300);
            });
        }
    });
});

// Export utility functions for use in other modules
window.TherapeuticCoding = {
    showNotification,
    saveMood,
    updateProgressBar,
    initializeTheme,
    initializeMoodSelector
};