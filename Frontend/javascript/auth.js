// auth.js - Manejo de autenticación
class AuthManager {
    constructor() {
        this.baseURL = 'http://localhost:8000/api';
        this.token = localStorage.getItem('authToken');
        this.user = JSON.parse(localStorage.getItem('user') || 'null');
        this.init();
    }

    init() {
        // Verificar si estamos en una página que requiere autenticación
        const currentPage = window.location.pathname;
        const isAuthPage = currentPage.includes('login.html') || currentPage.includes('register.html');
        const isIndexPage = currentPage.includes('index.html') || currentPage === '/';

        if (isIndexPage && !this.isAuthenticated()) {
            this.redirectToLogin();
        } else if (isAuthPage && this.isAuthenticated()) {
            this.redirectToDashboard();
        }

        this.bindEvents();
    }

    bindEvents() {
        // Login form
        const loginForm = document.getElementById('loginForm');
        if (loginForm) {
            loginForm.addEventListener('submit', (e) => this.handleLogin(e));
        }

        // Register form
        const registerForm = document.getElementById('registerForm');
        if (registerForm) {
            registerForm.addEventListener('submit', (e) => this.handleRegister(e));
        }

        // Logout button
        const logoutBtn = document.getElementById('logoutBtn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', () => this.logout());
        }

        // Auto-fill invitation code from URL
        this.fillInvitationCode();
    }

    fillInvitationCode() {
        const urlParams = new URLSearchParams(window.location.search);
        const invitationCode = urlParams.get('code');
        const invitationInput = document.getElementById('invitationCode');
        
        if (invitationCode && invitationInput) {
            invitationInput.value = invitationCode;
            invitationInput.readOnly = true;
        }
    }

    async handleLogin(e) {
        e.preventDefault();
        
        const submitBtn = document.getElementById('loginBtn');
        const errorDiv = document.getElementById('errorMessage');
        
        try {
            this.setLoading(submitBtn, true);
            this.hideError(errorDiv);

            const formData = new FormData(e.target);
            const loginData = {
                email: formData.get('email'),
                password: formData.get('password')
            };

            const response = await fetch(`${this.baseURL}/auth/login/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(loginData)
            });

            const data = await response.json();

            if (response.ok) {
                this.setAuthData(data.access, data.user);
                this.redirectToDashboard();
            } else {
                this.showError(errorDiv, data.detail || 'Error al iniciar sesión');
            }
        } catch (error) {
            console.error('Login error:', error);
            this.showError(errorDiv, 'Error de conexión. Intenta nuevamente.');
        } finally {
            this.setLoading(submitBtn, false);
        }
    }

    async handleRegister(e) {
        e.preventDefault();
        
        const submitBtn = document.getElementById('registerBtn');
        const errorDiv = document.getElementById('errorMessage');
        
        try {
            this.setLoading(submitBtn, true);
            this.hideError(errorDiv);

            const formData = new FormData(e.target);
            
            // Validar contraseñas
            const password = formData.get('password');
            const confirmPassword = formData.get('confirmPassword');
            
            if (password !== confirmPassword) {
                this.showError(errorDiv, 'Las contraseñas no coinciden');
                return;
            }

            const registerData = {
                invitation_code: formData.get('invitationCode'),
                first_name: formData.get('firstName'),
                last_name: formData.get('lastName'),
                email: formData.get('email'),
                password: password,
                bio: formData.get('bio')
            };

            // Manejar archivo de avatar si existe
            const avatarFile = formData.get('avatar');
            if (avatarFile && avatarFile.size > 0) {
                registerData.avatar = await this.fileToBase64(avatarFile);
            }

            const response = await fetch(`${this.baseURL}/auth/register/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(registerData)
            });

            const data = await response.json();

            if (response.ok) {
                this.setAuthData(data.access, data.user);
                this.redirectToDashboard();
            } else {
                let errorMessage = 'Error al registrarse';
                if (data.detail) {
                    errorMessage = data.detail;
                } else if (data.errors) {
                    errorMessage = Object.values(data.errors).flat().join(', ');
                }
                this.showError(errorDiv, errorMessage);
            }
        } catch (error) {
            console.error('Register error:', error);
            this.showError(errorDiv, 'Error de conexión. Intenta nuevamente.');
        } finally {
            this.setLoading(submitBtn, false);
        }
    }

    fileToBase64(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.readAsDataURL(file);
            reader.onload = () => resolve(reader.result);
            reader.onerror = error => reject(error);
        });
    }

    setAuthData(token, user) {
        this.token = token;
        this.user = user;
        localStorage.setItem('authToken', token);
        localStorage.setItem('user', JSON.stringify(user));
    }

    logout() {
        this.token = null;
        this.user = null;
        localStorage.removeItem('authToken');
        localStorage.removeItem('user');
        this.redirectToLogin();
    }

    isAuthenticated() {
        return !!this.token;
    }

    getAuthHeaders() {
        return {
            'Authorization': `Bearer ${this.token}`,
            'Content-Type': 'application/json'
        };
    }

    async makeAuthenticatedRequest(url, options = {}) {
        if (!this.isAuthenticated()) {
            this.redirectToLogin();
            return;
        }

        const response = await fetch(url, {
            ...options,
            headers: {
                ...this.getAuthHeaders(),
                ...options.headers
            }
        });

        if (response.status === 401) {
            this.logout();
            return;
        }

        return response;
    }

    redirectToLogin() {
        window.location.href = 'login.html';
    }

    redirectToDashboard() {
        window.location.href = 'index.html';
    }

    setLoading(button, isLoading) {
        if (isLoading) {
            button.disabled = true;
            button.textContent = 'Cargando...';
        } else {
            button.disabled = false;
            button.textContent = button.id === 'loginBtn' ? 'Iniciar Sesión' : 'Registrarse';
        }
    }

    showError(errorDiv, message) {
        errorDiv.textContent = message;
        errorDiv.classList.add('show');
    }

    hideError(errorDiv) {
        errorDiv.classList.remove('show');
    }

    getCurrentUser() {
        return this.user;
    }

    updateUserStats(stats) {
        if (this.user) {
            this.user = { ...this.user, ...stats };
            localStorage.setItem('user', JSON.stringify(this.user));
        }
    }
}

// Instancia global del manejador de autenticación
const authManager = new AuthManager();