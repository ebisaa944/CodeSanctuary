// Therapeutic Coding - Main JavaScript

$(document).ready(function() {
    // Initialize tooltips
    $('[data-bs-toggle="tooltip"]').tooltip();
    
    // Gentle mode enhancements
    if ($('.gentle-mode-alert').length) {
        applyGentleMode();
    }
    
    // Quick checkin functionality
    initQuickCheckin();
    
    // Emotional checkin form enhancements
    initCheckinForm();
    
    // Strategy recommendations
    initRecommendations();
    
    // Gentle reminders
    initGentleReminders();
    
    // Data visualization
    initCharts();
});

// ==================== GENTLE MODE ====================
function applyGentleMode() {
    console.log('Gentle mode activated');
    
    // Reduce motion
    $('body').addClass('reduce-motion');
    
    // Softer transitions
    $('*').css('transition-duration', '0.3s');
    
    // Gentle color scheme
    $('.btn-primary').addClass('btn-gentle');
    $('.alert-info').addClass('alert-gentle');
    
    // Limit visible items
    $('.table tbody tr:gt(4)').hide();
    $('.list-group-item:gt(2)').hide();
    
    // Add gentle message
    showGentleMessage();
}

function showGentleMessage() {
    const messages = [
        "Take your time. There's no rush.",
        "Be gentle with yourself today.",
        "Small steps are still progress.",
        "It's okay to pause and breathe.",
        "You're doing the best you can."
    ];
    
    const message = messages[Math.floor(Math.random() * messages.length)];
    
    $('<div class="alert alert-gentle gentle-pulse mt-3">' +
        '<i class="fas fa-heart me-2"></i>' + message +
        '</div>').prependTo('.page-header').delay(8000).fadeOut();
}

// ==================== QUICK CHECKIN ====================
function initQuickCheckin() {
    // Quick checkin form submission
    $(document).on('submit', '#quickCheckinForm', function(e) {
        e.preventDefault();
        
        const form = $(this);
        const submitBtn = form.find('button[type="submit"]');
        const originalText = submitBtn.html();
        
        // Show loading
        submitBtn.prop('disabled', true).html('<i class="fas fa-spinner fa-spin"></i> Processing...');
        
        $.ajax({
            url: form.attr('action'),
            method: 'POST',
            data: form.serialize(),
            success: function(response) {
                if (response.success) {
                    // Show success message
                    showNotification('Check-in recorded!', 'success');
                    
                    // Close modal if open
                    $('#quickCheckinModal').modal('hide');
                    
                    // Update dashboard if on dashboard page
                    if (window.location.pathname.includes('dashboard')) {
                        setTimeout(() => location.reload(), 1000);
                    }
                }
            },
            error: function(xhr) {
                showNotification('Error recording check-in. Please try again.', 'danger');
            },
            complete: function() {
                submitBtn.prop('disabled', false).html(originalText);
            }
        });
    });
    
    // Quick checkin shortcut
    $(document).on('keydown', function(e) {
        // Ctrl+Shift+Q for quick checkin
        if (e.ctrlKey && e.shiftKey && e.key === 'Q') {
            e.preventDefault();
            $('#quickCheckinModal').modal('show');
        }
    });
}

// ==================== CHECKIN FORM ====================
function initCheckinForm() {
    // Update intensity display
    $('.intensity-slider').on('input', function() {
        const value = $(this).val();
        const display = $(this).siblings('.intensity-display') || 
                       $(this).closest('.form-group').find('.intensity-value');
        
        if (display.length) {
            display.text(value);
            
            // Color code
            if (value <= 3) {
                display.css('color', '#4CAF50');
            } else if (value <= 6) {
                display.css('color', '#FFC107');
            } else {
                display.css('color', '#F44336');
            }
        }
    });
    
    // Emotion selection guidance
    $('.emotion-select').on('change', function() {
        const emotion = $(this).val();
        updateEmotionGuidance(emotion);
    });
    
    // Physical symptoms counter
    $('.symptom-checkboxes input').on('change', function() {
        const count = $('.symptom-checkboxes input:checked').length;
        $('.symptoms-count').text(count + ' selected');
    });
    
    // Autosave draft
    let autosaveTimer;
    $('.gentle-textarea').on('input', function() {
        clearTimeout(autosaveTimer);
        autosaveTimer = setTimeout(saveDraft, 2000);
    });
}

