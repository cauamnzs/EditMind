// ==========================================
// CONFIGURAÇÃO GLOBAL DA API - EditMind
// ==========================================

/**
 * 🎓 PARA APRESENTAÇÃO NA FACULDADE:
 * 1. Inicie backend: uvicorn main:app --reload
 * 2. Inicie ngrok: ngrok http 8000
 * 3. Copie a URL do ngrok
 * 4. Cole abaixo em NGROK_URL
 * 5. Faça git push
 * 6. Deploy no Vercel
 */

// ▼▼▼ COLE A URL DO NGROK AQUI ▼▼▼
const NGROK_URL = 'https://shelley-filar-alona.ngrok-free.dev';
// ▲▲▲ COLE A URL DO NGROK AQUI ▲▲▲

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
    console.log('[config] 🔗 Ngrok:', NGROK_URL);
} else {
    window.API_BASE_URL = NGROK_URL;
    console.log('[config] 🌐 Modo: Outro (usando ngrok)');
}

console.log('[config] 📡 API_BASE_URL:', window.API_BASE_URL);

// Verificação de saúde
fetch(`${window.API_BASE_URL}/`, {
    headers: { 'ngrok-skip-browser-warning': 'true' }
})
    .then(r => console.log('[config] ✅ Backend online'))
    .catch(e => console.log('[config] ❌ Backend offline:', e.message));
