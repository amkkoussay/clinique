/**
 * Clinic Management Platform - Main JavaScript
 * ============================================
 * Core functionality for the clinic management system.
 */

// ==================== INITIALIZATION ====================
document.addEventListener('DOMContentLoaded', function() {
    initializeTheme();
    initializeSidebar();
    initializeDropdowns();
    initializeNotifications();
    initializeSearch();
    initializeFAB();
    initializeFormValidation();
    initializeAutoComplete();
});

// ==================== THEME MANAGEMENT ====================
function initializeTheme() {
    const themeToggle = document.getElementById('themeToggle');
    const html = document.documentElement;
    
    // Check for saved theme preference
    const savedTheme = localStorage.getItem('theme') || 'light';
    html.setAttribute('data-theme', savedTheme);
    updateThemeIcon(savedTheme);
    
    if (themeToggle) {
        themeToggle.addEventListener('click', function() {
            const currentTheme = html.getAttribute('data-theme');
            const newTheme = currentTheme === 'light' ? 'dark' : 'light';
            
            html.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
            updateThemeIcon(newTheme);
            
            // Sync with server
            fetch(`/set-theme/${newTheme}`);
        });
    }
}

function updateThemeIcon(theme) {
    const themeToggle = document.getElementById('themeToggle');
    if (themeToggle) {
        const icon = themeToggle.querySelector('i');
        if (icon) {
            icon.className = theme === 'light' ? 'fas fa-moon' : 'fas fa-sun';
        }
    }
}

// ==================== SIDEBAR ====================
function initializeSidebar() {
    const sidebarToggle = document.getElementById('sidebarToggle');
    const sidebar = document.getElementById('sidebar');
    
    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener('click', function() {
            sidebar.classList.toggle('open');
        });
    }
    
    // Close sidebar when clicking outside on mobile
    document.addEventListener('click', function(e) {
        if (window.innerWidth <= 1024 && sidebar && sidebar.classList.contains('open')) {
            if (!sidebar.contains(e.target) && !sidebarToggle.contains(e.target)) {
                sidebar.classList.remove('open');
            }
        }
    });
}

// ==================== DROPDOWNS ====================
function initializeDropdowns() {
    // User menu dropdown
    const userMenuToggle = document.getElementById('userMenuToggle');
    const userMenu = document.getElementById('userMenu');
    
    if (userMenuToggle && userMenu) {
        userMenuToggle.addEventListener('click', function(e) {
            e.stopPropagation();
            userMenu.classList.toggle('show');
            closeOtherDropdowns(userMenu);
        });
    }
    
    // Notifications dropdown
    const notificationsToggle = document.getElementById('notificationsToggle');
    const notificationsMenu = document.getElementById('notificationsMenu');
    
    if (notificationsToggle && notificationsMenu) {
        notificationsToggle.addEventListener('click', function(e) {
            e.stopPropagation();
            notificationsMenu.classList.toggle('show');
            closeOtherDropdowns(notificationsMenu);
        });
    }
    
    // Close dropdowns when clicking outside
    document.addEventListener('click', function() {
        document.querySelectorAll('.dropdown-menu.show').forEach(menu => {
            menu.classList.remove('show');
        });
    });
}

function closeOtherDropdowns(currentMenu) {
    document.querySelectorAll('.dropdown-menu.show').forEach(menu => {
        if (menu !== currentMenu) {
            menu.classList.remove('show');
        }
    });
}

// ==================== NOTIFICATIONS ====================
function initializeNotifications() {
    // Fetch unread notification count
    fetchUnreadCount();
    
    // Poll for new notifications every 60 seconds
    setInterval(fetchUnreadCount, 60000);
}

function fetchUnreadCount() {
    const badge = document.getElementById('notificationCount');
    if (!badge) {
        return;
    }

    fetch('/api/notifications/unread-count')
        .then(response => {
            if (!response.ok) {
                throw new Error(`Notification request failed (${response.status})`);
            }
            return response.json();
        })
        .then(data => {
            if (data.count > 0) {
                badge.textContent = data.count > 99 ? '99+' : data.count;
                badge.style.display = 'block';
            } else {
                badge.style.display = 'none';
            }
        })
        .catch(error => console.error('Error fetching notifications:', error));
}

function markAllRead() {
    fetch('/dashboard/notifications/mark-all-read', {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCsrfToken()
        }
    })
    .then(response => {
        if (response.ok) {
            const badge = document.getElementById('notificationCount');
            if (badge) {
                badge.style.display = 'none';
            }
            window.location.reload();
        }
    })
    .catch(error => console.error('Error marking notifications read:', error));
}

// ==================== SEARCH ====================
function initializeSearch() {
    const globalSearch = document.getElementById('globalSearch');
    
    if (globalSearch) {
        let searchTimeout;
        
        globalSearch.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            const query = this.value.trim();
            
            if (query.length >= 2) {
                searchTimeout = setTimeout(() => {
                    performGlobalSearch(query);
                }, 300);
            }
        });
        
        globalSearch.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                const query = this.value.trim();
                if (query) {
                    window.location.href = `/patients?search=${encodeURIComponent(query)}`;
                }
            }
        });
    }
}

function performGlobalSearch(query) {
    // Implement global search functionality
    // This could show a dropdown with search results
    console.log('Searching for:', query);
}

// ==================== FLOATING ACTION BUTTON ====================
function initializeFAB() {
    const fabContainer = document.querySelector('.fab-container');
    const fabToggle = document.getElementById('fabToggle');
    
    if (fabToggle && fabContainer) {
        fabToggle.addEventListener('click', function() {
            fabContainer.classList.toggle('active');
        });
        
        // Close FAB menu when clicking outside
        document.addEventListener('click', function(e) {
            if (!fabContainer.contains(e.target)) {
                fabContainer.classList.remove('active');
            }
        });
    }
}

