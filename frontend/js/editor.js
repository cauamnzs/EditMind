// ==========================================
// RENDERIZAÇÃO ESTÚDIO E LÓGICA DE VÍDEO
// ==========================================

// ==========================================
// ESTILO DE LEGENDA — 3 TEMAS
// ==========================================
const SUBTITLE_CLASSES = ['subtitle-bold-neon', 'subtitle-classic-white', 'subtitle-impact-yellow'];

window.setSubtitleStyle = function(style, btn) {
    SUBTITLE_CLASSES.forEach(c => document.body.classList.remove(c));
    document.body.classList.add(`subtitle-${style}`);
    document.querySelectorAll('.subtitle-style-btn').forEach(b => b.classList.remove('active'));
    if (btn) btn.classList.add('active');
};

// ==========================================
// AI SCAN — ATIVA/DESATIVA ANIMAÇÃO
// ==========================================
window.setAiScanning = function(ativo, label) {
    const overlay = document.getElementById('ai-scan-overlay-el');
    const pulse = document.getElementById('ai-pulse-indicator');
    const statusLabel = document.getElementById('status-label');
    const msgEnvio = document.getElementById('mensagem-envio');

    if (ativo) {
        overlay && overlay.classList.remove('hidden');
        pulse && pulse.classList.remove('hidden');
        if (statusLabel) {
            statusLabel.classList.add('ai-status-text');
            statusLabel.textContent = label || 'IA Analisando Potencial Viral...';
        }
    } else {
        overlay && overlay.classList.add('hidden');
        pulse && pulse.classList.add('hidden');
        if (statusLabel) {
            statusLabel.classList.remove('ai-status-text');
            statusLabel.textContent = 'Pronto para Criar';
        }
    }
};

// ==========================================
// VIRAL SCORE — CLASSE NEON DINÂMICA
// ==========================================
function getViralScoreClass(score) {
    if (score >= 90) return { badge: 'viral-score-high', bar: 'viral-bar-high' };
    if (score >= 75) return { badge: 'viral-score-mid',  bar: 'viral-bar-mid'  };
    return                 { badge: 'viral-score-low',   bar: 'viral-bar-low'  };
}

window.acionarTelaIA = function() {
    if (window.ultimoResultadoIA) mostrarResultadosIA(window.ultimoResultadoIA);
}

