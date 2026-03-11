// ==========================================
// CONFIGURAÇÃO DO SERVIDOR (Atrito Zero)
// No dia da apresentação, troque este link pelo link do Ngrok
// ==========================================
const API_BASE_URL = 'http://127.0.0.1:8000';

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

// --- LÓGICA DE DRAG & DROP E UPLOAD ---
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
        alert('O EditMind aceita apenas arquivos de vídeo.');
        return;
    }

    // Resetando a interface de progresso
    nomeArquivoTexto.textContent = arquivo.name;
    mensagemTexto.textContent = 'Transferindo para a Inteligência Artificial...';
    mensagemTexto.classList.replace('text-green-500', 'text-gray-500');
    mensagemTexto.classList.replace('text-red-500', 'text-gray-500');
    barraProgresso.style.width = '15%';
    porcentagemTexto.textContent = '15%';

    const dados = new FormData();
    dados.append('arquivo', arquivo);

    try {
        const resposta = await fetch(`${API_BASE_URL}/api/upload`, {
            method: 'POST',
            body: dados
        });

        const resultado = await resposta.json();

        if (resposta.ok) {
            // Sucesso! Enche a barra.
            barraProgresso.style.width = '100%';
            porcentagemTexto.textContent = '100%';
            mensagemTexto.innerHTML = `✓ IA Finalizada! Carregando resultados...`;
            mensagemTexto.classList.replace('text-gray-500', 'text-green-500');
            
            // Puxa os detalhes técnicos (Apenas visual na tela de upload)
            const infos = resultado.detalhes_tecnicos;
            metaRes.textContent = infos.resolucao || 'N/A';
            metaFps.textContent = `${infos.fps} FPS` || 'N/A';
            metaDuracao.textContent = `${infos.duracao_segundos}s` || 'N/A';

            // O EFEITO UAU (Transição de Telas)
            setTimeout(() => {
                mostrarResultadosIA(resultado);
            }, 1000); // Espera 1 segundo pro professor ver a barra em 100%

        } else {
            throw new Error(resultado.detail || 'Falha no servidor');
        }
    } catch (erro) {
        mensagemTexto.textContent = "Erro na IA: " + erro.message;
        mensagemTexto.classList.replace('text-gray-500', 'text-red-500');
        barraProgresso.classList.replace('bg-[#f97316]', 'bg-red-500');
    }
}

// --- FUNÇÃO DE TRANSIÇÃO (A MÁGICA VISUAL) ---
function mostrarResultadosIA(resultado) {
    // 1. Esconde a tela de Upload
    painelUpload.classList.add('hidden');
    painelUpload.classList.remove('grid');

    // 2. Mostra a tela de IA
    painelIa.classList.remove('hidden');
    painelIa.classList.add('grid');
    
    // Pequeno delay pra dar o efeito de fade-in (opacity)
    setTimeout(() => {
        painelIa.classList.remove('opacity-0');
    }, 50);

    // 3. Injeta os dados do Backend (O Contrato JSON em ação)
    textoTranscricao.textContent = resultado.transcricao || "Transcrição não disponível.";
    
    if(resultado.corte_sugerido) {
        corteInicio.textContent = resultado.corte_sugerido.inicio || "00:00";
        corteFim.textContent = resultado.corte_sugerido.fim || "00:00";
        corteMotivo.textContent = `"${resultado.corte_sugerido.motivo}"` || "Sem motivo especificado.";
    }
}

// --- FUNÇÃO PARA RESETAR (Voltar pro Upload) ---
window.resetarNovoCorte = function() {
    // Esconde a IA e zera a opacidade
    painelIa.classList.add('opacity-0');
    
    setTimeout(() => {
        painelIa.classList.add('hidden');
        painelIa.classList.remove('grid');

        // Zera a barra de progresso
        barraProgresso.style.width = '0%';
        porcentagemTexto.textContent = '0%';
        nomeArquivoTexto.textContent = 'Aguardando feed...';
        mensagemTexto.textContent = 'Motor Python em Standby.';
        mensagemTexto.classList.replace('text-green-500', 'text-gray-500');
        
        // Zera os metadados
        metaRes.textContent = '—';
        metaFps.textContent = '—';
        metaDuracao.textContent = '—';

        // Mostra o Upload de novo
        painelUpload.classList.remove('hidden');
        painelUpload.classList.add('grid');
    }, 500); // Espera o fade out terminar
}

// --- FUNÇÃO DO YOUTUBE DOWNLOADER (Ferramentas) ---
async function baixarYouTube() {
    const inputLink = document.getElementById('input-youtube');
    const btn = document.getElementById('btn-youtube');
    const link = inputLink.value;

    if (!link) {
        alert("Cole um link do YouTube primeiro!");
        return;
    }

    const textoOriginal = btn.innerHTML;
    btn.innerHTML = `<svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white inline" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg> Processando...`;
    btn.disabled = true;

    try {
        const resposta = await fetch(`${API_BASE_URL}/api/download-youtube`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: link })
        });

        const resultado = await resposta.json();

        if (resposta.ok) {
            alert(`SUCESSO! O arquivo da IA processou: ${resultado.tamanho_mb}MB.`);
            inputLink.value = '';
        } else {
            throw new Error(resultado.detail);
        }
    } catch (erro) {
        alert("Erro: " + erro.message);
    } finally {
        btn.innerHTML = textoOriginal;
        btn.disabled = false;
    }
}

// --- FUNÇÃO DE NAVEGAÇÃO ENTRE ABAS ---
window.mudarAba = function(idAba) {
    document.querySelectorAll('.nav-item').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.view-section').forEach(aba => {
        aba.classList.remove('active');
    });

    if(window.event && window.event.currentTarget) {
        window.event.currentTarget.classList.add('active');
    }

    setTimeout(() => {
        document.getElementById('aba-' + idAba).classList.add('active');
    }, 50);
}