function updateEmotionGuidance(emotion) {
    const guidance = {
        'anxious': 'Try a grounding exercise or deep breathing.',
        'overwhelmed': 'Break tasks into smaller steps. You only need to do one thing at a time.',
        'doubtful': 'Remember past successes. You\'ve overcome challenges before.',
        'calm': 'Use this calm energy for focused work or creative expression.',
        'excited': 'Channel this energy into a project or learning.',
        'frustrated': 'Take a short break. Sometimes stepping away helps.',
        'neutral': 'Notice the absence of strong emotion. That\'s valuable information too.'
    };
    
    const guidanceElement = $('.emotion-guidance');
    if (guidanceElement.length && guidance[emotion]) {
        guidanceElement.html('<i class="fas fa-lightbulb"></i> ' + guidance[emotion]).fadeIn();
    }
}

function saveDraft() {
    const formData = $('form').serialize();
    
    // In a real app, you'd save to localStorage or send to server
    localStorage.setItem('checkinDraft', formData);
    
    showNotification('Draft saved', 'info', 1500);
}

// ==================== RECOMMENDATIONS ====================
function initRecommendations() {
    // Strategy filtering
    $('.strategy-filter').on('change', function() {
        filterStrategies();
    });
    
    // Mark strategy as tried
    $('.mark-tried-btn').on('click', function() {
        const strategyId = $(this).data('strategy-id');
        markStrategyTried(strategyId, $(this));
    });
    
    // Load more strategies
    $('.load-more-strategies').on('click', function() {
        loadMoreStrategies($(this));
    });
}

function filterStrategies() {
    const type = $('#strategyTypeFilter').val();
    const emotion = $('#emotionFilter').val();
    const duration = $('#durationFilter').val();
    
    // Show loading
    $('.strategies-container').addClass('loading');
    
    $.ajax({
        url: '/therapy/api/strategies/recommended/',
        data: {
            strategy_type: type || undefined,
            emotion: emotion || undefined,
            duration: duration || undefined
        },
        success: function(response) {
            updateStrategiesDisplay(response.results);
        },
        complete: function() {
            $('.strategies-container').removeClass('loading');
        }
    });
}

function markStrategyTried(strategyId, button) {
    $.ajax({
        url: `/therapy/api/strategies/${strategyId}/mark_tried/`,
        method: 'POST',
        headers: {
            'X-CSRFToken': getCSRFToken()
        },
        success: function(response) {
            button.html('<i class="fas fa-check"></i> Tried').prop('disabled', true);
            showNotification(response.message, 'success');
        }
    });
}

// ==================== GENTLE REMINDERS ====================
function initGentleReminders() {
    // Show reminder every 20 minutes
    setInterval(showRandomReminder, 20 * 60 * 1000);
    
    // First reminder after 10 minutes
    setTimeout(showRandomReminder, 10 * 60 * 1000);
    
    // Reminder on scroll
    let lastScrollReminder = 0;
    $(window).on('scroll', function() {
        const now = Date.now();
        if (now - lastScrollReminder > 5 * 60 * 1000) { // Every 5 minutes of scrolling
            if ($(window).scrollTop() > 500) {
                showScrollReminder();
                lastScrollReminder = now;
            }
        }
    });
}

function showRandomReminder() {
    const reminders = [
        "Take a moment to notice your breathing.",
        "How are you feeling right now?",
        "Remember to hydrate.",
        "Stretch for a moment if you can.",
        "Your emotions are valid.",
        "Progress, not perfection.",
        "You don't have to do everything at once."
    ];
    
    const reminder = reminders[Math.floor(Math.random() * reminders.length)];
    showNotification(reminder, 'info', 5000);
}

function showScrollReminder() {
    showNotification("You've been scrolling for a while. Consider taking a break.", 'warning', 3000);
}

// ==================== CHARTS & VISUALIZATION ====================
function initCharts() {
    // Initialize emotional trend chart if canvas exists
    const trendCanvas = $('#emotionalTrendChart');
    if (trendCanvas.length) {
        initEmotionalTrendChart(trendCanvas[0]);
    }
    
    // Initialize intensity chart
    const intensityCanvas = $('#intensityChart');
    if (intensityCanvas.length) {
        initIntensityChart(intensityCanvas[0]);
    }
}

