class ChatApp {
    constructor() {
        // Auto-detect API URL based on environment
        this.apiBaseUrl = this.detectApiUrl();
        this.chatMessages = document.getElementById('chat-messages');
        this.questionInput = document.getElementById('question-input');
        this.chatForm = document.getElementById('chat-form');
        this.suggestionsContainer = document.getElementById('suggestions');
        this.newChatBtn = document.getElementById('new-chat-btn');

        this.conversationHistory = [];
        this.isStreaming = false;

        this.initializeEventListeners();
        this.initializeAccessibility();
        this.loadDefaultSuggestions();

        // Configure marked for security
        marked.setOptions({
            breaks: true,
            gfm: true,
            sanitize: false, // We'll sanitize manually
            highlight: function (code, lang) {
                if (lang && hljs.getLanguage(lang)) {
                    try {
                        return hljs.highlight(code, { language: lang }).value;
                    } catch (err) { }
                }
                return hljs.highlightAuto(code).value;
            },
            langPrefix: 'hljs language-'
        });
    }

    detectApiUrl() {
        // Check if we're running in development (localhost)
        if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' || window.location.protocol === 'file:') {
            return 'http://localhost:8000';
        }

        // Check for environment variable or meta tag with API URL
        const apiUrlMeta = document.querySelector('meta[name="api-url"]');
        if (apiUrlMeta) {
            return apiUrlMeta.content;
        }