// ==================== FORM VALIDATION ====================
function initializeFormValidation() {
    const forms = document.querySelectorAll('form');
    
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const requiredFields = form.querySelectorAll('[required]');
            let isValid = true;
            
            requiredFields.forEach(field => {
                if (!field.value.trim()) {
                    isValid = false;
                    field.classList.add('is-invalid');
                    
                    // Add error message if not exists
                    let errorMsg = field.parentElement.querySelector('.error-message');
                    if (!errorMsg) {
                        errorMsg = document.createElement('span');
                        errorMsg.className = 'error-message';
                        errorMsg.textContent = 'This field is required';
                        field.parentElement.appendChild(errorMsg);
                    }
                } else {
                    field.classList.remove('is-invalid');
                    const errorMsg = field.parentElement.querySelector('.error-message');
                    if (errorMsg) {
                        errorMsg.remove();
                    }
                }
            });
            
            if (!isValid) {
                e.preventDefault();
            }
        });
    });
}

// ==================== AUTOCOMPLETE ====================
function initializeAutoComplete() {
    // Patient search autocomplete
    const patientSearchInputs = document.querySelectorAll('.patient-autocomplete');
    
    patientSearchInputs.forEach(input => {
        input.addEventListener('input', function() {
            const query = this.value.trim();
            
            if (query.length >= 2) {
                fetch(`/api/patients/search?q=${encodeURIComponent(query)}`)
                    .then(response => response.json())
                    .then(data => {
                        showAutocompleteResults(input, data);
                    })
                    .catch(error => console.error('Error fetching patients:', error));
            }
        });
    });
}

function showAutocompleteResults(input, results) {
    // Remove existing dropdown
    let dropdown = input.parentElement.querySelector('.autocomplete-dropdown');
    if (dropdown) {
        dropdown.remove();
    }
    
    if (results.length === 0) return;
    
    // Create dropdown
    dropdown = document.createElement('div');
    dropdown.className = 'autocomplete-dropdown';
    
    results.forEach(result => {
        const item = document.createElement('div');
        item.className = 'autocomplete-item';
        item.innerHTML = `
            <span class="name">${result.name}</span>
            <span class="id">${result.patient_id}</span>
        `;
        item.addEventListener('click', function() {
            input.value = result.name;
            input.dataset.patientId = result.id;
            dropdown.remove();
        });
        dropdown.appendChild(item);
    });
    
    input.parentElement.appendChild(dropdown);
    
    // Close dropdown when clicking outside
    document.addEventListener('click', function closeDropdown(e) {
        if (!input.parentElement.contains(e.target)) {
            dropdown.remove();
            document.removeEventListener('click', closeDropdown);
        }
    });
}

// ==================== UTILITY FUNCTIONS ====================
function getCsrfToken() {
    const token = document.querySelector('meta[name="csrf-token"]');
    return token ? token.content : '';
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(amount);
}

function confirmDelete(message) {
    return confirm(message || 'Are you sure you want to delete this item?');
}

function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.classList.add('show');
    }, 100);
    
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// ==================== AJAX HELPERS ====================
function ajaxGet(url, callback) {
    fetch(url)
        .then(response => response.json())
        .then(data => callback(null, data))
        .catch(error => callback(error, null));
}

function ajaxPost(url, data, callback) {
    fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(data => callback(null, data))
    .catch(error => callback(error, null));
}

// ==================== TABLE SORTING ====================
function initializeTableSorting() {
    const tables = document.querySelectorAll('.table-sortable');
    
    tables.forEach(table => {
        const headers = table.querySelectorAll('th[data-sort]');
        
        headers.forEach(header => {
            header.addEventListener('click', function() {
                const column = this.dataset.sort;
                const order = this.dataset.order === 'asc' ? 'desc' : 'asc';
                
                // Update sort indicators
                headers.forEach(h => delete h.dataset.order);
                this.dataset.order = order;
                
                // Sort table
                sortTable(table, column, order);
            });
        });
    });
}

function sortTable(table, column, order) {
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    
    rows.sort((a, b) => {
        const aVal = a.querySelector(`[data-column="${column}"]`).textContent;
        const bVal = b.querySelector(`[data-column="${column}"]`).textContent;
        
        if (order === 'asc') {
            return aVal.localeCompare(bVal);
        } else {
            return bVal.localeCompare(aVal);
        }
    });
    
    rows.forEach(row => tbody.appendChild(row));
}

// ==================== MODAL ====================
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('show');
        document.body.style.overflow = 'hidden';
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('show');
        document.body.style.overflow = '';
    }
}

// Close modal when clicking outside
document.addEventListener('click', function(e) {
    if (e.target.classList.contains('modal')) {
        e.target.classList.remove('show');
        document.body.style.overflow = '';
    }
});

// ==================== CHART INITIALIZATION ====================
function initializeCharts() {
    // Charts are initialized in individual pages
}

// ==================== OFFLINE SUPPORT ====================
if ('serviceWorker' in navigator) {
    window.addEventListener('load', function() {
        // Uncomment when service worker is implemented
        // navigator.serviceWorker.register('/static/js/sw.js');
    });
}

// ==================== EXPORT FUNCTIONS ====================
window.ClinicApp = {
    getCsrfToken,
    formatDate,
    formatCurrency,
    confirmDelete,
    showToast,
    ajaxGet,
    ajaxPost,
    openModal,
    closeModal
};
