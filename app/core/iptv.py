import os
import sys
import json
import time
import logging
import urllib.request
import urllib.parse
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger("mediafinder.iptv")

# Catálogo padrão de canais FAST e abertos testados e de alta estabilidade
DEFAULT_FAST_CHANNELS: List[Dict[str, Any]] = [
    {
        "id": "fast_record_news",
        "name": "Record News",
        "number": 7,
        "category": "Notícias",
        "logo": "https://i.imgur.com/HZDRG0K.png",
        "stream_url": "https://rnw-rn.otteravision.com/rnw/rn/rnw_rn.m3u8",
        "summary": "Canal brasileiro de notícias 24 horas no ar com jornalismo e debates.",
        "country": "BR"
    },
    {
        "id": "fast_tv_cultura",
        "name": "TV Cultura",
        "number": 2,
        "category": "Cultura & Educação",
        "logo": "https://images.pluto.tv/channels/62e010e6cd663f0007e57dc8/colorLogoPNG.png",
        "stream_url": "https://player-tvcultura.stream.uol.com.br/live/tvcultura.m3u8",
        "summary": "Emissora pública com programas culturais, documentários, infantis clássicos e jornalismo.",
        "country": "BR"
    },
    {
        "id": "fast_futura",
        "name": "Canal Futura",
        "number": 4,
        "category": "Cultura & Educação",
        "logo": "https://i.imgur.com/LgynEBC.png",
        "stream_url": "https://a.futuraplay.org/hls/futura/live.m3u8",
        "summary": "Conteúdo educativo, projetos sociais e documentários da Fundação Roberto Marinho.",
        "country": "BR"
    },
    {
        "id": "fast_tv_brasil",
        "name": "TV Brasil",
        "number": 1,
        "category": "Pública & Notícias",
        "logo": "https://i.imgur.com/noqGfuy.png",
        "stream_url": "https://ebc-hls-a-tvbrasil.akamaized.net/hls/live/2042125/tvbrasil/master.m3u8",
        "summary": "Emissora pública da EBC com jornalismo nacional, programas infantis e esportes.",
        "country": "BR"
    },
    {
        "id": "fast_rede_brasil",
        "name": "Rede Brasil de Televisão",
        "number": 9,
        "category": "Variedades & Clássicos",
        "logo": "https://upload.wikimedia.org/wikipedia/commons/d/d1/Marca_rede_brasil_rgb-color.png",
        "stream_url": "https://stmv1.srvif.com/rbctv/rbctv/playlist.m3u8",
        "summary": "Programação nostálgica com filmes de época, séries clássicas e desenhos animados.",
        "country": "BR"
    },
    {
        "id": "fast_tv_camara",
        "name": "TV Câmara",
        "number": 10,
        "category": "Pública & Notícias",
        "logo": "https://i.imgur.com/UpV2PRk.png",
        "stream_url": "https://stream3.camara.gov.br/tv1/manifest.m3u8",
        "summary": "Transmissão das sessões legislativas, debates e projetos da Câmara dos Deputados.",
        "country": "BR"
    },
    {
        "id": "fast_tv_senado",
        "name": "TV Senado",
        "number": 11,
        "category": "Pública & Notícias",
        "logo": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1a/Logo_da_TV_Senado.svg/640px-Logo_da_TV_Senado.svg.png",
        "stream_url": "https://video.senado.gov.br/live/tvsenado/playlist.m3u8",
        "summary": "Cobertura ao vivo das comissões e plenário do Senado Federal.",
        "country": "BR"
    },
    {
        "id": "fast_agrobrasil",
        "name": "AgroBrasil TV",
        "number": 3,
        "category": "Agronegócio",
        "logo": "https://upload.wikimedia.org/wikipedia/pt/6/60/Logo_AgroBrasilTV.jpg",
        "stream_url": "https://srv.painelcast.com:1936/agrobrasiltv/agrobrasiltv/playlist.m3u8",
        "summary": "Cotações agropecuárias, leilões, tecnologia rural e notícias do campo.",
        "country": "BR"
    },
    {
        "id": "fast_euronews_pt",
        "name": "Euronews (Português)",
        "number": 20,
        "category": "Notícias",
        "logo": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/62/Euronews_2016_logo.svg/640px-Euronews_2016_logo.svg.png",
        "stream_url": "https://euronews-euronews-portuguese-1-pt.samsung.wurl.tv/playlist.m3u8",
        "summary": "Noticiário internacional da Europa e do mundo em língua portuguesa.",
        "country": "EU"
    },
    {
        "id": "fast_free_movies_24h",
        "name": "24 Hour Free Movies",
        "number": 50,
        "category": "Filmes & Séries",
        "logo": "https://provider-static.plex.tv/epg/images/ott_channels/logos/24hrfreemovies_logo_dark.png",
        "stream_url": "https://epg.provider.plex.tv/library/parts/6a1610bebdf296985fd95603-5fd115bab7ef8d002dcf181d/?X-Plex-Token=tv-pYJbQx_8saNWwrbG5",
        "summary": "Canal contínuo de filmes clássicos de ação, suspense, comédia e faroeste.",
        "country": "US"
    },
    {
        "id": "fast_21_jump_street",
        "name": "21 Jump Street (Anjos da Lei)",
        "number": 51,
        "category": "Filmes & Séries",
        "logo": "https://provider-static.plex.tv/epg/cms/production/a93dc428-87b4-49ce-834c-94bcad531802/21JS_Logo_Dark.png",
        "stream_url": "https://epg.provider.plex.tv/library/parts/6a1610bebdf296985fd95603-66f6b947515e742745f5ca34/?X-Plex-Token=tv-pYJbQx_8saNWwrbG5",
        "summary": "Série clássica de investigação policial dos anos 80 e 90 com episódios 24h.",
        "country": "US"
    },
    {
        "id": "fast_retrocrush",
        "name": "RetroCrush Anime",
        "number": 60,
        "category": "Animes & Desenhos",
        "logo": "https://images.pluto.tv/channels/5f1710921e355700072b2ee6/colorLogoPNG.png",
        "stream_url": "https://epg.provider.plex.tv/library/parts/6a1610bebdf296985fd95603-5ea7f2f114e9f7003ff55848/?X-Plex-Token=tv-pYJbQx_8saNWwrbG5",
        "summary": "Animes clássicos das décadas de 70, 80 e 90 remasterizados em alta qualidade.",
        "country": "US"
    }
]


