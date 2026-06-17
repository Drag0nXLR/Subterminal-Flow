// Global Variables
let categories = {};
let currentCategory = 'all';
let selectedTags = [];
const availableTags = ['python', 'javascript', 'typescript', 'react', 'vue', 'angular', 'node.js', 'express', 'django', 'fastapi', 'flask', 'sql', 'postgresql', 'mongodb', 'mysql', 'api', 'rest', 'graphql', 'docker', 'kubernetes', 'aws', 'azure', 'git', 'linux', 'machine-learning', 'ai', 'deep-learning', 'tensorflow', 'pytorch', 'algorithms', 'data-structures', 'web', 'frontend', 'backend', 'fullstack', 'devops', 'testing', 'debugging', 'html', 'css', 'scss', 'sass', 'webpack', 'npm', 'yarn'];

let currentUser = null;

async function loadCurrentUser() {
    try {
        const response = await fetch('/api/me');
        if (response.ok) {
            currentUser = await response.json();
            updateSidebarUI();
        }
    } catch (error) {
        currentUser = null;
        updateSidebarUI();
    }
}

function updateSidebarUI() {
    const userInfo = document.getElementById('user-info');
    const authButtons = document.getElementById('auth-buttons');
    const logoutButtons = document.getElementById('logout-button');
    
    if (currentUser) {
        userInfo.style.display = 'flex';
        document.getElementById('user-name').textContent = currentUser.username;
        document.getElementById('user-initial').textContent = currentUser.username.charAt(0).toUpperCase();
        document.getElementById('user-reputation').textContent = currentUser.reputation || 1;
        
        authButtons.style.display = 'none';
        logoutButtons.style.display = 'flex';
    } else {
        userInfo.style.display = 'none';
        authButtons.style.display = 'flex';
        logoutButtons.style.display = 'none';
    }
}

function updateSidebarActive(page) {
    const sidebarLinks = document.querySelectorAll('.sidebar-link');
    
    sidebarLinks.forEach(link => {
        link.classList.remove('active');
        if (link.dataset.page === page) {
            link.classList.add('active');
        }
    });
}

// Initialize
async function loadCategories() {
    const res = await fetch('/categories');
    categories = await res.json();
    renderCategoryFilter();
    
    updateSidebarActive('all');
}

function renderCategoryFilter() {
    const container = document.getElementById('category-filter');
    let html = `<span class="category-badge ${currentCategory === 'all' ? 'active' : ''}" onclick="filterCategory('all')">All</span>`;
    
    for (const [key, value] of Object.entries(categories)) {
        html += `<span class="category-badge ${currentCategory === key ? 'active' : ''}" onclick="filterCategory('${key}')">${value}</span>`;
    }
    
    container.innerHTML = html;
}

function filterCategory(category) {
    currentCategory = category;
    renderCategoryFilter();
    loadQuestions();
    
    updateSidebarActive('all');
}

// Navigation
function showFeedView() {
    document.getElementById('feed-view').classList.remove('hidden');
    document.getElementById('create-view').classList.add('hidden');
    document.getElementById('question-view').classList.add('hidden');
    
    document.querySelectorAll('.nav-link').forEach(link => link.classList.remove('active'));
    document.querySelector('.nav-link').classList.add('active');
    
    loadQuestions();
    
    updateSidebarActive('all');
}

function showCreateView() {
    document.getElementById('feed-view').classList.add('hidden');
    document.getElementById('create-view').classList.remove('hidden');
    document.getElementById('question-view').classList.add('hidden');
    
    // Очищення форми
    document.getElementById('new-title').value = '';
    document.getElementById('new-body').value = '';
    document.getElementById('new-category').value = 'general';
    
    // Скидання тегів
    selectedTags = [];
    renderTags();
    document.getElementById('tags-input').value = '';
    hideTagSuggestions();
    
    // Закриття області завантаження зображень
    closeImageUpload();
    
    // Скидання редактора на вкладку "Write"
    const tabs = document.querySelectorAll('.editor-tab');
    const textarea = document.querySelector('.editor-textarea');
    const preview = document.querySelector('.editor-preview');
    
    tabs.forEach(t => t.classList.remove('active'));
    tabs[0].classList.add('active');
    preview.classList.remove('active');
    preview.innerHTML = '';
    textarea.style.display = 'block';
    
    // Оновлення сайдбару - "Ask Question" активний
    updateSidebarActive('ask');
}

