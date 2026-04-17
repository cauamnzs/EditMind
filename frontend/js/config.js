// ==========================================
// CONFIGURAÇÃO GLOBAL DA API
// ==========================================
// IMPORTANTE: Antes de fazer git push para o Vercel,
// atualize a URL do Ngrok abaixo!

// ▼▼▼ ATUALIZE ESTA URL COM SUA URL DO NGROK ▼▼▼
const NGROK_URL = 'https://shelley-filar-alona.ngrok-free.dev';
// ▲▲▲ ATUALIZE ESTA URL COM SUA URL DO NGROK ▲▲▲

// Detecta se está rodando localmente ou no Vercel
const isLocal = window.location.hostname === 'localhost' || 
                window.location.hostname === '127.0.0.1' ||
                window.location.protocol === 'file:';

// Define a URL da API
window.API_BASE_URL = isLocal ? 'http://localhost:8000' : NGROK_URL;

console.log(`[Config] Ambiente: ${isLocal ? 'Local' : 'Produção (Vercel)'}`);
console.log(`[Config] API_URL: ${window.API_BASE_URL}`);
