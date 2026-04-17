"""
Serviço de integração com Pexels API para B-Roll inteligente.
Busca imagens/stock photos relacionadas ao tema do corte.
"""
import requests
import os
from typing import Optional, Dict
from dotenv import load_dotenv

load_dotenv()

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")
PEXELS_BASE_URL = "https://api.pexels.com/v1"

# Session persistente — reutiliza conexão TCP/TLS entre chamadas
_session = requests.Session()
if PEXELS_API_KEY:
    _session.headers.update({"Authorization": PEXELS_API_KEY})


def buscar_imagem_broll(keyword: str, orientacao: str = "portrait") -> Optional[Dict]:
    """
    Busca imagem relacionada no Pexels.
    
    Args:
        keyword: Palavra-chave de busca (em inglês)
        orientacao: 'portrait' (9:16), 'landscape' (16:9), 'square'
    
    Returns:
        Dict com url da imagem, autor, etc. ou None se falhar
    """
    if not PEXELS_API_KEY:
        print("⚠️ [Pexels] API Key não configurada, usando imagem placeholder")
        return _mock_imagem_broll(keyword)
    
    try:
        params = {
            "query": keyword,
            "orientation": orientacao,
            "per_page": 5,
            "page": 1
        }
        response = _session.get(
            f"{PEXELS_BASE_URL}/search",
            params=params,
            timeout=15
        )
        
        if response.status_code == 200:
            data = response.json()
            fotos = data.get("photos", [])
            
            if fotos:
                # Pega a primeira imagem
                foto = fotos[0]
                resultado = {
                    "id": foto.get("id"),
                    "url_original": foto.get("src", {}).get("original"),
                    "url_large": foto.get("src", {}).get("large"),
                    "url_medium": foto.get("src", {}).get("medium"),
                    "url_small": foto.get("src", {}).get("small"),
                    "url_portrait": foto.get("src", {}).get("portrait"),
                    "url_landscape": foto.get("src", {}).get("landscape"),
                    "fotografo": foto.get("photographer"),
                    "largura": foto.get("width"),
                    "altura": foto.get("height"),
                    "keyword": keyword
                }
                print(f"✅ [Pexels] Imagem encontrada para '{keyword}': {resultado['url_medium'][:60]}...")
                return resultado
            else:
                print(f"⚠️ [Pexels] Nenhuma imagem encontrada para '{keyword}'")
                return _mock_imagem_broll(keyword)
        else:
            print(f"⚠️ [Pexels] Erro {response.status_code}: {response.text[:100]}")
            return _mock_imagem_broll(keyword)
            
    except Exception as e:
        print(f"❌ [Pexels] Erro buscando imagem: {e}")
        return _mock_imagem_broll(keyword)


def _mock_imagem_broll(keyword: str) -> Optional[Dict]:
    """
    Retorna uma imagem placeholder quando a API falha ou não está configurada.
    Usa picsum.photos como serviço de placeholder.
    """
    # Gera um ID baseado na keyword para consistência
    seed = sum(ord(c) for c in keyword) % 1000
    
    return {
        "id": f"mock_{seed}",
        "url_original": f"https://picsum.photos/seed/{seed}/1080/1920",
        "url_large": f"https://picsum.photos/seed/{seed}/1080/1920",
        "url_medium": f"https://picsum.photos/seed/{seed}/800/1200",
        "url_small": f"https://picsum.photos/seed/{seed}/400/600",
        "url_portrait": f"https://picsum.photos/seed/{seed}/1080/1920",
        "url_landscape": f"https://picsum.photos/seed/{seed}/1920/1080",
        "fotografo": "Placeholder (Picsum)",
        "largura": 1080,
        "altura": 1920,
        "keyword": keyword,
        "mock": True
    }


def baixar_imagem_para_cache(url: str, diretorio_cache: str = "uploads/broll") -> Optional[str]:
    """
    Baixa imagem para diretório local e retorna caminho.
    """
    os.makedirs(diretorio_cache, exist_ok=True)
    
    # Gera nome de arquivo baseado na URL
    nome_arquivo = f"broll_{hash(url) % 1000000}.jpg"
    caminho_local = os.path.join(diretorio_cache, nome_arquivo)
    
    # Se já existe, retorna direto
    if os.path.exists(caminho_local):
        return caminho_local
    
    try:
        response = _session.get(url, timeout=30, stream=True)
        if response.status_code == 200:
            with open(caminho_local, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"✅ [Pexels] Imagem baixada: {caminho_local}")
            return caminho_local
    except Exception as e:
        print(f"❌ [Pexels] Erro baixando imagem: {e}")
    
    return None
