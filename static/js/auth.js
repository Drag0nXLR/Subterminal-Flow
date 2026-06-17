// Login
async function handleLogin(event) {
    event.preventDefault();
    
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    
    try {
        const response = await fetch('/login/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        
        if (response.ok) {
            window.location.href = '/';
        } else {
            const error = await response.json();
            showError(error.detail || 'Login failed');
        }
    } catch (error) {
        showError('Network error. Please try again.');
    }
}

// Register
async function handleRegister(event) {
    event.preventDefault();
    
    const username = document.getElementById('username').value;
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    const confirmPassword = document.getElementById('confirm-password').value;
    
    if (password !== confirmPassword) {
        showError('Passwords do not match');
        return;
    }
    
    try {
        const response = await fetch('/register/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, email, password })
        });
        
        if (response.ok) {
            window.location.href = '/';
        } else {
            const error = await response.json();
            showError(error.detail || 'Registration failed');
        }
    } catch (error) {
        showError('Network error. Please try again.');
    }
}

function showError(message) {
    // Створюємо або знаходимо елемент помилки
    let errorEl = document.querySelector('.error-message');
    if (!errorEl) {
        errorEl = document.createElement('div');
        errorEl.className = 'error-message';
        document.querySelector('form').insertBefore(errorEl, document.querySelector('form').firstChild);
    }
    
    errorEl.textContent = message;
    errorEl.classList.add('show');
    
    // Прибираємо помилку через 5 секунд
    setTimeout(() => {
        errorEl.classList.remove('show');
    }, 5000);
}