function showQuestionView(id) {
    document.getElementById('feed-view').classList.add('hidden');
    document.getElementById('create-view').classList.add('hidden');
    document.getElementById('question-view').classList.remove('hidden');
    loadQuestionDetails(id);
    
    updateSidebarActive('all');
}

// Markdown Editor
function insertMarkdown(prefix, suffix) {
    const textarea = document.getElementById('new-body');
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const text = textarea.value;
    const selectedText = text.substring(start, end);
    
    const newText = text.substring(0, start) + prefix + selectedText + suffix + text.substring(end);
    textarea.value = newText;
    
    const newCursorPos = start + prefix.length + selectedText.length;
    textarea.setSelectionRange(newCursorPos, newCursorPos);
    textarea.focus();
}

function switchEditorTab(tab) {
    const tabs = document.querySelectorAll('.editor-tab');
    const textarea = document.querySelector('.editor-textarea');
    const preview = document.querySelector('.editor-preview');
    
    tabs.forEach(t => t.classList.remove('active'));
    
    if (tab === 'preview') {
        tabs[1].classList.add('active');
        const markdown = document.getElementById('new-body').value;
        preview.innerHTML = marked.parse(markdown);
        preview.classList.add('active');
        textarea.style.display = 'none';
    } else {
        tabs[0].classList.add('active');
        preview.classList.remove('active');
        textarea.style.display = 'block';
    }
}

// Image Upload
function openImageUpload() {
    document.getElementById('image-upload-area').classList.add('active');
}

function closeImageUpload() {
    document.getElementById('image-upload-area').classList.remove('active');
    document.getElementById('upload-progress').textContent = '';
    document.getElementById('upload-error').textContent = '';
}

function handleDragOver(event) {
    event.preventDefault();
    event.currentTarget.classList.add('dragover');
}

function handleDragLeave(event) {
    event.currentTarget.classList.remove('dragover');
}

function handleDrop(event) {
    event.preventDefault();
    event.currentTarget.classList.remove('dragover');
    
    const files = event.dataTransfer.files;
    if (files.length > 0) {
        uploadImage(files[0]);
    }
}

function handleFileSelect(event) {
    const files = event.target.files;
    if (files.length > 0) {
        uploadImage(files[0]);
    }
}

async function uploadImage(file) {
    const progressEl = document.getElementById('upload-progress');
    const errorEl = document.getElementById('upload-error');
    
    if (!file.type.startsWith('image/')) {
        errorEl.textContent = 'File must be an image';
        return;
    }
    
    if (file.size > 2 * 1024 * 1024) {
        errorEl.textContent = 'File must be less than 2MB';
        return;
    }
    
    progressEl.textContent = 'Uploading...';
    errorEl.textContent = '';
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const response = await fetch('/upload-image/', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (response.ok) {
            const markdown = `![${file.name}](${result.url})\n\n`;
            insertMarkdown(markdown, '');
            closeImageUpload();
        } else {
            errorEl.textContent = result.error || 'Upload failed';
        }
    } catch (error) {
        errorEl.textContent = 'Upload failed: ' + error.message;
    } finally {
        progressEl.textContent = '';
    }
}

