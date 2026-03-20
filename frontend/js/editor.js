// ==========================================
// RENDERIZAÇÃO ESTÚDIO E LÓGICA DE VÍDEO
// ==========================================

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
    
    window.cortesGlobais = resultado.corte_sugerido || [];
    
    // === FILTRO SÊNIOR DE URL ===
    if (resultado.detalhes_tecnicos && resultado.detalhes_tecnicos.caminho) {
        // 1. Troca barras do Windows por barras de Web
        let path = resultado.detalhes_tecnicos.caminho.replace(/\\/g, '/');
        
        // 2. Se o Python mandou o caminho inteiro (C:/Users...), corta e pega só a partir da pasta 'uploads'
        if (path.includes('uploads/')) {
            path = path.substring(path.indexOf('uploads/'));
        }
        
        // 3. Remove barra inicial se tiver, para não duplicar com a BASE_URL
        if (path.startsWith('/')) path = path.substring(1); 
        
        window.caminhoVideoGlobal = `${window.API_BASE_URL}/${path}`;
        console.log("🎬 Caminho do vídeo resolvido para:", window.caminhoVideoGlobal);
    }

    if (!Array.isArray(window.cortesGlobais) || window.cortesGlobais.length === 0) {
        listaCortes.innerHTML = '<div class="col-span-3 p-8 text-center text-gray-500 border border-dashed border-gray-700 rounded-2xl">A IA não encontrou cortes.</div>';
        return;
    }

    window.cortesGlobais.forEach((corte, index) => {
        const card = document.createElement('div');
        card.className = `glass-panel rounded-[2rem] p-6 cursor-pointer border border-gray-800 hover:border-[#f97316] hover:shadow-[0_10px_30px_rgba(249,115,22,0.1)] transition-all group flex flex-col h-full`;
        card.onclick = () => abrirEditorCorte(index); 
        
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
    if(!corte) return;

    // Transição Visual
    const telaGaleria = document.getElementById('tela-galeria');
    const telaEditor = document.getElementById('tela-editor');
    telaGaleria.classList.add('hidden');
    telaEditor.classList.remove('hidden');
    
    setTimeout(() => {
        telaEditor.classList.remove('opacity-0', 'scale-95');
        telaEditor.classList.add('opacity-100', 'scale-100');
    }, 50);

    // Preenche Interface Mínima
    document.getElementById('editor-titulo').textContent = corte.titulo || `Corte #${index + 1}`;
    document.getElementById('editor-badge').textContent = `Score Viral: ${corte.viral_score || 90}`;
    document.getElementById('editor-gancho').textContent = `"${corte.gancho || 'Gatilho não especificado.'}"`;
    document.getElementById('editor-motivo').textContent = corte.motivo || '...';
    document.getElementById('editor-tempo').textContent = `${corte.inicio || '00:00'} - ${corte.fim || '00:00'}`;
    
    const segInicio = converterParaSegundos(corte.inicio);
    const segFim = converterParaSegundos(corte.fim);
    const duracaoVideo = segFim - segInicio;

    // ==========================================
    // FILTRO ANTI-ALUCINAÇÃO DA IA
    // ==========================================
    // Pega a transcrição completa original que o Whisper gerou
    const transcricaoCompleta = (window.ultimoResultadoIA && window.ultimoResultadoIA.transcricao) ? window.ultimoResultadoIA.transcricao : "";
    let textoRealDoCorte = corte.texto_corte || "";

    // Se o texto for absurdamente grande (IA alucinou e trouxe tudo)
    // Uma pessoa fala no MÁXIMO 25 caracteres por segundo.
    if (!textoRealDoCorte || textoRealDoCorte.length > (duracaoVideo * 25)) {
        console.warn("IA alucinou o texto. Filtrando via JavaScript...");
        const ganchoAjustado = corte.gancho ? corte.gancho.substring(0, 30) : ""; // Pega o começo do gancho
        const indexInicio = transcricaoCompleta.indexOf(ganchoAjustado);
        
        if (indexInicio !== -1 && duracaoVideo > 0) {
            // Corta o texto partindo do gancho, baseado no tempo
            const limiteCaracteres = duracaoVideo * 18; // Média de fala normal
            textoRealDoCorte = transcricaoCompleta.substring(indexInicio, indexInicio + limiteCaracteres);
        } else {
            textoRealDoCorte = "Não foi possível extrair a legenda exata, mas o vídeo foi cortado corretamente.";
        }
    }

    // Joga o texto processado na caixa de edição
    document.getElementById('editor-texto').value = textoRealDoCorte;

    // ==========================================
    // LÓGICA DO PLAYER E LEGENDA
    // ==========================================
    const videoPlayer = document.getElementById('player-vertical');
    
    if(window.caminhoVideoGlobal) {
        
        // 1. Limpa legendas antigas
        const tracksAntigas = videoPlayer.querySelectorAll('track');
        tracksAntigas.forEach(t => t.remove());

        // 2. Gera a legenda dinâmica
        const urlLegenda = criarTrilhaLegendaCapCut(textoRealDoCorte, segInicio, segFim);
        if (urlLegenda && textoRealDoCorte.length > 10) {
            const track = document.createElement('track');
            track.kind = 'subtitles';
            track.label = 'Português';
            track.srclang = 'pt';
            track.src = urlLegenda;
            track.default = true; 
            videoPlayer.appendChild(track);
        }

        // 3. FORÇA O DOWNLOAD DO VÍDEO VIA JS (Burla o Ngrok e o file:///)
        videoPlayer.muted = true; // Essencial pro autoplay funcionar
        
        fetch(window.caminhoVideoGlobal, {
            headers: { 'ngrok-skip-browser-warning': 'true' }
        })
        .then(response => response.blob())
        .then(blob => {
            const videoBlobUrl = URL.createObjectURL(blob);
            videoPlayer.src = videoBlobUrl;
            
            videoPlayer.onloadedmetadata = function() {
                videoPlayer.currentTime = segInicio;
                videoPlayer.play().catch(e => console.log("Auto-play prevenido", e));
                
                // Força a legenda a aparecer
                setTimeout(() => {
                    if(videoPlayer.textTracks && videoPlayer.textTracks.length > 0) {
                        videoPlayer.textTracks[0].mode = 'showing';
                    }
                }, 100);
            };
        })
        .catch(err => console.error("Erro ao forçar carregamento do vídeo:", err));

        // 4. CRIA O AUTO-LOOP DO SHORT!
        videoPlayer.ontimeupdate = function() {
            if (videoPlayer.currentTime >= segFim) {
                videoPlayer.pause();
                videoPlayer.currentTime = segInicio;
                videoPlayer.play();
            }
        };
    
    }
}

window.fecharEditor = function() {
    const telaGaleria = document.getElementById('tela-galeria');
    const telaEditor = document.getElementById('tela-editor');
    const videoPlayer = document.getElementById('player-vertical');
    
    if(videoPlayer) {
        videoPlayer.pause(); 
        videoPlayer.ontimeupdate = null; // Tira o Loop
        videoPlayer.onloadedmetadata = null;
    }

    telaEditor.classList.remove('opacity-100', 'scale-100');
    telaEditor.classList.add('opacity-0', 'scale-95');

    setTimeout(() => {
        telaEditor.classList.add('hidden');
        telaGaleria.classList.remove('hidden');
    }, 500);
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
        document.getElementById('nome-arquivo').textContent = 'Aguardando feed...';
        
        const msg = document.getElementById('mensagem-envio');
        msg.innerHTML = 'Motor Python em Standby.';
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
    }, 500);
}