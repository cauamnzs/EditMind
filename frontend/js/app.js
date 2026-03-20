// ==========================================
// CONFIGURAÇÃO DO SERVIDOR E ESTADOS GLOBAIS
// ==========================================
window.API_BASE_URL = 'https://shelley-filar-alona.ngrok-free.dev';

// Variáveis Globais de Estado
window.ultimoResultadoIA = null;
window.cortesGlobais = [];
window.caminhoVideoGlobal = "";
window.tempoCorteAlvo = '60'; // Começa no Padrão Viral de 60s

// --- ELEMENTOS DA TELA DE UPLOAD ---
const areaSoltar = document.getElementById('area-soltar');
const entradaArquivo = document.getElementById('entrada-arquivo');
const nomeArquivoTexto = document.getElementById('nome-arquivo');
const barraProgresso = document.getElementById('barra-progresso');
const porcentagemTexto = document.getElementById('porcentagem-envio');
const mensagemTexto = document.getElementById('mensagem-envio');
const metaRes = document.getElementById('meta-res');
const metaFps = document.getElementById('meta-fps');
const metaDuracao = document.getElementById('meta-duracao');

// ==========================================
// 1. GERENCIAMENTO DE CONFIGURAÇÕES (TEMPO)
// ==========================================
window.selecionarTempo = function(botaoClicado, valor) {
    window.tempoCorteAlvo = valor;
    
    const todosBotoes = document.querySelectorAll('.btn-tempo');
    todosBotoes.forEach(btn => {
        btn.classList.remove('bg-[#f97316]/10', 'border-[#f97316]', 'shadow-[0_0_20px_rgba(249,115,22,0.1)]');
        btn.classList.add('bg-black/40', 'border-gray-800');
        
        const tag = btn.querySelector('span:nth-child(2)');
        if(tag) tag.classList.replace('text-[#f97316]', 'text-gray-500');
        
        const descricao = btn.querySelector('span:last-child');
        if(descricao) descricao.classList.replace('text-gray-300', 'text-gray-400');
    });
    
    botaoClicado.classList.remove('bg-black/40', 'border-gray-800');
    botaoClicado.classList.add('bg-[#f97316]/10', 'border-[#f97316]', 'shadow-[0_0_20px_rgba(249,115,22,0.1)]');
    
    const tag = botaoClicado.querySelector('span:nth-child(2)');
    if(tag) tag.classList.replace('text-gray-500', 'text-[#f97316]');
    
    const descricao = botaoClicado.querySelector('span:last-child');
    if(descricao) descricao.classList.replace('text-gray-400', 'text-gray-300');
};

// ==========================================
// 2. LÓGICA DE DRAG & DROP E UPLOAD LOCAL
// ==========================================
['dragenter', 'dragover', 'dragleave', 'drop'].forEach(evt => {
    areaSoltar.addEventListener(evt, e => { e.preventDefault(); e.stopPropagation(); });
});

['dragenter', 'dragover'].forEach(evt => {
    areaSoltar.addEventListener(evt, () => areaSoltar.classList.add('border-[#f97316]', 'bg-gray-800/50'));
});

['dragleave', 'drop'].forEach(evt => {
    areaSoltar.addEventListener(evt, () => areaSoltar.classList.remove('border-[#f97316]', 'bg-gray-800/50'));
});

areaSoltar.addEventListener('drop', e => processarArquivos(e.dataTransfer.files));
entradaArquivo.addEventListener('change', e => processarArquivos(e.target.files));

async function processarArquivos(arquivos) {
    if (arquivos.length === 0) return;
    const arquivo = arquivos[0];

    if (!arquivo.type.startsWith('video/')) {
        alert('O EditMind aceita apenas arquivos de vídeo (mp4, mov, avi, etc).');
        return;
    }

    nomeArquivoTexto.textContent = arquivo.name;
    mensagemTexto.textContent = 'Processando motor de IA...';
    mensagemTexto.classList.replace('text-green-500', 'text-gray-500');
    mensagemTexto.classList.replace('text-red-500', 'text-gray-500');
    
    // Animação Inteligente (Fake Progress)
    barraProgresso.style.width = '30%';
    porcentagemTexto.textContent = '30%';
    let progresso = 30;
    const animacaoIA = setInterval(() => {
        if (progresso < 90) {
            progresso += 1;
            barraProgresso.style.width = `${progresso}%`;
            porcentagemTexto.textContent = `${progresso}%`;
        }
    }, 800); // Sobe 1% quase por segundo

    const dados = new FormData();
    dados.append('arquivo', arquivo);
    dados.append('tempo_corte', window.tempoCorteAlvo); 

    try {
        const resposta = await fetch(`${window.API_BASE_URL}/api/upload`, {
            method: 'POST',
            headers: { 'ngrok-skip-browser-warning': 'true' },
            body: dados
        });

        clearInterval(animacaoIA); // IA respondeu! Para a animação.
        const resultado = await resposta.json();

        if (resposta.ok) {
            preencherMetadadosSucesso(resultado);
        } else {
            throw new Error(resultado.detail || 'Falha no processamento.');
        }
    } catch (erro) {
        clearInterval(animacaoIA);
        tratarErroEngine(erro.message);
    }
}

