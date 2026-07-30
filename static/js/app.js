/**
 * Harpi - Custom JavaScript Helpers
 * Minimal JS for HTMX + Alpine.js integration
 */

(function() {
    'use strict';

    // ==========================================================================
    // Global Harpi Namespace
    // ==========================================================================
    window.Harpi = {
        version: '0.1.0',
        config: {
            pollingInterval: 3000,
            toastDuration: 5000,
            apiBase: '/api',
            htmxBase: '/htmx'
        },
        state: {
            selectedGuildId: null,
            selectedChannelId: null,
            botConnected: false,
            wsConnected: false,
            latency: 0
        },
        utils: {},
        components: {}
    };

    // ==========================================================================
    // Utility Functions
    // ==========================================================================

    Harpi.utils = {
        // Format milliseconds to MM:SS or HH:MM:SS
        formatDuration: function(ms) {
            if (!ms || ms < 0) return '--:--';
            const totalSeconds = Math.floor(ms / 1000);
            const hours = Math.floor(totalSeconds / 3600);
            const minutes = Math.floor((totalSeconds % 3600) / 60);
            const seconds = totalSeconds % 60;
            
            if (hours > 0) {
                return `${hours}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
            }
            return `${minutes}:${seconds.toString().padStart(2, '0')}`;
        },

        // Format bytes to human readable
        formatBytes: function(bytes) {
            if (!bytes || bytes < 0) return '0 B';
            const units = ['B', 'KB', 'MB', 'GB', 'TB'];
            const i = Math.floor(Math.log(bytes) / Math.log(1024));
            return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${units[i]}`;
        },

        // Format percentage
        formatPercent: function(value, decimals = 1) {
            if (value === null || value === undefined) return '--%';
            return `${value.toFixed(decimals)}%`;
        },

        // Format number with commas
        formatNumber: function(num) {
            if (num === null || num === undefined) return '--';
            return num.toLocaleString();
        },

        // Debounce function
        debounce: function(func, wait) {
            let timeout;
            return function(...args) {
                clearTimeout(timeout);
                timeout = setTimeout(() => func.apply(this, args), wait);
            };
        },

        // Throttle function
        throttle: function(func, limit) {
            let inThrottle;
            return function(...args) {
                if (!inThrottle) {
                    func.apply(this, args);
                    inThrottle = true;
                    setTimeout(() => inThrottle = false, limit);
                }
            };
        },

        // Generate unique ID
        generateId: function(prefix = 'harpi') {
            return `${prefix}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
        },

        // Safe JSON parse
        safeParse: function(str, fallback = null) {
            try {
                return JSON.parse(str);
            } catch {
                return fallback;
            }
        },

        // Get query parameter
        getQueryParam: function(name) {
            const urlParams = new URLSearchParams(window.location.search);
            return urlParams.get(name);
        },

        // Set query parameter without reload
        setQueryParam: function(name, value) {
            const url = new URL(window.location);
            if (value) {
                url.searchParams.set(name, value);
            } else {
                url.searchParams.delete(name);
            }
            window.history.replaceState({}, '', url);
        }
    };

    // ==========================================================================
    // Toast Notifications
    // ==========================================================================

    Harpi.components.toast = {
        container: null,

        init: function() {
            this.container = document.getElementById('toast-container');
            if (!this.container) {
                this.container = document.createElement('div');
                this.container.id = 'toast-container';
                this.container.className = 'toast-container';
                this.container.setAttribute('aria-live', 'polite');
                this.container.setAttribute('aria-atomic', 'true');
                document.body.appendChild(this.container);
            }
        },

        show: function(message, type = 'info', duration = null) {
            if (!this.container) this.init();
            
            const toast = document.createElement('div');
            toast.className = `toast toast-${type}`;
            toast.setAttribute('role', 'alert');
            toast.setAttribute('aria-live', 'assertive');
            
            const icons = {
                success: '✓',
                error: '✕',
                warning: '⚠',
                info: 'ℹ'
            };
            
            toast.innerHTML = `
                <span class="toast-icon">${icons[type] || icons.info}</span>
                <span class="toast-message">${this.escapeHtml(message)}</span>
                <button class="toast-close" aria-label="Dismiss">&times;</button>
            `;
            
            this.container.appendChild(toast);
            
            // Animate in
            requestAnimationFrame(() => {
                toast.classList.add('show');
            });
            
            // Auto dismiss
            const dismissDuration = duration ?? Harpi.config.toastDuration;
            const dismissTimer = setTimeout(() => this.dismiss(toast), dismissDuration);
            
            // Manual dismiss
            toast.querySelector('.toast-close').addEventListener('click', () => {
                clearTimeout(dismissTimer);
                this.dismiss(toast);
            });
            
            return toast;
        },

        dismiss: function(toast) {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        },

        success: function(message, duration) {
            return this.show(message, 'success', duration);
        },

        error: function(message, duration) {
            return this.show(message, 'error', duration);
        },

        warning: function(message, duration) {
            return this.show(message, 'warning', duration);
        },

        info: function(message, duration) {
            return this.show(message, 'info', duration);
        },

        escapeHtml: function(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
    };

    // ==========================================================================
    // Modal Management
    // ==========================================================================

    Harpi.components.modal = {
        element: null,
        alpineComponent: null,

        init: function() {
            this.element = document.querySelector('[x-data*="modalOpen"]');
            if (this.element && this.element._x_dataStack) {
                this.alpineComponent = this.element._x_dataStack[0];
            }
        },

        open: function(title, content) {
            if (!this.alpineComponent) this.init();
            if (this.alpineComponent) {
                this.alpineComponent.modalTitle = title;
                this.alpineComponent.modalContent = content;
                this.alpineComponent.modalOpen = true;
                document.body.classList.add('modal-open');
            } else {
                // Fallback: dispatch event for Alpine to catch
                document.body.dispatchEvent(new CustomEvent('harpi:open-modal', {
                    detail: { title, content }
                }));
            }
        },

        close: function() {
            if (this.alpineComponent) {
                this.alpineComponent.modalOpen = false;
                document.body.classList.remove('modal-open');
            }
        },

        confirm: function(title, message, onConfirm, onCancel) {
            const content = `
                <p>${Harpi.utils.escapeHtml(message)}</p>
                <div class="modal-footer" style="display:flex;gap:8px;justify-content:flex-end;margin-top:16px;">
                    <button class="btn btn-secondary" onclick="Harpi.components.modal.close(); ${onCancel ? onCancel + '()' : ''}">Cancel</button>
                    <button class="btn btn-primary" onclick="Harpi.components.modal.close(); ${onConfirm ? onConfirm + '()' : ''}">Confirm</button>
                </div>
            `;
            this.open(title, content);
        }
    };

    // ==========================================================================
    // Guild/Channel Selection State
    // ==========================================================================

    Harpi.components.guildSelector = {
        _listenersAttached: false,

        init: function(firstInit) {
            // On first initialization, restore from localStorage and attach listeners
            if (firstInit) {
                const guildSelect = document.getElementById('guild-select');
                const savedGuild = localStorage.getItem('harpi_selected_guild');
                const savedChannel = localStorage.getItem('harpi_selected_channel');

                if (savedGuild && guildSelect) {
                    guildSelect.value = savedGuild;
                    Harpi.state.selectedGuildId = savedGuild;
                    // Trigger HTMX to load channels (only on first init)
                    if (window.htmx) {
                        htmx.trigger(guildSelect, 'change');
                    }
                }

                if (savedChannel) {
                    const channelSelect = document.getElementById('channel-select');
                    if (channelSelect) {
                        channelSelect.value = savedChannel;
                        Harpi.state.selectedChannelId = savedChannel;
                    }
                }

                // Attach delegated listeners once (survive HTMX swaps)
                if (!this._listenersAttached) {
                    this._listenersAttached = true;

                    // Listen for guild changes (delegated)
                    document.addEventListener('change', (e) => {
                        if (e.target.id === 'guild-select') {
                            Harpi.state.selectedGuildId = e.target.value;
                            localStorage.setItem('harpi_selected_guild', e.target.value);
                            localStorage.removeItem('harpi_selected_channel');
                            Harpi.state.selectedChannelId = null;
                            Harpi.components.guildSelector.updateConnectButton();
                        }
                    });

                    // Listen for channel changes (delegated)
                    document.addEventListener('change', (e) => {
                        if (e.target.id === 'channel-select') {
                            Harpi.state.selectedChannelId = e.target.value;
                            localStorage.setItem('harpi_selected_channel', e.target.value);
                            Harpi.components.guildSelector.updateConnectButton();
                        }
                    });
                }
            }

            this.updateConnectButton();
        },

        updateConnectButton: function() {
            const btn = document.querySelector('#guild-channel-selector button[type="submit"]');
            const guildSelect = document.getElementById('guild-select');
            const channelSelect = document.getElementById('channel-select');
            if (btn) {
                const guildValue = guildSelect && guildSelect.value;
                const channelValue = channelSelect && channelSelect.value;
                btn.disabled = !(guildValue && channelValue);
            }
        },

        getSelectedGuild: function() {
            return Harpi.state.selectedGuildId;
        },

        getSelectedChannel: function() {
            return Harpi.state.selectedChannelId;
        }
    };

    // ==========================================================================
    // WebSocket Connection Status
    // ==========================================================================

    Harpi.components.wsStatus = {
        element: null,
        reconnectAttempts: 0,
        maxReconnectAttempts: 5,

        init: function() {
            this.element = document.getElementById('ws-status');
            this.updateStatus('connecting');
        },

        updateStatus: function(status) {
            if (!this.element) return;
            
            const statusConfig = {
                connected: { text: 'LIVE', class: 'connected', dot: true },
                disconnected: { text: 'OFFLINE', class: 'disconnected', dot: false },
                connecting: { text: 'CONNECTING...', class: 'connecting', dot: true },
                error: { text: 'ERROR', class: 'error', dot: false }
            };
            
            const config = statusConfig[status] || statusConfig.disconnected;
            this.element.className = `ws-status ${config.class}`;
            this.element.innerHTML = `
                <span class="status-dot" style="display:${config.dot ? 'block' : 'none'}"></span>
                <span>${config.text}</span>
            `;
            
            Harpi.state.wsConnected = (status === 'connected');
        },

        onConnect: function() {
            this.reconnectAttempts = 0;
            this.updateStatus('connected');
        },

        onDisconnect: function() {
            this.updateStatus('disconnected');
            this.attemptReconnect();
        },

        onError: function() {
            this.updateStatus('error');
        },

        attemptReconnect: function() {
            if (this.reconnectAttempts < this.maxReconnectAttempts) {
                this.reconnectAttempts++;
                this.updateStatus('connecting');
                // Actual reconnection handled by Socket.IO client
            } else {
                this.updateStatus('error');
            }
        }
    };

    // ==========================================================================
    // Latency Display
    // ==========================================================================

    Harpi.components.latency = {
        element: null,
        updateInterval: null,

        init: function() {
            this.element = document.getElementById('latency-display');
            this.startUpdates();
        },

        startUpdates: function() {
            this.updateInterval = setInterval(() => {
                this.fetchLatency();
            }, 10000); // Update every 10 seconds
            
            // Initial fetch
            this.fetchLatency();
        },

        fetchLatency: async function() {
            try {
                const start = performance.now();
                const response = await fetch('/api/ping', { method: 'HEAD', cache: 'no-cache' });
                const latency = Math.round(performance.now() - start);
                
                if (response.ok) {
                    this.updateDisplay(latency);
                    Harpi.state.latency = latency;
                }
            } catch (e) {
                this.updateDisplay('--');
            }
        },

        updateDisplay: function(latency) {
            if (this.element) {
                this.element.textContent = `${latency}ms`;
                // Color code
                if (typeof latency === 'number') {
                    this.element.style.color = latency < 100 ? 'var(--color-success)' : 
                                              latency < 300 ? 'var(--color-warning)' : 'var(--color-error)';
                }
            }
        },

        destroy: function() {
            if (this.updateInterval) {
                clearInterval(this.updateInterval);
            }
        }
    };

    // ==========================================================================
    // Clock Display
    // ==========================================================================

    Harpi.components.clock = {
        element: null,
        interval: null,

        init: function() {
            this.element = document.getElementById('current-time');
            this.start();
        },

        start: function() {
            this.update();
            this.interval = setInterval(() => this.update(), 1000);
        },

        update: function() {
            if (this.element) {
                const now = new Date();
                this.element.textContent = now.toLocaleTimeString('en-US', {
                    hour12: false,
                    hour: '2-digit',
                    minute: '2-digit',
                    second: '2-digit'
                });
            }
        },

        destroy: function() {
            if (this.interval) clearInterval(this.interval);
        }
    };

    // ==========================================================================
    // HTMX Event Handlers
    // ==========================================================================

    Harpi.htmx = {
        // Handle HTMX config request
        configRequest: function(evt) {
            // Add auth headers if needed
            // evt.detail.headers['Authorization'] = `Bearer ${token}`;
        },

        // Handle before swap
        beforeSwap: function(evt) {
            // Handle error responses
            if (evt.detail.xhr.status >= 400) {
                evt.detail.shouldSwap = true;
                evt.detail.isError = true;
                
                // Show error toast
                const errorMsg = evt.detail.xhr.responseText || `Error ${evt.detail.xhr.status}`;
                Harpi.components.toast.error(errorMsg);
            }
        },

        // Handle after swap
        afterSwap: function(evt) {
            // Re-initialize Alpine components in swapped content
            if (window.Alpine) {
                Alpine.initTree(evt.detail.target);
            }
            
            // Re-initialize Lucide icons across the document.
            // For outerHTML swaps, evt.detail.target is the OLD (detached) element,
            // so scoping to it would find nothing. Lucide skips already-processed
            // elements, so a full-document scan is safe and correct.
            if (window.lucide) {
                lucide.createIcons();
            }
            
            // Re-initialize guild selector if it or channel selector was swapped
            if (evt.detail.target.querySelector('#guild-select') || evt.detail.target.querySelector('#channel-select')) {
                Harpi.components.guildSelector.init(false); // refresh button state, no localStorage restore
            }
            
            // Focus management for accessibility
            const autofocus = evt.detail.target.querySelector('[autofocus]');
            if (autofocus) {
                autofocus.focus();
            }
        },

        // Handle response error
        responseError: function(evt) {
            console.error('HTMX Error:', evt.detail);
            Harpi.components.toast.error('Request failed. Please try again.');
        },

        // Handle send error
        sendError: function(evt) {
            console.error('HTMX Send Error:', evt.detail);
        }
    };

    // ==========================================================================
    // API Helpers
    // ==========================================================================

    Harpi.api = {
        baseUrl: Harpi.config.apiBase,

        async request(endpoint, options = {}) {
            const url = `${this.baseUrl}${endpoint}`;
            const config = {
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest',
                    ...options.headers
                },
                ...options
            };

            if (config.body && typeof config.body === 'object') {
                config.body = JSON.stringify(config.body);
            }

            try {
                const response = await fetch(url, config);
                
                if (!response.ok) {
                    const error = await response.json().catch(() => ({ message: response.statusText }));
                    throw new Error(error.message || `HTTP ${response.status}`);
                }
                
                const contentType = response.headers.get('content-type');
                if (contentType && contentType.includes('application/json')) {
                    return await response.json();
                }
                return await response.text();
            } catch (error) {
                console.error(`API Error (${endpoint}):`, error);
                throw error;
            }
        },

        get: function(endpoint) {
            return this.request(endpoint, { method: 'GET' });
        },

        post: function(endpoint, data) {
            return this.request(endpoint, { method: 'POST', body: data });
        },

        put: function(endpoint, data) {
            return this.request(endpoint, { method: 'PUT', body: data });
        },

        patch: function(endpoint, data) {
            return this.request(endpoint, { method: 'PATCH', body: data });
        },

        delete: function(endpoint) {
            return this.request(endpoint, { method: 'DELETE' });
        }
    };

    // ==========================================================================
    // Music Player Helpers
    // ==========================================================================

    Harpi.components.music = {
        // Format queue item for display
        formatQueueItem: function(item, index, isPlaying) {
            return `
                <div class="queue-item ${isPlaying ? 'playing' : ''}" data-track-id="${item.id}">
                    <span class="queue-item-index">${index + 1}</span>
                    <div class="queue-item-info">
                        <div class="queue-item-title">${Harpi.utils.escapeHtml(item.title)}</div>
                        <div class="queue-item-meta">
                            <span class="queue-item-duration">${Harpi.utils.formatDuration(item.duration)}</span>
                            ${item.requester ? `<span class="queue-item-requester">by ${Harpi.utils.escapeHtml(item.requester)}</span>` : ''}
                        </div>
                    </div>
                    <div class="queue-item-actions">
                        <button class="btn btn-ghost btn-sm" hx-delete="/api/music/queue/${item.id}" hx-target="closest .queue-item" hx-swap="outerHTML" aria-label="Remove from queue">✕</button>
                    </div>
                </div>
            `;
        },

        // Update playback progress bar
        updateProgress: function(current, total) {
            const progressBar = document.querySelector('.playback-progress .progress-bar');
            const currentTime = document.querySelector('.playback-current-time');
            const totalTime = document.querySelector('.playback-total-time');
            
            if (progressBar && total > 0) {
                const percent = (current / total) * 100;
                progressBar.style.width = `${percent}%`;
            }
            
            if (currentTime) currentTime.textContent = Harpi.utils.formatDuration(current);
            if (totalTime) totalTime.textContent = Harpi.utils.formatDuration(total);
        },

        // Update volume display
        updateVolume: function(volume) {
            const volumeFill = document.querySelector('.volume-fill');
            const volumeText = document.querySelector('.volume-text');
            
            if (volumeFill) volumeFill.style.width = `${volume * 100}%`;
            if (volumeText) volumeText.textContent = `${Math.round(volume * 100)}%`;
        }
    };

    // ==========================================================================
    // Initialization
    // ==========================================================================

    function init() {
        // Initialize components
        Harpi.components.toast.init();
        Harpi.components.guildSelector.init(true);
        Harpi.components.wsStatus.init();
        Harpi.components.latency.init();
        Harpi.components.clock.init();
        
        // Initialize Lucide icons
        if (window.lucide) {
            lucide.createIcons();
        }

        // HTMX event listeners
        document.body.addEventListener('htmx:configRequest', Harpi.htmx.configRequest);
        document.body.addEventListener('htmx:beforeSwap', Harpi.htmx.beforeSwap);
        document.body.addEventListener('htmx:afterSwap', Harpi.htmx.afterSwap);
        document.body.addEventListener('htmx:responseError', Harpi.htmx.responseError);
        document.body.addEventListener('htmx:sendError', Harpi.htmx.sendError);

        // Global keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            // Escape closes modals
            if (e.key === 'Escape') {
                Harpi.components.modal.close();
            }
            
            // Ctrl/Cmd + K for search (future)
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                // TODO: Open search modal
            }
        });

        // Handle page visibility for polling
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                // Page hidden - could pause polling
                document.body.classList.add('page-hidden');
            } else {
                // Page visible - resume polling
                document.body.classList.remove('page-hidden');
                // Trigger HTMX polling elements
                document.querySelectorAll('[hx-trigger*="every"]').forEach(el => {
                    htmx.trigger(el, 'poll');
                });
            }
        });

        // Announce to Alpine that Harpi is ready
        document.dispatchEvent(new CustomEvent('harpi:ready', { detail: Harpi }));

        console.log(`[Harpi] v${Harpi.version} initialized`);
    }

    // Auto-initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Export for module systems
    if (typeof module !== 'undefined' && module.exports) {
        module.exports = Harpi;
    }
})();