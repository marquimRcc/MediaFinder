import os
import sys
import json
import time
import logging
import urllib.request
import urllib.parse
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger("mediafinder.iptv")

# Fontes comunitárias pré-configuradas e testadas
IPTV_SOURCES: List[Dict[str, Any]] = [
    {
        "id": "github_br",
        "name": "🇧🇷 GitHub iptv-org (Brasil - ~290 canais)",
        "desc": "Emissoras abertas, esportes, notícias e entretenimento de todo o Brasil (sem duplicar Pluto TV)",
        "url": "https://iptv-org.github.io/iptv/countries/br.m3u",
    },
    {
        "id": "github_movies",
        "name": "🎬 GitHub iptv-org (Filmes 24h - ~550 canais)",
        "desc": "Transmissões contínuas de longas-metragens e cinema",
        "url": "https://iptv-org.github.io/iptv/categories/movies.m3u",
    },
    {
        "id": "fast_essentials",
        "name": "⚡ Canais FAST (Essenciais - 12 canais)",
        "desc": "Canais de alta estabilidade (Record News, Cultura, Futura, etc.)",
        "url": None,
    },
    {
        "id": "custom",
        "name": "➕ Minha Lista M3U (Personalizada)",
        "desc": "Lista personalizada configurada pelo usuário (URL web ou arquivo local)",
        "url": None,
    }
]

# Catálogo padrão de canais FAST essenciais de altíssima estabilidade
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

# Mapa de normalização e tradução para categorias amigáveis em português
CATEGORY_TRANSLATION_MAP = {
    "movies": "Filmes",
    "movie": "Filmes",
    "series": "Séries",
    "news": "Notícias",
    "sports": "Esportes",
    "sport": "Esportes",
    "animation": "Desenhos & Animes",
    "anime": "Desenhos & Animes",
    "kids": "Infantil",
    "music": "Música",
    "entertainment": "Entretenimento",
    "general": "Variedades",
    "documentary": "Documentários",
    "comedy": "Comédia",
    "classic": "Clássicos",
    "culture": "Cultura",
    "education": "Educação",
    "religious": "Religioso",
    "outdoor": "Natureza & Campo",
    "shop": "Compras",
    "business": "Negócios",
    "auto": "Automobilismo",
    "science": "Ciência",
    "undefined": "Geral",
    "other": "Outros"
}