// Tags
function handleTagInput(event) {
    if (event.key === ' ' || event.key === 'Enter' || event.key === ',') {
        event.preventDefault();
        const input = document.getElementById('tags-input');
        const tag = input.value.trim().toLowerCase();
        
        if (tag && !selectedTags.includes(tag) && selectedTags.length < 5) {
            selectedTags.push(tag);
            renderTags();
            input.value = '';
            hideTagSuggestions();
        }
    } else if (event.key === 'Backspace' && event.target.value === '' && selectedTags.length > 0) {
        selectedTags.pop();
        renderTags();
    }
}

function renderTags() {
    const container = document.getElementById('selected-tags');
    container.innerHTML = selectedTags.map(tag => `
        <span class="tag-item">
            ${tag}
            <span class="tag-remove" onclick="removeTag('${tag}')">×</span>
        </span>
    `).join('');
}

function removeTag(tag) {
    selectedTags = selectedTags.filter(t => t !== tag);
    renderTags();
}

function showTagSuggestions(event) {
    const input = event.target.value.toLowerCase();
    const suggestionsContainer = document.getElementById('tag-suggestions');
    
    if (input.length < 1) {
        hideTagSuggestions();
        return;
    }
    
    const suggestions = availableTags.filter(tag => 
        tag.includes(input) && !selectedTags.includes(tag)
    ).slice(0, 5);
    
    if (suggestions.length > 0) {
        suggestionsContainer.innerHTML = suggestions.map(tag => `
            <div class="tag-suggestion" onclick="addTag('${tag}')">${tag}</div>
        `).join('');
        suggestionsContainer.style.display = 'block';
    } else {
        hideTagSuggestions();
    }
}

function addTag(tag) {
    if (!selectedTags.includes(tag) && selectedTags.length < 5) {
        selectedTags.push(tag);
        renderTags();
        document.getElementById('tags-input').value = '';
        hideTagSuggestions();
    }
}

function hideTagSuggestions() {
    document.getElementById('tag-suggestions').style.display = 'none';
}

// API Calls
async function loadQuestions() {
    const url = currentCategory === 'all' 
        ? '/questions/' 
        : `/questions/?category=${currentCategory}`;
    
    const res = await fetch(url);
    const questions = await res.json();
    renderQuestions(questions, 'questions-list');
}

async function submitQuestion() {
    const title = document.getElementById('new-title').value;
    const body = document.getElementById('new-body').value;
    const category = document.getElementById('new-category').value;

    if (!title || !body) return alert('Please fill in title and body');
    if (title.length < 15) return alert('Title must be at least 15 characters');
    if (body.length < 20) return alert('Body must be at least 20 characters');
    if (selectedTags.length === 0) return alert('Please add at least one tag');

    await fetch('/questions/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
            title, 
            body, 
            category,
            tags: selectedTags.join(',')
        })
    });

    showFeedView();
}

function triggerSearch() {
    document.getElementById('search-input').dispatchEvent(new KeyboardEvent('keypress', {'key': 'Enter'}));
}

async function handleSearch(e) {
    if (e.key === 'Enter') {
        const query = document.getElementById('search-input').value;
        if (!query.trim()) return;
        
        const category = currentCategory === 'all' ? null : currentCategory;
        
        const res = await fetch('/search/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query, category, top_k: 20 })
        });
        const results = await res.json();
        renderQuestions(results, 'questions-list', true);
    }
}