function initEmotionalTrendChart(canvas) {
    const ctx = canvas.getContext('2d');
    
    // Sample data - in real app, fetch from API
    const data = {
        labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
        datasets: [{
            label: 'Emotional Intensity',
            data: [6, 7, 5, 8, 6, 4, 5],
            borderColor: '#5c6bc0',
            backgroundColor: 'rgba(92, 107, 192, 0.1)',
            fill: true,
            tension: 0.4
        }]
    };
    
    new Chart(ctx, {
        type: 'line',
        data: data,
        options: {
            responsive: true,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            let label = 'Intensity: ' + context.raw;
                            if (context.raw >= 8) label += ' (High)';
                            else if (context.raw >= 5) label += ' (Medium)';
                            else label += ' (Low)';
                            return label;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    max: 10,
                    ticks: {
                        callback: function(value) {
                            if (value >= 8) return 'High';
                            if (value >= 5) return 'Medium';
                            if (value >= 2) return 'Low';
                            return 'Very Low';
                        }
                    }
                }
            }
        }
    });
}

// ==================== UTILITY FUNCTIONS ====================
function showNotification(message, type = 'info', duration = 3000) {
    const notification = $(
        '<div class="alert alert-' + type + ' alert-dismissible fade show floating-notification">' +
        '<button type="button" class="btn-close" data-bs-dismiss="alert"></button>' +
        message +
        '</div>'
    );
    
    $('body').append(notification);
    
    // Position
    notification.css({
        position: 'fixed',
        top: '20px',
        right: '20px',
        zIndex: 9999,
        maxWidth: '300px',
        boxShadow: '0 4px 12px rgba(0,0,0,0.15)'
    });
    
    // Auto-remove
    setTimeout(() => {
        notification.alert('close');
    }, duration);
}

function getCSRFToken() {
    return $('input[name=csrfmiddlewaretoken]').val() || 
           $('meta[name="csrf-token"]').attr('content');
}

function updateStrategiesDisplay(strategies) {
    const container = $('.strategies-container');
    container.empty();
    
    if (strategies.length === 0) {
        container.html('<div class="text-center py-4">No strategies match your filters.</div>');
        return;
    }
    
    strategies.forEach(strategy => {
        const strategyHtml = `
            <div class="col-md-4 mb-4">
                <div class="card strategy-card">
                    <div class="card-body">
                        <h6 class="card-title">${strategy.name}</h6>
                        <p class="card-text small">${strategy.description.substring(0, 100)}...</p>
                        <div class="d-flex justify-content-between align-items-center">
                            <small class="text-muted">
                                <i class="fas fa-clock"></i> ${strategy.estimated_minutes} min
                            </small>
                            <button class="btn btn-sm btn-outline-primary mark-tried-btn" 
                                    data-strategy-id="${strategy.id}">
                                <i class="fas fa-check"></i> Try
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        container.append(strategyHtml);
    });
}

function loadMoreStrategies(button) {
    const page = parseInt(button.data('page') || 1) + 1;
    const url = button.data('url') + '?page=' + page;
    
    button.prop('disabled', true).html('<i class="fas fa-spinner fa-spin"></i> Loading...');
    
    $.ajax({
        url: url,
        success: function(data) {
            // Append new strategies
            $(data).find('.strategy-card').appendTo('.strategies-container');
            
            // Update button
            if (data.includes('has-next')) {
                button.data('page', page).prop('disabled', false).html('Load More');
            } else {
                button.remove();
            }
        }
    });
}

// ==================== ERROR HANDLING ====================
$(document).ajaxError(function(event, jqxhr, settings, thrownError) {
    if (jqxhr.status === 401) {
        showNotification('Please log in to continue', 'warning');
    } else if (jqxhr.status === 403) {
        showNotification('You don\'t have permission to do that', 'danger');
    } else if (jqxhr.status === 500) {
        showNotification('Server error. Please try again later.', 'danger');
    }
});

// ==================== ACCESSIBILITY ====================
// Keyboard navigation
$(document).on('keydown', function(e) {
    // Escape closes modals
    if (e.key === 'Escape') {
        $('.modal.show').modal('hide');
    }
    
    // Tab navigation within forms
    if (e.key === 'Tab' && e.shiftKey) {
        // Handle shift+tab for accessibility
    }
});

// Focus management for screen readers
$('.modal').on('shown.bs.modal', function() {
    $(this).find('[autofocus]').focus();
});

// Skip to main content link for screen readers
$('.skip-to-content').on('click', function(e) {
    e.preventDefault();
    $('#main-content').attr('tabindex', -1).focus();
});