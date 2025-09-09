class ChatApp {
    constructor(apiBaseUrl, trackTelemetry) {
        this.apiBaseUrl = apiBaseUrl;
        this.trackTelemetry = trackTelemetry;
        this.chatMessages = document.getElementById('chat-messages');
        this.questionInput = document.getElementById('question-input');
        this.chatForm = document.getElementById('chat-form');
        this.suggestionsContainer = document.getElementById('suggestions');
        this.newChatBtn = document.getElementById('new-chat-btn');

        this.conversationHistory = [];
        this.isStreaming = false;
        this.magicKey = null; // Store the magic key

        // AI configuration options
        this.aiOptions = {
            dotnetVersion: '.NET 9',
            aiLibrary: 'OpenAI',
            aiProvider: 'OpenAI'
        };

        // Initialize session tracking
        this.initializeSessionTracking();

        this.initializeEventListeners();
        this.initializeAccessibility();
        this.loadDefaultSuggestions();
        this.updateOptionsSummary(); // Initialize the options summary

        // Initialize markdown and syntax highlighting when libraries are loaded
        this.initializeMarkdownSupport();
        
        // Initialize magic key functionality
        this.initializeMagicKey();
    }

    initializeSessionTracking() {
        // Initialize session storage for chat tracking
        if (!sessionStorage.getItem('session_chat_count')) {
            sessionStorage.setItem('session_chat_count', '0');
        }
        if (!sessionStorage.getItem('session_start_time')) {
            sessionStorage.setItem('session_start_time', Date.now().toString());
        }
    }

    getSessionChatCount() {
        return parseInt(sessionStorage.getItem('session_chat_count') || '0');
    }

    incrementSessionChatCount() {
        const currentCount = this.getSessionChatCount();
        sessionStorage.setItem('session_chat_count', (currentCount + 1).toString());
    }

    detectApiUrl() {
        // Check if we're running in development (localhost)
        if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' || window.location.protocol === 'file:') {
            return 'http://localhost:8000/api';
        }

        // Check for environment variable or meta tag with API URL
        const apiUrlMeta = document.querySelector('meta[name="api-url"]');
        if (apiUrlMeta) {
            return apiUrlMeta.content;
        }

        // Default to production API URL (you'll need to update this with your Render URL)
        return 'https://csharp-ai-buddy-api.onrender.com/api';
    }

    isDevelopmentEnvironment() {
        // Check if we're running in development (localhost, or GitHub Codespaces)
        // Check for simulateProd query param to force production mode
        const urlParams = new URLSearchParams(window.location.search);
        return !urlParams.has('simulateProd') && (
            window.location.hostname === 'localhost' ||
            window.location.hostname === '127.0.0.1' ||
            window.location.protocol === 'file:' ||
            window.location.hostname.endsWith("github.dev")
        );
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

        // Options modal
        this.initializeOptionsModal();
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

    initializeOptionsModal() {
        const optionsBtn = document.getElementById('options-btn');
        const optionsModal = document.getElementById('options-modal');
        const optionsModalClose = document.getElementById('options-modal-close');
        const dotnetVersionSelect = document.getElementById('dotnet-version');
        const aiLibrarySelect = document.getElementById('ai-library');
        const customLibraryInput = document.getElementById('custom-library');
        const aiProviderSelect = document.getElementById('ai-provider');
        const experimentalNotice = document.querySelector('.experimental-notice');

        // Open options modal
        optionsBtn.addEventListener('click', () => {
            this.openOptionsModal();
        });

        // Close options modal
        optionsModalClose.addEventListener('click', () => {
            this.closeOptionsModal();
        });

        // Close modal when clicking outside
        optionsModal.addEventListener('click', (e) => {
            if (e.target === optionsModal) {
                this.closeOptionsModal();
            }
        });

        // Close modal with Escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && optionsModal.style.display !== 'none') {
                this.closeOptionsModal();
            }
        });

        // Handle custom library input
        aiLibrarySelect.addEventListener('change', () => {
            if (aiLibrarySelect.value === 'Other') {
                customLibraryInput.style.display = 'block';
                customLibraryInput.focus();
            } else {
                customLibraryInput.style.display = 'none';
                customLibraryInput.value = '';
            }
            this.updateAiOptions();
        });

        // Update options when selects change
        [dotnetVersionSelect, aiLibrarySelect, aiProviderSelect].forEach(select => {
            select.addEventListener('change', () => {
                this.updateAiOptions();
            });
        });

        // Update options when custom library input changes
        customLibraryInput.addEventListener('input', () => {
            this.updateAiOptions();
        });
    }

    openOptionsModal() {
        const optionsModal = document.getElementById('options-modal');
        optionsModal.style.display = 'flex';
        optionsModal.setAttribute('aria-hidden', 'false');
        
        // Focus first element
        const firstSelect = document.getElementById('dotnet-version');
        firstSelect.focus();
        
        // Update experimental notice
        this.updateExperimentalNotice();
    }

    closeOptionsModal() {
        const optionsModal = document.getElementById('options-modal');
        optionsModal.style.display = 'none';
        optionsModal.setAttribute('aria-hidden', 'true');
        
        // Return focus to options button
        document.getElementById('options-btn').focus();
    }

    updateAiOptions() {
        const dotnetVersionSelect = document.getElementById('dotnet-version');
        const aiLibrarySelect = document.getElementById('ai-library');
        const customLibraryInput = document.getElementById('custom-library');
        const aiProviderSelect = document.getElementById('ai-provider');

        this.aiOptions = {
            dotnetVersion: dotnetVersionSelect.value,
            aiLibrary: aiLibrarySelect.value === 'Other' ? customLibraryInput.value || 'Other' : aiLibrarySelect.value,
            aiProvider: aiProviderSelect.value
        };

        this.updateExperimentalNotice();
        this.updateOptionsSummary();
    }

    updateExperimentalNotice() {
        const experimentalNotice = document.querySelector('.experimental-notice');
        const dotnetVersionSelect = document.getElementById('dotnet-version');
        const aiProviderSelect = document.getElementById('ai-provider');

        const isExperimental = 
            dotnetVersionSelect.selectedOptions[0]?.dataset.experimental === 'true' ||
            aiProviderSelect.selectedOptions[0]?.dataset.experimental === 'true';

        experimentalNotice.style.display = isExperimental ? 'block' : 'none';
    }

    updateOptionsSummary() {
        const optionsSummary = document.getElementById('options-summary');
        if (optionsSummary) {
            // Create a condensed summary of current options (without model)
            const summary = `${this.aiOptions.dotnetVersion} | ${this.aiOptions.aiLibrary} | Provider: ${this.aiOptions.aiProvider}`;
            optionsSummary.textContent = summary;
        }
    }

    async handleSubmit() {
        const question = this.questionInput.value.trim();
        if (!question || this.isStreaming) return;

        try {
            // Track that a developer started a chat
            this.trackTelemetry('chat_started', { 
                question_length: question.length,
                conversation_length: this.conversationHistory.length,
                session_chat_count: this.getSessionChatCount() + 1
            });
            
            // Increment session chat count
            this.incrementSessionChatCount();

            // Add user message
            this.addMessage('user', question);

            // Clear input and reset height
            this.questionInput.value = '';
            this.questionInput.style.height = 'auto';

            // Hide suggestions temporarily
            this.suggestionsContainer.style.display = 'none';

            // Send message to backend
            await this.sendMessage(question);
        } catch (error) {
            // Handle magic key errors specifically
            if (error.message.includes('Magic key required')) {
                // Show a user-friendly message
                this.addMessage('assistant', '🔑 A magic key is required to use the AI chat feature. Please provide a valid key to continue.');
            } else {
                console.error('Error in handleSubmit:', error);
                this.addMessage('assistant', '❌ Sorry, something went wrong. Please try again.');
            }
        }
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

    initializeMagicKey() {
        // Check URL parameters for magic key (works in both dev and production)
        const urlParams = new URLSearchParams(window.location.search);
        const urlMagicKey = urlParams.get('key');
        
        if (urlMagicKey) {
            // Store the key from URL and remove it from URL for security
            this.storeMagicKey(urlMagicKey);
            // Remove the key from URL without reloading the page
            const url = new URL(window.location);
            url.searchParams.delete('key');
            window.history.replaceState({}, '', url);
            return; // Key loaded from URL, we're done
        }
        
        // In development environment, skip magic key requirement
        if (this.isDevelopmentEnvironment()) {
            this.magicKey = null; // No key needed in development
            console.log('Development environment detected - magic key not required');
            return;
        }
        
        // Check localStorage for existing valid key (production only)
        const storedKeyData = localStorage.getItem('ai_buddy_magic_key');
        if (storedKeyData) {
            try {
                const keyData = JSON.parse(storedKeyData);
                const now = new Date().getTime();
                
                // Check if key is still valid (not expired)
                if (keyData.expiry && now < keyData.expiry) {
                    this.magicKey = keyData.key;
                    console.log('Valid magic key loaded from storage');
                    return;
                } else {
                    // Key expired, remove it
                    localStorage.removeItem('ai_buddy_magic_key');
                    console.log('Stored magic key expired and removed');
                }
            } catch (e) {
                // Invalid stored data, remove it
                localStorage.removeItem('ai_buddy_magic_key');
                console.log('Invalid stored magic key data removed');
            }
        }
        
        // If no valid key found, will prompt user when they try to chat (production only)
        this.magicKey = null;
    }

    storeMagicKey(key) {
        // Store key with 10-day expiration
        const expiryTime = new Date().getTime() + (10 * 24 * 60 * 60 * 1000); // 10 days
        const keyData = {
            key: key,
            expiry: expiryTime
        };
        
        localStorage.setItem('ai_buddy_magic_key', JSON.stringify(keyData));
        this.magicKey = key;
        console.log('Magic key stored successfully');
    }

    async promptForMagicKey() {
        return new Promise((resolve) => {
            // Create modal overlay
            const overlay = document.createElement('div');
            overlay.className = 'magic-key-overlay';

            // Create modal
            const modal = document.createElement('div');
            modal.className = 'magic-key-modal';

            modal.innerHTML = `
                <h2>Early Access Key Required</h2>
                <p>This AI chat feature is currently in early testing. Please enter your magic key to continue.</p>
                <input type="text" id="magic-key-input" placeholder="Enter your magic key">
                <div class="button-container">
                    <button id="magic-key-cancel" class="cancel-btn">Cancel</button>
                    <button id="magic-key-submit" class="submit-btn">Continue</button>
                </div>
            `;

            overlay.appendChild(modal);
            document.body.appendChild(overlay);

            const input = modal.querySelector('#magic-key-input');
            const submitBtn = modal.querySelector('#magic-key-submit');
            const cancelBtn = modal.querySelector('#magic-key-cancel');

            // Focus the input
            input.focus();

            const cleanup = () => {
                document.body.removeChild(overlay);
            };

            // Handle submit
            const handleSubmit = () => {
                const key = input.value.trim();
                if (key) {
                    this.storeMagicKey(key);
                    cleanup();
                    resolve(key);
                } else {
                    input.focus();
                    input.classList.add('error');
                    setTimeout(() => {
                        input.classList.remove('error');
                    }, 2000);
                }
            };

            // Handle cancel
            const handleCancel = () => {
                cleanup();
                resolve(null);
            };

            // Event listeners
            submitBtn.addEventListener('click', handleSubmit);
            cancelBtn.addEventListener('click', handleCancel);
            
            input.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    handleSubmit();
                } else if (e.key === 'Escape') {
                    e.preventDefault();
                    handleCancel();
                }
            });

            // Close on overlay click
            overlay.addEventListener('click', (e) => {
                if (e.target === overlay) {
                    handleCancel();
                }
            });
        });
    }

    async ensureMagicKey() {
        // Skip magic key requirement in development environment
        if (this.isDevelopmentEnvironment()) {
            return 'dev-bypass';
        }
        
        if (!this.magicKey) {
            const key = await this.promptForMagicKey();
            if (!key) {
                throw new Error('Magic key required to use AI chat');
            }
        }
        return this.magicKey;
    }

    async sendMessage(question) {
        this.isStreaming = true;
        const submitBtn = document.querySelector('.send-btn');
        submitBtn.disabled = true;

        // Add loading message
        const assistantMessageContent = this.addMessage('assistant', '', true);

        try {
            // Ensure magic key is available
            await this.ensureMagicKey();
            
            const response = await fetch(`${this.apiBaseUrl}/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: question,
                    history: this.conversationHistory,
                    filters: this.aiOptions,
                    magic_key: this.magicKey
                })
            });
            
            if (!response.ok) {
                // Handle magic key validation errors specifically
                if (response.status === 401 || response.status === 403) {
                    const errorData = await response.json().catch(() => ({ detail: 'Magic key validation failed' }));
                    
                    // Remove invalid key from storage
                    localStorage.removeItem('ai_buddy_magic_key');
                    this.magicKey = null;
                    
                    // Show error and prompt for new key
                    assistantMessageContent.innerHTML = `
                        <div class="error-message">
                            <p>🔑 ${errorData.detail}</p>
                            <p>Please try again with a valid magic key.</p>
                        </div>
                    `;
                    return;
                }
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            // Add to conversation history
            this.conversationHistory.push({ role: 'user', content: question });
            
            // Handle streaming response
            await this.handleStreamingResponse(response, assistantMessageContent);

            // Update conversation history
            this.conversationHistory.push(
                { role: 'user', content: question },
                { role: 'assistant', content: assistantMessageContent.textContent }
            );

            // Generate follow-up suggestions
            this.generateFollowUpSuggestions(assistantMessageContent.textContent);
            
            /*if (response.headers.get('content-type')?.includes('text/plain')) {
                await this.handleStreamingResponse(response, assistantMessageContent);
            } else {
                // Handle non-streaming response
                const data = await response.json();
                const content = data.response || data.content || 'Sorry, I received an empty response.';
                assistantMessageContent.innerHTML = this.sanitizeAndRenderMarkdown(content);
                
                // Add to conversation history
                this.conversationHistory.push({ role: 'assistant', content: content });
            }*/
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
                    }
                } catch (parseError) {
                    console.warn('Failed to parse remaining buffer:', buffer, parseError);
                }
            }

            // Add final response to conversation history
            if (fullContent) {
                this.conversationHistory.push({ role: 'assistant', content: fullContent });
                
                // Track chat response received
                this.trackTelemetry('chat_response_received', {
                    response_length: fullContent.length,
                    conversation_length: this.conversationHistory.length,
                    has_links: /\[.*?\]\(https?:\/\/.*?\)/.test(fullContent) || /\[.*?\]\(www\..*?\)/.test(fullContent),
                    session_chat_count: this.getSessionChatCount()
                });
                
                // Add click tracking to all links in the response
                this.addLinkClickTracking(contentElement);
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

    addLinkClickTracking(contentElement) {
        // Add click tracking to all links in the chat response
        const links = contentElement.querySelectorAll('a[href]');
        links.forEach((link, index) => {
            link.addEventListener('click', () => {
                this.trackTelemetry('chat_link_clicked', {
                    url: link.href,
                    link_text: link.textContent.trim(),
                    link_index: index,
                    conversation_length: this.conversationHistory.length,
                    session_chat_count: this.getSessionChatCount()
                });
            });
        });
        
        // Track if user interacts with the response (clicks, selects text, etc.)
        let hasInteracted = false;
        const trackInteraction = () => {
            if (!hasInteracted) {
                hasInteracted = true;
                this.trackTelemetry('chat_response_interacted', {
                    conversation_length: this.conversationHistory.length,
                    session_chat_count: this.getSessionChatCount()
                });
            }
        };
        
        contentElement.addEventListener('click', trackInteraction);
        contentElement.addEventListener('mouseup', trackInteraction); // For text selection
        
        // Track if user does not interact with response after a timeout
        setTimeout(() => {
            if (!hasInteracted) {
                this.trackTelemetry('chat_response_not_interacted', {
                    conversation_length: this.conversationHistory.length,
                    session_chat_count: this.getSessionChatCount()
                });
            }
        }, 30000); // 30 second timeout
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

        // Focus input
        this.questionInput.focus();
    }
    
    scrollToBottom() {
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }
}

class NewsApp {
    constructor(apiBaseUrl, trackTelemetry) {
        this.apiBaseUrl = apiBaseUrl;
        this.newsCurrentPage = 1;
        this.newsSearchQuery = '';
        this.newsPageSize = 20;
        this.newsInitialized = false;
        this.trackTelemetry = trackTelemetry;
        
        // DOM elements (will be set during initialization)
        this.newsSearchInput = null;
        this.newsClearSearchBtn = null;
        this.newsSearchBtn = null;
        this.newsLoading = null;
        this.newsFeed = null;
        this.newsNoResults = null;
        this.newsPagination = null;
        this.newsSearchTimeout = null;
    }

    initialize() {
        if (this.newsInitialized) return;
        
        // Get DOM elements
        this.newsSearchInput = document.getElementById('news-search');
        this.newsClearSearchBtn = document.getElementById('news-clear-search-btn');
        this.newsSearchBtn = document.getElementById('news-search-btn');
        this.newsLoading = document.getElementById('news-loading');
        this.newsFeed = document.getElementById('news-feed');
        this.newsNoResults = document.getElementById('news-no-results');
        this.newsPagination = document.getElementById('news-pagination');
        
        // Setup event listeners
        this.newsSearchInput.addEventListener('input', () => {
            this.debounceNewsSearch();
        });
        
        this.newsClearSearchBtn.addEventListener('click', () => {
            this.clearNewsSearch();
        });
        
        this.newsSearchBtn.addEventListener('click', () => {
            this.performNewsSearch();
        });
        
        // Load initial news
        this.loadNews();
        this.newsInitialized = true;
    }

    debounceNewsSearch() {
        clearTimeout(this.newsSearchTimeout);
        this.newsSearchTimeout = setTimeout(() => {
            this.performNewsSearch();
        }, 500);
        
        // Show/hide clear button
        if (this.newsSearchInput.value.trim()) {
            this.newsClearSearchBtn.style.display = 'block';
        } else {
            this.newsClearSearchBtn.style.display = 'none';
        }
    }

    performNewsSearch() {
        this.newsSearchQuery = this.newsSearchInput.value.trim();
        this.newsCurrentPage = 1;
        this.loadNews();
    }

    clearNewsSearch() {
        this.newsSearchInput.value = '';
        this.newsClearSearchBtn.style.display = 'none';
        this.newsSearchQuery = '';
        this.newsCurrentPage = 1;
        this.loadNews();
    }

    async loadNews() {
        try {
            this.showNewsLoading();
            
            // Build query parameters
            const params = new URLSearchParams({
                page: this.newsCurrentPage.toString(),
                page_size: this.newsPageSize.toString()
            });
            
            if (this.newsSearchQuery) {
                params.append('search', this.newsSearchQuery);
            }
            
            const response = await fetch(`${this.apiBaseUrl}/news?${params}`);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            this.renderNews(data);
            this.renderNewsPagination(data);
            
        } catch (error) {
            console.error('Error loading news:', error);
            this.showNewsError();
        } finally {
            this.hideNewsLoading();
        }
    }

    showNewsLoading() {
        this.newsLoading.style.display = 'flex';
        this.newsFeed.style.display = 'none';
        this.newsNoResults.style.display = 'none';
        this.newsPagination.style.display = 'none';
    }

    hideNewsLoading() {
        this.newsLoading.style.display = 'none';
    }

    showNewsError() {
        this.newsFeed.innerHTML = `
            <div class="error-message">
                <h3>Unable to load news</h3>
                <p>Please try again later.</p>
            </div>
        `;
        this.newsFeed.style.display = 'block';
    }

    renderNews(data) {
        if (!data.news || data.news.length === 0) {
            this.newsFeed.style.display = 'none';
            this.newsNoResults.style.display = 'block';
          
            // Track no results for news search
            if (this.newsSearchQuery) {
                this.trackTelemetry('news_search_no_results', {
                    search_query: this.newsSearchQuery,
                    current_page: this.newsCurrentPage
                });
            }
            return;
        }

        this.newsFeed.innerHTML = '';
        this.newsFeed.style.display = 'flex';
        this.newsNoResults.style.display = 'none';

        data.news.forEach(item => {
            const newsCard = this.createNewsCard(item);
          
            // Track successful news search results
            if (this.newsSearchQuery && data.news.length > 0) {
                this.trackTelemetry('news_search_results_found', {
                    search_query: this.newsSearchQuery,
                    results_count: data.news.length,
                    current_page: this.newsCurrentPage
                });
            }
            this.newsFeed.appendChild(newsCard);
        });
    }

    createNewsCard(item) {
        const card = document.createElement('div');
        card.className = 'news-item';
        card.setAttribute('tabindex', '0');
        card.setAttribute('role', 'button');
        card.setAttribute('aria-label', `Read news article: ${this.escapeHtml(item.title)}`);

        const publishedDate = this.formatDate(item.published_date);
        
        card.innerHTML = `
            <div class="news-item-header">
                <div class="news-item-title">
                    <h3>${this.escapeHtml(item.title)}</h3>
                </div>
                <div class="news-item-meta">
                    <span class="news-item-source">${this.escapeHtml(item.source)}</span>
                    <span class="news-item-date">${publishedDate}</span>
                    ${item.author ? `<span class="news-item-author">by ${this.escapeHtml(item.author)}</span>` : ''}
                </div>
            </div>
            <div class="news-item-summary">${this.escapeHtml(item.summary)}</div>
        `;

        card.addEventListener('click', () => {
            window.open(item.url, '_blank', 'noopener,noreferrer');
            this.trackTelemetry('news_item_clicked', {
                    url: item.url,
                    title: item.title,
                    source: item.source,
                    search_query: this.newsSearchQuery || null,
                    current_page: this.newsCurrentPage
                });
        });

        return card;
    }

    renderNewsPagination(data) {
        if (data.pages <= 1) {
            this.newsPagination.style.display = 'none';
            return;
        }

        this.newsPagination.innerHTML = '';
        this.newsPagination.style.display = 'flex';
        
        // Previous button
        const prevBtn = document.createElement('button');
        prevBtn.className = 'pagination-btn';
        prevBtn.textContent = '« Previous';
        prevBtn.disabled = data.page === 1;
        prevBtn.addEventListener('click', () => {
            if (data.page > 1) {
                this.newsCurrentPage = data.page - 1;
                this.loadNews();
            }
        });
        this.newsPagination.appendChild(prevBtn);
        
        // Page numbers (show max 5 pages)
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
                this.newsCurrentPage = i;
                this.loadNews();
            });
            
            this.newsPagination.appendChild(pageBtn);
        }
        
        // Info
        const info = document.createElement('div');
        info.className = 'pagination-info';
        info.textContent = `${data.page} of ${data.pages} (${data.total} articles)`;
        this.newsPagination.appendChild(info);
        
        // Next button
        const nextBtn = document.createElement('button');
        nextBtn.className = 'pagination-btn';
        nextBtn.textContent = 'Next »';
        nextBtn.disabled = data.page === data.pages;
        nextBtn.addEventListener('click', () => {
            if (data.page < data.pages) {
                this.newsCurrentPage = data.page + 1;
                this.loadNews();
            }
        });
        this.newsPagination.appendChild(nextBtn);
    }

    formatDate(dateString) {
        try {
            const date = new Date(dateString);
            return date.toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'short',
                day: 'numeric'
            });
        } catch (error) {
            return dateString;
        }
    }

    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

class SamplesGallery {

    constructor(apiBaseUrl = null, trackTelemetry) {
        this.trackTelemetry = trackTelemetry;
        this.apiBaseUrl = apiBaseUrl;
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
            this.chatApp.trackTelemetry('search_no_results', { 
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
             
        card.innerHTML = `
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
        this.modalSampleDetails.innerHTML = `
            <div class="sample-detail-header">
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
                const linkType = link.href.includes(sample.authorUrl) ? 'author' : 'source';
                
                // Mark that source links were viewed for this sample
                if (linkType === 'source') {
                    sample._viewedSourceLinks = true;
                }
                
                this.trackTelemetry('external_click', { 
                    url: link.href, 
                    sample_id: sample.id,
                    link_type: linkType
                });
            });
        });
    }

    closeSampleModal() {
        // Track modal close behavior
        if (this.currentSample) {
            this.trackTelemetry('sample_modal_closed', { 
                sample_id: this.currentSample.id,
                title: this.currentSample.title,
                viewed_source_links: this.currentSample._viewedSourceLinks || false
            });
        }
        
        this.sampleModal.style.display = 'none';
        this.sampleModal.setAttribute('aria-inert', 'true');
        this.currentSample = null;
    }
}

class AppManager {
    constructor() {
        this.apiBaseUrl = this.detectApiUrl();
        this.chatApp = new ChatApp(this.apiBaseUrl, this.trackTelemetry);
        this.samplesGallery = new SamplesGallery(this.apiBaseUrl, this.trackTelemetry);
        this.newsApp = new NewsApp(this.apiBaseUrl, this.trackTelemetry);
        this.currentTab = 'chat';
        
        this.initializeSidebarState();
        this.initializeNavigation();
        this.initializePrivacyNotice();
        this.initializeUrlHandling();
        this.initializeThemeToggle();
    }

    detectApiUrl() {
        var apiUrl = 'https://csharp-ai-buddy-api.onrender.com/';

        // Check if we're running in development (localhost)
        if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' || window.location.protocol === 'file:') {
            apiUrl = 'http://localhost:8000';
        }

        // Check for environment variable or meta tag with API URL
        const apiUrlMeta = document.querySelector('meta[name="api-url"]');
        if (apiUrlMeta && apiUrlMeta.content.trim() != '') {
            apiUrl = apiUrlMeta.content;
        }

        // Default to production API URL
        return apiUrl + "/api";
    }

    trackTelemetry(eventType, data) {
        // Check if telemetry is enabled
        const telemetryEnabled = localStorage.getItem('telemetry_enabled') !== 'false';
        
        if (!telemetryEnabled) {
            return;
        }
        
        // Only log telemetry in development environment
        if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' || window.location.protocol === 'file:') {
            console.log('Telemetry:', eventType, data);
        }
        
        // Send event to Goat Counter if available
        if (window.goatcounter && window.goatcounter.count) {
            try {
                // Construct a meaningful path for Goat Counter
                const eventPath = `/analytics/${eventType}`;
                const title = `${eventType}: ${JSON.stringify(data)}`;
                
                window.goatcounter.count({
                    path: eventPath,
                    title: title,
                    event: true
                });
            } catch (error) {
                console.error('Error sending analytics event:', error);
            }
        }
        
        // Also send to backend telemetry endpoint if available
        this.sendBackendTelemetry(eventType, data);
    }

    async sendBackendTelemetry(eventType, data) {
        try {
            const response = await fetch(`${this.apiBaseUrl}/telemetry`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    event_type: eventType,
                    data: data,
                    user_consent: localStorage.getItem('telemetry_enabled') !== 'false',
                    timestamp: new Date().toISOString()
                })
            });
            
            if (!response.ok) {
                console.warn('Backend telemetry request failed:', response.status);
            }
        } catch (error) {
            // Silently fail - telemetry should not break the user experience
            console.debug('Backend telemetry not available:', error.message);
        }
    }

    initializeNavigation() {
        const chatTab = document.getElementById('chat-tab');
        const samplesTab = document.getElementById('samples-tab');
        const newsTab = document.getElementById('news-tab');
        const sidebarToggle = document.getElementById('sidebar-toggle');
        const sidebar = document.getElementById('sidebar');

        // Tab navigation
        chatTab.addEventListener('click', () => {
            this.switchTab('chat');
        });

        samplesTab.addEventListener('click', () => {
            this.switchTab('samples');
        });

        newsTab.addEventListener('click', () => {
            this.switchTab('news');
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
            [chatTab, samplesTab, newsTab].forEach(tab => {
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

    switchTab(tab) {
        const chatTab = document.getElementById('chat-tab');
        const samplesTab = document.getElementById('samples-tab');
        const newsTab = document.getElementById('news-tab');
        const chatSection = document.getElementById('chat-section');
        const samplesSection = document.getElementById('samples-section');
        const newsSection = document.getElementById('news-section');

        // Update tab states
        chatTab.classList.toggle('active', tab === 'chat');
        samplesTab.classList.toggle('active', tab === 'samples');
        newsTab.classList.toggle('active', tab === 'news');

        // Update section visibility
        chatSection.style.display = tab === 'chat' ? 'flex' : 'none';
        samplesSection.style.display = tab === 'samples' ? 'flex' : 'none';
        newsSection.style.display = tab === 'news' ? 'flex' : 'none';

        this.currentTab = tab;
        
        // Initialize news if switching to news tab
        if (tab === 'news' && !this.newsApp.newsInitialized) {
            this.newsApp.initialize();
        }
        
        // Update URL for deep linking
        const url = new URL(window.location);
        if (tab === 'samples') {
            this.trackTelemetry('samples_section_viewed', {
                previous_tab: this.currentTab || 'chat'
            });
            url.searchParams.set('tab', 'samples');
        } else if (tab === 'news') {
            this.trackTelemetry('news_section_viewed', {
                previous_tab: this.currentTab || 'chat'
            });
            url.searchParams.set('tab', 'news');
        } else {
            this.trackTelemetry('chat_section_viewed', {
                previous_tab: this.currentTab || 'chat'
            });
            url.searchParams.delete('tab');
        }
        window.history.replaceState({}, '', url);
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
        } else if (initialTab === 'news') {
            this.switchTab('news');
        }
        
        // Handle back/forward navigation
        window.addEventListener('popstate', () => {
            const urlParams = new URLSearchParams(window.location.search);
            const tab = urlParams.get('tab') || 'chat';
            this.switchTab(tab);
        });
    }

    initializeThemeToggle() {
        this.themeToggle = document.getElementById('theme-toggle');
        this.sunIcon = this.themeToggle.querySelector('.sun-icon');
        this.moonIcon = this.themeToggle.querySelector('.moon-icon');
        
        // Set initial theme based on system preference or saved preference
        this.setInitialTheme();
        
        // Add click event listener for manual toggle
        this.themeToggle.addEventListener('click', () => {
            this.toggleTheme();
        });
        
        // Listen for system theme changes
        const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
        mediaQuery.addEventListener('change', (e) => {
            // Only update if user hasn't manually set a theme
            if (!localStorage.getItem('theme_preference')) {
                this.applyTheme(e.matches ? 'dark' : 'light');
            }
        });
    }

    setInitialTheme() {
        const savedTheme = localStorage.getItem('theme_preference');
        
        if (savedTheme) {
            // User has manually set a theme preference
            this.applyTheme(savedTheme);
        } else {
            // Use system preference
            const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
            this.applyTheme(systemPrefersDark ? 'dark' : 'light');
        }
    }

    toggleTheme() {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        
        // Save user preference
        localStorage.setItem('theme_preference', newTheme);
        
        // Apply the new theme
        this.applyTheme(newTheme);
        
        // Update tooltip
        this.updateThemeTooltip(newTheme);
    }

    applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        const hljsTheme = document.getElementById('hljs-theme');
        
        // Update icon visibility
        if (theme === 'dark') {
            this.sunIcon.style.display = 'none';
            this.moonIcon.style.display = 'block';
            hljsTheme.href = 'https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github-dark.min.css';
        } else {
            this.sunIcon.style.display = 'block';
            this.moonIcon.style.display = 'none';
            hljsTheme.href = 'https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github.min.css';
        }
        
        // Update tooltip
        this.updateThemeTooltip(theme);
        
        // Add transition class for smooth transitions
        document.body.classList.add('theme-transitioning');
        setTimeout(() => {
            document.body.classList.remove('theme-transitioning');
        }, 300);
    }

    updateThemeTooltip(currentTheme) {
        const nextTheme = currentTheme === 'dark' ? 'light' : 'dark';
        const tooltipText = `Switch to ${nextTheme} theme`;
        this.themeToggle.setAttribute('title', tooltipText);
        this.themeToggle.setAttribute('aria-label', tooltipText);
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