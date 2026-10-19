import os
import sys
import re
import json
import time
import logging
import threading
import urllib.request
import urllib.parse
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from PySide6.QtCore import QObject, Signal

logger = logging.getLogger("mediafinder.iptv")

# Fontes comunitárias pré-configuradas e testadas
IPTV_SOURCES: List[Dict[str, Any]] = [
    {
        "id": "saimo_br",
        "name": "🇧🇷 Saimo TV Brasil (~400 canais curados)",
        "desc": "Canais abertos, notícias, esportes, variedades e filmes com múltiplas fontes e alta estabilidade",
        "url": "https://saimo-canais.pages.dev/catalogo.txt",
        "format": "saimo",
    },
    {
        "id": "github_br",
        "name": "🇧🇷 GitHub iptv-org (Brasil - ~260 canais únicos)",
        "desc": "Emissoras abertas, esportes, notícias e entretenimento de todo o Brasil (sem duplicar Pluto TV)",
        "url": "https://iptv-org.github.io/iptv/countries/br.m3u",
        "format": "m3u",
    },
    {
        "id": "github_movies",
        "name": "🎬 GitHub iptv-org (Filmes 24h - ~460 canais únicos)",
        "desc": "Transmissões contínuas de longas-metragens e cinema",
        "url": "https://iptv-org.github.io/iptv/categories/movies.m3u",
        "format": "m3u",
    },
    {
        "id": "fast_essentials",
        "name": "⚡ Canais FAST (Essenciais - 12 canais)",
        "desc": "Canais de alta estabilidade (Record News, Cultura, Futura, etc.)",
        "url": None,
        "format": "fast",
    },
    {
        "id": "custom",
        "name": "➕ Minha Lista M3U (Personalizada)",
        "desc": "Lista personalizada configurada pelo usuário (URL web ou arquivo local)",
        "url": None,
        "format": "auto",
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

# Cidades, capitais, estados e termos regionais para desduplicação profunda
CITIES_AND_REGIONS = set([
    # Estados e siglas
    "acre", "ac", "alagoas", "al", "amapa", "ap", "amazonas", "am", "bahia", "ba",
    "ceara", "ce", "distrito federal", "df", "brasilia", "espirito santo", "es",
    "goias", "go", "maranhao", "ma", "mato grosso", "mt", "mato grosso do sul", "ms",
    "minas gerais", "minas", "mg", "para", "pa", "paraiba", "pb", "parana", "pr",
    "pernambuco", "pe", "piaui", "pi", "rio de janeiro", "rj", "rio",
    "rio grande do norte", "rn", "rio grande do sul", "rs", "rondonia", "ro",
    "roraima", "rr", "santa catarina", "sc", "sao paulo", "sp", "sergipe", "se", "tocantins", "to",
    # Capitais e grandes cidades
    "aracaju", "belem", "belo horizonte", "boa vista", "campo grande", "cuiaba", "curitiba",
    "florianopolis", "fortaleza", "goiania", "joao pessoa", "macapa", "maceio", "manaus",
    "natal", "palmas", "porto alegre", "porto", "alegre", "porto velho", "recife", "rio branco", "salvador",
    "sao luis", "teresina", "vitoria",
    # Cidades do interior e polos regionais
    "campinas", "santos", "sorocaba", "ribeirao preto", "sao jose dos campos", "sao jose do rio preto",
    "uberlandia", "juiz de fora", "montes claros", "governador valadares", "ipatinga", "uberaba",
    "londrina", "maringa", "ponta grossa", "cascavel", "foz do iguacu", "joinville", "blumenau",
    "caxias do sul", "pelotas", "santa maria", "petropolis", "niteroi", "campos dos goytacazes",
    "nova friburgo", "volta redonda", "marica", "cabo frio", "angra dos reis",
    "anapolis", "rio verde", "itumbiara", "jatai", "dourados", "rondonopolis", "sinop",
    "feira de santana", "vitoria da conquista", "itabuna", "ilheus", "juazeiro", "petrolina",
    "caruaru", "campina grande", "mossoro", "sobral", "juazeiro do norte", "imperatriz",
    "caxias", "parnaiba", "santarem", "maraba", "parauapebas", "castanhal", "ji parana",
    "cachoeiro", "cachoeiro de itapemirim", "sao mateus", "mateus", "colatina", "linhares", "guarapari",
    "jundiai", "piracicaba", "bauru", "franca", "taubate", "limeira", "araras", "rio claro",
    "aracatuba", "marilia", "presidente prudente", "sao carlos", "araraquara", "birigui",
    "passo fundo", "pelotas", "bage", "uruguaiana", "chapeco", "criciuma", "itajaí", "brusque",
    "oeste", "leste", "norte", "sul", "interior", "capital", "litoral", "metropolitana", "vale",
    "central", "centro", "nacional", "regional", "noroeste", "sudoeste", "nordeste", "sudeste"
])

GENERIC_PREFIXES = {"tv", "canal", "rede", "radio"}


class IPTVSignalBridge(QObject):
    channels_updated = Signal(str)


class IPTVService:
    """
    Serviço central de canais FAST e IPTV ao vivo.
    Fornece catálogo multi-fontes com parser resiliente, desduplicação profunda por cidade
    e cache local persistente por fonte.
    """

    _instance = None

    def __init__(self):
        self.signals = IPTVSignalBridge()
        self._cache_dir = self._get_cache_dir()
        self._settings_file = self._cache_dir / "iptv_settings.json"
        self._active_source_id = "saimo_br"
        self._custom_url_or_path = ""
        self._custom_name = "Minha Lista M3U"
        self._channels: List[Dict[str, Any]] = []
        self._bg_threads: Dict[str, threading.Thread] = {}

        self._load_settings()
        self._load_channels_for_source(self._active_source_id, allow_network=False)

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
                self._active_source_id = data.get("active_source", "saimo_br")
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
        cache_file = self._get_cache_file(source_id)
        # Se force_refresh ou sem cache prévio, não bloqueia a interface
        allow_net = not force_refresh and cache_file.exists()
        self._load_channels_for_source(source_id, force_refresh=force_refresh, allow_network=allow_net)
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

            if "canal:" in m3u_text[:4000].lower():
                parsed_channels = self.parse_saimo_catalog(m3u_text, default_source=name)
            else:
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
                try:
                    self.signals.channels_updated.emit("custom")
                except Exception:
                    pass

            return True, len(parsed_channels), f"Lista carregada com sucesso ({len(parsed_channels)} canais encontrados)!"
        except Exception as e:
            logger.error(f"Erro ao carregar lista customizada: {e}")
            return False, 0, f"Erro ao acessar lista: {str(e)}"

    def _get_cache_file(self, source_id: str) -> Path:
        return self._cache_dir / f"iptv_cache_{source_id}.json"

    def _start_background_fetch(self, source_id: str):
        """Inicia download em segundo plano para não congelar a interface."""
        existing = self._bg_threads.get(source_id)
        if existing and existing.is_alive():
            return

        def _worker():
            self._fetch_remote_source(source_id)

        t = threading.Thread(target=_worker, name=f"IPTVFetch-{source_id}", daemon=True)
        self._bg_threads[source_id] = t
        t.start()

    def _fetch_remote_source(self, source_id: str) -> bool:
        """Executa a requisição remota de uma lista IPTV."""
        source_meta = next((s for s in IPTV_SOURCES if s["id"] == source_id), None)
        if not source_meta or not source_meta.get("url"):
            return False

        try:
            url = source_meta["url"]
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "MediaFinder/2.0 (Mozilla/5.0 compatible)"}
            )
            with urllib.request.urlopen(req, timeout=12) as resp:
                text = resp.read().decode("utf-8", errors="ignore")

            if source_meta.get("format") == "saimo" or source_id == "saimo_br" or "canal:" in text[:4000].lower():
                parsed = self.parse_saimo_catalog(text, default_source="Geral")
            else:
                parsed = self.parse_m3u_content(text, default_source="Geral")
            if parsed:
                self._save_cache_for_source(source_id, parsed)
                if self._active_source_id == source_id:
                    self._channels = parsed
                logger.info(f"IPTVService: {len(parsed)} canais baixados e salvos para {source_id}.")
                try:
                    self.signals.channels_updated.emit(source_id)
                except Exception:
                    pass
                return True
        except Exception as e:
            logger.error(f"Erro ao baixar lista remota {source_id}: {e}")
        return False

    def _load_channels_for_source(self, source_id: str, force_refresh: bool = False, allow_network: bool = True):
        """Carrega os canais da fonte informada, buscando do cache ou baixando."""
        cache_file = self._get_cache_file(source_id)

        # 1. Se não for refresh forçado e o cache existir, carrega do disco
        if not force_refresh and cache_file.exists():
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list) and len(data) > 0:
                    filtered_data = [
                        c for c in data
                        if not self.is_pluto_tv_channel(c.get("name", ""), c.get("stream_url", ""), c.get("id", ""))
                    ]
                    self._channels = self.deduplicate_channels(filtered_data)
                    logger.info(f"IPTVService: {len(self._channels)} canais carregados do cache para {source_id}.")
                    return
            except Exception as e:
                logger.warning(f"Erro ao ler cache de {source_id}: {e}")

        # 2. Fonte: FAST Essenciais
        if source_id == "fast_essentials":
            self._channels = self.deduplicate_channels(list(DEFAULT_FAST_CHANNELS))
            self._save_cache_for_source(source_id, self._channels)
            return

        # 3. Fonte: Customizada
        if source_id == "custom":
            if self._custom_url_or_path:
                if os.path.exists(self._custom_url_or_path):
                    ok, count, _ = self.set_custom_source(self._custom_url_or_path, self._custom_name)
                    if ok:
                        return
                elif allow_network:
                    ok, count, _ = self.set_custom_source(self._custom_url_or_path, self._custom_name)
                    if ok:
                        return
                else:
                    self._channels = self.deduplicate_channels(list(DEFAULT_FAST_CHANNELS))
                    threading.Thread(
                        target=lambda: self.set_custom_source(self._custom_url_or_path, self._custom_name),
                        daemon=True
                    ).start()
                    return
            self._channels = self.deduplicate_channels(list(DEFAULT_FAST_CHANNELS))
            return

        # 4. Fontes remotas da comunidade (github_br, github_movies, etc.)
        if not allow_network:
            if cache_file.exists():
                try:
                    with open(cache_file, "r", encoding="utf-8") as f:
                        cached_list = json.load(f)
                        self._channels = self.deduplicate_channels(cached_list)
                        self._start_background_fetch(source_id)
                        return
                except Exception:
                    pass
            self._channels = self.deduplicate_channels(list(DEFAULT_FAST_CHANNELS))
            self._start_background_fetch(source_id)
            return

        # 5. Se download síncrono for permitido
        success = self._fetch_remote_source(source_id)
        if not success:
            if cache_file.exists():
                try:
                    with open(cache_file, "r", encoding="utf-8") as f:
                        cached_list = json.load(f)
                        self._channels = self.deduplicate_channels(cached_list)
                        return
                except Exception:
                    pass
            self._channels = self.deduplicate_channels(list(DEFAULT_FAST_CHANNELS))

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

    @staticmethod
    def get_channel_quality_score(ch: Dict[str, Any]) -> int:
        """Calcula pontuação de qualidade/resolução do canal para priorizar versões HD e de melhor sinal."""
        name = (ch.get("name") or "").lower()
        cid = (ch.get("id") or "").lower()
        url = (ch.get("stream_url") or "").lower()
        score = 500

        # Resolução numérica explícita (ex: 1080p, 720p, 480p, 360p, 320p, etc.)
        match_res = re.search(r"\b(\d+)[pi]?\b", name)
        if match_res:
            val = int(match_res.group(1))
            if val in (2160, 1080, 720, 576, 540, 480, 360, 320, 240):
                score = val

        # Termos em nome, id ou url
        if re.search(r"\b(2160p|4k)\b", name) or "4k" in cid:
            score = max(score, 2160)
        elif re.search(r"\b1080p?\b", name) or "@fhd" in cid or "/1080" in url or "_1080" in url:
            score = max(score, 1080)
        elif re.search(r"\b720p?\b", name) or "@hd" in cid or "/720" in url or "_720" in url or re.search(r"\bhd\b", name):
            score = max(score, 720)
        elif re.search(r"\b(576p|540p)\b", name):
            score = max(score, 540)
        elif re.search(r"\b(480p|sd)\b", name) or "@sd" in cid:
            score = max(score, 480)

        # Penalidades para streams instáveis ou restritos
        if "geo-blocked" in name:
            score -= 200
        if "not 24/7" in name:
            score -= 100

        # Prioridade para transmissões nacionais/oficiais em relação a repetidoras de cidades
        if re.search(r"\b(nacional|oficial|master|brasil|rede)\b", name):
            score += 30

        # Preferência secundária para HTTPS e presença de logotipo
        if url.startswith("https://"):
            score += 10
        if ch.get("logo"):
            score += 5

        return score

    @classmethod
    def get_canonical_channel_key(cls, ch: Dict[str, Any]) -> str:
        """Extrai a identidade canônica do canal removendo sufixos de cidade, estado e resolução."""
        name = (ch.get("name") or "").strip()
        # Remove sufixos de resolução
        clean = re.sub(r"\(\s*\d+\s*[pi]?\s*\)", "", name, flags=re.IGNORECASE)
        clean = re.sub(r"\((?:2160p|1080p|720p|480p|360p|240p|4k|sd|hd|fhd|1080i|576i|480i)\)", "", clean, flags=re.IGNORECASE)
        clean = re.sub(r"\[.*?\]", "", clean)
        clean = re.sub(r"\(brazil|\(brasil|\(português|\(portuguese\)", "", clean, flags=re.IGNORECASE)
        clean = re.sub(r"\s+", " ", clean).strip()
        cl = clean.lower()

        # Principais redes nacionais e marcas consolidadas com afiliadas/cidades
        if "globo" in cl and not any(x in cl for x in ["globonews", "globo news", "novelas", "globo rural", "globo esporte"]):
            return "rede_globo"
        if ("record" in cl or "recordtv" in cl) and not ("news" in cl):
            return "record_tv"
        if "sbt" in cl and not any(x in cl for x in ["news", "kids", "sports"]):
            return "sbt_nacional"
        if ("band" in cl or "bandeirantes" in cl) and not any(x in cl for x in ["news", "sports", "agro"]):
            return "band_nacional"
        if "cultura" in cl and not any(x in cl for x in ["educativa", "maranhao"]):
            return "tv_cultura"
        if re.search(r"\b(redetv|rede\s+tv)\b", cl):
            return "redetv"
        if re.search(r"\b(rede\s+cnt|cnt)\b", cl):
            return "rede_cnt"
        if re.search(r"\b(tv\s+brasil)\b", cl) and not any(x in cl for x in ["conectv", "rctv", "natal"]):
            return "tv_brasil"
        if re.search(r"\b(tv\s+camara|camara)\b", cl) and not any(x in cl for x in ["deputados"]):
            return "tv_camara"
        if re.search(r"\b(tv\s+assembleia|assembleia)\b", cl):
            return "tv_assembleia"
        if re.search(r"\b(tve)\b", cl):
            return "tve"
        if re.search(r"\b(tv\s+sim)\b", cl):
            return "tv_sim"
        if re.search(r"\b(tv\s+cidade\s+verde)\b", cl):
            return "tv_cidade_verde"
        if re.search(r"\b(tv\s+diario)\b", cl):
            return "tv_diario"
        if re.search(r"\b(tv\s+difusora)\b", cl):
            return "tv_difusora"
        if re.search(r"\b(catve)\b", cl):
            return "catve"
        if re.search(r"\b(tv\s+birigui|birigui)\b", cl):
            return "tv_birigui"
        if re.search(r"\b(unitv)\b", cl):
            return "unitv"
        if re.search(r"\b(tv\s+petropolis)\b", cl) or ("petropolis" in cl and "tv" in cl):
            return "tv_petropolis"
        if re.search(r"\b(tv\s+sul)\b", cl):
            return "tv_sul"

        # Regra profunda para variantes com nome de cidade/estado/região no final
        words = [w for w in re.split(r"[^\w]+", cl) if w]
        stripped = list(words)
        while stripped and (stripped[-1] in CITIES_AND_REGIONS or stripped[-1] in {"de", "do", "da", "dos", "das"}):
            stripped.pop()

        if len(stripped) == 1 and stripped[0] in GENERIC_PREFIXES:
            return "_".join(words)

        if stripped:
            return "_".join(stripped)

        # Se possuir ID tvg-id sem sufixo de qualidade
        cid = (ch.get("id") or "").split("@")[0].lower()
        if cid and not cid.startswith("iptv_") and not cid.startswith("fast_"):
            return cid

        return re.sub(r"[^\w\s]", "", cl).strip()

    @classmethod
    def sanitize_stream_url(cls, url: str) -> str:
        """Converte streams Xtream de .ts para manifesto .m3u8 para maior estabilidade."""
        url = url.strip()
        if url.endswith(".ts") and "/live/" in url:
            return url[:-3] + ".m3u8"
        return url

    @classmethod
    def deduplicate_channels(cls, channels: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove canais duplicados mantendo sempre a versão com maior resolução/qualidade e unindo fallbacks."""
        from collections import defaultdict
        groups = defaultdict(list)
        for ch in channels:
            key = cls.get_canonical_channel_key(ch)
            groups[key].append(ch)

        deduped = []
        for key, ch_list in groups.items():
            if len(ch_list) > 1:
                ch_list.sort(key=cls.get_channel_quality_score, reverse=True)
                best_ch = dict(ch_list[0])
                merged_urls = list(best_ch.get("stream_urls") or ([best_ch.get("stream_url")] if best_ch.get("stream_url") else []))
                merged_meta = list(best_ch.get("sources_meta") or [])
                for other in ch_list[1:]:
                    other_urls = other.get("stream_urls") or ([other.get("stream_url")] if other.get("stream_url") else [])
                    for u in other_urls:
                        if u and u not in merged_urls:
                            merged_urls.append(u)
                    other_meta = other.get("sources_meta") or []
                    for m in other_meta:
                        if m.get("url") and not any(x.get("url") == m["url"] for x in merged_meta):
                            merged_meta.append(m)

                best_ch["stream_urls"] = merged_urls
                best_ch["sources_meta"] = merged_meta
                if len(merged_urls) > 1:
                    best_ch["summary"] = f"Transmissão ao vivo • {len(merged_urls)} fontes disponíveis • Categoria: {best_ch.get('category', 'Geral')}."
                deduped.append(best_ch)
            else:
                ch = dict(ch_list[0])
                if not ch.get("stream_urls"):
                    ch["stream_urls"] = [ch["stream_url"]] if ch.get("stream_url") else []
                if not ch.get("sources_meta"):
                    ch["sources_meta"] = [{"url": ch["stream_url"]}] if ch.get("stream_url") else []
                deduped.append(ch)
        return deduped

    def get_channels(self, category: Optional[str] = None, query: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retorna os canais da lista ativa filtrados e desduplicados (HD preferido, sem Pluto TV)."""
        result = [
            c for c in self._channels
            if not self.is_pluto_tv_channel(c.get("name", ""), c.get("stream_url", ""), c.get("id", ""))
        ]
        result = self.deduplicate_channels(result)

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
        """Retorna lista única e ordenada das categorias dos canais ativos desduplicados."""
        cats = set()
        deduped = self.deduplicate_channels(self._channels)
        for ch in deduped:
            if self.is_pluto_tv_channel(ch.get("name", ""), ch.get("stream_url", ""), ch.get("id", "")):
                continue
            cat = ch.get("category")
            if cat:
                cats.add(cat.strip())
        return sorted(list(cats))

    @classmethod
    def normalize_category_static(cls, raw_cat: str, default: str = "Geral") -> str:
        """Traduz e padroniza títulos de grupos M3U ou catálogos em categorias legíveis em português."""
        if not raw_cat or not raw_cat.strip():
            return default

        parts = [p.strip() for p in raw_cat.split(";") if p.strip()]
        for part in parts:
            part_lower = part.lower()
            if part_lower in CATEGORY_TRANSLATION_MAP:
                return CATEGORY_TRANSLATION_MAP[part_lower]

        first = parts[0]
        return first[:1].upper() + first[1:]

    def normalize_category(self, raw_cat: str, default: str = "Geral") -> str:
        """Compatibilidade de instância para tradução de categoria."""
        return self.normalize_category_static(raw_cat, default=default)

    @classmethod
    def parse_saimo_catalog(
        cls,
        text: str,
        default_source: str = "Geral",
        exclude_pluto: bool = True
    ) -> List[Dict[str, Any]]:
        """Parser para catálogo Saimo TV (formato chave: valor com múltiplas fontes por canal)."""
        channels: List[Dict[str, Any]] = []
        current_ch: Optional[Dict[str, Any]] = None
        current_source: Optional[Dict[str, Any]] = None

        def _finish_channel():
            nonlocal current_ch, current_source
            if not current_ch:
                return
            if current_source:
                current_ch["sources"].append(current_source)
                current_source = None

            raw_name = current_ch.get("name", "").strip()
            sources = current_ch.get("sources", [])
            valid_sources = [s for s in sources if s.get("url") and s["url"].startswith(("http://", "https://"))]

            if not raw_name or not valid_sources:
                current_ch = None
                return

            stream_urls = []
            sources_meta = []
            for s in valid_sources:
                clean_url = cls.sanitize_stream_url(s["url"])
                if clean_url not in stream_urls:
                    stream_urls.append(clean_url)
                    s_meta = dict(s)
                    s_meta["url"] = clean_url
                    sources_meta.append(s_meta)

            if not stream_urls:
                current_ch = None
                return

            primary_url = stream_urls[0]
            ch_id = f"saimo_{re.sub(r'[^a-zA-Z0-9_]', '', raw_name.lower())}"

            if exclude_pluto and cls.is_pluto_tv_channel(raw_name, primary_url, ch_id):
                current_ch = None
                return

            raw_cat = current_ch.get("category") or default_source
            cat = cls.normalize_category_static(raw_cat, default=default_source)
            logo = current_ch.get("logo", "")

            channels.append({
                "id": ch_id,
                "name": raw_name,
                "number": len(channels) + 1,
                "category": cat,
                "logo": logo,
                "stream_url": primary_url,
                "stream_urls": stream_urls,
                "sources_meta": sources_meta,
                "summary": f"Transmissão ao vivo • {len(stream_urls)} fontes disponíveis • Categoria: {cat}.",
                "country": "BR"
            })
            current_ch = None

        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            if ":" not in line:
                continue

            key, _, val = line.partition(":")
            key = key.strip().lower()
            val = val.strip()

            if key == "canal":
                _finish_channel()
                current_ch = {
                    "name": val,
                    "category": default_source,
                    "logo": "",
                    "sources": []
                }
                current_source = None
            elif current_ch is not None:
                if key in ("categoria", "group", "grupo"):
                    current_ch["category"] = val
                elif key == "logo":
                    current_ch["logo"] = val
                elif key == "fonte":
                    if current_source:
                        current_ch["sources"].append(current_source)
                    current_source = {
                        "url": val,
                        "qualidade": "",
                        "referer": "",
                        "agente": "",
                        "chave": "",
                        "nome": ""
                    }
                elif current_source is not None:
                    if key in ("qualidade", "quality"):
                        current_source["qualidade"] = val
                    elif key in ("referer", "referrer"):
                        current_source["referer"] = val
                    elif key in ("agente", "user-agent", "agent"):
                        current_source["agente"] = val
                    elif key in ("chave", "clearkey", "key"):
                        current_source["chave"] = val
                    elif key in ("nome", "name"):
                        current_source["nome"] = val

        _finish_channel()
        return cls.deduplicate_channels(channels)

    def parse_m3u_content(self, m3u_text: str, default_source: str = "Geral", exclude_pluto: bool = True) -> List[Dict[str, Any]]:
        """Parser robusto e otimizado para listas M3U e M3UPlus com deduplicação automática."""
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
                    stream_url = self.sanitize_stream_url(line)
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
                        "stream_urls": [stream_url],
                        "sources_meta": [{"url": stream_url, "qualidade": ""}],
                        "summary": f"Transmissão ao vivo • Categoria: {group}.",
                        "country": current_meta.get("tvg-country", "")
                    })
                    current_meta = {}

        return self.deduplicate_channels(channels)

    def _parse_extinf_line(self, line: str) -> Dict[str, Any]:
        """Extrai tags chave-valor e título da linha #EXTINF."""
        meta: Dict[str, Any] = {}
        comma_idx = line.rfind(",")
        if comma_idx != -1:
            meta["title"] = line[comma_idx + 1:].strip()
            tags_part = line[8:comma_idx].strip()
        else:
            tags_part = line[8:].strip()

        pattern = re.compile(r"([\w-]+)=\"([^\"]*)\"")
        for match in pattern.finditer(tags_part):
            key = match.group(1).lower()
            val = match.group(2)
            meta[key] = val

        return meta

    def add_custom_m3u_url(self, url: str) -> int:
        """Compatibilidade: adiciona uma lista M3U externa como lista customizada."""
        ok, count, _ = self.set_custom_source(url)
        return count if ok else 0
