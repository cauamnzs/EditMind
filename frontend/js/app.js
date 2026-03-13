// ==========================================
// CONFIGURAÇÃO DO SERVIDOR (Atrito Zero)
// ==========================================
const API_BASE_URL = 'https://shelley-filar-alona.ngrok-free.dev';

// --- ELEMENTOS DA TELA DE UPLOAD ---
const painelUpload = document.getElementById('painel-upload');
const areaSoltar = document.getElementById('area-soltar');
const entradaArquivo = document.getElementById('entrada-arquivo');
const nomeArquivoTexto = document.getElementById('nome-arquivo');
const barraProgresso = document.getElementById('barra-progresso');
const porcentagemTexto = document.getElementById('porcentagem-envio');
const mensagemTexto = document.getElementById('mensagem-envio');

const metaRes = document.getElementById('meta-res');
const metaFps = document.getElementById('meta-fps');
const metaDuracao = document.getElementById('meta-duracao');

// --- ELEMENTOS DA TELA DA IA ---
const painelIa = document.getElementById('painel-ia');
const textoTranscricao = document.getElementById('texto-transcricao');
const corteInicio = document.getElementById('corte-inicio');
const corteFim = document.getElementById('corte-fim');
const corteMotivo = document.getElementById('corte-motivo');

// Variável global para segurar o resultado da IA até o clique do botão
window.ultimoResultadoIA = null;

// --- LÓGICA DE DRAG & DROP ---
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

// --- PROCESSAMENTO DO VÍDEO (UPLOAD LOCAL) ---
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
    barraProgresso.style.width = '30%';
    porcentagemTexto.textContent = '30%';

    const dados = new FormData();
    dados.append('arquivo', arquivo);

    try {
        const resposta = await fetch(`${API_BASE_URL}/api/upload`, {
            method: 'POST',
            headers: { 'ngrok-skip-browser-warning': 'true' },
            body: dados
        });

        const resultado = await resposta.json();

        if (resposta.ok) {
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
        } else {
            throw new Error(resultado.detail || 'Falha no processamento.');
        }
    } catch (erro) {
        mensagemTexto.textContent = "Erro na Engine: " + erro.message;
        mensagemTexto.classList.replace('text-gray-500', 'text-red-500');
        barraProgresso.classList.replace('bg-[#f97316]', 'bg-red-500');
        setTimeout(() => { barraProgresso.style.width = '0%'; }, 2000);
    }
}

// --- NAVEGAÇÃO E IA ---
window.acionarTelaIA = function() {
    if (window.ultimoResultadoIA) mostrarResultadosIA(window.ultimoResultadoIA);
}

function mostrarResultadosIA(resultado) {
    painelUpload.classList.add('hidden');
    painelUpload.classList.remove('grid');
    painelIa.classList.remove('hidden');
    painelIa.classList.add('grid');
    setTimeout(() => { painelIa.classList.remove('opacity-0'); }, 50);

    textoTranscricao.textContent = resultado.transcricao || "Sem transcrição disponível.";
    if(resultado.corte_sugerido) {
        corteInicio.textContent = resultado.corte_sugerido.inicio || "00:00";
        corteFim.textContent = resultado.corte_sugerido.fim || "00:00";
        corteMotivo.textContent = `"${resultado.corte_sugerido.motivo}"` || "Sem motivo.";
    }
}

window.resetarNovoCorte = function() {
    painelIa.classList.add('opacity-0');
    setTimeout(() => {
        painelIa.classList.add('hidden');
        painelIa.classList.remove('grid');
        barraProgresso.style.width = '0%';
        porcentagemTexto.textContent = '0%';
        nomeArquivoTexto.textContent = 'Aguardando feed...';
        mensagemTexto.innerHTML = 'Motor Python em Standby.';
        mensagemTexto.classList.replace('text-red-500', 'text-gray-500');
        metaRes.textContent = '—'; metaFps.textContent = '—'; metaDuracao.textContent = '—';
        painelUpload.classList.remove('hidden');
        painelUpload.classList.add('grid');
        window.ultimoResultadoIA = null;
    }, 500);
}

// --- YOUTUBE DOWNLOADER (ESTILIZADO E ANIMADO) ---
async function baixarYouTube() {
    const inputLink = document.getElementById('input-youtube');
    const btn = document.getElementById('btn-youtube');
    const link = inputLink.value.trim();

    if (!link || (!link.includes('youtube.com') && !link.includes('youtu.be'))) {
        alert("Insira um link válido do YouTube.");
        return;
    }

    // 1. ESTADO DE LOADING (Animação de Processamento)
    btn.disabled = true;
    const originalClasses = [...btn.classList]; // Guarda as classes originais
    
    // Transição suave para cinza enquanto processa
    btn.classList.remove('bg-[#f97316]', 'hover:bg-white');
    btn.classList.add('bg-gray-600', 'cursor-not-allowed');
    btn.innerHTML = `
        <span class="flex items-center justify-center gap-2">
            <svg class="animate-spin h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
            PROCESSANDO...
        </span>
    `;

    try {
        const resposta = await fetch(`${API_BASE_URL}/api/download-youtube`, {
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

            // 2. ESTADO DE SUCESSO (Verde e Concluído)
            btn.classList.remove('bg-gray-600');
            btn.classList.add('bg-green-600');
            btn.innerHTML = `CONCLUÍDO! ✅`;
            inputLink.value = '';

            // 3. RESET SUAVE (Volta ao laranja original após 3 segundos)
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
        // Reset imediato em caso de erro para permitir nova tentativa
        btn.classList.remove('bg-gray-600', 'bg-green-600');
        btn.classList.add('bg-[#f97316]');
        btn.disabled = false;
        btn.innerHTML = `PUXAR PARA NUVEM`;
    }
}

// --- CONTROLE DE ABAS ---
window.mudarAba = function(idAba) {
    document.querySelectorAll('.nav-item').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.view-section').forEach(aba => aba.classList.remove('active'));
    if(window.event && window.event.currentTarget) window.event.currentTarget.classList.add('active');
    setTimeout(() => {
        const abaAlvo = document.getElementById('aba-' + idAba);
        if(abaAlvo) abaAlvo.classList.add('active');
    }, 50);
}