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
// INICIALIZAÇÃO COM REDIRECIONAMENTO INTELIGENTE
// ==========================================

// Whitelist de páginas públicas (não precisam de token)
const PAGINAS_PUBLICAS = ['/login.html', '/cadastro.html', '/index.html', '/'];
const paginaAtual = window.location.pathname;
const isPaginaPublica = PAGINAS_PUBLICAS.some(page => paginaAtual.includes(page)) || 
                        paginaAtual === '/' || 
                        paginaAtual.endsWith('index.html');

const token = localStorage.getItem('access_token');
const temToken = token && token !== 'null' && token !== 'undefined';

console.log('[Auth Init] Página:', paginaAtual);
console.log('[Auth Init] Pública?', isPaginaPublica);
console.log('[Auth Init] Token?', temToken ? 'SIM' : 'NÃO');

// Lógica de redirecionamento
if (!temToken && !isPaginaPublica) {
    // Sem token em página protegida → manda pro login
    console.log('[Auth] Sem token em rota protegida, redirecionando...');
    window.location.replace('login.html');
} else if (temToken && isPaginaPublica) {
    // Tem token mas está em página pública → manda pro app
    console.log('[Auth] Usuário logado, redirecionando para app...');
    window.location.replace('app.html');
}

// ==========================================
// MODO DEMO - Para apresentação rápida
// ==========================================
Auth.modoDemo = function() {
    console.log('[Auth] Ativando MODO DEMO...');
    // Cria um token fake para a apresentação
    localStorage.setItem('access_token', 'demo_token_123');
    localStorage.setItem('usuario_demo', JSON.stringify({
        nome: 'Dev',
        email: 'dev@gmail.com',
        modo: 'demo'
    }));
    window.location.href = 'app.html';
};

// Verifica se está em modo demo
Auth.isDemo = function() {
    const token = localStorage.getItem('access_token');
    return token === 'demo_token_123';
};

// Expõe globalmente
window.Auth = Auth;
window.AuthGuard = AuthGuard;