class IPTVService:
    """
    Serviço central de canais FAST e IPTV ao vivo.
    Fornece catálogo de canais confiáveis, leitura de listas M3U e cache offline.
    """

    _instance = None

    def __init__(self):
        self._cache_dir = self._get_cache_dir()
        self._cache_file = self._cache_dir / "iptv_cache.json"
        self._channels: List[Dict[str, Any]] = []
        self._load_channels()

    @classmethod
    def get_instance(cls) -> "IPTVService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _get_cache_dir(self) -> Path:
        if sys.platform == "win32":
            base = os.getenv("APPDATA") or str(Path.home())
        else:
            base = os.getenv("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
        cache_path = Path(base) / "MediaFinder"
        cache_path.mkdir(parents=True, exist_ok=True)
        return cache_path

    def _load_channels(self):
        """Carrega canais do cache ou inicializa com o catálogo padrão."""
        if self._cache_file.exists():
            try:
                with open(self._cache_file, "r", encoding="utf-8") as f:
                    cached_data = json.load(f)
                if isinstance(cached_data, list) and len(cached_data) > 0:
                    self._channels = cached_data
                    logger.info(f"IPTVService: {len(self._channels)} canais carregados do cache.")
                    return
            except Exception as e:
                logger.warning(f"Erro ao ler cache de IPTV: {e}")

        # Catálogo padrão inicial
        self._channels = list(DEFAULT_FAST_CHANNELS)
        self._save_cache()

    def _save_cache(self):
        try:
            with open(self._cache_file, "w", encoding="utf-8") as f:
                json.dump(self._channels, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Erro ao salvar cache de IPTV: {e}")

    def get_channels(self, category: Optional[str] = None, query: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retorna os canais filtrados por categoria e termo de pesquisa."""
        result = list(self._channels)

        if category and category.lower() not in ("all", "todos", "todas"):
            cat_clean = category.strip().lower()
            result = [c for c in result if (c.get("category") or "").strip().lower() == cat_clean]

        if query and query.strip():
            q_clean = query.strip().lower()
            result = [
                c for c in result
                if q_clean in (c.get("name") or "").lower()
                or q_clean in (c.get("category") or "").lower()
                or q_clean in (c.get("summary") or "").lower()
            ]

        # Ordenação: canais com número definido primeiro, depois alfabético
        result.sort(key=lambda x: (x.get("number") if x.get("number", 0) > 0 else 9999, x.get("name", "")))
        return result

    def get_categories(self) -> List[str]:
        """Retorna lista única e ordenada das categorias de canais."""
        cats = set()
        for ch in self._channels:
            cat = ch.get("category")
            if cat:
                cats.add(cat.strip())
        return sorted(list(cats))

    def parse_m3u_content(self, m3u_text: str, default_source: str = "Personalizado") -> List[Dict[str, Any]]:
        """Parser robusto para formato M3U / M3UPlus."""
        channels: List[Dict[str, Any]] = []
        current_meta: Dict[str, Any] = {}

        for line in m3u_text.splitlines():
            line = line.strip()
            if not line:
                continue

            if line.startswith("#EXTINF:"):
                current_meta = self._parse_extinf_line(line)
            elif not line.startswith("#") and (line.startswith("http://") or line.startswith("https://")):
                if current_meta:
                    stream_url = line
                    ch_id = current_meta.get("tvg-id") or f"iptv_{len(channels)+1}_{int(time.time())}"
                    name = current_meta.get("title") or current_meta.get("tvg-name") or f"Canal {len(channels)+1}"
                    logo = current_meta.get("tvg-logo") or ""
                    group = current_meta.get("group-title") or default_source
                    chno = 0
                    try:
                        chno = int(current_meta.get("tvg-chno") or 0)
                    except ValueError:
                        pass

                    channels.append({
                        "id": ch_id,
                        "name": name,
                        "number": chno,
                        "category": group,
                        "logo": logo,
                        "stream_url": stream_url,
                        "summary": f"Transmissão ao vivo via {group}.",
                        "country": current_meta.get("tvg-country", "")
                    })
                    current_meta = {}

        return channels

    def _parse_extinf_line(self, line: str) -> Dict[str, Any]:
        """Extrai tags chave-valor e título da linha #EXTINF."""
        meta: Dict[str, Any] = {}
        comma_idx = line.rfind(",")
        if comma_idx != -1:
            meta["title"] = line[comma_idx + 1:].strip()
            tags_part = line[8:comma_idx].strip()
        else:
            tags_part = line[8:].strip()

        import re
        pattern = re.compile(r"([\w-]+)=\"([^\"]*)\"")
        for match in pattern.finditer(tags_part):
            key = match.group(1).lower()
            val = match.group(2)
            meta[key] = val

        return meta

    def add_custom_m3u_url(self, url: str) -> int:
        """Baixa e incorpora uma lista M3U da web ao catálogo."""
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=12) as resp:
                text = resp.read().decode("utf-8", errors="ignore")
            new_channels = self.parse_m3u_content(text)
            if new_channels:
                existing_urls = {c["stream_url"] for c in self._channels}
                added = 0
                for ch in new_channels:
                    if ch["stream_url"] not in existing_urls:
                        self._channels.append(ch)
                        existing_urls.add(ch["stream_url"])
                        added += 1
                if added > 0:
                    self._save_cache()
                return added
        except Exception as e:
            logger.error(f"Erro ao carregar M3U de {url}: {e}")
        return 0