function mostrarResultadosIA(resultado) {
    document.getElementById('painel-upload').classList.add('hidden');
    document.getElementById('painel-upload').classList.remove('grid');
    
    const painelIa = document.getElementById('painel-ia');
    painelIa.classList.remove('hidden');
    painelIa.classList.add('flex');
    
    document.getElementById('tela-galeria').classList.remove('hidden');
    document.getElementById('tela-editor').classList.add('hidden');

    setTimeout(() => { painelIa.classList.remove('opacity-0'); }, 50);

    const listaCortes = document.getElementById('lista-cortes');
    listaCortes.innerHTML = ''; 
    
    // ==========================================
    // BUSCA INTELIGENTE DE CORTES NO JSON
    // ==========================================
    let cortesEncontrados = resultado.cortes || resultado.corte_sugerido || resultado.sugestoes || [];
    
    if (cortesEncontrados && !Array.isArray(cortesEncontrados) && typeof cortesEncontrados === 'object') {
        cortesEncontrados = [cortesEncontrados];
    }

    // Fallback para demonstração
    if (!cortesEncontrados || cortesEncontrados.length === 0) {
        console.warn("Sem cortes válidos. Carregando demonstração.");
        cortesEncontrados = [
            { titulo: "O Gatilho da Retenção ", inicio: "00:15", fim: "01:05", viral_score: 98, gancho: "Se você faz isso no YouTube...", motivo: "Alta taxa de quebra de padrão visual." },
            { titulo: "Como viralizar amanhã", inicio: "03:10", fim: "04:00", viral_score: 85, gancho: "A regra secreta do algoritmo.", motivo: "Gera extrema curiosidade nos 3s iniciais." },
            { titulo: "Pare de errar nisso", inicio: "10:05", fim: "10:55", viral_score: 92, gancho: "Você está perdendo visualizações.", motivo: "Identificação direta com a dor da audiência." }
        ];
    }
    
    window.cortesGlobais = cortesEncontrados;
    
    // ==========================================
    // RESOLUÇÃO DO CAMINHO DO VÍDEO
    // ==========================================
    if (resultado.id_video) {
        window.idVideoAtual = resultado.id_video;
    }
    
    // Preferência: video_url > caminho > id_video
    if (resultado.detalhes_tecnicos) {
        const dt = resultado.detalhes_tecnicos;
        if (dt.video_url) {
            window.caminhoVideoGlobal = `${window.API_BASE_URL}${dt.video_url}`;
        } else if (dt.caminho) {
            let path = dt.caminho.replace(/\\\\/g, '/');
            if (path.includes('uploads/')) path = path.substring(path.indexOf('uploads/'));
            if (path.startsWith('/')) path = path.substring(1); 
            window.caminhoVideoGlobal = `${window.API_BASE_URL}/${path}`;
        } else if (resultado.id_video) {
            window.caminhoVideoGlobal = `${window.API_BASE_URL}/api/video/${resultado.id_video}`;
        }
        console.log(" Caminho vídeo:", window.caminhoVideoGlobal);
    }

    // ==========================================
    // DESENHA OS CARDS NA TELA
    // ==========================================
    window.cortesGlobais.forEach((corte, index) => {
        const score = corte.viral_score || 85;
        const cls = getViralScoreClass(score);
        const card = document.createElement('div');
        card.className = `glass-panel rounded-[2rem] p-6 cursor-pointer border border-gray-800 hover:border-[#f97316] hover:shadow-[0_10px_30px_rgba(249,115,22,0.1)] transition-all group flex flex-col h-full`;
        card.onclick = () => abrirEditorCorte(index); 
        
        // Suporta formato v2 (raw_start/raw_end) e legado (inicio/fim)
        const _tsInicio = corte.inicio || (corte.raw_start ? corte.raw_start.substring(0, 5) : null) || '--';
        const _tsFim    = corte.fim    || (corte.raw_end   ? corte.raw_end.substring(0, 5)   : null) || '--';
        const _durSeg   = corte.final_edited_duration_seconds ? `${corte.final_edited_duration_seconds.toFixed(0)}s` : '';
        card.innerHTML = `
            <div class="flex justify-between items-start mb-4">
                <span class="bg-black/50 text-[#f97316] text-[9px] font-black uppercase px-2 py-1 rounded-md border border-[#f97316]/30">Corte ${index + 1}</span>
                <span class="text-gray-400 text-xs font-mono font-bold bg-gray-900 px-2 py-1 rounded-md">${_tsInicio} → ${_tsFim}${_durSeg ? ' · ' + _durSeg : ''}</span>
            </div>
            <h4 class="text-white font-black text-lg mb-4 leading-snug group-hover:text-[#f97316] transition-colors flex-1">${corte.titulo || 'Momento Viral Identificado'}</h4>
            <div class="mt-auto border-t border-gray-800 pt-4 flex items-end justify-between gap-4">
                <div class="flex-1">
                    <span class="text-[9px] text-gray-500 uppercase tracking-widest font-black block mb-1.5">Potencial Viral</span>
                    <div class="w-full bg-gray-900 rounded-full h-1.5 overflow-hidden">
                        <div class="${cls.bar} h-full rounded-full transition-all duration-700" style="width:${score}%"></div>
                    </div>
                </div>
                <span class="viral-score-badge ${cls.badge} shrink-0">${score}</span>
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

function formatarTempoVTT(segundosTotais) {
    const h = Math.floor(segundosTotais / 3600);
    const m = Math.floor((segundosTotais % 3600) / 60);
    const s = Math.floor(segundosTotais % 60);
    const ms = Math.floor((segundosTotais % 1) * 1000);
    return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}.${ms.toString().padStart(3, '0')}`;
}

// ==========================================
// ALGORITMO SÊNIOR: GERA LEGENDA CAPCUT
// ==========================================
function criarTrilhaLegendaCapCut(texto, segInicio, segFim) {
    if (!texto) return null;
    
    let vttContent = "WEBVTT\n\n";
    
    // Limpa o texto e divide em array de palavras
    const palavras = texto.replace(/\n/g, ' ').split(' ').filter(p => p.trim() !== '');
    const duracaoTotal = segFim - segInicio;
    
    if(duracaoTotal <= 0) return null;

    // Calcula um tempo médio aproximado para cada palavra
    const tempoPorPalavra = duracaoTotal / palavras.length;
    
    let tempoAtual = segInicio;
    let contador = 1;

    // Agrupa de 5 em 5 palavras para gerar os blocos de legenda
    for (let i = 0; i < palavras.length; i += 5) {
        const blocoPalavras = palavras.slice(i, i + 5).join(' ');
        const duracaoBloco = tempoPorPalavra * palavras.slice(i, i + 5).length;
        const tempoFimBloco = tempoAtual + duracaoBloco;
        
        vttContent += `${contador}\n`;
        vttContent += `${formatarTempoVTT(tempoAtual)} --> ${formatarTempoVTT(tempoFimBloco)}\n`;
        vttContent += `${blocoPalavras}\n\n`;
        
        tempoAtual = tempoFimBloco;
        contador++;
    }

    const blob = new Blob([vttContent], { type: 'text/vtt' });
    return URL.createObjectURL(blob);
}

window.abrirEditorCorte = function(index) {
    const corte = window.cortesGlobais[index];
    if (!corte) return;

    // Transição Visual
    document.getElementById('tela-galeria').classList.add('hidden');
    const telaEditor = document.getElementById('tela-editor');
    telaEditor.classList.remove('hidden');
    setTimeout(() => {
        telaEditor.classList.remove('opacity-0', 'scale-95');
        telaEditor.classList.add('opacity-100', 'scale-100');
    }, 50);

    // Preenche metadados do card
    document.getElementById('editor-titulo').textContent = corte.titulo || `Corte #${index + 1}`;
    const _score = corte.viral_score || 90;
    const _cls = getViralScoreClass(_score);
    const badge = document.getElementById('editor-badge');
    badge.textContent = `⚡ Potencial Viral: ${_score}`;
    badge.className = badge.className.replace(/viral-score-\S+/g, '');
    badge.classList.add(_cls.badge);
    document.getElementById('editor-gancho').textContent = `"${corte.gancho || 'Gatilho não especificado.'}"`;
    document.getElementById('editor-motivo').textContent = corte.motivo || '...';

    // Exibe timestamp: suporta v2 (raw_start/raw_end) e legado (inicio/fim)
    const _tsIni = corte.inicio || (corte.raw_start ? corte.raw_start.substring(0, 8) : '00:00');
    const _tsFm  = corte.fim    || (corte.raw_end   ? corte.raw_end.substring(0, 8)   : '00:00');
    const _durLabel = corte.final_edited_duration_seconds ? ` · ${corte.final_edited_duration_seconds.toFixed(0)}s editados` : '';
    document.getElementById('editor-tempo').textContent = `${_tsIni} - ${_tsFm}${_durLabel}`;

    // Texto para edição (usa synced_transcript ou texto_corte)
    let textoEditor = '';
    if (corte.synced_transcript && corte.synced_transcript.length > 0) {
        textoEditor = corte.synced_transcript.map(c => c.text || '').join(' ').trim();
    } else if (corte.texto_corte) {
        textoEditor = corte.texto_corte;
    } else {
        textoEditor = corte.gancho || '';
    }
    document.getElementById('editor-texto').value = textoEditor;

    // Headline
    const headlineInput = document.getElementById('editor-headline');
    if (headlineInput && corte.titulo) headlineInput.value = corte.titulo;

    // Guarda estado no Editor
    Editor.corteAtual = corte;
    const tsInicio = corte.inicio || corte.raw_start || '0';
    const tsFim    = corte.fim    || corte.raw_end   || '0';
    Editor.segInicio = converterParaSegundos(tsInicio);
    Editor.segFim    = converterParaSegundos(tsFim);

    // ─────────────────────────────────────────────────────────────
    // PLAYER: sempre carrega o clipe RECORTADO (nunca o bruto)
    // ─────────────────────────────────────────────────────────────
    const videoPlayer = document.getElementById('player-vertical');
    videoPlayer.pause();
    videoPlayer.ontimeupdate = null;
    videoPlayer.onloadedmetadata = null;
    videoPlayer.querySelectorAll('track').forEach(t => t.remove());

    const temSegmentos = corte.segments_to_keep && corte.segments_to_keep.length > 0;

    // ── Injeta overlay de legenda no wrapper do player ──
    const playerWrapper = videoPlayer.parentElement;
    if (playerWrapper) {
        playerWrapper.style.position = 'relative';
        let overlay = document.getElementById('legenda-overlay-el');
        if (!overlay) {
            overlay = document.createElement('div');
            overlay.id = 'legenda-overlay-el';
            overlay.className = 'legenda-overlay';
            playerWrapper.appendChild(overlay);
        }
        // Adiciona botão CC se ainda não existir
        if (!document.getElementById('btn-legenda-cc')) {
            const btnCC = document.createElement('button');
            btnCC.id = 'btn-legenda-cc';
            btnCC.onclick = () => window.abrirPainelLegenda && window.abrirPainelLegenda();
            btnCC.title = 'Templates de Legenda';
            btnCC.className = 'absolute top-3 right-3 z-20 bg-black/60 hover:bg-[#f97316] text-white text-[10px] font-black px-2 py-1 rounded-lg border border-white/10 transition-all';
            btnCC.textContent = 'CC';
            playerWrapper.appendChild(btnCC);
        }
        // Re-aplica sincronização se template já selecionado
        if (window._templateAtual && window._templateAtual !== 'nenhum') {
            setTimeout(() => window.selecionarTemplate && window.selecionarTemplate(window._templateAtual), 300);
        }
    }

    if (temSegmentos && window.idVideoAtual) {
        // ── CAMINHO A: chama /api/ai/preview-corte (clipe físico nvenc) ──
        if (playerWrapper) playerWrapper.style.position = 'relative';
        document.getElementById('preview-spinner')?.remove();
        const spinnerEl = document.createElement('div');
        spinnerEl.id = 'preview-spinner';
        spinnerEl.className = 'absolute inset-0 flex flex-col items-center justify-center bg-black/75 z-20 rounded-2xl gap-2';
        spinnerEl.innerHTML = `
            <div class="relative">
                <div class="absolute inset-0 bg-[#f97316] blur-xl opacity-30 rounded-full"></div>
                <svg class="animate-spin w-12 h-12 text-[#f97316] relative z-10" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-20" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                    <path class="opacity-90" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                </svg>
            </div>
            <div class="text-center">
                <span class="text-[#f97316] text-xs font-bold block">Gerando preview na GPU...</span>
                <span class="text-gray-500 text-[10px] mt-1 block">Corte 9:16 com Smart Focus</span>
            </div>`;
        if (playerWrapper) playerWrapper.appendChild(spinnerEl);

        const focusVal = parseInt(document.getElementById('slider-focus')?.value || '50');

        fetch(`${window.API_BASE_URL}/api/ai/preview-corte`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'ngrok-skip-browser-warning': 'true' },
            body: JSON.stringify({
                id_video: window.idVideoAtual,
                segments_to_keep: corte.segments_to_keep,
                start: Editor.segInicio,
                end: Editor.segFim,
                focus_x: focusVal,
                synced_transcript: corte.synced_transcript || null
            })
        })
        .then(r => r.json())
        .then(data => {
            document.getElementById('preview-spinner')?.remove();
            if (!data.sucesso) {
                console.warn('[Preview] Falha no backend:', data);
                _carregarVideoLegado(videoPlayer, corte, Editor.segInicio, Editor.segFim, textoEditor);
                return;
            }

            // Carrega clipe recortado via blob
            fetch(`${window.API_BASE_URL}${data.video_url}`, {
                headers: { 'ngrok-skip-browser-warning': 'true' }
            })
            .then(r => r.blob())
            .then(blob => {
                videoPlayer.src = URL.createObjectURL(blob);
                videoPlayer.muted = false;
                videoPlayer.loop = true;

                const duracaoClipe = data.duracao_exata || 0;

                // Atualiza display de duração
                document.getElementById('editor-tempo').textContent =
                    `${_tsIni} - ${_tsFm} · ${duracaoClipe.toFixed(1)}s editados`;

                // Guarda para gerarVideoFinal usar
                Editor._previewClipUuid = data.clip_uuid;
                Editor._previewDuracao  = duracaoClipe;

                // Impede navegar além do clipe
                videoPlayer.ontimeupdate = () => {
                    if (duracaoClipe > 0 && videoPlayer.currentTime > duracaoClipe) {
                        videoPlayer.currentTime = 0;
                    }
                };

                // VTT sincronizado
                if (data.vtt_url) {
                    fetch(`${window.API_BASE_URL}${data.vtt_url}`, {
                        headers: { 'ngrok-skip-browser-warning': 'true' }
                    })
                    .then(r => r.text())
                    .then(vttText => {
                        const track = document.createElement('track');
                        track.kind = 'subtitles';
                        track.label = 'Português';
                        track.srclang = 'pt';
                        track.src = URL.createObjectURL(new Blob([vttText], { type: 'text/vtt' }));
                        track.default = true;
                        videoPlayer.appendChild(track);
                        setTimeout(() => {
                            if (videoPlayer.textTracks[0]) videoPlayer.textTracks[0].mode = 'showing';
                        }, 200);
                    });
                }

                videoPlayer.play().catch(() => {});
                console.log(` [Preview] ${data.video_url} (${duracaoClipe}s)`);
            })
            .catch(err => {
                console.warn('[Preview] Erro carregando blob:', err);
                _carregarVideoLegado(videoPlayer, corte, Editor.segInicio, Editor.segFim, textoEditor);
            });
        })
        .catch(err => {
            document.getElementById('preview-spinner')?.remove();
            console.warn('[Preview] Erro na requisição:', err);
            _carregarVideoLegado(videoPlayer, corte, Editor.segInicio, Editor.segFim, textoEditor);
        });

    } else if (window.caminhoVideoGlobal) {
        _carregarVideoLegado(videoPlayer, corte, Editor.segInicio, Editor.segFim, textoEditor);
    }
};