        // Default to production API URL (you'll need to update this with your Render URL)
        return 'https://csharp-ai-buddy-api.onrender.com/';
    }

    initializeEventListeners() {
        // Form submission
        this.chatForm.addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleSubmit();
        });

        // Auto-resize textarea
        this.questionInput.addEventListener('input', () => {
            this.autoResizeTextarea();
        });

        // Enter key handling (Shift+Enter for new line, Enter to submit)
        this.questionInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.handleSubmit();
            }
        });

        // New chat button
        this.newChatBtn.addEventListener('click', () => {
            this.startNewChat();
        });

        // Suggestion clicks
        this.suggestionsContainer.addEventListener('click', (e) => {
            if (e.target.classList.contains('suggestion-btn')) {
                const suggestion = e.target.dataset.suggestion;
                this.questionInput.value = suggestion;
                this.questionInput.focus();
                this.autoResizeTextarea();
            }
        });
    }

    initializeAccessibility() {
        // Ensure proper focus management
        this.questionInput.focus();

        // Add keyboard navigation for suggestions
        this.suggestionsContainer.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                if (e.target.classList.contains('suggestion-btn')) {
                    e.target.click();
                }
            }
        });
    }

    autoResizeTextarea() {
        this.questionInput.style.height = 'auto';
        this.questionInput.style.height = Math.min(this.questionInput.scrollHeight, 120) + 'px';
    }

    async handleSubmit() {
        const question = this.questionInput.value.trim();
        if (!question || this.isStreaming) return;

        // Add user message
        this.addMessage('user', question);

        // Clear input and reset height
        this.questionInput.value = '';
        this.questionInput.style.height = 'auto';

        // Hide suggestions temporarily
        this.suggestionsContainer.style.display = 'none';

        // Send message to backend
        await this.sendMessage(question);
    }


    addMessage(role, content, isStreaming = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}`;
        messageDiv.setAttribute('role', 'article');
        messageDiv.setAttribute('aria-label', `${role} message`);

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';

        if (role === 'user') {
            // Sanitize user input to prevent XSS
            contentDiv.textContent = content;
        } else {
            // For assistant messages, render markdown
            if (isStreaming) {
                contentDiv.innerHTML = '<div class="loading">Thinking...</div>';
            } else {
                contentDiv.innerHTML = this.sanitizeAndRenderMarkdown(content);
            }
        }

        messageDiv.appendChild(contentDiv);
        this.chatMessages.appendChild(messageDiv);

        // Remove welcome message if it exists
        const welcomeMessage = this.chatMessages.querySelector('.welcome-message');
        if (welcomeMessage) {
            welcomeMessage.remove();
        }

        // Scroll to bottom
        this.scrollToBottom();

        return contentDiv;
    }

    sanitizeAndRenderMarkdown(content) {
        // Basic HTML sanitization to prevent XSS
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = marked.parse(content);

        // Remove potentially dangerous elements and attributes
        this.sanitizeElement(tempDiv);

        // Apply syntax highlighting to code blocks
        const codeBlocks = tempDiv.querySelectorAll('pre code');
        codeBlocks.forEach(block => {
            hljs.highlightElement(block);
        });

        return tempDiv.innerHTML;
    }

    sanitizeElement(element) {
        // Remove script tags and event handlers
        const scripts = element.querySelectorAll('script');
        scripts.forEach(script => script.remove());

        // Remove dangerous attributes
        const dangerousAttrs = ['onclick', 'onload', 'onerror', 'onmouseover', 'javascript:'];
        const allElements = element.querySelectorAll('*');

        allElements.forEach(el => {
            // Remove dangerous attributes
            Array.from(el.attributes).forEach(attr => {
                if (dangerousAttrs.some(dangerous =>
                    attr.name.toLowerCase().includes(dangerous.toLowerCase()) ||
                    attr.value.toLowerCase().includes('javascript:')
                )) {
                    el.removeAttribute(attr.name);
                }
            });

            // Only allow safe tags
            const safeTags = ['p', 'br', 'strong', 'em', 'code', 'pre', 'ul', 'ol', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote', 'a'];
            if (!safeTags.includes(el.tagName.toLowerCase())) {
                // Replace with span to preserve content
                const span = document.createElement('span');
                span.innerHTML = el.innerHTML;
                el.parentNode.replaceChild(span, el);
            }
        });

        // Sanitize links
        const links = element.querySelectorAll('a');
        links.forEach(link => {
            if (link.href && !link.href.startsWith('http')) {
                link.removeAttribute('href');
            }
            link.setAttribute('target', '_blank');
            link.setAttribute('rel', 'noopener noreferrer');
        });
    }

    async sendMessage(question) {
        this.isStreaming = true;
        const submitBtn = document.querySelector('.send-btn');
        submitBtn.disabled = true;

        // Add loading message
        const assistantMessageContent = this.addMessage('assistant', '', true);

        try {
            // Using relative URL that will be proxied to backend
            const response = await fetch(`${this.apiBaseUrl}/api/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify({
                    message: question,
                    history: this.conversationHistory
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            // Handle streaming response
            await this.handleStreamingResponse(response, assistantMessageContent);

            // Update conversation history
            this.conversationHistory.push(
                { role: 'user', content: question },
                { role: 'assistant', content: assistantMessageContent.textContent }
            );

            // Generate follow-up suggestions
            this.generateFollowUpSuggestions(assistantMessageContent.textContent);
        } catch (error) {
            console.error('Error sending message:', error);
            assistantMessageContent.innerHTML = `
                <div class="error-message">
                    <p>Sorry, I encountered an error while processing your request. Please try again.</p>
                    <small>Error: ${error.message}</small>
                </div>
            `;
        } finally {
            this.isStreaming = false;
            submitBtn.disabled = false;
            this.questionInput.focus();
        }
    }

    async handleStreamingResponse(response, contentElement) {
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let fullContent = '';

        try {
            while (true) {
                const { done, value } = await reader.read();

                if (done) break;

                buffer += decoder.decode(value, { stream: true });

                // Process complete JSON-L lines
                const lines = buffer.split('\n');
                buffer = lines.pop(); // Keep incomplete line in buffer

                for (const line of lines) {
                    if (line.trim()) {
                        try {
                            const data = JSON.parse(line);

                            if (data.type === 'content') {
                                fullContent += data.content;
                                contentElement.innerHTML = this.sanitizeAndRenderMarkdown(fullContent);

                                // Apply syntax highlighting to any new code blocks
                                const codeBlocks = contentElement.querySelectorAll('pre code:not(.hljs)');
                                codeBlocks.forEach(block => {
                                    hljs.highlightElement(block);
                                });

                                this.scrollToBottom();
                            } else if (data.type === 'error') {
                                throw new Error(data.message);
                            }
                        } catch (parseError) {
                            console.warn('Failed to parse JSON line:', line, parseError);
                        }
                    }
                }
            }

            // Process any remaining buffer content
            if (buffer.trim()) {
                try {
                    const data = JSON.parse(buffer);
                    if (data.type === 'content') {
                        fullContent += data.content;
                        contentElement.innerHTML = this.sanitizeAndRenderMarkdown(fullContent);
                        
                        // Apply syntax highlighting to any remaining code blocks
                        const codeBlocks = contentElement.querySelectorAll('pre code:not(.hljs)');
                        codeBlocks.forEach(block => {
                            hljs.highlightElement(block);
                        });
                    }
                } catch (parseError) {
                    console.warn('Failed to parse final buffer:', buffer, parseError);
                }
            }
            
        } finally {
            reader.releaseLock();
        }
    }
    
    generateFollowUpSuggestions(assistantResponse) {
        // Simple follow-up suggestion generation based on response content
        const suggestions = [];
        
        if (assistantResponse.toLowerCase().includes('class')) {
            suggestions.push('Can you show me an example?');
            suggestions.push('What about inheritance?');
        } else if (assistantResponse.toLowerCase().includes('exception')) {
            suggestions.push('What are best practices for exception handling?');
            suggestions.push('How do I create custom exceptions?');
        } else if (assistantResponse.toLowerCase().includes('async')) {
            suggestions.push('How does Task.Run differ from async/await?');
            suggestions.push('What about cancellation tokens?');
        } else {
            suggestions.push('Can you explain this further?');
            suggestions.push('Show me a practical example');
            suggestions.push('What are common mistakes to avoid?');
        }
        
        this.updateSuggestions(suggestions.slice(0, 3));
    }
    
    loadDefaultSuggestions() {
        const defaultSuggestions = [
            'How do I create a class in C#?',
            'What are the differences between var and explicit types?',
            'How do I handle exceptions in C#?'
        ];
        this.updateSuggestions(defaultSuggestions);
    }
    
    updateSuggestions(suggestions) {
        this.suggestionsContainer.innerHTML = '';
        
        suggestions.forEach(suggestion => {
            const button = document.createElement('button');
            button.className = 'suggestion-btn';
            button.textContent = suggestion;
            button.dataset.suggestion = suggestion;
            button.setAttribute('tabindex', '0');
            button.setAttribute('aria-label', `Suggestion: ${suggestion}`);
            
            this.suggestionsContainer.appendChild(button);
        });
        
        this.suggestionsContainer.style.display = 'block';
    }
    
    startNewChat() {
        // Clear conversation history
        this.conversationHistory = [];
        
        // Clear chat messages
        this.chatMessages.innerHTML = `
            <div class="welcome-message">
                <h2>Welcome to C# AI Buddy!</h2>
                <p>Ask me anything about C# programming, and I'll help you out.</p>
            </div>
        `;
        
        // Reset suggestions
        this.loadDefaultSuggestions();
        
        // Focus input
        this.questionInput.focus();
        
        // Announce to screen readers
        const announcement = document.createElement('div');
        announcement.setAttribute('aria-live', 'polite');
        announcement.setAttribute('aria-atomic', 'true');
        announcement.className = 'sr-only';
        announcement.textContent = 'Started new chat conversation';
        document.body.appendChild(announcement);

        
        setTimeout(() => {
            document.body.removeChild(announcement);
        }, 1000);
    }
    
    scrollToBottom() {
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }
}

