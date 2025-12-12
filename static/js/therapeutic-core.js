// static/js/therapeutic-core.js
class TherapeuticApp {
    constructor() {
        this.gentleMode = localStorage.getItem('gentleMode') === 'true';
        this.highContrast = localStorage.getItem('highContrast') === 'true';
        this.init();
    }

    init() {
        this.applySettings();
        this.setupEventListeners();
        this.setupGentleReminders();
        this.setupEmotionalTracking();
        this.checkPageLoadTime();
    }

    applySettings() {
        if (this.gentleMode) {
            document.body.classList.add('gentle-mode');
        }
        if (this.highContrast) {
            document.body.classList.add('high-contrast');
        }
    }

    setupEventListeners() {
        // Gentle mode toggle
        document.querySelectorAll('[data-toggle-gentle]').forEach(btn => {
            btn.addEventListener('click', () => this.toggleGentleMode());
        });

        // High contrast toggle
        document.querySelectorAll('[data-toggle-contrast]').forEach(btn => {
            btn.addEventListener('click', () => this.toggleHighContrast());
        });

        // Emotional buttons
        document.querySelectorAll('.emotion-btn').forEach(btn => {
            btn.addEventListener('click', (e) => this.recordEmotion(e));
        });

        // Gentle form validation
        document.querySelectorAll('form').forEach(form => {
            form.addEventListener('submit', (e) => this.validateForm(e));
        });

        // Smooth scrolling for anchor links
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', (e) => this.smoothScroll(e));
        });
    }

    toggleGentleMode() {
        this.gentleMode = !this.gentleMode;
        document.body.classList.toggle('gentle-mode', this.gentleMode);
        localStorage.setItem('gentleMode', this.gentleMode);
        
        this.showGentleNotification(
            this.gentleMode ? 
            'Gentle mode activated. Take it easy.' : 
            'Gentle mode deactivated. Proceed mindfully.'
        );
    }

    toggleHighContrast() {
        this.highContrast = !this.highContrast;
        document.body.classList.toggle('high-contrast', this.highContrast);
        localStorage.setItem('highContrast', this.highContrast);
    }

    recordEmotion(event) {
        const emotion = event.currentTarget.dataset.emotion;
        const emotionData = {
            emotion: emotion,
            intensity: 5,
            timestamp: new Date().toISOString(),
            page: window.location.pathname
        };

        // Send to server
        if (window.csrfToken) {
            fetch('/api/therapy/quick-checkin/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': window.csrfToken
                },
                body: JSON.stringify(emotionData)
            })
            .then(response => response.json())
            .then(data => {
                this.showGentleNotification(`Recorded feeling ${emotion}. Thank you for checking in.`);
            });
        }

        // Visual feedback
        event.currentTarget.classList.add('animate-pulse');
        setTimeout(() => {
            event.currentTarget.classList.remove('animate-pulse');
        }, 1000);
    }

    validateForm(event) {
        const form = event.target;
        const requiredFields = form.querySelectorAll('[required]');
        let isValid = true;
        let firstInvalid = null;

        requiredFields.forEach(field => {
            if (!field.value.trim()) {
                isValid = false;
                if (!firstInvalid) firstInvalid = field;
                
                // Gentle error indication
                field.classList.add('form-error');
                this.showFieldMessage(field, 'This field is gently required');
            } else {
                field.classList.remove('form-error');
                this.hideFieldMessage(field);
            }
        });

        if (!isValid) {
            event.preventDefault();
            if (firstInvalid) {
                firstInvalid.focus();
            }
            this.showGentleNotification('Please fill in all required fields gently');
        }
    }

    showFieldMessage(field, message) {
        let messageEl = field.nextElementSibling;
        if (!messageEl || !messageEl.classList.contains('field-message')) {
            messageEl = document.createElement('div');
            messageEl.className = 'field-message gentle-error';
            field.parentNode.insertBefore(messageEl, field.nextSibling);
        }
        messageEl.textContent = message;
    }

    hideFieldMessage(field) {
        const messageEl = field.nextElementSibling;
        if (messageEl && messageEl.classList.contains('field-message')) {
            messageEl.remove();
        }
    }

    showGentleNotification(message, type = 'info') {
        const container = document.getElementById('gentle-notifications') || this.createNotificationContainer();
        const notification = document.createElement('div');
        notification.className = `notification notification-${type} animate-float`;
        notification.innerHTML = `
            <i class="fas fa-${this.getNotificationIcon(type)}"></i>
            <span>${message}</span>
            <button class="notification-close" onclick="this.parentElement.remove()">
                <i class="fas fa-times"></i>
            </button>
        `;
        
        container.appendChild(notification);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.style.opacity = '0';
                setTimeout(() => notification.remove(), 300);
            }
        }, 5000);
    }

    createNotificationContainer() {
        const container = document.createElement('div');
        container.id = 'gentle-notifications';
        container.className = 'notifications-container';
        document.body.insertBefore(container, document.body.firstChild);
        return container;
    }

    getNotificationIcon(type) {
        const icons = {
            'info': 'info-circle',
            'success': 'check-circle',
            'warning': 'exclamation-triangle',
            'error': 'exclamation-circle'
        };
        return icons[type] || 'info-circle';
    }

    setupGentleReminders() {
        // Periodic gentle reminders
        setInterval(() => {
            if (this.shouldShowReminder()) {
                const reminders = [
                    "Take a deep breath. You're doing great.",
                    "Remember to hydrate and stretch.",
                    "Progress, not perfection.",
                    "It's okay to take breaks.",
                    "Be kind to yourself today."
                ];
                const randomReminder = reminders[Math.floor(Math.random() * reminders.length)];
                this.showGentleNotification(randomReminder, 'info');
            }
        }, 15 * 60 * 1000); // Every 15 minutes
    }

    shouldShowReminder() {
        // Only show if user is active and not recently notified
        const lastReminder = localStorage.getItem('lastReminderTime');
        if (lastReminder) {
            const timeSinceLast = Date.now() - parseInt(lastReminder);
            return timeSinceLast > 30 * 60 * 1000; // 30 minutes minimum
        }
        return true;
    }

    setupEmotionalTracking() {
        // Track time on page for therapeutic insights
        let pageEnterTime = Date.now();
        
        window.addEventListener('beforeunload', () => {
            const timeSpent = Date.now() - pageEnterTime;
            if (timeSpent > 10000) { // Only track if spent >10 seconds
                this.sendActivityData({
                    page: window.location.pathname,
                    timeSpent: timeSpent,
                    activity: 'page_view'
                });
            }
        });
    }

    sendActivityData(data) {
        if (window.csrfToken) {
            fetch('/api/learning/track-activity/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': window.csrfToken
                },
                body: JSON.stringify(data)
            });
        }
    }

    checkPageLoadTime() {
        const loadTime = window.performance.timing.domContentLoadedEventEnd - window.performance.timing.navigationStart;
        if (loadTime > 3000) {
            this.showGentleNotification('The page is taking a moment to load. Practice patience. 🧘', 'info');
        }
    }

    smoothScroll(event) {
        event.preventDefault();
        const targetId = event.currentTarget.getAttribute('href');
        if (targetId === '#') return;
        
        const targetElement = document.querySelector(targetId);
        if (targetElement) {
            window.scrollTo({
                top: targetElement.offsetTop - 80,
                behavior: 'smooth'
            });
        }
    }
}

// Initialize therapeutic app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.therapeuticApp = new TherapeuticApp();
    
    // Add CSRF token to window for AJAX requests
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
    if (csrfToken) {
        window.csrfToken = csrfToken.value;
    }
});

// Gentle error handling
window.addEventListener('error', (event) => {
    console.error('Therapeutic error caught:', event.error);
    window.therapeuticApp?.showGentleNotification(
        'A gentle error occurred. Please try again or take a break.',
        'error'
    );
});

// Page visibility for gentle pauses
document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
        // User switched tabs - gentle reminder when they return
        window.wasAway = true;
    } else if (window.wasAway) {
        window.therapeuticApp?.showGentleNotification(
            'Welcome back. Take a moment to re-center.',
            'info'
        );
        window.wasAway = false;
    }
});