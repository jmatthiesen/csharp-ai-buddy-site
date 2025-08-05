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

        // Initialize markdown and syntax highlighting when libraries are loaded
        this.initializeMarkdownSupport();
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
            // Switch to chat tab when starting a new chat
            document.dispatchEvent(new CustomEvent('switchToChat'));
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
            // For assistant messages, render markdown and apply syntax highlighting
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

    initializeMarkdownSupport() {
        // Configure marked for security when available
        if (typeof marked !== 'undefined') {
            marked.setOptions({
                breaks: true,
                gfm: true,
                sanitize: false, // We'll sanitize manually
                highlight: function (code, lang) {
                    if (typeof hljs !== 'undefined' && lang && hljs.getLanguage && hljs.getLanguage(lang)) {
                        try {
                            return hljs.highlight(code, { language: lang }).value;
                        } catch (err) { }
                    }
                    if (typeof hljs !== 'undefined' && hljs.highlightAuto) {
                        try {
                            return hljs.highlightAuto(code).value;
                        } catch (err) { }
                    }
                    return code;
                },
                langPrefix: 'hljs language-'
            });
        }
    }

    sanitizeAndRenderMarkdown(content) {
        // Basic HTML sanitization to prevent XSS
        const tempDiv = document.createElement('div');
        
        // Use marked if available, otherwise fall back to basic formatting
        if (typeof marked !== 'undefined' && marked.parse) {
            tempDiv.innerHTML = marked.parse(content);
        } else {
            // Basic markdown-like formatting as fallback
            let formatted = content
                .replace(/```(\w+)?\n([\s\S]*?)\n```/g, '<pre><code class="language-$1">$2</code></pre>')
                .replace(/`([^`]+)`/g, '<code>$1</code>')
                .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                .replace(/\*(.*?)\*/g, '<em>$1</em>')
                .replace(/\n/g, '<br>');
            tempDiv.innerHTML = formatted;
        }

        // Remove potentially dangerous elements and attributes
        this.sanitizeElement(tempDiv);

        // Apply syntax highlighting to code blocks if hljs is available
        if (typeof hljs !== 'undefined' && hljs.highlightElement) {
            const codeBlocks = tempDiv.querySelectorAll('pre code');
            codeBlocks.forEach(block => {
                try {
                    hljs.highlightElement(block);
                } catch (err) {
                    console.warn('Syntax highlighting failed:', err);
                }
            });
        }

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
                // Replace unsafe tags with spans
                const span = document.createElement('span');
                span.innerHTML = el.innerHTML;
                el.parentNode?.replaceChild(span, el);
            }

            // Ensure links are safe
            if (el.tagName.toLowerCase() === 'a') {
                el.setAttribute('target', '_blank');
                el.setAttribute('rel', 'noopener noreferrer');
                
                // Only allow http/https links
                const href = el.getAttribute('href');
                if (href && !href.match(/^https?:\/\//)) {
                    el.removeAttribute('href');
                }
            }
        });
    }

    async sendMessage(question) {
        this.isStreaming = true;
        const submitBtn = document.querySelector('.send-btn');
        submitBtn.disabled = true;

        // Add loading message
        const assistantMessageContent = this.addMessage('assistant', '', true);

        try {
            // Add to conversation history
            this.conversationHistory.push({ role: 'user', content: question });

            const response = await fetch(`${this.apiBaseUrl}/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    messages: this.conversationHistory,
                    stream: true
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            // Handle streaming response
            if (response.headers.get('content-type')?.includes('text/plain')) {
                await this.handleStreamingResponse(response, assistantMessageContent);
            } else {
                // Handle non-streaming response
                const data = await response.json();
                const content = data.response || data.content || 'Sorry, I received an empty response.';
                assistantMessageContent.innerHTML = this.sanitizeAndRenderMarkdown(content);
                
                // Add to conversation history
                this.conversationHistory.push({ role: 'assistant', content: content });
            }
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

                                // Apply syntax highlighting to any new code blocks if hljs is available
                                if (typeof hljs !== 'undefined') {
                                    const codeBlocks = contentElement.querySelectorAll('pre code:not(.hljs)');
                                    codeBlocks.forEach(block => {
                                        try {
                                            hljs.highlightElement(block);
                                        } catch (err) {
                                            console.warn('Syntax highlighting failed:', err);
                                        }
                                    });
                                }

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
                    }
                } catch (parseError) {
                    console.warn('Failed to parse remaining buffer:', buffer, parseError);
                }
            }

            // Add final response to conversation history
            if (fullContent) {
                this.conversationHistory.push({ role: 'assistant', content: fullContent });
            }

        } catch (error) {
            console.error('Streaming error:', error);
            contentElement.innerHTML = `
                <div class="error-message">
                    <p>Error during streaming response: ${error.message}</p>
                </div>
            `;
        }
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
        this.clearSearchBtn = document.getElementById('clear-search-btn');
        this.sortSelect = document.getElementById('sort-select');
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
        this.currentSort = 'alphabetical';
        this.currentFilters = [];
        this.availableTags = [];
        this.currentSample = null;

        this.initializeEventListeners();
        this.loadMockData(); // Load mock data for demonstration
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
            this.updateClearSearchButton();
            this.debounceSearch();
        });

        this.searchBtn.addEventListener('click', () => {
            this.performSearch();
        });

        // Clear search functionality
        this.clearSearchBtn.addEventListener('click', () => {
            this.clearSearch();
        });

        this.samplesSearch.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                this.performSearch();
            } else if (e.key === 'Escape') {
                this.clearSearch();
            }
        });

        // Sort functionality
        this.sortSelect.addEventListener('change', () => {
            this.currentSort = this.sortSelect.value;
            this.performSearch();
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
        this.loadMockData();
    }

    clearSearch() {
        this.samplesSearch.value = '';
        this.currentSearch = '';
        this.updateClearSearchButton();
        this.currentPage = 1;
        this.loadMockData();
    }

    updateClearSearchButton() {
        const hasText = this.samplesSearch.value.trim().length > 0;
        this.clearSearchBtn.style.display = hasText ? 'block' : 'none';
    }

    toggleFilters() {
        const isVisible = this.filtersPanel.style.display !== 'none';
        this.filtersPanel.style.display = isVisible ? 'none' : 'block';
    }

    loadMockData() {
        // Mock data for demonstration
        const mockSamples = [
            {
                id: '1',
                title: '.NET + Semantic Search + AI Search - eShopLite',
                description: 'eShopLite - Semantic Search - Azure AI Search is a reference .NET application implementing an eCommerce site with advanced search capabilities using semantic search and Azure AI services.',
                author: 'Bruno Capuano',
                authorUrl: 'https://github.com/BrunoCapuano',
                source: 'https://github.com/Microsoft/eshoplite-semantic-search',
                tags: ['AI', 'Azure AI Search', '.NET/C#', 'msft'],
                date: '2024-01-15'
            },
            {
                id: '2',
                title: 'Blazor Server Chat with SignalR',
                description: 'A real-time chat application built with Blazor Server and SignalR, demonstrating real-time communication in .NET applications with modern web UI patterns.',
                author: 'Microsoft .NET Team',
                authorUrl: 'https://github.com/dotnet',
                source: 'https://github.com/dotnet-samples/blazor-signalr-chat',
                tags: ['.NET/C#', 'Blazor', 'SignalR', 'msft'],
                date: '2024-02-10'
            },
            {
                id: '3',
                title: 'Minimal API with Entity Framework Core',
                description: 'A simple yet powerful example of building RESTful APIs using .NET Minimal APIs with Entity Framework Core for data access and modern authentication patterns.',
                author: 'Microsoft .NET Team',
                authorUrl: 'https://github.com/dotnet',
                source: 'https://github.com/dotnet-samples/minimal-api-ef-core',
                tags: ['.NET/C#', 'Entity Framework', 'API', 'msft'],
                date: '2024-01-28'
            },
            {
                id: '4',
                title: 'MAUI Cross-Platform App',
                description: 'Cross-platform mobile and desktop application built with .NET MAUI, showcasing native UI patterns across iOS, Android, Windows, and macOS from a single codebase.',
                author: 'Microsoft .NET Team',
                authorUrl: 'https://github.com/dotnet',
                source: 'https://github.com/dotnet-samples/maui-cross-platform',
                tags: ['.NET/C#', 'MAUI', 'Mobile', 'msft'],
                date: '2024-02-05'
            },
            {
                id: '5',
                title: 'Clean Architecture Template',
                description: 'A comprehensive Clean Architecture solution template for .NET applications, including CQRS, Domain-Driven Design patterns, and extensive testing examples.',
                author: 'Jason Taylor',
                authorUrl: 'https://github.com/jasontaylordev',
                source: 'https://github.com/jasontaylordev/CleanArchitecture',
                tags: ['.NET/C#', 'Architecture', 'CQRS', 'Testing'],
                date: '2024-01-20'
            },
            {
                id: '6',
                title: 'Machine Learning with ML.NET',
                description: 'Machine learning examples using ML.NET framework, including classification, regression, clustering, and recommendation systems with custom model training.',
                author: 'Microsoft ML.NET Team',
                authorUrl: 'https://github.com/dotnet',
                source: 'https://github.com/dotnet-samples/mlnet-machine-learning',
                tags: ['.NET/C#', 'ML.NET', 'AI', 'msft'],
                date: '2024-02-12'
            }
        ];

        // Filter samples based on search and filters
        let filteredSamples = mockSamples;
        
        if (this.currentSearch) {
            const searchLower = this.currentSearch.toLowerCase();
            filteredSamples = filteredSamples.filter(sample =>
                sample.title.toLowerCase().includes(searchLower) ||
                sample.description.toLowerCase().includes(searchLower) ||
                sample.author.toLowerCase().includes(searchLower) ||
                sample.tags.some(tag => tag.toLowerCase().includes(searchLower))
            );
        }

        if (this.currentFilters.length > 0) {
            filteredSamples = filteredSamples.filter(sample =>
                this.currentFilters.some(filter => sample.tags.includes(filter))
            );
        }

        // Sort samples based on current sort option
        if (this.currentSort === 'alphabetical') {
            filteredSamples.sort((a, b) => b.title.localeCompare(a.title)); // Z-A (descending)
        } else if (this.currentSort === 'date') {
            filteredSamples.sort((a, b) => new Date(b.date) - new Date(a.date)); // Newest first
        }

        // Extract unique tags from all samples
        this.availableTags = [...new Set(mockSamples.flatMap(sample => sample.tags))].sort();
        this.renderTagFilters();

        if (filteredSamples.length === 0) {
            this.showNoResults();
            this.trackTelemetry('search_no_results', { 
                query: this.currentSearch, 
                filters: this.currentFilters 
            });
        } else {
            this.renderSamples(filteredSamples);
            this.renderPagination({
                samples: filteredSamples,
                total: filteredSamples.length,
                page: 1,
                pages: 1,
                page_size: 20
            });
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
        this.loadMockData();
        
        // Track filter usage
        this.trackTelemetry('filter_used', { filter: tag, action: this.currentFilters.includes(tag) ? 'add' : 'remove' });
    }

    clearAllFilters() {
        this.currentFilters = [];
        this.renderTagFilters();
        this.currentPage = 1;
        this.loadMockData();
    }

    showNoResults() {
        this.noResults.style.display = 'flex';
        this.samplesGrid.style.display = 'none';
        this.pagination.style.display = 'none';
    }

    renderSamples(samples) {
        this.samplesGrid.innerHTML = '';
        this.samplesGrid.style.display = 'grid';
        this.noResults.style.display = 'none';
        
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
        this.pagination.innerHTML = `
            <div class="pagination-info">
                Showing ${data.samples.length} of ${data.total} samples
            </div>
        `;
        this.pagination.style.display = 'flex';
    }

    openSampleModal(sample) {
        this.currentSample = sample;
        
        // Track sample view
        this.trackTelemetry('sample_viewed', { sample_id: sample.id, title: sample.title });
        
        this.renderSampleModal(sample);
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
                <button class="copy-btn" onclick="navigator.clipboard?.writeText?.('git clone ${this.escapeHtml(sample.source)}')">Copy</button>
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
        
        console.log('Telemetry:', eventType, data);
        
        // In a real implementation, this would send to the backend
        // For now, just log to console
    }
}

class AppManager {
    constructor() {
        this.chatApp = new ChatApp();
        this.samplesGallery = new SamplesGallery();
        this.currentTab = 'chat';
        
        this.initializeSidebarState();
        this.initializeNavigation();
        this.initializePrivacyNotice();
        this.initializeUrlHandling();
    }

    initializeNavigation() {
        const chatTab = document.getElementById('chat-tab');
        const samplesTab = document.getElementById('samples-tab');
        const chatSection = document.getElementById('chat-section');
        const samplesSection = document.getElementById('samples-section');
        const sidebarToggle = document.getElementById('sidebar-toggle');
        const sidebar = document.getElementById('sidebar');

        // Tab navigation
        chatTab.addEventListener('click', () => {
            this.switchTab('chat');
        });

        samplesTab.addEventListener('click', () => {
            this.switchTab('samples');
        });

        // Listen for New Chat button requests to switch to chat tab
        document.addEventListener('switchToChat', () => {
            this.switchTab('chat');
        });

        // Sidebar toggle
        sidebarToggle.addEventListener('click', () => {
            this.toggleSidebar();
        });

        // Auto-collapse sidebar on mobile when clicking nav items
        if (window.innerWidth <= 768) {
            [chatTab, samplesTab].forEach(tab => {
                tab.addEventListener('click', () => {
                    if (sidebar.classList.contains('expanded')) {
                        this.toggleSidebar();
                    }
                });
            });
        }

        // Handle window resize
        window.addEventListener('resize', () => {
            if (window.innerWidth > 768) {
                sidebar.classList.add('expanded');
            } else {
                sidebar.classList.remove('expanded');
            }
        });
    }

    toggleSidebar() {
        const sidebar = document.getElementById('sidebar');
        const isExpanded = sidebar.classList.contains('expanded');
        
        if (isExpanded) {
            sidebar.classList.remove('expanded');
            sidebar.classList.add('collapsed');
        } else {
            sidebar.classList.remove('collapsed');
            sidebar.classList.add('expanded');
        }
        
        // Save sidebar state to localStorage
        localStorage.setItem('sidebarExpanded', !isExpanded);
    }

    initializeSidebarState() {
        const sidebar = document.getElementById('sidebar');
        const savedState = localStorage.getItem('sidebarExpanded');
        
        // Default to expanded on desktop, collapsed on mobile
        if (window.innerWidth <= 768) {
            sidebar.classList.remove('expanded');
            sidebar.classList.add('collapsed');
        } else {
            const shouldExpand = savedState === null ? true : savedState === 'true';
            if (shouldExpand) {
                sidebar.classList.add('expanded');
                sidebar.classList.remove('collapsed');
            } else {
                sidebar.classList.remove('expanded');
                sidebar.classList.add('collapsed');
            }
        }
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

    initializePrivacyNotice() {
        const privacyNotice = document.getElementById('privacy-notice');
        const acceptBtn = document.getElementById('accept-privacy');
        const declineBtn = document.getElementById('decline-privacy');
        
        // Check if user has already made a choice
        const privacyChoice = localStorage.getItem('privacy_choice');
        
        if (!privacyChoice) {
            // Show privacy notice if no choice has been made
            privacyNotice.style.display = 'block';
        }
        
        acceptBtn.addEventListener('click', () => {
            localStorage.setItem('privacy_choice', 'accepted');
            localStorage.setItem('telemetry_enabled', 'true');
            privacyNotice.style.display = 'none';
        });
        
        declineBtn.addEventListener('click', () => {
            localStorage.setItem('privacy_choice', 'declined');
            localStorage.setItem('telemetry_enabled', 'false');
            privacyNotice.style.display = 'none';
        });
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