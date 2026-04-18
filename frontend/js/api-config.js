/**
 * CONFIGURAÇÃO DA API - EditMind
 * 
 * Para apresentação na faculdade:
 * 1. Inicie o backend: uvicorn main:app --reload
 * 2. Inicie o ngrok: ngrok http 8000
 * 3. Copie a URL do ngrok (ex: https://abc123.ngrok-free.app)
 * 4. Cole abaixo em NGROK_URL
 * 5. Faça deploy no Vercel
 */

const CONFIG = {
    // 👇👇👇 COLE A URL DO NGROK AQUI 👇👇👇
    NGROK_URL: 'https://SEU_NGROK_AQUI.ngrok-free.app',
    
    // Não alterar abaixo
    LOCAL_URL: 'http://localhost:8000',
    
    getApiUrl: function() {
        // Se estiver no Vercel (produção), usa ngrok
        if (window.location.hostname.includes('vercel.app') || 
            window.location.hostname.includes('editmind')) {
            console.log('[API] Modo Produção (Vercel) → usando ngrok:', this.NGROK_URL);
            return this.NGROK_URL;
        }
        // Desenvolvimento local
        console.log('[API] Modo Desenvolvimento → usando localhost:', this.LOCAL_URL);
        return this.LOCAL_URL;
    }
};

window.API_BASE_URL = CONFIG.getApiUrl();
console.log('[API] URL configurada:', window.API_BASE_URL);
