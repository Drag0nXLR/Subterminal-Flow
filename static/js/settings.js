async function updateProfile() {
    const username = document.getElementById('username').value;
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    
    const data = {};
    if (username) data.username = username;
    if (email) data.email = email;
    if (password) data.password = password;
    
    if (Object.keys(data).length === 0) {
        alert('Please fill at least one field');
        return;
    }
    
    const res = await fetch('/user/', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
    
    if (res.ok) {
        alert('Profile updated successfully!');
        location.reload();
    } else {
        alert('Failed to update profile');
    }
}