class IPTVService:
    """
    Serviço central de canais FAST e IPTV ao vivo.
    Fornece catálogo multi-fontes (GitHub da comunidade e listas customizadas M3U),
    com parser resiliente e cache local persistente por fonte.
    """

    _instance = None

    def __init__(self):
        self._cache_dir = self._get_cache_dir()
        self._settings_file = self._cache_dir / "iptv_settings.json"
        self._active_source_id = "github_br"
        self._custom_url_or_path = ""
        self._custom_name = "Minha Lista M3U"
        self._channels: List[Dict[str, Any]] = []

        self._load_settings()
        self._load_channels_for_source(self._active_source_id)

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

    def _load_settings(self):
        """Carrega as configurações salvas de IPTV."""
        if self._settings_file.exists():
            try:
                with open(self._settings_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._active_source_id = data.get("active_source", "github_br")
                self._custom_url_or_path = data.get("custom_url_or_path", "")
                self._custom_name = data.get("custom_name", "Minha Lista M3U")
            except Exception as e:
                logger.warning(f"Erro ao ler configurações de IPTV: {e}")

    def _save_settings(self):
        """Persiste as configurações de IPTV."""
        try:
            with open(self._settings_file, "w", encoding="utf-8") as f:
                json.dump({
                    "active_source": self._active_source_id,
                    "custom_url_or_path": self._custom_url_or_path,
                    "custom_name": self._custom_name
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Erro ao salvar configurações de IPTV: {e}")

    def get_sources(self) -> List[Dict[str, Any]]:
        """Retorna as opções de listas disponíveis para exibição."""
        sources = []
        for src in IPTV_SOURCES:
            item = dict(src)
            if item["id"] == "custom" and self._custom_url_or_path:
                item["name"] = f"➕ {self._custom_name}"
            sources.append(item)
        return sources

    def get_active_source(self) -> str:
        return self._active_source_id

    def set_active_source(self, source_id: str, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Altera a fonte ativa e carrega seus canais."""
        self._active_source_id = source_id
        self._save_settings()
        self._load_channels_for_source(source_id, force_refresh=force_refresh)
        return self._channels

    def get_custom_config(self) -> Tuple[str, str]:
        """Retorna (url_ou_caminho, nome) da lista personalizada."""
        return self._custom_url_or_path, self._custom_name

    def set_custom_source(self, url_or_path: str, name: str = "Minha Lista M3U") -> Tuple[bool, int, str]:
        """Configura e valida uma lista personalizada (URL web ou arquivo local)."""
        url_or_path = url_or_path.strip()
        if not url_or_path:
            return False, 0, "URL ou caminho do arquivo não pode ser vazio."

        try:
            m3u_text = ""
            if os.path.exists(url_or_path):
                with open(url_or_path, "r", encoding="utf-8", errors="ignore") as f:
                    m3u_text = f.read()
            elif url_or_path.startswith("http://") or url_or_path.startswith("https://"):
                req = urllib.request.Request(
                    url_or_path,
                    headers={"User-Agent": "MediaFinder/2.0 (Mozilla/5.0 compatible)"}
                )
                with urllib.request.urlopen(req, timeout=15) as resp:
                    m3u_text = resp.read().decode("utf-8", errors="ignore")
            else:
                return False, 0, "Caminho de arquivo inválido ou protocolo não suportado (use http/https ou caminho local)."

            parsed_channels = self.parse_m3u_content(m3u_text, default_source=name)
            if not parsed_channels:
                return False, 0, "Nenhum canal com URL válida foi encontrado na lista M3U."

            self._custom_url_or_path = url_or_path
            self._custom_name = name or "Minha Lista M3U"
            self._save_settings()

            # Salva o cache da lista personalizada
            custom_cache = self._get_cache_file("custom")
            with open(custom_cache, "w", encoding="utf-8") as f:
                json.dump(parsed_channels, f, ensure_ascii=False, indent=2)

            if self._active_source_id == "custom":
                self._channels = parsed_channels

            return True, len(parsed_channels), f"Lista carregada com sucesso ({len(parsed_channels)} canais encontrados)!"
        except Exception as e:
            logger.error(f"Erro ao carregar lista customizada: {e}")
            return False, 0, f"Erro ao acessar lista: {str(e)}"

    def _get_cache_file(self, source_id: str) -> Path:
        return self._cache_dir / f"iptv_cache_{source_id}.json"

    def _load_channels_for_source(self, source_id: str, force_refresh: bool = False):
        """Carrega os canais da fonte informada, buscando do cache ou baixando."""
        cache_file = self._get_cache_file(source_id)

        # 1. Se não for refresh forçado e o cache existir, carrega do disco
        if not force_refresh and cache_file.exists():
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list) and len(data) > 0:
                    self._channels = [
                        c for c in data
                        if not self.is_pluto_tv_channel(c.get("name", ""), c.get("stream_url", ""), c.get("id", ""))
                    ]
                    logger.info(f"IPTVService: {len(self._channels)} canais carregados do cache para {source_id}.")
                    return
            except Exception as e:
                logger.warning(f"Erro ao ler cache de {source_id}: {e}")

        # 2. Fonte: FAST Essenciais
        if source_id == "fast_essentials":
            self._channels = list(DEFAULT_FAST_CHANNELS)
            self._save_cache_for_source(source_id, self._channels)
            return

        # 3. Fonte: Customizada
        if source_id == "custom":
            if self._custom_url_or_path:
                ok, count, _ = self.set_custom_source(self._custom_url_or_path, self._custom_name)
                if ok:
                    return
            # Se não houver custom configurada ainda, usa os FAST essenciais como fallback
            self._channels = list(DEFAULT_FAST_CHANNELS)
            return

        # 4. Fontes remotas da comunidade (github_br, github_movies, etc.)
        source_meta = next((s for s in IPTV_SOURCES if s["id"] == source_id), None)
        if source_meta and source_meta.get("url"):
            try:
                url = source_meta["url"]
                req = urllib.request.Request(
                    url,
                    headers={"User-Agent": "MediaFinder/2.0 (Mozilla/5.0 compatible)"}
                )
                with urllib.request.urlopen(req, timeout=12) as resp:
                    text = resp.read().decode("utf-8", errors="ignore")

                parsed = self.parse_m3u_content(text, default_source="Geral")
                if parsed:
                    self._channels = parsed
                    self._save_cache_for_source(source_id, self._channels)
                    logger.info(f"IPTVService: {len(self._channels)} canais baixados e salvos para {source_id}.")
                    return
            except Exception as e:
                logger.error(f"Erro ao baixar lista remota {source_id}: {e}")

        # Fallback se download falhar: tenta cache antigo ou essenciais
        if cache_file.exists():
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    self._channels = json.load(f)
                    return
            except Exception:
                pass

        self._channels = list(DEFAULT_FAST_CHANNELS)

    def _save_cache_for_source(self, source_id: str, channels: List[Dict[str, Any]]):
        try:
            cache_file = self._get_cache_file(source_id)
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(channels, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Erro ao salvar cache de {source_id}: {e}")

    def refresh_current_source(self) -> int:
        """Força a atualização da lista de canais da fonte ativa."""
        self.set_active_source(self._active_source_id, force_refresh=True)
        return len(self._channels)

    @staticmethod
    def is_pluto_tv_channel(name: str, stream_url: str, ch_id: str = "") -> bool:
        """Identifica se o canal pertence à Pluto TV para evitar duplicidade na aba IPTV."""
        nl = (name or "").lower()
        ul = (stream_url or "").lower()
        il = (ch_id or "").lower()
        return (
            "pluto" in nl
            or "pluto.tv" in ul
            or "plutotv" in ul
            or "jmp2.uk/plu-" in ul
            or "pluto" in il
        )

    def get_channels(self, category: Optional[str] = None, query: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retorna os canais da lista ativa filtrados por categoria e termo de pesquisa (excluindo Pluto TV)."""
        result = [
            c for c in self._channels
            if not self.is_pluto_tv_channel(c.get("name", ""), c.get("stream_url", ""), c.get("id", ""))
        ]

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
        """Retorna lista única e ordenada das categorias dos canais ativos."""
        cats = set()
        for ch in self._channels:
            if self.is_pluto_tv_channel(ch.get("name", ""), ch.get("stream_url", ""), ch.get("id", "")):
                continue
            cat = ch.get("category")
            if cat:
                cats.add(cat.strip())
        return sorted(list(cats))

    def normalize_category(self, raw_cat: str, default: str = "Geral") -> str:
        """Traduz e padroniza títulos de grupos M3U em categorias legíveis em português."""
        if not raw_cat or not raw_cat.strip():
            return default

        parts = [p.strip() for p in raw_cat.split(";") if p.strip()]
        for part in parts:
            part_lower = part.lower()
            if part_lower in CATEGORY_TRANSLATION_MAP:
                return CATEGORY_TRANSLATION_MAP[part_lower]

        first = parts[0]
        return first[:1].upper() + first[1:]

    def parse_m3u_content(self, m3u_text: str, default_source: str = "Geral", exclude_pluto: bool = True) -> List[Dict[str, Any]]:
        """Parser robusto e otimizado para listas M3U e M3UPlus."""
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
                    raw_name = current_meta.get("title") or current_meta.get("tvg-name") or f"Canal {len(channels)+1}"

                    # Exclui canais pertencentes à Pluto TV
                    if exclude_pluto and self.is_pluto_tv_channel(raw_name, stream_url, ch_id):
                        current_meta = {}
                        continue

                    logo = current_meta.get("tvg-logo") or ""
                    raw_group = current_meta.get("group-title") or default_source
                    group = self.normalize_category(raw_group, default=default_source)

                    chno = 0
                    try:
                        chno = int(current_meta.get("tvg-chno") or 0)
                    except ValueError:
                        pass

                    channels.append({
                        "id": ch_id,
                        "name": raw_name,
                        "number": chno,
                        "category": group,
                        "logo": logo,
                        "stream_url": stream_url,
                        "summary": f"Transmissão ao vivo • Categoria: {group}.",
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
        pattern = re.compile(r'([\w-]+)="([^"]*)"')
        for match in pattern.finditer(tags_part):
            key = match.group(1).lower()
            val = match.group(2)
            meta[key] = val

        return meta

    def add_custom_m3u_url(self, url: str) -> int:
        """Compatibilidade: adiciona uma lista M3U externa como lista customizada."""
        ok, count, _ = self.set_custom_source(url)
        return count if ok else 0
