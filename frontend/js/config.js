// ==========================================
// CONFIGURAÇÃO GLOBAL DA API - EditMind
// ==========================================

/**
 * 🎓 PARA APRESENTAÇÃO NA FACULDADE:
 * 1. Inicie backend: uvicorn main:app --reload
 * 2. Inicie tunnel: cloudflared tunnel --url http://localhost:8000
 * 3. Copie a URL gerada (ex: https://xxx.trycloudflare.com)
 * 4. Cole abaixo em TUNNEL_URL
 * 5. Faça git push
 * 6. Deploy no Vercel
 */

// ▼▼▼ COLE A URL DO TUNNEL AQUI ▼▼▼
const NGROK_URL = 'https://months-intersection-herb-cool.trycloudflare.com';
// ▲▲▲ COLE A URL DO TUNNEL AQUI ▲▲▲

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