// ==========================================
// 3. PROCESSAMENTO VIA YOUTUBE
// ==========================================
window.processarLinkYoutubePrincipal = async function() {
    const inputLink = document.getElementById('input-yt-principal');
    const btnYt = document.getElementById('btn-yt-principal');
    const link = inputLink.value.trim();

    if (!link || (!link.includes('youtube.com') && !link.includes('youtu.be'))) {
        alert("Ops! Insira um link válido do YouTube.");
        return;
    }

    btnYt.disabled = true;
    btnYt.innerHTML = "...";
    btnYt.classList.add('opacity-50', 'cursor-not-allowed');
    
    nomeArquivoTexto.textContent = "Puxando vídeo da nuvem...";
    mensagemTexto.textContent = 'Extraindo áudio e acionando IA...';
    mensagemTexto.classList.remove('text-red-500');
    mensagemTexto.classList.add('text-gray-500');
    barraProgresso.style.width = '30%';
    porcentagemTexto.textContent = '30%';

    try {
        const resposta = await fetch(`${window.API_BASE_URL}/api/processar-youtube`, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'ngrok-skip-browser-warning': 'true'
            },
            body: JSON.stringify({ url: link, tempo_corte: window.tempoCorteAlvo }) 
        });

        const resultado = await resposta.json();

        if (resposta.ok) {
            preencherMetadadosSucesso(resultado);
            inputLink.value = '';
            btnYt.disabled = false;
            btnYt.innerHTML = "Processar";
            btnYt.classList.remove('opacity-50', 'cursor-not-allowed');
        } else {
            throw new Error(resultado.detail || 'Falha desconhecida no backend.');
        }
    } catch (erro) {
        tratarErroEngine(erro.message);
        btnYt.disabled = false;
        btnYt.innerHTML = "Falhou";
        btnYt.classList.remove('opacity-50', 'cursor-not-allowed');
    }
};

// ==========================================
// 4. FUNÇÕES AUXILIARES DE SUCESSO E ERRO
// ==========================================
function preencherMetadadosSucesso(resultado) {
    const infos = resultado.detalhes_tecnicos || {};
    metaRes.textContent = infos.resolucao || 'N/A';
    metaFps.textContent = infos.fps ? `${infos.fps} FPS` : 'N/A';
    metaDuracao.textContent = infos.duracao_segundos ? `${infos.duracao_segundos}s` : 'N/A';

    barraProgresso.style.width = '100%';
    porcentagemTexto.textContent = '100%';
    window.ultimoResultadoIA = resultado; 
    
    mensagemTexto.innerHTML = `
        <button onclick="acionarTelaIA()" class="mt-4 bg-[#f97316] hover:bg-white hover:text-[#f97316] text-white font-black py-4 px-10 rounded-full text-[10px] uppercase tracking-[0.2em] shadow-[0_15px_35px_rgba(249,115,22,0.4)] transition-all animate-pulse border-none cursor-pointer scale-110">
            Ver Relatório da IA ⚡
        </button>
    `;
}

function tratarErroEngine(msgErro) {
    console.error("Erro na Engine:", msgErro);
    mensagemTexto.textContent = "Erro: " + msgErro;
    mensagemTexto.classList.replace('text-gray-500', 'text-red-500');
    barraProgresso.classList.replace('bg-[#f97316]', 'bg-red-500');
    setTimeout(() => { 
        barraProgresso.style.width = '0%'; 
        porcentagemTexto.textContent = '0%'; 
    }, 3000);
}

// ==========================================
// 5. UTILITÁRIOS E NAVEGAÇÃO
// ==========================================
window.mudarAba = function(idAba) {
    document.querySelectorAll('.nav-item').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.view-section').forEach(aba => aba.classList.remove('active'));
    
    if(window.event && window.event.currentTarget) {
        window.event.currentTarget.classList.add('active');
    }
    
    setTimeout(() => {
        const abaAlvo = document.getElementById('aba-' + idAba);
        if(abaAlvo) abaAlvo.classList.add('active');
    }, 50);
}

async function baixarYouTube() {
    const inputLink = document.getElementById('input-youtube');
    const btn = document.getElementById('btn-youtube');
    const link = inputLink.value.trim();

    if (!link || (!link.includes('youtube.com') && !link.includes('youtu.be'))) {
        alert("Insira um link válido do YouTube.");
        return;
    }

    btn.disabled = true;
    btn.classList.remove('bg-[#f97316]', 'hover:bg-white');
    btn.classList.add('bg-gray-600', 'cursor-not-allowed');
    btn.innerHTML = `PROCESSANDO...`;

    try {
        const resposta = await fetch(`${window.API_BASE_URL}/api/download-youtube`, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'ngrok-skip-browser-warning': 'true'
            },
            body: JSON.stringify({ url: link })
        });

        if (resposta.ok) {
            const blob = await resposta.blob();
            const urlArquivo = window.URL.createObjectURL(blob);
            const linkDownload = document.createElement('a');
            linkDownload.href = urlArquivo;
            linkDownload.download = 'Corte_EditMind.mp4';
            document.body.appendChild(linkDownload);
            linkDownload.click();
            window.URL.revokeObjectURL(urlArquivo);
            document.body.removeChild(linkDownload);

            btn.classList.remove('bg-gray-600');
            btn.classList.add('bg-green-600');
            btn.innerHTML = `CONCLUÍDO! ✅`;
            inputLink.value = '';

            setTimeout(() => {
                btn.classList.remove('bg-green-600', 'cursor-not-allowed');
                btn.classList.add('bg-[#f97316]', 'hover:bg-white');
                btn.disabled = false;
                btn.innerHTML = `PUXAR PARA NUVEM`;
            }, 3000);
        } else {
            throw new Error("Erro no servidor.");
        }
    } catch (e) {
        alert(`Erro: ${e.message}`);
        btn.classList.remove('bg-gray-600', 'bg-green-600');
        btn.classList.add('bg-[#f97316]');
        btn.disabled = false;
        btn.innerHTML = `PUXAR PARA NUVEM`;
    }
}