async function loadQuestionDetails(id) {
    const res = await fetch(`/questions/${id}`);
    const q = await res.json();
    
    const categoryName = categories[q.category] || q.category;
    const date = new Date(q.created_at).toLocaleString('en-US', { 
        year: 'numeric', 
        month: 'short', 
        day: 'numeric', 
        hour: '2-digit', 
        minute: '2-digit' 
    });
    
    const tags = q.tags ? q.tags.split(',').map(t => `<span class="question-tag">${t.trim()}</span>`).join('') : '';
    
    document.getElementById('main-question-card').innerHTML = `
        <div class="question-detail">
            <span class="category-badge">${categoryName}</span>
            <h1>${q.title}</h1>
            <div class="question-meta" style="margin-bottom: 20px;">
                <span class="timestamp">Asked ${date}</span>
                ${tags}
            </div>
            <div class="markdown-body question-detail-body">
                ${marked.parse(q.body)}
            </div>
        </div>
    `;
    
    document.querySelectorAll('#main-question-card pre code').forEach((block) => {
        hljs.highlightElement(block);
    });

    const relatedRes = await fetch(`/questions/${id}/related`);
    const related = await relatedRes.json();
    
    const relatedContainer = document.getElementById('related-posts-list');
    if (related.length === 0) {
        relatedContainer.innerHTML = '<p style="color: var(--text-muted);">No related questions found.</p>';
    } else {
        relatedContainer.innerHTML = related.map(r => {
            const relatedCategory = categories[r.category] || r.category;
            const relatedDate = new Date(r.created_at).toLocaleDateString('en-US');
            const relatedTags = r.tags ? r.tags.split(',').map(t => `<span class="question-tag">${t.trim()}</span>`).join('') : '';
            
            return `
                <div class="question-item" onclick="showQuestionView(${r.id})" style="cursor: pointer;">
                    <div class="question-stats">
                        <div class="stat-box stat-answers">AI ${(r.similarity_score * 100).toFixed(0)}%</div>
                    </div>
                    <div class="question-content">
                        <h3>${r.title}</h3>
                        <div class="question-excerpt">${r.body.substring(0, 200)}...</div>
                        <div class="question-meta">
                            ${relatedTags}
                            <span class="question-time">asked ${relatedDate}</span>
                        </div>
                    </div>
                </div>
            `}).join('');
    }
}

function renderQuestions(questions, containerId, isSearch = false) {
    const container = document.getElementById(containerId);
    if (questions.length === 0) {
        container.innerHTML = `
            <div class="card" style="text-align: center; padding: 40px;">
                <h3 style="color: var(--text-muted); font-weight: 400;">No questions found</h3>
                <p style="color: var(--text-muted);">Be the first to ask a question!</p>
                <button class="btn" onclick="showCreateView()" style="margin-top: 16px;">Ask Question</button>
            </div>
        `;
        return;
    }

    container.innerHTML = questions.map(q => {
        const categoryName = categories[q.category] || q.category;
        const date = new Date(q.created_at).toLocaleDateString('en-US', { 
            year: 'numeric', 
            month: 'short', 
            day: 'numeric' 
        });
        const tags = q.tags ? q.tags.split(',').slice(0, 3).map(t => `<span class="question-tag">${t.trim()}</span>`).join('') : '';
        
        return `
            <div class="card question-item" onclick="showQuestionView(${q.id})" style="cursor: pointer; padding: 16px;">
                <div class="question-stats">
                    <div class="stat-box stat-answers">0</div>
                    <div class="stat-box stat-views">0</div>
                </div>
                <div class="question-content">
                    <h3>${q.title}</h3>
                    <div class="question-excerpt">${marked.parse(q.body.substring(0, 200)).replace(/<[^>]*>/g, '').substring(0, 200)}...</div>
                    <div class="question-meta">
                        ${tags}
                        <span class="question-time">asked ${date}</span>
                        ${isSearch && q.similarity_score ? `<span style="color: var(--success); margin-left: auto; font-size: 11px;">AI Match: ${(q.similarity_score * 100).toFixed(0)}%</span>` : ''}
                    </div>
                </div>
            </div>
        `}).join('');
    
    container.querySelectorAll('pre code').forEach((block) => {
        hljs.highlightElement(block);
    });
}

// Event Listeners
document.addEventListener('click', function(event) {
    if (!event.target.closest('.tags-input-container')) {
        hideTagSuggestions();
    }
});

// Initialize App
document.addEventListener('DOMContentLoaded', function() {
    loadCurrentUser();
    loadCategories();
    loadQuestions();
});