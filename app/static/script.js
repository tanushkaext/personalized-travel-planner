// Central helper for API requests
async function apiCall(endpoint, method = 'GET', body = null) {
  const token = localStorage.getItem('token');
  const headers = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const options = { method, headers };
  if (body) options.body = JSON.stringify(body);

  const res = await fetch(`/api${endpoint}`, options);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.message || 'Request failed');
  return data;
}

// Authentication Handlers
async function handleLogin(e) {
  e.preventDefault();
  const email = document.getElementById('loginEmail').value.trim();
  const password = document.getElementById('loginPassword').value.trim();

  try {
    const res = await apiCall('/auth/login', 'POST', { email, password });
    // Cookie is automatically set by Flask in response headers!
    window.location.href = '/my-trips';
  } catch (err) {
    alert(err.message || 'Invalid login');
  }
}

async function handleSignup(e) {
  e.preventDefault();
  const name = document.getElementById('regName').value.trim();
  const email = document.getElementById('regEmail').value.trim();
  const password = document.getElementById('regPassword').value.trim();

  try {
    const res = await apiCall('/auth/register', 'POST', { name, email, password });
    // Cookie is automatically set by Flask in response headers!
    window.location.href = '/my-trips';
  } catch (err) {
    alert(err.message || 'Registration failed');
  }
}

// Update navbar if user is logged in
document.addEventListener('DOMContentLoaded', () => {
  const token = localStorage.getItem('token');
  const userStr = localStorage.getItem('user');
  const authContainer = document.getElementById('navAuthSection');

  if (token && userStr && authContainer) {
    const user = JSON.parse(userStr);
    authContainer.innerHTML = `
      <span class="small fw-semibold text-secondary me-2"><i class="bi bi-person-circle"></i> ${user.name}</span>
      <button class="btn btn-outline-danger btn-sm" onclick="logout()">Logout</button>
    `;
  }
});

function logout() {
  localStorage.removeItem('token');
  localStorage.removeItem('user');
  window.location.href = '/';
}

