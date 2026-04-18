# 🚀 DEPLOY PARA VERCEL - INSTRUÇÕES RÁPIDAS

## FLUXO PARA APRESENTAÇÃO NA FACULDADE

### Passo 1: Iniciar Backend no Seu PC
```bash
cd backend
uvicorn main:app --reload
```

### Passo 2: Expor Backend com Ngrok
```bash
# Em outro terminal
ngrok http 8000
```

### Passo 3: Atualizar URL do Ngrok
1. Copie a URL do ngrok (ex: `https://abc123.ngrok-free.app`)
2. Abra `frontend/js/config.js`
3. Cole a URL na linha 16: `const NGROK_URL = 'https://SEU_NGROK_AQUI.ngrok-free.app';`
4. Salve o arquivo

### Passo 4: Commit e Push
```bash
git add .
git commit -m "Atualiza URL do ngrok para apresentação"
git push origin main
```

### Passo 5: Deploy no Vercel
1. Vá para https://vercel.com
2. Conecte seu repositório GitHub
3. Configure:
   - **Root Directory**: `frontend`
   - **Framework Preset**: `Other`
   - **Build Command**: Deixe em branco (site estático)
   - **Output Directory**: `.`
4. Clique em **Deploy**

### Passo 6: Testar
1. Abra o link do Vercel
2. Faça login com: `dev@gmail.com` / `dev123`
3. O sistema deve funcionar usando SEU PC como servidor!

---

## ⚠️ IMPORTANTE

- **Seu PC precisa estar ligado** durante a apresentação
- **Ngrok precisa estar rodando** (terminal aberto)
- **Backend precisa estar rodando** (outro terminal)
- A cada vez que reiniciar o ngrok, a URL muda → precisa atualizar no config.js

## 🔧 SOLUÇÃO DE PROBLEMAS

### CORS Error?
- Verifique se o backend está rodando
- Verifique se o ngrok está rodando
- Verifique se a URL no config.js está correta

### "Backend offline" no console?
- Confirme que uvicorn está rodando
- Confirme que ngrok está rodando
- Teste a URL do ngrok no navegador

### Redirect loop?
- Limpe o localStorage (F12 → Application → Local Storage → Clear)
- Recarregue a página
