async function loadTags() {
    const res = await fetch('/api/tags');
    const data = await res.json();
    
    const grid = document.getElementById('tags-grid');
    grid.innerHTML = data.tags.map(tag => `
        <a href="/?tag=${tag}" class="tag-card">
            <div class="tag-name">${tag}</div>
            <div class="tag-count">0 questions</div>
        </a>
    `).join('');
}

// Оновлення сайдбару на сторінці тегів
document.addEventListener('DOMContentLoaded', function() {
    const sidebarLinks = document.querySelectorAll('.sidebar-link');
    sidebarLinks.forEach(link => {
        link.classList.remove('active');
        if (link.textContent.includes('Tags')) {
            link.classList.add('active');
        }
    });
});

loadTags();