class SamplesGallery {
    constructor() {
        this.apiBaseUrl = this.detectApiUrl();
        this.samplesGrid = document.getElementById('samples-grid');
        this.samplesSearch = document.getElementById('samples-search');
        this.searchBtn = document.getElementById('search-btn');
        this.filtersToggle = document.getElementById('filters-toggle');
        this.filtersPanel = document.getElementById('filters-panel');
        this.tagFilters = document.getElementById('tag-filters');
        this.clearFiltersBtn = document.getElementById('clear-filters');
        this.pagination = document.getElementById('pagination');
        this.loadingSpinner = document.getElementById('samples-loading');
        this.noResults = document.getElementById('no-results');
        this.sampleModal = document.getElementById('sample-modal');
        this.modalClose = document.getElementById('modal-close');
        this.modalSampleDetails = document.getElementById('modal-sample-details');

        this.currentPage = 1;
        this.currentSearch = '';
        this.currentFilters = [];
        this.availableTags = [];
        this.currentSample = null;

        this.initializeEventListeners();
        this.loadAvailableTags();
        this.loadSamples();
    }

    detectApiUrl() {
        // Check if we're running in development (localhost)
        if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' || window.location.protocol === 'file:') {
            return 'http://localhost:8000';
        }

        // Check for environment variable or meta tag with API URL
        const apiUrlMeta = document.querySelector('meta[name="api-url"]');
        if (apiUrlMeta) {
            return apiUrlMeta.content;
        }