function _carregarVideoLegado(videoPlayer, corte, segInicio, segFim, texto) {
    videoPlayer.querySelectorAll('track').forEach(t => t.remove());
    const urlLegenda = criarTrilhaLegendaCapCut(texto, segInicio, segFim);
    if (urlLegenda && texto && texto.length > 10) {
        const track = document.createElement('track');
        track.kind = 'subtitles';
        track.label = 'Português';
        track.srclang = 'pt';
        track.src = urlLegenda;
        track.default = true;
        videoPlayer.appendChild(track);
    }
    videoPlayer.muted = true;
    fetch(window.caminhoVideoGlobal, { headers: { 'ngrok-skip-browser-warning': 'true' } })
    .then(r => r.blob())
    .then(blob => {
        videoPlayer.src = URL.createObjectURL(blob);
        videoPlayer.onloadedmetadata = () => {
            videoPlayer.currentTime = segInicio;
            videoPlayer.play().catch(() => {});
            setTimeout(() => {
                if (videoPlayer.textTracks[0]) videoPlayer.textTracks[0].mode = 'showing';
            }, 100);
        };
        videoPlayer.ontimeupdate = () => {
            if (segFim > 0 && videoPlayer.currentTime >= segFim) {
                videoPlayer.currentTime = segInicio;
                videoPlayer.play();
            }
        };
    })
    .catch(err => console.error('[Legado] Erro:', err));
}

