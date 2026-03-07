// ==========================================
// CONFIGURAÇÃO DO SERVIDOR (Atrito Zero)
// No dia da apresentação, troque este link pelo link do Ngrok
// Exemplo: const API_BASE_URL = 'https://1a2b-3c4d.ngrok-free.app';
// ==========================================
const API_BASE_URL = 'http://127.0.0.1:8000';


// --- FUNÇÃO DO YOUTUBE DOWNLOADER ---
async function baixarYouTube() {
    const inputLink = document.getElementById('input-youtube');
    const btn = document.getElementById('btn-youtube');
    const link = inputLink.value;

    if (!link) {
        alert("Cole um link do YouTube primeiro!");
        return;
    }

    // Efeito visual de carregamento
    const textoOriginal = btn.innerHTML;
    btn.innerHTML = `<svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white inline" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg> Baixando e Processando...`;
    btn.disabled = true;

    try {
        const resposta = await fetch(`${API_BASE_URL}/api/download-youtube`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ url: link })
        });

        const resultado = await resposta.json();

        if (resposta.ok) {
            alert(`SUCESSO! Vídeo baixado (${resultado.tamanho_mb}MB). Confira a pasta uploads/videos!`);
            inputLink.value = ''; // Limpa o campo
        } else {
            throw new Error(resultado.detail);
        }
    } catch (erro) {
        alert("Erro: " + erro.message);
    } finally {
        // Restaura o botão
        btn.innerHTML = textoOriginal;
        btn.disabled = false;
    }
}

// --- FUNÇÃO DE NAVEGAÇÃO ENTRE ABAS ---
function mudarAba(idAba) {
    document.querySelectorAll('.nav-item').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.view-section').forEach(aba => {
        aba.classList.remove('active');
    });

    // Pega o botão que foi clicado (se o evento existir)
    if(window.event && window.event.currentTarget) {
        window.event.currentTarget.classList.add('active');
    }

    setTimeout(() => {
        document.getElementById('aba-' + idAba).classList.add('active');
    }, 50);
}

// --- LÓGICA DE DRAG & DROP E UPLOAD ---
const areaSoltar = document.getElementById('area-soltar');
const entradaArquivo = document.getElementById('entrada-arquivo');
const nomeArquivoTexto = document.getElementById('nome-arquivo');
const barraProgresso = document.getElementById('barra-progresso');
const porcentagemTexto = document.getElementById('porcentagem-envio');
const mensagemTexto = document.getElementById('mensagem-envio');

const metaRes = document.getElementById('meta-res');
const metaFps = document.getElementById('meta-fps');
const metaDuracao = document.getElementById('meta-duracao');

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

    nomeArquivoTexto.textContent = arquivo.name;
    mensagemTexto.textContent = 'Transferindo para o motor FFmpeg...';
    mensagemTexto.classList.replace('text-green-500', 'text-gray-500');
    mensagemTexto.classList.replace('text-red-500', 'text-gray-500');

    const dados = new FormData();
    dados.append('arquivo', arquivo);

    try {
        barraProgresso.style.width = '15%';
        porcentagemTexto.textContent = '15%';

        const resposta = await fetch(`${API_BASE_URL}/api/upload`, {
            method: 'POST',
            body: dados
        });

        const resultado = await resposta.json();

        if (resposta.ok) {
            barraProgresso.style.width = '100%';
            porcentagemTexto.textContent = '100%';
            
            const infos = resultado.detalhes_tecnicos;
            
            metaRes.textContent = infos.resolucao || 'N/A';
            metaFps.textContent = `${infos.fps} FPS` || 'N/A';
            metaDuracao.textContent = `${infos.duracao_segundos}s` || 'N/A';

            mensagemTexto.innerHTML = `✓ Sucesso! Áudio extraído e vídeo salvo (${resultado.tamanho_mb} MB)`;
            mensagemTexto.classList.replace('text-gray-500', 'text-green-500');
        } else {
            throw new Error(resultado.detail || 'Falha no servidor');
        }
    } catch (erro) {
        mensagemTexto.textContent = "Erro: O servidor Python não está rodando. " + erro.message;
        mensagemTexto.classList.replace('text-gray-500', 'text-red-500');
        barraProgresso.classList.replace('bg-[#f97316]', 'bg-red-500');
    }
}