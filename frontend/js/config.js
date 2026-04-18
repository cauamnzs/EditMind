// ==========================================
// CONFIGURAÇÃO GLOBAL DA API - EditMind
// ==========================================

/**
 * 🚀 CONFIGURAÇÃO DO BACKEND (Render.com):
 * 1. Acesse https://render.com e crie um novo Web Service
 * 2. Aponte para o repositório GitHub (pasta /backend)
 * 3. Render detecta o Dockerfile automaticamente
 * 4. Após deploy, copie a URL gerada (ex: https://editmind-api.onrender.com)
 * 5. Cole abaixo em RENDER_URL e faça git push
 * 6. Também descomente a URL em backend/main.py (allow_origins)
 */

// ▼▼▼ COLE A URL DO RENDER AQUI ▼▼▼
const NGROK_URL = 'https://editmind-api.onrender.com';
// ▲▲▲ COLE A URL DO RENDER AQUI ▲▲▲

// Detecta ambiente
const isLocal = window.location.hostname === 'localhost' || 
                window.location.hostname === '127.0.0.1';
const isVercel = window.location.hostname.includes('vercel.app') ||
                 window.location.hostname.includes('editmind');

// Define URL da API
if (isLocal) {
    window.API_BASE_URL = 'http://localhost:8000';
    console.log('[config] 🖥️  Modo: Desenvolvimento Local');
} else if (isVercel) {
    window.API_BASE_URL = NGROK_URL;
    console.log('[config] 🚀 Modo: Vercel (Produção)');
    console.log('[config] 🔗 Tunnel:', NGROK_URL);
} else {
    window.API_BASE_URL = NGROK_URL;
    console.log('[config] 🌐 Modo: Outro (usando tunnel)');
}

console.log('[config] 📡 API_BASE_URL:', window.API_BASE_URL);

// Verificação de saúde
fetch(`${window.API_BASE_URL}/`)
    .then(r => r.ok ? console.log('[System] Backend online ✅') : console.warn('[System] Backend retornou', r.status))
    .catch(() => console.warn('[System] Backend offline — verifique o tunnel'));
