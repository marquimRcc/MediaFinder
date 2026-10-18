import os
import sys
import time
import uuid
import json
import logging
import urllib.request
import urllib.parse
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger("MediaFinder.PlutoTV")

PLUTO_API_CHANNELS = "https://api.pluto.tv/v2/channels"
PLUTO_BOOT_URL = "https://boot.pluto.tv/v4/start"
PLUTO_PLAYOUT_BASE = "https://ipv4.pluto.tv/api/tn/video/playout/v2/stitch/hls/channel/{channel_id}/master.m3u8"

KIDS_CATEGORIES = {"infantil", "nickelodeon", "anime & geek", "desenhos"}

class PlutoTVService:
    """Serviço de integração com a API aberta e streams da Pluto TV."""

    _instance: Optional["PlutoTVService"] = None

    def __init__(self):
        self._cached_channels: List[Dict[str, Any]] = []
        self._last_fetch_time: float = 0.0
        self._cache_ttl_seconds: float = 3600.0  # Cache de 1 hora
        self._device_id: str = str(uuid.uuid4())
        self._session_token: str = ""
        self._token_fetch_time: float = 0.0
        self._token_ttl_seconds: float = 14400.0  # Cache de 4 horas para o JWT token
        self._cache_dir = self._get_cache_dir()
        self._cache_file = self._cache_dir / "pluto_channels_cache.json"
        self._load_disk_cache()

    def _get_cache_dir(self) -> Path:
        if sys.platform == "win32":
            base = os.getenv("APPDATA") or str(Path.home())
        else:
            base = os.getenv("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
        cache_path = Path(base) / "MediaFinder"
        cache_path.mkdir(parents=True, exist_ok=True)
        return cache_path

    def _load_disk_cache(self):
        if self._cache_file.exists():
            try:
                with open(self._cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list) and len(data) > 0:
                    self._cached_channels = data
                    self._last_fetch_time = self._cache_file.stat().st_mtime
                    logger.info(f"Pluto TV: {len(data)} canais carregados do cache em disco.")
            except Exception as e:
                logger.warning(f"Erro ao ler cache em disco da Pluto TV: {e}")

    @classmethod
    def get_instance(cls) -> "PlutoTVService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _get_session_token(self) -> str:
        """Obtém ou renova o JWT sessionToken via boot.pluto.tv."""
        now = time.time()
        if self._session_token and (now - self._token_fetch_time) < self._token_ttl_seconds:
            return self._session_token

        try:
            params = {
                "appName": "web",
                "appVersion": "5.0.0",
                "deviceVersion": "120.0.0",
                "deviceModel": "web",
                "deviceMake": "chrome",
                "deviceType": "web",
                "clientID": self._device_id,
                "clientModelNumber": "1.0.0",
                "serverSideAds": "false",
                "drmCapabilities": "widevine:L3",
                "appLaunchCount": "0"
            }
            url = f"{PLUTO_BOOT_URL}?{urllib.parse.urlencode(params)}"
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "application/json"
                }
            )
            with urllib.request.urlopen(req, timeout=8.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                token = data.get("sessionToken")
                if token:
                    self._session_token = token
                    self._token_fetch_time = now
                    logger.info("Pluto TV: Novo token JWT de sessão obtido com sucesso.")
                    return token
        except Exception as e:
            logger.error(f"Erro ao obter sessionToken da Pluto TV: {e}")

        return self._session_token or ""

    def get_stream_url(self, channel_id: str) -> str:
        """Gera a URL oficial de streaming autenticada com JWT playout v2."""
        token = self._get_session_token()
        base = PLUTO_PLAYOUT_BASE.format(channel_id=channel_id)
        if token:
            return f"{base}?jwt={token}"
        return base

    def get_channels(self, category: Optional[str] = None, is_kids: bool = False, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Retorna lista de canais da Pluto TV (com cache e suporte a filtros)."""
        now = time.time()
        if force_refresh or not self._cached_channels or (now - self._last_fetch_time) > self._cache_ttl_seconds:
            self._fetch_channels_from_api()

        channels = list(self._cached_channels)

        if is_kids:
            channels = [
                c for c in channels
                if (c.get("category") or "").strip().lower() in KIDS_CATEGORIES
                or "kids" in (c.get("name") or "").lower()
                or "junior" in (c.get("name") or "").lower()
            ]

        if category and category.strip().lower() not in ("all", "todos"):
            cat_lower = category.strip().lower()
            channels = [c for c in channels if (c.get("category") or "").strip().lower() == cat_lower]

        return channels

    def _fetch_channels_from_api(self):
        """Busca canais da API da Pluto TV e normaliza estrutura."""
        try:
            req = urllib.request.Request(
                PLUTO_API_CHANNELS,
                headers={
                    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "application/json"
                }
            )
            with urllib.request.urlopen(req, timeout=7.0) as resp:
                raw_data = json.loads(resp.read().decode("utf-8"))

            parsed_list = []
            for item in raw_data:
                ch_id = item.get("_id")
                if not ch_id:
                    continue

                logo_dict = item.get("colorLogoPNG") or item.get("solidLogoPNG")
                logo_url = logo_dict.get("path") if isinstance(logo_dict, dict) else ""

                thumb_dict = item.get("thumbnail") or item.get("tile")
                thumb_url = thumb_dict.get("path") if isinstance(thumb_dict, dict) else ""

                feat_dict = item.get("featuredImage")
                feat_url = feat_dict.get("path") if isinstance(feat_dict, dict) else ""

                parsed_list.append({
                    "id": ch_id,
                    "name": item.get("name") or "Canal Pluto TV",
                    "number": item.get("number") or 0,
                    "slug": item.get("slug") or "",
                    "category": item.get("category") or "Geral",
                    "summary": item.get("summary") or "",
                    "logo": logo_url,
                    "thumbnail": thumb_url or feat_url or logo_url,
                    "featured_image": feat_url or thumb_url or logo_url,
                    "stream_url": self.get_stream_url(ch_id)
                })

            parsed_list.sort(key=lambda x: (x["number"] if x["number"] > 0 else 9999, x["name"]))
            self._cached_channels = parsed_list
            self._last_fetch_time = time.time()
            logger.info(f"Pluto TV: {len(parsed_list)} canais carregados com sucesso.")
            try:
                with open(self._cache_file, "w", encoding="utf-8") as f:
                    json.dump(parsed_list, f, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.warning(f"Erro ao salvar cache em disco da Pluto TV: {e}")
        except Exception as e:
            logger.error(f"Erro ao consultar API da Pluto TV: {e}")
            if not self._cached_channels:
                self._cached_channels = []

    def get_categories(self, is_kids: bool = False) -> List[str]:
        """Retorna lista única e ordenada de categorias de canais."""
        channels = self.get_channels(is_kids=is_kids)
        categories = sorted(list(set(c["category"] for c in channels if c.get("category"))))
        return categories
