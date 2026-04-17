// ==========================================
// CONFIGURAÇÃO DO SERVIDOR E ESTADOS GLOBAIS
// ==========================================
// window.API_BASE_URL é definido em config.js

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
// 6. SSE LABELS — definido antes de processarArquivos
// ==========================================
window._sseConexao = null;
const _SSE_LABELS = {
    audio_extraindo:  [15, 'Extraindo áudio em alta fidelidade...'],
    audio_extraido:   [20, 'Áudio extraído — iniciando Whisper...'],
    transcricao:      [30, 'Whisper transcrevendo com timestamps...'],
    transcricao_ok:   [55, 'Transcrição concluída — analisando ganchos...'],
    analise_ia:       [65, 'Brain Engine v2 identificando momentos virais...'],
    analise_ok:       [90, 'Cortes identificados — finalizando...'],
    concluido:        [100, 'Análise Concluída ✓'],
    erro:             [0,   'Erro no processamento'],
};

function _aplicarEventoSSE(d) {
    const etapa = d.etapa || '';
    const info = _SSE_LABELS[etapa];
    if (info) {
        const [pct, msg] = info;
        if (pct > 0) {
            barraProgresso.style.width = `${pct}%`;
            porcentagemTexto.textContent = `${pct}%`;
        }
        const statusLabel = document.getElementById('status-label');
        if (statusLabel) statusLabel.textContent = msg;
        if (window.setAiScanning) window.setAiScanning(etapa !== 'concluido' && etapa !== 'erro', msg);
    }
}

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
    mensagemTexto.textContent = 'Enviando para o Brain Engine...';
    mensagemTexto.classList.replace('text-green-500', 'text-gray-500');
    mensagemTexto.classList.replace('text-red-500', 'text-gray-500');

    // 1. Gera id único no frontend para SSE pré-conectado
    const idVideo = 'up_' + Date.now() + '_' + Math.random().toString(36).slice(2, 7);

    // 2. Inicia feedback visual imediato
    if (window.setAiScanning) window.setAiScanning(true, 'Enviando para o Brain Engine...');
    barraProgresso.style.width = '5%';
    porcentagemTexto.textContent = '5%';
    const statusLabel = document.getElementById('status-label');
    if (statusLabel) statusLabel.textContent = 'Conectando...';

    // 3. Fecha SSE anterior se existir
    if (window._sseConexao) {
        try { window._sseConexao.close(); } catch(_) {}
        window._sseConexao = null;
    }

    // 4. Abre SSE — backend aguarda até 15s pela fila ser criada
    let sseAtivo = false;
    let sseReceivedFinal = false;
    const sseUrl = `${window.API_BASE_URL}/api/upload/stream/${idVideo}`;
    const es = new EventSource(sseUrl);
    window._sseConexao = es;

    es.onopen = () => {
        sseAtivo = true;
        console.log('[SSE] Conexão aberta para', idVideo);
    };
    es.onmessage = (ev) => {
        if (!ev.data || ev.data.trim().startsWith(':')) return; // heartbeat
        try {
            const d = JSON.parse(ev.data);
            console.log('[SSE] Evento:', d.etapa, d.progresso);
            _aplicarEventoSSE(d);
            if (d.etapa === 'concluido' || d.etapa === 'erro') {
                sseReceivedFinal = true;
                es.close();
                window._sseConexao = null;
            }
        } catch(e) { console.warn('[SSE] Parse error:', e, ev.data); }
    };
    es.onerror = (e) => {
        console.warn('[SSE] Erro de conexão — usando fake-progress como fallback', e);
        sseAtivo = false;
    };

    // 5. Fake-progress fallback — avança suavemente até 88% se SSE não vier
    let fakePct = 5;
    const fakeTick = setInterval(() => {
        if (sseReceivedFinal) { clearInterval(fakeTick); return; }
        // Se SSE ativo, para de forçar mas mantém vivo para não resetar
        if (sseAtivo) return;
        const teto = 88;
        if (fakePct < teto) {
            fakePct = Math.min(fakePct + 1, teto);
            barraProgresso.style.width = `${fakePct}%`;
            porcentagemTexto.textContent = `${fakePct}%`;
        }
    }, 700);

    // 6. Monta FormData e envia
    const dados = new FormData();
    dados.append('arquivo', arquivo);
    dados.append('tempo_corte', window.tempoCorteAlvo);
    dados.append('id_video_hint', idVideo);

    try {
        const resposta = await fetch(`${window.API_BASE_URL}/api/upload`, {
            method: 'POST',
            headers: { 'ngrok-skip-browser-warning': 'true' },
            body: dados
        });

        clearInterval(fakeTick);
        const resultado = await resposta.json();

        if (resposta.ok) {
            preencherMetadadosSucesso(resultado);
            // Fecha SSE se ainda aberto (resultado veio antes do evento 'concluido')
            if (window._sseConexao) { window._sseConexao.close(); window._sseConexao = null; }
        } else {
            console.error('[Upload] Falha HTTP', resposta.status, resultado);
            if (window._sseConexao) { window._sseConexao.close(); window._sseConexao = null; }
            throw new Error(resultado.detail || `Erro ${resposta.status}`);
        }
    } catch (erro) {
        clearInterval(fakeTick);
        if (window._sseConexao) { window._sseConexao.close(); window._sseConexao = null; }
        if (window.setAiScanning) window.setAiScanning(false);
        console.error('[Upload] Erro capturado:', erro);
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
    
    nomeArquivoTexto.textContent = "Baixando vídeo do YouTube...";
    mensagemTexto.textContent = 'Sincronizando com o Brain Engine...';
    mensagemTexto.classList.remove('text-red-500');
    mensagemTexto.classList.add('text-gray-500');
    if (window.setAiScanning) window.setAiScanning(true, 'Baixando e Analisando Vídeo do YouTube...');
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
        if (window.setAiScanning) window.setAiScanning(false);
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

    // Desativa AI Scan e mostra label de sucesso
    if (window.setAiScanning) window.setAiScanning(false);
    const statusLabel = document.getElementById('status-label');
    if (statusLabel) statusLabel.textContent = 'Análise Concluída ✓';
    
    mensagemTexto.innerHTML = `
        <button onclick="acionarTelaIA()" class="mt-4 bg-[#f97316] hover:bg-white hover:text-[#f97316] text-white font-black py-4 px-10 rounded-full text-[10px] uppercase tracking-[0.2em] shadow-[0_15px_35px_rgba(249,115,22,0.4)] transition-all animate-pulse border-none cursor-pointer scale-110">
            🔥 Ver Momentos Virais
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

// ==========================================
// 7. HISTÓRICO — ABA MEUS CONTEÚDOS
// ==========================================
window.carregarHistorico = async function() {
    const loading = document.getElementById('historico-loading');
    const lista   = document.getElementById('historico-lista');
    const vazio   = document.getElementById('historico-vazio');

    if (!loading || !lista || !vazio) return;

    loading.classList.remove('hidden');
    lista.classList.add('hidden');
    vazio.classList.add('hidden');

    try {
        const resp = await fetch(`${window.API_BASE_URL}/api/projetos`, {
            headers: { 'ngrok-skip-browser-warning': 'true' }
        });
        const dados = await resp.json();

        loading.classList.add('hidden');

        if (!dados.projetos || dados.projetos.length === 0) {
            vazio.classList.remove('hidden');
            return;
        }

        lista.innerHTML = dados.projetos.map(p => {
            const dur  = p.duracao_segundos ? `${Math.round(p.duracao_segundos)}s` : '—';
            const data = p.criado_em ? new Date(p.criado_em).toLocaleDateString('pt-BR') : '—';
            const statusCor = p.status === 'pronto' ? 'text-green-400' :
                              p.status === 'erro'   ? 'text-red-400'   : 'text-yellow-400';
            const statusIcon = p.status === 'pronto' ? '✓' :
                               p.status === 'erro'   ? '✗' : '⟳';

            return `
            <div class="glass-panel rounded-2xl p-5 border border-gray-800 hover:border-gray-600 transition-all flex flex-col gap-3 cursor-pointer group"
                 onclick="reabrirProjeto('${p.id}')">
                <div class="flex items-start justify-between gap-2">
                    <p class="text-sm font-bold text-white truncate flex-1">${p.video_nome || 'Sem título'}</p>
                    <span class="text-[10px] font-black ${statusCor} shrink-0">${statusIcon} ${p.status}</span>
                </div>
                <p class="text-[10px] text-gray-500 leading-relaxed line-clamp-2">${p.transcricao_curta || '—'}</p>
                <div class="flex items-center justify-between text-[10px] text-gray-600 mt-1">
                    <span>⏱ ${dur}</span>
                    <span>🎬 ${p.n_clips || 0} corte(s)</span>
                    <span>${data}</span>
                </div>
                <button class="mt-1 w-full py-2 bg-white/5 hover:bg-[#f97316]/20 hover:text-[#f97316] text-gray-400 rounded-xl text-[10px] font-black uppercase tracking-widest border border-gray-800 hover:border-[#f97316]/40 transition-all">
                    Abrir Projeto
                </button>
            </div>`;
        }).join('');

        lista.classList.remove('hidden');
    } catch (err) {
        loading.classList.add('hidden');
        vazio.classList.remove('hidden');
        console.error('[Histórico]', err);
    }
};

window.reabrirProjeto = async function(idVideo) {
    try {
        const resp = await fetch(`${window.API_BASE_URL}/api/video/${idVideo}/clips`, {
            headers: { 'ngrok-skip-browser-warning': 'true' }
        });
        if (!resp.ok) throw new Error('Projeto não encontrado');
        const dados = await resp.json();

        // Recarrega o estado global como se fosse um upload novo
        window.caminhoVideoGlobal = dados.id_video;
        window.ultimoResultadoIA  = {
            id_video: dados.id_video,
            corte_sugerido: dados.metadados_edicao || [],
            transcricao: dados.transcricao || '',
            detalhes_tecnicos: { video_url: `/uploads/videos/${idVideo}.mp4` }
        };
        window.cortesGlobais = dados.metadados_edicao || [];

        mudarAba('inicio');
        setTimeout(() => {
            if (window.acionarTelaIA) window.acionarTelaIA();
        }, 200);
    } catch (err) {
        alert(`Erro ao reabrir projeto: ${err.message}`);
    }
};

// Carrega histórico automaticamente ao clicar na aba
const _mudarAbaOriginal = window.mudarAba;
window.mudarAba = function(idAba) {
    _mudarAbaOriginal(idAba);
    if (idAba === 'conteudos') {
        setTimeout(window.carregarHistorico, 100);
    }
};

// ==========================================
// 8. TEMPLATES DE LEGENDA — Hormozi & MrBeast
// ==========================================
window._templateAtual = 'nenhum';
window._legendaRafId  = null;
window._legendaPalavras = []; // [{palavra, start, end}]

window.abrirPainelLegenda = function() {
    const painel = document.getElementById('painel-legenda');
    if (painel) painel.classList.toggle('hidden');
};

window.selecionarTemplate = function(nome) {
    window._templateAtual = nome;

    // Atualiza botões
    ['nenhum', 'hormozi', 'mrbeast'].forEach(t => {
        const btn = document.getElementById('tmpl-' + t);
        if (btn) btn.classList.toggle('selecionado', t === nome);
    });

    // Aplica/remove overlay no vídeo do editor
    const overlay = document.getElementById('legenda-overlay-el');
    if (!overlay) return;

    overlay.className = 'legenda-overlay';
    if (nome === 'hormozi') overlay.classList.add('legenda-hormozi');
    if (nome === 'mrbeast') overlay.classList.add('legenda-mrbeast');

    if (nome === 'nenhum') {
        overlay.innerHTML = '';
        if (window._legendaRafId) { cancelAnimationFrame(window._legendaRafId); window._legendaRafId = null; }
        return;
    }

    // Carrega palavras do synced_transcript se disponível
    const resultado = window.ultimoResultadoIA;
    if (!resultado) return;

    const segs = resultado.synced_transcript || resultado.segmentos_whisper || [];
    window._legendaPalavras = [];

    segs.forEach(seg => {
        const words = (seg.words || []);
        if (words.length > 0) {
            words.forEach(w => {
                window._legendaPalavras.push({ palavra: w.word || w.text || '', start: w.start, end: w.end });
            });
        } else if (seg.text && seg.start != null) {
            // Fallback: divide o segmento igualmente entre palavras
            const partes = seg.text.trim().split(/\s+/);
            const durPalavra = (seg.end - seg.start) / (partes.length || 1);
            partes.forEach((p, i) => {
                window._legendaPalavras.push({
                    palavra: p,
                    start: seg.start + i * durPalavra,
                    end: seg.start + (i + 1) * durPalavra
                });
            });
        }
    });

    if (window._legendaPalavras.length === 0) {
        overlay.innerHTML = '<span class="legenda-palavra ativa" style="color:#f97316;font-size:12px">Sem timestamps — processe o vídeo primeiro</span>';
        return;
    }

    // Renderiza todas as palavras uma vez
    overlay.innerHTML = window._legendaPalavras.map((w, i) =>
        `<span class="legenda-palavra" data-idx="${i}">${w.palavra}</span>`
    ).join('');

    _iniciarSincronizacaoLegenda();
};

function _iniciarSincronizacaoLegenda() {
    if (window._legendaRafId) cancelAnimationFrame(window._legendaRafId);

    const videoEl = document.getElementById('video-preview') || document.querySelector('video');
    if (!videoEl) return;

    const overlay = document.getElementById('legenda-overlay-el');
    if (!overlay) return;

    let ultimoIdx = -1;

    function tick() {
        const t = videoEl.currentTime;
        const palavras = window._legendaPalavras;

        // Encontra palavra ativa no tempo atual
        let idxAtivo = -1;
        for (let i = 0; i < palavras.length; i++) {
            if (t >= palavras[i].start && t < palavras[i].end) {
                idxAtivo = i;
                break;
            }
        }

        if (idxAtivo !== ultimoIdx) {
            // Remove 'ativa' da anterior
            if (ultimoIdx >= 0) {
                const elAnterior = overlay.querySelector(`[data-idx="${ultimoIdx}"]`);
                if (elAnterior) elAnterior.classList.remove('ativa');
            }
            // Adiciona 'ativa' na atual
            if (idxAtivo >= 0) {
                const elAtivo = overlay.querySelector(`[data-idx="${idxAtivo}"]`);
                if (elAtivo) {
                    elAtivo.classList.add('ativa');
                    // Scroll suave para manter palavra visível (MrBeast)
                    elAtivo.scrollIntoView && elAtivo.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
                }
            }
            ultimoIdx = idxAtivo;
        }

        window._legendaRafId = requestAnimationFrame(tick);
    }

    window._legendaRafId = requestAnimationFrame(tick);
}