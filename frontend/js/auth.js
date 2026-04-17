// ==========================================
// AUTH SERVICE - JWT Authentication
// ==========================================

const Auth = {
    API_URL: window.API_BASE_URL || 'http://localhost:8000',
    
    /**
     * Registra novo usuário
     */
    async cadastrar(nome, email, senha) {
        try {
            const response = await fetch(`${this.API_URL}/api/auth/cadastrar`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'ngrok-skip-browser-warning': 'true'
                },
                body: JSON.stringify({ nome, email, senha })
            });
            
            const data = await response.json();
            
            if (response.ok && data.access_token) {
                this._setToken(data.access_token);
                return { sucesso: true, usuario: data.usuario };
            }
            
            return { sucesso: false, erro: data.detail || 'Erro ao cadastrar' };
        } catch (error) {
            return { sucesso: false, erro: error.message };
        }
    },

    /**
     * Login de usuário
     */
    async login(email, senha) {
        try {
            const response = await fetch(`${this.API_URL}/api/auth/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'ngrok-skip-browser-warning': 'true'
                },
                body: JSON.stringify({ email, senha })
            });
            
            const data = await response.json();
            
            if (response.ok && data.access_token) {
                this._setToken(data.access_token);
                return { sucesso: true, usuario: data.usuario };
            }
            
            return { sucesso: false, erro: data.detail || 'Email ou senha incorretos' };
        } catch (error) {
            return { sucesso: false, erro: error.message };
        }
    },

    /**
     * Login Dev - Apenas para desenvolvimento/testes
     */
    async loginDev() {
        try {
            const response = await fetch(`${this.API_URL}/api/auth/setup-dev`, {
                method: 'GET',
                headers: {
                    'ngrok-skip-browser-warning': 'true'
                }
            });
            
            const data = await response.json();
            
            if (response.ok && data.access_token) {
                this._setToken(data.access_token);
                window.location.href = 'app.html';
                return { sucesso: true };
            }
            
            return { sucesso: false, erro: data.detail || 'Erro no login dev' };
        } catch (error) {
            return { sucesso: false, erro: error.message };
        }
    },

    /**
     * Logout
     */
    logout() {
        localStorage.removeItem('access_token');
        localStorage.removeItem('usuario');
        window.location.href = 'login.html';
    },

    /**
     * Verifica se está autenticado
     */
    isAuthenticated() {
        return !!this._getToken();
    },

    /**
     * Retorna usuário atual
     */
    getUsuario() {
        const usuario = localStorage.getItem('usuario');
        return usuario ? JSON.parse(usuario) : null;
    },

    /**
     * Headers com auth para fetch
     */
    getAuthHeaders() {
        const token = this._getToken();
        return {
            'Authorization': token ? `Bearer ${token}` : '',
            'ngrok-skip-browser-warning': 'true'
        };
    },

    // Private methods
    _setToken(token) {
        localStorage.setItem('access_token', token);
    },

    _getToken() {
        return localStorage.getItem('access_token');
    },

    _setUsuario(usuario) {
        localStorage.setItem('usuario', JSON.stringify(usuario));
    }
};

// ==========================================
// GUARD - Proteção de rotas
// ==========================================

const AuthGuard = {
    /**
     * Verifica auth e redireciona se necessário
     */
    check() {
        const publicPages = ['/login.html', '/cadastro.html', '/index.html', '/'];
        const currentPage = window.location.pathname;
        
        const isPublic = publicPages.some(page => currentPage.includes(page));
        
        if (!isPublic && !Auth.isAuthenticated()) {
            window.location.href = 'login.html';
            return false;
        }
        
        return true;
    },

    /**
     * Protege uma página específica
     */
    protect() {
        if (!Auth.isAuthenticated()) {
            window.location.href = 'login.html';
            return false;
        }
        return true;
    }
};

// ==========================================
// INICIALIZAÇÃO
// ==========================================

// Verifica auth em todas as páginas exceto login/cadastro
document.addEventListener('DOMContentLoaded', () => {
    const currentPage = window.location.pathname;
    if (!currentPage.includes('login.html') && !currentPage.includes('cadastro.html')) {
        AuthGuard.check();
    }
});

// Expõe globalmente
window.Auth = Auth;
window.AuthGuard = AuthGuard;