window.fecharEditor = function() {
    const telaEditor = document.getElementById('tela-editor');
    const videoPlayer = document.getElementById('player-vertical');
    if (videoPlayer) {
        videoPlayer.pause();
        videoPlayer.ontimeupdate = null;
        videoPlayer.onloadedmetadata = null;
    }
    if (window._legendaRafId) { cancelAnimationFrame(window._legendaRafId); window._legendaRafId = null; }
    document.getElementById('preview-spinner')?.remove();
    telaEditor.classList.remove('opacity-100', 'scale-100');
    telaEditor.classList.add('opacity-0', 'scale-95');
    setTimeout(() => {
        telaEditor.classList.add('hidden');
        document.getElementById('tela-galeria').classList.remove('hidden');
    }, 300);
}

window.resetarNovoCorte = function() {
    const painelIa = document.getElementById('painel-ia');
    painelIa.classList.add('opacity-0');
    
    const videoPlayer = document.getElementById('player-vertical');
    if(videoPlayer) {
        videoPlayer.pause();
        videoPlayer.ontimeupdate = null;
        videoPlayer.onloadedmetadata = null;
        // O SEGREDO SÊNIOR: Arranca a fonte do vídeo para limpar a RAM!
        videoPlayer.removeAttribute('src'); 
        videoPlayer.load();
    }
    
    setTimeout(() => {
        painelIa.classList.add('hidden');
        painelIa.classList.remove('flex');
        
        // Garante que o estado interno das telas resete
        document.getElementById('tela-galeria').classList.remove('hidden');
        document.getElementById('tela-editor').classList.add('hidden');
        
        document.getElementById('barra-progresso').style.width = '0%';
        document.getElementById('porcentagem-envio').textContent = '0%';
        document.getElementById('nome-arquivo').textContent = 'Solte seu vídeo aqui e a IA faz o resto...';

        if (window.setAiScanning) window.setAiScanning(false);
        
        const msg = document.getElementById('mensagem-envio');
        msg.innerHTML = 'IA em Standby. Aguardando seu vídeo.';
        msg.classList.replace('text-red-500', 'text-gray-500');
        
        document.getElementById('meta-res').textContent = '—'; 
        document.getElementById('meta-fps').textContent = '—'; 
        document.getElementById('meta-duracao').textContent = '—';
        
        const painelUpload = document.getElementById('painel-upload');
        painelUpload.classList.remove('hidden');
        painelUpload.classList.add('grid');
        
        // Limpa a memória global
        window.ultimoResultadoIA = null;
        window.cortesGlobais = [];
        window.caminhoVideoGlobal = "";
        window.idVideoAtual = null;
    }, 500);
}

