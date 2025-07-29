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

// Initialize the app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new ChatApp();
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