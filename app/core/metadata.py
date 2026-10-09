import os
import sys
import re
import time
import json
import logging
import threading
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List

logger = logging.getLogger("mediafinder.metadata")

def get_posters_dir() -> Path:
    """Retorna o diretório de cache local para os pôsteres dos filmes."""
    if sys.platform == "win32":
        base_dir = os.getenv("APPDATA") or str(Path.home())
    else:
        base_dir = os.getenv("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    posters_path = Path(base_dir) / "MediaFinder" / "posters"
    posters_path.mkdir(parents=True, exist_ok=True)
    return posters_path

def clean_movie_title(raw_name: str) -> Tuple[str, Optional[int]]:
    """
    Limpa o nome do arquivo para otimizar a busca no IMDb:
    Remove extensoes, resolucao (1080p, 4k), rip tags (bluray, web-dl),
    idiomas (dublado, dual), simbolos e extrai o ano de lancamento se presente.
    """
    name = re.sub(r"\.[a-zA-Z0-9]+$", "", raw_name)
    name = re.sub(r"@[a-zA-Z0-9_-]+", " ", name)
    name = re.sub(r"\[.*?\]|\(.*?\)", " ", name)
    name = re.sub(r"[\._-]+", " ", name)

    year_match = re.search(r"\b(19\d\d|20\d\d)\b", name)
    year = int(year_match.group(1)) if year_match else None
    name = re.sub(r"\b(19\d\d|20\d\d)\b", " ", name)

    keywords = [
        r"\b1080p\b", r"\b720p\b", r"\b4k\b", r"\b2160p\b", r"\b480p\b",
        r"\bbluray\b", r"\bbdrip\b", r"\bwebrip\b", r"\bweb-dl\b", r"\bdvdrip\b",
        r"\bvhsrip\b", r"\bhdrip\b", r"\bbrrip\b", r"\bcam\b",
        r"\bdublado\b", r"\blegendado\b", r"\bdual\b", r"\bnacional\b",
        r"\bx264\b", r"\bx265\b", r"\bhevc\b", r"\bavc\b", r"\baac\b",
        r"\bac3\b", r"\b5\.1\b", r"\b7\.1\b"
    ]
    for kw in keywords:
        name = re.sub(kw, " ", name, flags=re.IGNORECASE)

    clean = " ".join(name.split()).strip()
    return clean or raw_name, year

def translate_parental_rating(rated: Optional[str]) -> str:
    """Converte as classificações etárias americanas (MPAA) para padrão brasileiro."""
    if not rated or rated.upper() in ["N/A", "NOT RATED", "UNRATED"]:
        return "Livre"
    r = rated.upper().strip()
    if r in ["G", "TV-G", "TV-Y", "PASSED", "APPROVED"]:
        return "Livre"
    if r in ["PG", "TV-PG", "TV-Y7"]:
        return "10+"
    if r in ["PG-13", "TV-14"]:
        return "14+"
    if r in ["R", "TV-MA", "NC-17"]:
        return "16+"
    return rated

class MediaMetadataService:
    """Gerencia consultas ao IMDb, enriquecimento de capas e cache local de pôsteres."""

    _instance = None
    _lock = threading.Lock()

    def __init__(self, db=None):
        self.db = db
        self.posters_dir = get_posters_dir()
        self._bg_thread = None
        self._stop_event = threading.Event()

    @classmethod
    def get_instance(cls, db=None):
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls(db)
            elif db and cls._instance.db is None:
                cls._instance.db = db
            return cls._instance

    def fetch_from_network(self, raw_title: str) -> Optional[Dict[str, Any]]:
        """
        Consulta o IMDb via sugestão oficial (sem API key necessária)
        e enriquece com OMDb (nota oficial, sinopse, classificação).
        """
        clean_title, year = clean_movie_title(raw_title)
        query = urllib.parse.quote(clean_title.lower())
        imdb_url = f"https://v3.sg.media-imdb.com/suggestion/x/{query}.json"

        try:
            req = urllib.request.Request(
                imdb_url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            )
            with urllib.request.urlopen(req, timeout=6) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            logger.debug(f"Falha ao consultar IMDb suggestion para '{clean_title}': {e}")
            return None

        items = data.get("d", [])
        if not items:
            return None

        best_match = None
        for item in items:
            qid = item.get("qid") or item.get("q")
            item_year = item.get("y")
            if year and item_year and abs(item_year - year) <= 1:
                best_match = item
                break
            if not best_match and qid in ["movie", "feature", "tvSeries", "tvMiniSeries"]:
                best_match = item

        if not best_match:
            best_match = items[0]

        imdb_id = best_match.get("id")
        imdb_title = best_match.get("l")
        imdb_year = best_match.get("y") or year
        actors = best_match.get("s", "")
        poster_info = best_match.get("i", {})
        poster_url = poster_info.get("imageUrl") if isinstance(poster_info, dict) else None

        result: Dict[str, Any] = {
            "imdb_id": imdb_id,
            "title": clean_title,
            "original_title": imdb_title,
            "year": imdb_year,
            "rating": None,
            "votes": None,
            "runtime": None,
            "genre": None,
            "rated": "Livre",
            "plot": None,
            "director": None,
            "actors": actors,
            "poster_url": poster_url,
            "poster_local": None,
            "backdrop_url": poster_url
        }

        if imdb_id:
            try:
                omdb_url = f"https://www.omdbapi.com/?i={imdb_id}&apikey=trilogy"
                req_omdb = urllib.request.Request(omdb_url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req_omdb, timeout=6) as resp_omdb:
                    omdb_data = json.loads(resp_omdb.read().decode("utf-8"))
                if omdb_data.get("Response") == "True":
                    try:
                        result["rating"] = float(omdb_data.get("imdbRating", 0.0))
                    except (ValueError, TypeError):
                        pass
                    result["votes"] = omdb_data.get("imdbVotes")
                    result["runtime"] = omdb_data.get("Runtime")
                    result["genre"] = omdb_data.get("Genre")
                    result["rated"] = translate_parental_rating(omdb_data.get("Rated"))
                    result["plot"] = omdb_data.get("Plot")
                    result["director"] = omdb_data.get("Director")
                    if omdb_data.get("Actors") and omdb_data.get("Actors") != "N/A":
                        result["actors"] = omdb_data.get("Actors")
                    if not result["poster_url"] and omdb_data.get("Poster") != "N/A":
                        result["poster_url"] = omdb_data.get("Poster")
            except Exception as e:
                logger.debug(f"Aviso ao consultar OMDb para {imdb_id}: {e}")

        return result

    def download_poster(self, file_id: int, poster_url: str) -> Optional[str]:
        """Baixa o pôster e salva no disco local para carregamento instantâneo."""
        if not poster_url or not poster_url.startswith("http"):
            return None

        local_file = self.posters_dir / f"{file_id}.jpg"
        if local_file.exists() and local_file.stat().st_size > 1024:
            return f"/api/media/{file_id}/poster"

        try:
            req = urllib.request.Request(
                poster_url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                content = resp.read()
                if len(content) > 1024:
                    with open(local_file, "wb") as f:
                        f.write(content)
                    return f"/api/media/{file_id}/poster"
        except Exception as e:
            logger.debug(f"Falha ao baixar pôster para file_id {file_id}: {e}")
            return None
        return None

    def get_or_fetch(self, file_id: int, file_name: str, force: bool = False) -> Optional[Dict[str, Any]]:
        """Retorna metadados do cache ou busca da rede e armazena em cache."""
        if not self.db:
            return None

        if not force:
            cached = self.db.get_media_metadata(file_id)
            if cached:
                return cached

        data = self.fetch_from_network(file_name)
        if not data:
            clean_title, year = clean_movie_title(file_name)
            data = {
                "imdb_id": None,
                "title": clean_title,
                "original_title": clean_title,
                "year": year,
                "rating": None,
                "votes": None,
                "runtime": None,
                "genre": "Filme",
                "rated": "Livre",
                "plot": None,
                "director": None,
                "actors": None,
                "poster_url": None,
                "poster_local": None,
                "backdrop_url": None
            }
        else:
            if data.get("poster_url"):
                local_rel = self.download_poster(file_id, data["poster_url"])
                data["poster_local"] = local_rel

        self.db.save_media_metadata(file_id, data)
        return self.db.get_media_metadata(file_id)

    def start_background_enricher(self):
        """Inicia thread em segundo plano que processa vídeos sem metadados gradualmente."""
        if self._bg_thread and self._bg_thread.is_alive():
            return

        def _worker():
            logger.info("Iniciando varredura em segundo plano de metadados do IMDb...")
            while not self._stop_event.is_set():
                if not self.db:
                    time.sleep(2)
                    continue

                missing = self.db.get_video_files_missing_metadata(limit=10)
                if not missing:
                    time.sleep(15)
                    continue

                for item in missing:
                    if self._stop_event.is_set():
                        break
                    file_id = item["id"]
                    file_name = item["name"]
                    try:
                        self.get_or_fetch(file_id, file_name)
                    except Exception as e:
                        logger.debug(f"Erro ao enriquecer {file_name}: {e}")
                    time.sleep(0.8)

        self._stop_event.clear()
        self._bg_thread = threading.Thread(target=_worker, name="IMDbEnricherThread", daemon=True)
        self._bg_thread.start()

    def stop_background_enricher(self):
        self._stop_event.set()
