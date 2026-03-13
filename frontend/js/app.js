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

// --- PROCESSAMENTO DO VÍDEO ---
async function processarArquivos(arquivos) {
    if (arquivos.length === 0) return;
    const arquivo = arquivos[0];

    if (!arquivo.type.startsWith('video/')) {
        alert('O EditMind aceita apenas arquivos de vídeo.');
        return;
    }

    // Resetando a interface
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
            headers: {
                // ESSA LINHA É O PULO DO GATO PARA O NGROK NÃO BLOQUEAR
                'ngrok-skip-browser-warning': 'true'
            },
            body: dados
        });

        const resultado = await resposta.json();

        if (resposta.ok) {
            // 1. Preenche os metadados IMEDIATAMENTE pro professor ver
            const infos = resultado.detalhes_tecnicos;
            metaRes.textContent = infos.resolucao || 'N/A';
            metaFps.textContent = `${infos.fps} FPS` || 'N/A';
            metaDuracao.textContent = `${infos.duracao_segundos}s` || 'N/A';

            // 2. Finaliza a barra visualmente
            barraProgresso.style.width = '100%';
            porcentagemTexto.textContent = '100%';
            
            // 3. O PULO DO GATO: Cria o botão de acionamento manual
            window.ultimoResultadoIA = resultado; // Guarda o JSON
            
            mensagemTexto.innerHTML = `
                <button onclick="acionarTelaIA()" class="mt-4 bg-[#f97316] hover:bg-white hover:text-[#f97316] text-white font-black py-4 px-10 rounded-full text-[10px] uppercase tracking-[0.2em] shadow-[0_15px_35px_rgba(249,115,22,0.4)] transition-all animate-pulse border-none cursor-pointer scale-110">
                    Ver Relatório da IA ⚡
                </button>
            `;

        } else {
            throw new Error(resultado.detail || 'Falha no servidor');
        }
    } catch (erro) {
        mensagemTexto.textContent = "Erro na Engine: " + erro.message;
        mensagemTexto.classList.replace('text-gray-500', 'text-red-500');
        barraProgresso.classList.replace('bg-[#f97316]', 'bg-red-500');
    }
}

// --- FUNÇÃO QUE O BOTÃO NOVO CHAMA ---
window.acionarTelaIA = function() {
    if (window.ultimoResultadoIA) {
        mostrarResultadosIA(window.ultimoResultadoIA);
    }
}

// --- TRANSIÇÃO VISUAL ---
function mostrarResultadosIA(resultado) {
    painelUpload.classList.add('hidden');
    painelUpload.classList.remove('grid');

    painelIa.classList.remove('hidden');
    painelIa.classList.add('grid');
    
    setTimeout(() => {
        painelIa.classList.remove('opacity-0');
    }, 50);

    textoTranscricao.textContent = resultado.transcricao || "Sem transcrição.";
    
    if(resultado.corte_sugerido) {
        corteInicio.textContent = resultado.corte_sugerido.inicio || "00:00";
        corteFim.textContent = resultado.corte_sugerido.fim || "00:00";
        corteMotivo.textContent = `"${resultado.corte_sugerido.motivo}"` || "...";
    }
}

// --- RESET E NAVEGAÇÃO ---
window.resetarNovoCorte = function() {
    painelIa.classList.add('opacity-0');
    setTimeout(() => {
        painelIa.classList.add('hidden');
        painelIa.classList.remove('grid');
        barraProgresso.style.width = '0%';
        porcentagemTexto.textContent = '0%';
        nomeArquivoTexto.textContent = 'Aguardando feed...';
        mensagemTexto.innerHTML = 'Motor Python em Standby.';
        metaRes.textContent = '—'; metaFps.textContent = '—'; metaDuracao.textContent = '—';
        painelUpload.classList.remove('hidden');
        painelUpload.classList.add('grid');
    }, 500);
}

async function baixarYouTube() {
    const inputLink = document.getElementById('input-youtube');
    const btn = document.getElementById('btn-youtube');
    const link = inputLink.value;
    if (!link) return;

    btn.disabled = true;
    btn.innerHTML = `Processando...`;

    try {
        const resposta = await fetch(`${API_BASE_URL}/api/download-youtube`, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                // ADICIONADO AQUI TAMBÉM PARA SEGURANÇA
                'ngrok-skip-browser-warning': 'true'
            },
            body: JSON.stringify({ url: link })
        });
        const res = await resposta.json();
        if (resposta.ok) {
            alert("Sucesso! Vídeo capturado.");
            inputLink.value = '';
        }
    } catch (e) {
        alert("Erro no download.");
    } finally {
        btn.disabled = false;
        btn.innerHTML = `Puxar para Nuvem`;
    }
}

window.mudarAba = function(idAba) {
    document.querySelectorAll('.nav-item').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.view-section').forEach(aba => aba.classList.remove('active'));
    if(window.event && window.event.currentTarget) window.event.currentTarget.classList.add('active');
    setTimeout(() => {
        document.getElementById('aba-' + idAba).classList.add('active');
    }, 50);
}