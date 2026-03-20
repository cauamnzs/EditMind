// ==========================================
// CONFIGURAÇÃO DO SERVIDOR E ESTADOS
// ==========================================
const API_BASE_URL = 'https://shelley-filar-alona.ngrok-free.dev';

// Variáveis Globais de Estado
window.ultimoResultadoIA = null;
window.cortesGlobais = [];
window.caminhoVideoGlobal = "";
window.tempoCorteAlvo = '60'; // Começa no Padrão Viral de 60s

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
    barraProgresso.style.width = '30%';
    porcentagemTexto.textContent = '30%';

    const dados = new FormData();
    dados.append('arquivo', arquivo);
    dados.append('tempo_corte', window.tempoCorteAlvo); // <-- Envia a configuração atual

    try {
        const resposta = await fetch(`${API_BASE_URL}/api/upload`, {
            method: 'POST',
            headers: { 'ngrok-skip-browser-warning': 'true' },
            body: dados
        });

        const resultado = await resposta.json();

        if (resposta.ok) {
            preencherMetadadosSucesso(resultado);
        } else {
            throw new Error(resultado.detail || 'Falha no processamento.');
        }
    } catch (erro) {
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

    // Loader visual
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
        const resposta = await fetch(`${API_BASE_URL}/api/processar-youtube`, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'ngrok-skip-browser-warning': 'true'
            },
            // Envia o link e a configuração de tempo
            body: JSON.stringify({ url: link, tempo_corte: window.tempoCorteAlvo }) 
        });

        const resultado = await resposta.json();

        if (resposta.ok) {
            preencherMetadadosSucesso(resultado);
            
            // Restaura o botão
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
// 5. RENDERIZAÇÃO ESTÚDIO (GALERIA -> EDITOR)
// ==========================================
window.acionarTelaIA = function() {
    if (window.ultimoResultadoIA) mostrarResultadosIA(window.ultimoResultadoIA);
}

function mostrarResultadosIA(resultado) {
    // Esconde Upload, Mostra Painel IA
    painelUpload.classList.add('hidden');
    painelUpload.classList.remove('grid');
    painelIa.classList.remove('hidden');
    painelIa.classList.add('flex');
    
    // Garante que a Galeria está visível e o Editor escondido
    document.getElementById('tela-galeria').classList.remove('hidden');
    document.getElementById('tela-editor').classList.add('hidden');

    setTimeout(() => { painelIa.classList.remove('opacity-0'); }, 50);

    const listaCortes = document.getElementById('lista-cortes');
    listaCortes.innerHTML = ''; 
    
    window.cortesGlobais = resultado.corte_sugerido || [];
    
    if(resultado.detalhes_tecnicos && resultado.detalhes_tecnicos.caminho) {
        let path = resultado.detalhes_tecnicos.caminho.replace(/\\/g, '/');
        window.caminhoVideoGlobal = `${API_BASE_URL}/${path}`; 
    }

    if (!Array.isArray(window.cortesGlobais) || window.cortesGlobais.length === 0) {
        listaCortes.innerHTML = '<div class="col-span-3 p-8 text-center text-gray-500 border border-dashed border-gray-700 rounded-2xl">A IA não encontrou cortes.</div>';
        return;
    }

    // Cria os cards da Galeria
    window.cortesGlobais.forEach((corte, index) => {
        const card = document.createElement('div');
        
        card.className = `glass-panel rounded-[2rem] p-6 cursor-pointer border border-gray-800 hover:border-[#f97316] hover:shadow-[0_10px_30px_rgba(249,115,22,0.1)] transition-all group flex flex-col h-full`;
        card.onclick = () => abrirEditorCorte(index); // Ao clicar, abre o estúdio!
        
        card.innerHTML = `
            <div class="flex justify-between items-start mb-4">
                <span class="bg-black/50 text-[#f97316] text-[9px] font-black uppercase px-2 py-1 rounded-md border border-[#f97316]/30">Opção ${index + 1}</span>
                <span class="text-gray-400 text-xs font-mono font-bold bg-gray-900 px-2 py-1 rounded-md">${corte.inicio || '--'} - ${corte.fim || '--'}</span>
            </div>
            <h4 class="text-white font-black text-lg mb-4 leading-snug group-hover:text-[#f97316] transition-colors flex-1">${corte.titulo || 'Momento Viral Identificado'}</h4>
            <div class="mt-auto border-t border-gray-800 pt-4 flex items-center justify-between">
                <span class="text-[9px] text-gray-500 uppercase tracking-widest font-black">Viral Score</span>
                <div class="flex items-center gap-3 w-1/2">
                    <div class="w-full bg-gray-900 rounded-full h-1.5 flex-1 overflow-hidden">
                        <div class="bg-gradient-to-r from-yellow-500 to-[#f97316] h-full" style="width: ${corte.viral_score || 85}%"></div>
                    </div>
                    <span class="text-[#f97316] text-sm font-black">${corte.viral_score || 85}</span>
                </div>
            </div>
        `;
        listaCortes.appendChild(card);
    });
}

function converterParaSegundos(tempoStr) {
    if(!tempoStr || typeof tempoStr !== 'string') return 0;
    const partes = tempoStr.split(':');
    if(partes.length === 2) return parseInt(partes[0]) * 60 + parseInt(partes[1]);
    if(partes.length === 3) return parseInt(partes[0]) * 3600 + parseInt(partes[1]) * 60 + parseInt(partes[2]);
    return 0;
}

// Abre a tela do Estúdio de Edição
window.abrirEditorCorte = function(index) {
    const corte = window.cortesGlobais[index];
    if(!corte) return;

    // 1. Transição de Telas
    const telaGaleria = document.getElementById('tela-galeria');
    const telaEditor = document.getElementById('tela-editor');
    
    telaGaleria.classList.add('hidden');
    telaEditor.classList.remove('hidden');
    
    // Animação suave
    setTimeout(() => {
        telaEditor.classList.remove('opacity-0', 'scale-95');
        telaEditor.classList.add('opacity-100', 'scale-100');
    }, 50);

    // 2. Preenche os Dados do Editor
    document.getElementById('editor-titulo').textContent = corte.titulo || `Corte #${index + 1}`;
    document.getElementById('editor-badge').textContent = `Score Viral: ${corte.viral_score || 90}`;
    document.getElementById('editor-gancho').textContent = `"${corte.gancho || 'Gatilho não especificado.'}"`;
    document.getElementById('editor-motivo').textContent = corte.motivo || '...';
    document.getElementById('editor-tempo').textContent = `${corte.inicio || '00:00'} - ${corte.fim || '00:00'}`;
    
    // Como a IA atual não devolve o texto picado, colocamos o gancho como base ou uma mensagem
    document.getElementById('editor-texto').value = corte.texto_corte || `[A IA identificou este trecho como de alta retenção]\n\nGancho detectado: "${corte.gancho}"\n\n(A transcrição completa extraída deste intervalo de tempo será carregada aqui para edição de legendas na próxima versão do motor Python).`;

    // 3. O Truque do Vídeo Cortado (Media Fragments #t=inicio,fim)
    const videoPlayer = document.getElementById('player-vertical');
    if(window.caminhoVideoGlobal) {
        const segInicio = converterParaSegundos(corte.inicio);
        const segFim = converterParaSegundos(corte.fim);
        
        // Adicionar #t=inicio,fim na URL diz pro navegador tocar SÓ essa parte
        videoPlayer.src = `${window.caminhoVideoGlobal}#t=${segInicio},${segFim}`;
        videoPlayer.load();
        videoPlayer.play().catch(e => console.log("Auto-play prevenido", e));
    }
}

// Botão Voltar (Fecha o Editor e volta pra Galeria)
window.fecharEditor = function() {
    const telaGaleria = document.getElementById('tela-galeria');
    const telaEditor = document.getElementById('tela-editor');
    const videoPlayer = document.getElementById('player-vertical');
    
    if(videoPlayer) videoPlayer.pause(); // Para o vídeo

    telaEditor.classList.remove('opacity-100', 'scale-100');
    telaEditor.classList.add('opacity-0', 'scale-95');

    setTimeout(() => {
        telaEditor.classList.add('hidden');
        telaGaleria.classList.remove('hidden');
    }, 500);
}

// Reset Total (Botão Descartar Lote)
window.resetarNovoCorte = function() {
    painelIa.classList.add('opacity-0');
    const videoPlayer = document.getElementById('player-vertical');
    if(videoPlayer) videoPlayer.pause();
    
    setTimeout(() => {
        painelIa.classList.add('hidden');
        painelIa.classList.remove('flex');
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

// ==========================================
// 6. UTILITÁRIOS E NAVEGAÇÃO
// ==========================================
window.resetarNovoCorte = function() {
    painelIa.classList.add('opacity-0');
    
    // Pausa o vídeo para não ficar tocando em background
    const videoPlayer = document.getElementById('player-video');
    if(videoPlayer) videoPlayer.pause();
    
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

// --- YT Downloader Extra (Aba Utilitários) ---
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