        // Default to production API URL
        return 'https://csharp-ai-buddy-api.onrender.com/';
    }

    initializeEventListeners() {
        // Search functionality
        this.samplesSearch.addEventListener('input', () => {
            this.debounceSearch();
        });

        this.searchBtn.addEventListener('click', () => {
            this.performSearch();
        });

        this.samplesSearch.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                this.performSearch();
            }
        });

        // Filters
        this.filtersToggle.addEventListener('click', () => {
            this.toggleFilters();
        });

        this.clearFiltersBtn.addEventListener('click', () => {
            this.clearAllFilters();
        });

        // Modal
        this.modalClose.addEventListener('click', () => {
            this.closeSampleModal();
        });

        this.sampleModal.addEventListener('click', (e) => {
            if (e.target === this.sampleModal) {
                this.closeSampleModal();
            }
        });

        // Keyboard navigation for modal
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.sampleModal.style.display !== 'none') {
                this.closeSampleModal();
            }
        });

        // Outside click to close filters
        document.addEventListener('click', (e) => {
            if (!this.filtersToggle.contains(e.target) && !this.filtersPanel.contains(e.target)) {
                this.filtersPanel.style.display = 'none';
            }
        });
    }

    debounceSearch() {
        clearTimeout(this.searchTimeout);
        this.searchTimeout = setTimeout(() => {
            this.performSearch();
        }, 500);
    }

    performSearch() {
        this.currentSearch = this.samplesSearch.value.trim();
        this.currentPage = 1;
        this.loadSamples();
    }

    toggleFilters() {
        const isVisible = this.filtersPanel.style.display !== 'none';
        this.filtersPanel.style.display = isVisible ? 'none' : 'block';
    }

    async loadAvailableTags() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/api/samples/tags`);
            if (response.ok) {
                const data = await response.json();
                this.availableTags = data.tags;
                this.renderTagFilters();
            }
        } catch (error) {
            console.error('Error loading available tags:', error);
        }
    }

    renderTagFilters() {
        this.tagFilters.innerHTML = '';
        
        this.availableTags.forEach(tag => {
            const button = document.createElement('button');
            button.className = 'tag-filter';
            button.textContent = tag;
            button.dataset.tag = tag;
            
            if (this.currentFilters.includes(tag)) {
                button.classList.add('active');
            }
            
            button.addEventListener('click', () => {
                this.toggleTagFilter(tag);
            });
            
            this.tagFilters.appendChild(button);
        });
    }

    toggleTagFilter(tag) {
        if (this.currentFilters.includes(tag)) {
            this.currentFilters = this.currentFilters.filter(t => t !== tag);
        } else {
            this.currentFilters.push(tag);
        }
        
        this.currentPage = 1;
        this.renderTagFilters();
        this.loadSamples();
        
        // Track filter usage
        this.trackTelemetry('filter_used', { filter: tag, action: this.currentFilters.includes(tag) ? 'add' : 'remove' });
    }

    clearAllFilters() {
        this.currentFilters = [];
        this.renderTagFilters();
        this.currentPage = 1;
        this.loadSamples();
    }

    async loadSamples() {
        this.showLoading();
        
        try {
            const params = new URLSearchParams({
                page: this.currentPage.toString(),
                page_size: '20'
            });
            
            if (this.currentSearch) {
                params.append('search', this.currentSearch);
            }
            
            if (this.currentFilters.length > 0) {
                params.append('tags', this.currentFilters.join(','));
            }
            
            const response = await fetch(`${this.apiBaseUrl}/api/samples?${params}`);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.samples.length === 0 && (this.currentSearch || this.currentFilters.length > 0)) {
                this.showNoResults();
                // Track no results
                this.trackTelemetry('search_no_results', { 
                    query: this.currentSearch, 
                    filters: this.currentFilters 
                });
            } else {
                this.renderSamples(data.samples);
                this.renderPagination(data);
            }
            
        } catch (error) {
            console.error('Error loading samples:', error);
            this.showError('Failed to load samples. Please try again.');
        } finally {
            this.hideLoading();
        }
    }

    showLoading() {
        this.loadingSpinner.style.display = 'flex';
        this.samplesGrid.style.display = 'none';
        this.noResults.style.display = 'none';
        this.pagination.style.display = 'none';
    }

    hideLoading() {
        this.loadingSpinner.style.display = 'none';
    }

    showNoResults() {
        this.noResults.style.display = 'flex';
        this.samplesGrid.style.display = 'none';
        this.pagination.style.display = 'none';
    }

    showError(message) {
        this.noResults.innerHTML = `
            <h3>Error</h3>
            <p>${message}</p>
        `;
        this.noResults.style.display = 'flex';
        this.samplesGrid.style.display = 'none';
        this.pagination.style.display = 'none';
    }

    renderSamples(samples) {
        this.samplesGrid.innerHTML = '';
        this.samplesGrid.style.display = 'grid';
        
        samples.forEach(sample => {
            const card = this.createSampleCard(sample);
            this.samplesGrid.appendChild(card);
        });
    }

    createSampleCard(sample) {
        const card = document.createElement('div');
        card.className = 'sample-card';
        card.setAttribute('tabindex', '0');
        card.setAttribute('role', 'button');
        card.setAttribute('aria-label', `View details for ${sample.title}`);
        
        const isMicrosoft = sample.tags.includes('msft');
        
        card.innerHTML = `
            <div class="sample-header">
                ${isMicrosoft ? `
                    <div class="microsoft-badge">
                        <div class="microsoft-icon">MS</div>
                        Microsoft Authored
                    </div>
                ` : ''}
            </div>
            <h3 class="sample-title">${this.escapeHtml(sample.title)}</h3>
            <div class="sample-author">by ${this.escapeHtml(sample.author)}</div>
            <div class="sample-description">${this.escapeHtml(sample.description)}</div>
            <div class="sample-tags">
                ${sample.tags.map(tag => `
                    <span class="sample-tag ${tag === 'msft' ? 'msft' : ''}">${this.escapeHtml(tag)}</span>
                `).join('')}
            </div>
        `;
        
        card.addEventListener('click', () => {
            this.openSampleModal(sample);
        });
        
        card.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                this.openSampleModal(sample);
            }
        });
        
        return card;
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    renderPagination(data) {
        this.pagination.innerHTML = '';
        this.pagination.style.display = 'flex';
        
        // Previous button
        const prevBtn = document.createElement('button');
        prevBtn.className = 'pagination-btn';
        prevBtn.textContent = '« Previous';
        prevBtn.disabled = data.page === 1;
        prevBtn.addEventListener('click', () => {
            if (data.page > 1) {
                this.currentPage = data.page - 1;
                this.loadSamples();
            }
        });
        this.pagination.appendChild(prevBtn);
        
        // Page numbers
        const maxVisiblePages = 5;
        const startPage = Math.max(1, data.page - Math.floor(maxVisiblePages / 2));
        const endPage = Math.min(data.pages, startPage + maxVisiblePages - 1);
        
        for (let i = startPage; i <= endPage; i++) {
            const pageBtn = document.createElement('button');
            pageBtn.className = 'pagination-btn';
            pageBtn.textContent = i.toString();
            
            if (i === data.page) {
                pageBtn.classList.add('active');
            }
            
            pageBtn.addEventListener('click', () => {
                this.currentPage = i;
                this.loadSamples();
            });
            
            this.pagination.appendChild(pageBtn);
        }
        
        // Info
        const info = document.createElement('div');
        info.className = 'pagination-info';
        info.textContent = `${data.page} of ${data.pages} (${data.total} samples)`;
        this.pagination.appendChild(info);
        
        // Next button
        const nextBtn = document.createElement('button');
        nextBtn.className = 'pagination-btn';
        nextBtn.textContent = 'Next »';
        nextBtn.disabled = data.page === data.pages;
        nextBtn.addEventListener('click', () => {
            if (data.page < data.pages) {
                this.currentPage = data.page + 1;
                this.loadSamples();
            }
        });
        this.pagination.appendChild(nextBtn);
    }

    async openSampleModal(sample) {
        this.currentSample = sample;
        
        // Track sample view
        this.trackTelemetry('sample_viewed', { sample_id: sample.id, title: sample.title });
        
        try {
            // Fetch full sample details
            const response = await fetch(`${this.apiBaseUrl}/api/samples/${sample.id}`);
            if (response.ok) {
                const fullSample = await response.json();
                this.renderSampleModal(fullSample);
            } else {
                this.renderSampleModal(sample);
            }
        } catch (error) {
            console.error('Error fetching sample details:', error);
            this.renderSampleModal(sample);
        }
        
        this.sampleModal.style.display = 'flex';
        this.sampleModal.setAttribute('aria-hidden', 'false');
        this.modalClose.focus();
    }

    renderSampleModal(sample) {
        const isMicrosoft = sample.tags.includes('msft');
        
        this.modalSampleDetails.innerHTML = `
            <div class="sample-detail-header">
                ${isMicrosoft ? `
                    <div class="microsoft-badge">
                        <div class="microsoft-icon">MS</div>
                        Microsoft Authored
                    </div>
                ` : ''}
                <h3>${this.escapeHtml(sample.title)}</h3>
            </div>
            
            <div class="sample-detail-description">
                ${this.escapeHtml(sample.description)}
            </div>
            
            <div class="sample-detail-meta">
                <div class="meta-item">
                    <div class="meta-label">Author</div>
                    <div class="meta-value">
                        <a href="${this.escapeHtml(sample.authorUrl)}" target="_blank" rel="noopener noreferrer">
                            ${this.escapeHtml(sample.author)}
                        </a>
                    </div>
                </div>
                
                <div class="meta-item">
                    <div class="meta-label">Source</div>
                    <div class="meta-value">
                        <a href="${this.escapeHtml(sample.source)}" target="_blank" rel="noopener noreferrer">
                            View on GitHub
                        </a>
                    </div>
                </div>
                
                <div class="meta-item">
                    <div class="meta-label">Tags</div>
                    <div class="meta-value">
                        ${sample.tags.map(tag => `<span class="sample-tag ${tag === 'msft' ? 'msft' : ''}">${this.escapeHtml(tag)}</span>`).join(' ')}
                    </div>
                </div>
            </div>
            
            <div class="clone-instructions">
                <button class="copy-btn" onclick="navigator.clipboard.writeText('git clone ${this.escapeHtml(sample.source)}')">Copy</button>
                <div>git clone ${this.escapeHtml(sample.source)}</div>
            </div>
        `;
        
        // Add external link tracking
        this.modalSampleDetails.querySelectorAll('a[target="_blank"]').forEach(link => {
            link.addEventListener('click', () => {
                this.trackTelemetry('external_click', { 
                    url: link.href, 
                    sample_id: sample.id,
                    link_type: link.href.includes(sample.authorUrl) ? 'author' : 'source'
                });
            });
        });
    }

    closeSampleModal() {
        this.sampleModal.style.display = 'none';
        this.sampleModal.setAttribute('aria-hidden', 'true');
        this.currentSample = null;
    }

    trackTelemetry(eventType, data) {
        // Check if telemetry is enabled
        const telemetryEnabled = localStorage.getItem('telemetry_enabled') !== 'false';
        
        if (!telemetryEnabled) {
            return;
        }
        
        const telemetryData = {
            event_type: eventType,
            data: {
                ...data,
                timestamp: new Date().toISOString(),
                url: window.location.href
            },
            user_consent: telemetryEnabled
        };
        
        // Send telemetry to backend
        fetch(`${this.apiBaseUrl}/api/telemetry`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(telemetryData)
        }).catch(error => {
            console.warn('Failed to send telemetry:', error);
        });
    }
}

class AppManager {
    constructor() {
        this.chatApp = new ChatApp();
        this.samplesGallery = new SamplesGallery();
        this.currentTab = 'chat';
        
        this.initializeNavigation();
        this.initializeTelemetryToggle();
        this.initializeUrlHandling();
    }

    initializeNavigation() {
        const chatTab = document.getElementById('chat-tab');
        const samplesTab = document.getElementById('samples-tab');
        const chatSection = document.getElementById('chat-section');
        const samplesSection = document.getElementById('samples-section');

        chatTab.addEventListener('click', () => {
            this.switchTab('chat');
        });

        samplesTab.addEventListener('click', () => {
            this.switchTab('samples');
        });
    }

    switchTab(tab) {
        const chatTab = document.getElementById('chat-tab');
        const samplesTab = document.getElementById('samples-tab');
        const chatSection = document.getElementById('chat-section');
        const samplesSection = document.getElementById('samples-section');

        // Update tab states
        chatTab.classList.toggle('active', tab === 'chat');
        samplesTab.classList.toggle('active', tab === 'samples');

        // Update section visibility
        chatSection.style.display = tab === 'chat' ? 'flex' : 'none';
        samplesSection.style.display = tab === 'samples' ? 'flex' : 'none';

        this.currentTab = tab;
        
        // Update URL for deep linking
        const url = new URL(window.location);
        if (tab === 'samples') {
            url.searchParams.set('tab', 'samples');
        } else {
            url.searchParams.delete('tab');
        }
        window.history.replaceState({}, '', url);
    }

    initializeTelemetryToggle() {
        const telemetryToggle = document.getElementById('telemetry-toggle');
        const telemetryStatus = document.getElementById('telemetry-status');
        
        // Load saved preference
        const telemetryEnabled = localStorage.getItem('telemetry_enabled') !== 'false';
        this.updateTelemetryUI(telemetryEnabled);
        
        telemetryToggle.addEventListener('click', () => {
            const currentlyEnabled = localStorage.getItem('telemetry_enabled') !== 'false';
            const newState = !currentlyEnabled;
            
            localStorage.setItem('telemetry_enabled', newState.toString());
            this.updateTelemetryUI(newState);
        });
    }

    updateTelemetryUI(enabled) {
        const telemetryToggle = document.getElementById('telemetry-toggle');
        const telemetryStatus = document.getElementById('telemetry-status');
        
        telemetryStatus.textContent = `Telemetry: ${enabled ? 'On' : 'Off'}`;
        telemetryToggle.classList.toggle('disabled', !enabled);
    }

    initializeUrlHandling() {
        // Handle initial URL
        const urlParams = new URLSearchParams(window.location.search);
        const initialTab = urlParams.get('tab');
        
        if (initialTab === 'samples') {
            this.switchTab('samples');
        }
        
        // Handle back/forward navigation
        window.addEventListener('popstate', () => {
            const urlParams = new URLSearchParams(window.location.search);
            const tab = urlParams.get('tab') || 'chat';
            this.switchTab(tab);
        });
    }
}

// Initialize the app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new AppManager();
});

// Add screen reader only class for accessibility announcements
const style = document.createElement('style');
style.textContent = `
    .sr-only {
        position: absolute;
        width: 1px;
        height: 1px;
        padding: 0;
        margin: -1px;
        overflow: hidden;
        clip: rect(0, 0, 0, 0);
        white-space: nowrap;
        border: 0;
    }
`;
document.head.appendChild(style);