// ==========================================
// EDITOR CONTROLS - FASE 1 & 2
// ==========================================
const Editor = {
    corteAtual: null,
    segInicio: 0,
    segFim: 0,
    
    init() {
        // Setup slider focus com LIVE PREVIEW
        const slider = document.getElementById('slider-focus');
        const focusValor = document.getElementById('focus-valor');
        const player = document.getElementById('player-vertical');
        const guideEl = document.getElementById('focus-guide');
        const guideLine = document.getElementById('focus-guide-line');
        
        if (slider) {
            slider.addEventListener('input', (e) => {
                const val = parseInt(e.target.value);
                focusValor.textContent = `${val}%`;

                // Converte 0-100 para object-position X (0% = esquerda, 50% = centro, 100% = direita)
                if (player) {
                    player.style.objectPosition = `${val}% center`;
                }

                // Mostra linha guia de foco no player
                if (guideEl && guideLine) {
                    guideEl.classList.remove('hidden');
                    guideLine.style.left = `${val}%`;
                    clearTimeout(slider._guideTimer);
                    slider._guideTimer = setTimeout(() => guideEl.classList.add('hidden'), 1200);
                }
            });
        }
        
        // Setup headline input
        const headlineInput = document.getElementById('editor-headline');
        if (headlineInput) {
            headlineInput.addEventListener('input', (e) => {
                console.log('Headline:', e.target.value);
            });
        }

        // Aplica tema padrão
        document.body.classList.add('subtitle-bold-neon');
    },
    
    atualizarLegendas() {
        const videoPlayer = document.getElementById('player-vertical');
        const texto = document.getElementById('editor-texto').value;
        
        if (!videoPlayer || !this.segFim) return;
        
        // Remove legendas antigas
        const tracksAntigas = videoPlayer.querySelectorAll('track');
        tracksAntigas.forEach(t => t.remove());
        
        // Cria nova legenda
        const urlLegenda = criarTrilhaLegendaCapCut(texto, this.segInicio, this.segFim);
        if (urlLegenda && texto.length > 10) {
            const track = document.createElement('track');
            track.kind = 'subtitles';
            track.label = 'Português (Editado)';
            track.srclang = 'pt';
            track.src = urlLegenda;
            track.default = true;
            videoPlayer.appendChild(track);
            
            // Força exibição
            setTimeout(() => {
                if(videoPlayer.textTracks && videoPlayer.textTracks.length > 0) {
                    videoPlayer.textTracks[0].mode = 'showing';
                }
            }, 100);
        }
        
        // Feedback visual
        const btn = event.target;
        const originalText = btn.textContent;
        btn.textContent = '✓ Atualizado!';
        btn.classList.add('bg-green-500/20', 'text-green-500');
        setTimeout(() => {
            btn.textContent = originalText;
            btn.classList.remove('bg-green-500/20', 'text-green-500');
        }, 1500);
    },
    
    async gerarVideoFinal() {
        const btn = document.getElementById('btn-gerar');
        const statusDiv = document.getElementById('gerar-status');
        const statusP = statusDiv.querySelector('p');

        if (!window.idVideoAtual || !this.corteAtual) {
            statusP.textContent = 'Selecione um corte primeiro';
            statusP.className = 'text-red-500 text-sm font-semibold';
            statusDiv.classList.remove('hidden');
            return;
        }

        btn.disabled = true;
        btn.innerHTML = `
            <svg class="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
            </svg>
            Processando com IA...
        `;
        statusDiv.classList.add('hidden');

        try {
            // Coleta todos os parâmetros Fase 2
            const headline = document.getElementById('editor-headline').value;
            const focusX = parseInt(document.getElementById('slider-focus').value);
            const jumpCut = document.getElementById('chk-jump-cut').checked;
            const usarBroll = document.getElementById('chk-broll').checked;
            const keywordBroll = document.getElementById('keyword-broll').value;

            // Usa keyword do corte se não preenchida manualmente
            const keywordFinal = keywordBroll || this.corteAtual.keyword_broll || null;

            console.log('🎬 [Editor] Gerando corte com:', {
                jumpCut, usarBroll, keywordFinal, focusX
            });

            // Usa pipeline Editor Chefe v2 se segments_to_keep disponível
            const temSegmentos = this.corteAtual.segments_to_keep && this.corteAtual.segments_to_keep.length > 0;
            const endpoint = temSegmentos
                ? `${window.API_BASE_URL}/api/ai/gerar-corte-viral`
                : `${window.API_BASE_URL}/api/ai/gerar-corte`;

            const bodyPayload = temSegmentos
                ? {
                    id_video: window.idVideoAtual,
                    segments_to_keep: this.corteAtual.segments_to_keep,
                    synced_transcript: this.corteAtual.synced_transcript || null,
                    headline: headline || null,
                    focus_x: focusX,
                    usar_broll: usarBroll,
                    keyword_broll: keywordFinal,
                    titulo: this.corteAtual.titulo,
                    viral_score: this.corteAtual.viral_score
                }
                : {
                    id_video: window.idVideoAtual,
                    inicio: this.corteAtual.inicio,
                    fim: this.corteAtual.fim,
                    headline: headline || null,
                    focus_x: focusX,
                    texto_legendas: document.getElementById('editor-texto').value,
                    jump_cut: jumpCut,
                    usar_broll: usarBroll,
                    keyword_broll: keywordFinal
                };

            console.log(`🎬 [Editor] Usando ${temSegmentos ? 'Editor Chefe v2 (segments_to_keep)' : 'pipeline legado'}`);

            const response = await fetch(endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'ngrok-skip-browser-warning': 'true'
                },
                body: JSON.stringify(bodyPayload)
            });

            const data = await response.json();

            if (response.ok && data.sucesso) {
                const features = data.features || {};
                const duracaoEditada = data.duracao_editada || data.duracao || null;
                const featuresTxt = [
                    features.jump_cut_viral ? '✂️ Jump Cuts IA' : (features.jump_cut ? '⚡ Jump Cut' : ''),
                    features.broll         ? '🎨 B-Roll' : '',
                    features.headline      ? '📝 Headline' : '',
                    features.synced_transcript ? '📄 Legenda Sincronizada' : ''
                ].filter(Boolean).join(' · ') || 'Corte Padrão';

                const duracaoStr = duracaoEditada ? `<span class="text-gray-400 text-[10px]">⏱ ${duracaoEditada.toFixed(1)}s editados</span><br>` : '';

                statusP.innerHTML = `
                    ✅ <span class="text-green-400 font-bold">Short Viral Pronto!</span><br>
                    ${duracaoStr}
                    <span class="text-[10px] text-orange-400">${featuresTxt}</span><br>
                    <a href="${window.API_BASE_URL}${data.download_url}"
                       download
                       class="inline-block mt-3 bg-[#f97316] hover:bg-[#ea580c] text-white font-bold py-2 px-6 rounded-full text-xs transition-colors">
                        ⬇️ Baixar Short
                    </a>
                `;
                statusP.className = 'text-sm';
                statusDiv.classList.remove('hidden');

                // Carrega o vídeo RENDERIZADO no player (bypass ngrok via fetch+blob)
                const videoPlayer = document.getElementById('player-vertical');
                videoPlayer.ontimeupdate = null;

                fetch(`${window.API_BASE_URL}${data.video_url}`, {
                    headers: { 'ngrok-skip-browser-warning': 'true' }
                })
                .then(r => r.blob())
                .then(blob => {
                    const blobUrl = URL.createObjectURL(blob);

                    // Remove tracks antigas
                    videoPlayer.querySelectorAll('track').forEach(t => t.remove());

                    // Carrega VTT sincronizado do backend se disponível
                    if (data.vtt_url) {
                        fetch(`${window.API_BASE_URL}${data.vtt_url}`, {
                            headers: { 'ngrok-skip-browser-warning': 'true' }
                        })
                        .then(r => r.text())
                        .then(vttText => {
                            const vttBlob = new Blob([vttText], { type: 'text/vtt' });
                            const track = document.createElement('track');
                            track.kind = 'subtitles';
                            track.label = 'Português (Sincronizado)';
                            track.srclang = 'pt';
                            track.src = URL.createObjectURL(vttBlob);
                            track.default = true;
                            videoPlayer.appendChild(track);
                        });
                    }

                    videoPlayer.src = blobUrl;
                    videoPlayer.muted = false;
                    videoPlayer.loop = true;
                    videoPlayer.play().catch(() => {});

                    setTimeout(() => {
                        if (videoPlayer.textTracks[0]) videoPlayer.textTracks[0].mode = 'showing';
                    }, 200);
                })
                .catch(err => console.warn('[Player] Erro carregando vídeo renderizado:', err));

            } else {
                throw new Error(data.detail || 'Erro ao gerar vídeo');
            }
        } catch (error) {
            statusP.textContent = `❌ Erro: ${error.message}`;
            statusP.className = 'text-red-500 text-sm font-semibold';
            statusDiv.classList.remove('hidden');
        } finally {
            btn.disabled = false;
            btn.innerHTML = `
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"></path>
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                </svg>
                Gerar Vídeo Final
            `;
        }
    }
};

// Inicializa
Editor.init();