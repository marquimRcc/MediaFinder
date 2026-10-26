import os
import sys
import time
import socket
import logging
import mimetypes
import uuid
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
import threading
import urllib.parse

from PySide6.QtCore import QObject, Signal

logger = logging.getLogger("MediaFinder.Streamer")

EXTRA_MIME_TYPES = {
    ".mp4": "video/mp4",
    ".m4v": "video/mp4",
    ".mkv": "video/x-matroska",
    ".webm": "video/webm",
    ".avi": "video/x-msvideo",
    ".mov": "video/quicktime",
    ".ts": "video/mp2t",
    ".mp3": "audio/mpeg",
    ".m4a": "audio/mp4",
    ".aac": "audio/aac",
    ".ogg": "audio/ogg",
    ".flac": "audio/flac",
    ".wav": "audio/wav",
    ".vtt": "text/vtt; charset=utf-8",
    ".srt": "text/plain; charset=utf-8",
}


def convert_srt_to_vtt(srt_path: str, vtt_path: str) -> bool:
    """Converte legenda .srt para formato WebVTT com detecção automática de encoding (UTF-8, Windows-1252, ISO-8859-1)."""
    try:
        with open(srt_path, "rb") as f:
            raw = f.read()

        text = None
        for enc in ("utf-8", "windows-1252", "iso-8859-1", "cp1252", "latin-1"):
            try:
                text = raw.decode(enc)
                break
            except UnicodeDecodeError:
                continue

        if text is None:
            text = raw.decode("utf-8", errors="replace")

        import re
        vtt_content = "WEBVTT\n\n" + re.sub(r"(\d{2}:\d{2}:\d{2}),(\d{3})", r"\1.\2", text)
        with open(vtt_path, "w", encoding="utf-8") as f:
            f.write(vtt_content)
        return True
    except Exception as e:
        logger.debug(f"Erro ao converter legenda para VTT: {e}")
        return False


def get_local_ip() -> str:
    """Retorna o IP da máquina na rede local (LAN)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def get_tailscale_ip() -> Optional[str]:
    """Retorna o endereço IP IPv4 do Tailscale na máquina local se ativo (faixa 100.64.0.0/10)."""
    import shutil
    import subprocess

    # 1. Tentar comando oficial tailscale CLI
    tailscale_bin = shutil.which("tailscale")
    if tailscale_bin:
        try:
            res = subprocess.run([tailscale_bin, "ip", "-4"], capture_output=True, text=True, timeout=1.5)
            if res.returncode == 0 and res.stdout.strip():
                ip = res.stdout.strip().splitlines()[0]
                if ip.startswith("100."):
                    return ip
        except Exception:
            pass

    # 2. Inspecionar interfaces de rede (tailscale0)
    try:
        res = subprocess.run(["ip", "-brief", "addr", "show", "tailscale0"], capture_output=True, text=True, timeout=1.5)
        if res.returncode == 0 and "100." in res.stdout:
            for part in res.stdout.split():
                if part.startswith("100."):
                    return part.split("/")[0]
    except Exception:
        pass

    return None


def get_tailscale_info() -> Dict[str, Any]:
    """Retorna o status completo de instalação e conexão do Tailscale no sistema local."""
    import shutil
    tailscale_bin = shutil.which("tailscale")
    ip = get_tailscale_ip()
    return {
        "installed": tailscale_bin is not None,
        "active": ip is not None,
        "ip": ip,
    }


WEB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web")


class RangeHTTPRequestHandler(BaseHTTPRequestHandler):
    """
    Handler HTTP com suporte a Range Requests (Status 206 Partial Content),
    cabeçalhos CORS, rotas de API REST e arquivos estáticos para o PWA Mobile.
    """

    def log_message(self, format, *args):
        pass

    def do_HEAD(self):
        self._dispatch_request(send_body=False)

    def do_GET(self):
        self._dispatch_request(send_body=True)

    def do_POST(self):
        self._handle_post_api()

    def do_OPTIONS(self):
        """Responde a requisições pre-flight CORS enviadas por navegadores e Smart TVs."""
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Range, Content-Type, Accept, Origin, Authorization")
        self.send_header("Access-Control-Allow-Methods", "GET, HEAD, POST, OPTIONS")
        self.send_header("Access-Control-Max-Age", "86400")
        self.end_headers()

    def _dispatch_request(self, send_body: bool = True):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        # 1. Rotas da API REST
        if path.startswith("/api/"):
            self._handle_get_api(path, parsed.query, send_body)
            return

        # 2. Transmissão de vídeo via token existente
        if path.startswith("/stream/"):
            self._process_media_stream(send_body)
            return

        # 3. Arquivos da aplicação Web / PWA Mobile
        self._serve_static_file(path, send_body)

    def _send_json_response(self, data: Any, status: int = 200, send_body: bool = True):
        import json
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        if send_body:
            try:
                self.wfile.write(payload)
            except (BrokenPipeError, ConnectionResetError):
                pass

    def _serve_static_file(self, req_path: str, send_body: bool):
        clean_path = req_path.split("?")[0].strip()
        if clean_path in ("", "/", "/index.html", "/mobile"):
            target_file = os.path.join(WEB_DIR, "index.html")
        elif clean_path == "/manifest.json":
            target_file = os.path.join(WEB_DIR, "manifest.json")
        elif clean_path == "/sw.js":
            target_file = os.path.join(WEB_DIR, "sw.js")
        elif clean_path.startswith("/static/"):
            rel = clean_path[len("/static/"):].lstrip("/")
            target_file = os.path.normpath(os.path.join(WEB_DIR, rel))
        else:
            rel = clean_path.lstrip("/")
            target_file = os.path.normpath(os.path.join(WEB_DIR, rel))

        # Proteção rigorosa contra Path Traversal
        real_web_dir = os.path.abspath(WEB_DIR)
        real_target = os.path.abspath(target_file)
        try:
            if os.path.commonpath([real_target, real_web_dir]) != real_web_dir or not os.path.isfile(real_target):
                self.send_error(404, "Arquivo não encontrado")
                return
        except ValueError:
            self.send_error(404, "Arquivo não encontrado")
            return

        _, ext = os.path.splitext(target_file)
        mime = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
            ".json": "application/json; charset=utf-8",
            ".svg": "image/svg+xml",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".ico": "image/x-icon",
        }.get(ext.lower(), "application/octet-stream")

        try:
            total_size = os.path.getsize(target_file)
            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(total_size))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()

            if send_body:
                with open(target_file, "rb") as f:
                    self.wfile.write(f.read())
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as e:
            logger.debug(f"Erro ao servir arquivo estático: {e}")

    def _handle_get_api(self, path: str, query_str: str, send_body: bool):
        media_server = getattr(self.server, "media_server", None)
        if not media_server or not media_server.db:
            self._send_json_response({"error": "Banco não inicializado"}, 500, send_body)
            return

        db = media_server.db
        query_params = urllib.parse.parse_qs(query_str)

        # GET /api/profiles
        if path == "/api/profiles":
            profiles = db.get_profiles()
            self._send_json_response(profiles, 200, send_body)
            return

        # GET /api/continue?profile=<id>
        if path == "/api/continue":
            profile_id = query_params.get("profile", ["marcos"])[0]
            items = db.get_continue_watching(profile_id, limit=10)
            self._send_json_response(items, 200, send_body)
            return

        # GET /api/catalog?profile=<id>&category=<cat>&query=<q>&is_kids=<0|1>&limit=<n>&offset=<o>
        if path == "/api/catalog":
            profile_id = query_params.get("profile", [""])[0]
            is_kids_param = query_params.get("is_kids", ["0"])[0]
            is_kids = (is_kids_param == "1") or (profile_id == "kids")
            cat = query_params.get("category", ["video"])[0]
            if not cat or cat.lower() == "all":
                cat = "video"
            query = query_params.get("query", [None])[0]
            limit = int(query_params.get("limit", [50])[0])
            offset = int(query_params.get("offset", [0])[0])

            items, total = db.get_mobile_catalog(is_kids=is_kids, category=cat, query=query, limit=limit, offset=offset)
            self._send_json_response({"items": items, "total": total}, 200, send_body)
            return

        # GET /api/media/<file_id>/stream
        import re
        m_stream = re.match(r"^/api/media/(\d+)/stream$", path)
        if m_stream:
            file_id = int(m_stream.group(1))
            with db._get_connection() as conn:
                row = conn.execute("SELECT path, category FROM files WHERE id = ?;", (file_id,)).fetchone()
            if not row or row["category"] not in ("video", "audio", "image") or not os.path.isfile(row["path"]):
                self._send_json_response({"error": "Mídia não encontrada ou formato não suportado"}, 404, send_body)
                return
            stream_url = media_server.register_file(row["path"])
            self.send_response(302)
            self.send_header("Location", stream_url)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            return

        # GET /api/media/<file_id>/poster ou /api/media/poster?id=<file_id>
        import re
        m_poster = re.match(r"^/api/media/(\d+)/poster$", path)
        poster_id = None
        if m_poster:
            poster_id = int(m_poster.group(1))
        elif path == "/api/media/poster":
            poster_id = int(query_params.get("id", [0])[0])

        if poster_id:
            from app.core.metadata import get_posters_dir
            posters_dir = get_posters_dir()
            local_poster = posters_dir / f"{poster_id}.jpg"
            if local_poster.exists() and local_poster.stat().st_size > 100:
                self.send_response(200)
                self.send_header("Content-Type", "image/jpeg")
                self.send_header("Cache-Control", "public, max-age=604800")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Content-Length", str(local_poster.stat().st_size))
                self.end_headers()
                if send_body:
                    with open(local_poster, "rb") as f:
                        self.wfile.write(f.read())
                return
            else:
                meta = db.get_media_metadata(poster_id)
                if meta and meta.get("poster_url"):
                    self.send_response(302)
                    self.send_header("Location", meta["poster_url"])
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    return
                self._send_json_response({"error": "Pôster não encontrado"}, 404, send_body)
                return

        # GET /api/media/details?id=<file_id>
        if path == "/api/media/details":
            file_id = int(query_params.get("id", [0])[0])
            if file_id <= 0:
                self._send_json_response({"error": "ID de arquivo inválido"}, 400, send_body)
                return

            from app.core.metadata import MediaMetadataService, clean_movie_title
            service = MediaMetadataService.get_instance(db)
            meta = db.get_media_metadata(file_id)
            if not meta:
                with db._get_connection() as conn:
                    row = conn.execute("SELECT name FROM files WHERE id = ?;", (file_id,)).fetchone()
                if row:
                    meta = service.get_or_fetch(file_id, row["name"])

            if not meta:
                with db._get_connection() as conn:
                    row = conn.execute("SELECT id, name, size, category FROM files WHERE id = ?;", (file_id,)).fetchone()
                if row:
                    c_title, yr = clean_movie_title(row["name"])
                    meta = {
                        "file_id": file_id,
                        "title": c_title,
                        "original_title": c_title,
                        "year": yr,
                        "rating": None,
                        "votes": None,
                        "runtime": None,
                        "genre": "Vídeo",
                        "rated": "Livre",
                        "plot": "Nenhuma sinopse disponível para este arquivo.",
                        "director": None,
                        "actors": None,
                        "poster_url": None,
                        "poster_local": None,
                        "backdrop_url": None
                    }

            details = dict(meta or {})
            profile_id = query_params.get("profile", ["marcos"])[0]
            prog = db.get_playback_progress(profile_id, file_id)
            if prog:
                pos = float(prog.get("position_seconds", 0.0))
                dur = float(prog.get("duration_seconds", 0.0))
                if pos >= 10.0 and (dur <= 0 or pos < dur * 0.95):
                    details["saved_position"] = pos
                    details["saved_duration"] = dur

            self._send_json_response(details, 200, send_body)
            return

        # GET /api/playback/progress?profile=<id>&file_id=<id>
        if path == "/api/playback/progress":
            profile_id = query_params.get("profile", ["marcos"])[0]
            file_id = int(query_params.get("file_id", [0])[0])
            prog = db.get_playback_progress(profile_id, file_id) if file_id > 0 else None
            self._send_json_response(prog or {}, 200, send_body)
            return

        # GET /api/pluto/channels
        if path == "/api/pluto/channels":
            from app.core.pluto_tv import PlutoTVService
            svc = PlutoTVService.get_instance()
            is_kids_param = query_params.get("is_kids", ["0"])[0]
            profile_id = query_params.get("profile", [""])[0]
            is_kids = (is_kids_param == "1") or (profile_id == "kids")
            cat = query_params.get("category", [None])[0]
            channels = svc.get_channels(category=cat, is_kids=is_kids)
            categories = svc.get_categories(is_kids=is_kids)
            self._send_json_response({"channels": channels, "categories": categories}, 200, send_body)
            return

        # GET /api/pluto/stream?id=<channel_id>
        if path == "/api/pluto/stream":
            channel_id = query_params.get("id", [""])[0]
            if not channel_id:
                self._send_json_response({"error": "ID de canal ausente"}, 400, send_body)
                return
            from app.core.pluto_tv import PlutoTVService
            svc = PlutoTVService.get_instance()
            self._send_json_response({
                "channel_id": channel_id,
                "stream_url": svc.get_stream_url(channel_id)
            }, 200, send_body)
            return

        # GET /api/iptv/channels
        if path == "/api/iptv/channels":
            from app.core.iptv import IPTVService
            svc = IPTVService.get_instance()
            cat = query_params.get("category", [None])[0]
            q = query_params.get("query", [None])[0]
            channels = svc.get_channels(category=cat, query=q)
            categories = svc.get_categories()
            self._send_json_response({"channels": channels, "categories": categories}, 200, send_body)
            return

        # GET /api/cast/devices
        if path == "/api/cast/devices":
            cast_mgr = TVCastManager.get_instance()
            cast_mgr.start_discovery()
            devices_list = []
            for d in cast_mgr.discovered_devices.values():
                devices_list.append({
                    "id": d.device_id,
                    "name": d.name,
                    "model": d.model,
                    "type": d.device_type,
                    "host": d.host
                })
            self._send_json_response(devices_list, 200, send_body)
            return

        # GET /api/cast/status
        if path == "/api/cast/status":
            cast_mgr = TVCastManager.get_instance()
            self._send_json_response({
                "is_casting": bool(cast_mgr.is_casting),
                "device": cast_mgr.active_cast_device.name if cast_mgr.active_cast_device else None,
                "file_name": os.path.basename(cast_mgr._current_file_path) if cast_mgr._current_file_path else None,
                "state": getattr(cast_mgr, "last_state", "IDLE"),
                "current_time": getattr(cast_mgr, "last_position", 0.0),
                "duration": getattr(cast_mgr, "last_duration", 0.0),
                "volume": getattr(cast_mgr, "last_volume", 1.0),
                "is_muted": getattr(cast_mgr, "last_muted", False),
                "audio_tracks": cast_mgr.get_audio_tracks(),
                "subtitle_tracks": cast_mgr.get_subtitle_tracks(),
                "active_audio_id": getattr(cast_mgr, "active_audio_id", 0),
                "active_subtitle_id": getattr(cast_mgr, "active_subtitle_id", 1)
            }, 200, send_body)
            return

        self._send_json_response({"error": "Endpoint não encontrado"}, 404, send_body)

    def _handle_post_api(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/")

        media_server = getattr(self.server, "media_server", None)
        if not media_server or not media_server.db:
            self._send_json_response({"error": "Servidor não inicializado"}, 500)
            return

        import json
        content_length = int(self.headers.get("Content-Length", 0))
        body = {}
        if content_length > 0:
            try:
                body = json.loads(self.rfile.read(content_length).decode("utf-8"))
            except Exception:
                self._send_json_response({"error": "JSON inválido"}, 400)
                return

        db = media_server.db
        cast_mgr = TVCastManager.get_instance()

        # POST /api/profiles/verify-pin
        if path == "/api/profiles/verify-pin":
            profile_id = body.get("profile_id", "")
            pin = body.get("pin", "")
            ok = db.verify_profile_pin(profile_id, pin)
            self._send_json_response({"success": ok})
            return

        # POST /api/profiles/set-pin
        if path == "/api/profiles/set-pin":
            profile_id = body.get("profile_id", "")
            new_pin = body.get("pin", "")
            current_pin = body.get("current_pin", "")
            profile = db.get_profile(profile_id)
            if not profile:
                self._send_json_response({"error": "Perfil não encontrado", "success": False}, 404)
                return
            # Se o perfil já possui PIN configurado, exige validação do PIN atual
            if profile.get("has_pin"):
                if not db.verify_profile_pin(profile_id, current_pin):
                    self._send_json_response({"error": "PIN atual incorreto", "success": False}, 403)
                    return
            ok = db.set_profile_pin(profile_id, new_pin)
            self._send_json_response({"success": ok})
            return

        # POST /api/playback/progress
        if path == "/api/playback/progress":
            profile_id = body.get("profile_id", "marcos")
            file_id = int(body.get("file_id", 0))
            pos = float(body.get("position", 0.0))
            dur = float(body.get("duration", 0.0))
            if file_id > 0:
                db.save_playback_progress(profile_id, file_id, pos, dur)
            self._send_json_response({"success": True})
            return

        # POST /api/cast/play
        if path == "/api/cast/play":
            device_id = body.get("device_id")
            file_id = int(body.get("file_id", 0))
            profile_id = body.get("profile_id", "marcos")

            device = cast_mgr.discovered_devices.get(device_id)
            if not device:
                for d in cast_mgr.discovered_devices.values():
                    if d.host == device_id:
                        device = d
                        break

            if not device:
                self._send_json_response({"success": False, "error": "Dispositivo TV não encontrado"}, 404)
                return

            channel_id = body.get("channel_id")
            stream_url = body.get("stream_url")
            channel_name = body.get("channel_name", "Pluto TV Ao Vivo")

            if channel_id or stream_url:
                from app.core.pluto_tv import PlutoTVService
                svc = PlutoTVService.get_instance()
                target_url = stream_url or svc.get_stream_url(channel_id)
                cast_mgr.cast_stream(device, target_url, title=channel_name)
                self._send_json_response({"success": True, "device": device.name, "live": True})
                return

            with db._get_connection() as conn:
                row = conn.execute("SELECT path FROM files WHERE id = ?;", (file_id,)).fetchone()
            if not row or not os.path.isfile(row["path"]):
                self._send_json_response({"success": False, "error": "Arquivo não encontrado"}, 404)
                return

            cast_mgr.active_profile_id = profile_id
            cast_mgr._current_file_id = file_id
            if not getattr(cast_mgr, "db", None):
                cast_mgr.db = db

            # Retoma de onde parou se houver progresso salvo e não for forçado do início
            start_time = float(body.get("start_time", -1.0))
            if start_time < 0 and file_id > 0:
                prog = db.get_playback_progress(profile_id, file_id)
                if prog:
                    pos = float(prog.get("position_seconds", 0.0))
                    dur = float(prog.get("duration_seconds", 0.0))
                    if pos >= 10.0 and (dur <= 0 or pos < dur * 0.95):
                        start_time = pos
            if start_time < 0:
                start_time = 0.0

            cast_mgr.cast_media(device, row["path"], start_time=start_time)
            self._send_json_response({"success": True, "device": device.name, "start_time": start_time})
            return

        # POST /api/cast/control
        if path == "/api/cast/control":
            action = body.get("action", "")
            val = body.get("value")

            if action == "play":
                cast_mgr.play()
            elif action == "pause":
                cast_mgr.pause()
            elif action == "seek" and val is not None:
                cast_mgr.seek(float(val))
            elif action == "volume" and val is not None:
                cast_mgr.set_volume(float(val))
            elif action == "stop":
                cast_mgr.stop_cast()
            elif action == "subtitle_track" and val is not None:
                cast_mgr.set_subtitle_track(int(val))
            elif action == "audio_track" and val is not None:
                cast_mgr.set_audio_track(int(val))

            self._send_json_response({"success": True, "action": action})
            return

        self._send_json_response({"error": "Endpoint não encontrado"}, 404)

    def _process_media_stream(self, send_body: bool = True):
        media_server = getattr(self.server, "media_server", None)
        if not media_server:
            self.send_error(500, "Servidor de mídia não configurado")
            return

        parsed_url = urllib.parse.urlparse(self.path)
        token = parsed_url.path.strip("/").split("/")[-1]

        file_path = media_server.get_file_path(token)
        if not file_path or not os.path.isfile(file_path):
            self.send_error(404, "Arquivo não encontrado")
            return

        try:
            total_size = os.path.getsize(file_path)
            _, ext = os.path.splitext(file_path)
            content_type = EXTRA_MIME_TYPES.get(ext.lower()) or mimetypes.guess_type(file_path)[0] or "video/mp4"

            range_header = self.headers.get("Range")
            start = 0
            end = total_size - 1

            if range_header and range_header.startswith("bytes="):
                range_str = range_header[6:].strip()
                try:
                    if range_str.startswith("-"):
                        suffix_len = int(range_str[1:])
                        start = max(0, total_size - suffix_len)
                        end = total_size - 1
                    else:
                        parts = range_str.split("-")
                        if parts[0]:
                            start = int(parts[0])
                        if len(parts) > 1 and parts[1]:
                            end = int(parts[1])
                except (ValueError, IndexError):
                    self.send_error(400, "Header Range inválido")
                    return

                # RFC 7233 / RFC 9110: Status 416 somente se 'start' ultrapassar o tamanho total
                if start >= total_size:
                    self.send_response(416)
                    self.send_header("Content-Range", f"bytes */{total_size}")
                    self.end_headers()
                    return

                # Clampa 'end' ao final do arquivo quando for maior que o tamanho
                if end >= total_size or end < start:
                    end = total_size - 1

                length = end - start + 1
                self.send_response(206)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Range", f"bytes {start}-{end}/{total_size}")
                self.send_header("Content-Length", str(length))
            else:
                length = total_size
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(length))

            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, HEAD, OPTIONS")
            self.end_headers()

            if not send_body:
                return

            chunk_size = 512 * 1024  # 512 KB por bloco para streaming fluido e sem engasgos em 1080p
            bytes_left = length
            with open(file_path, "rb") as f:
                f.seek(start)
                while bytes_left > 0:
                    to_read = min(chunk_size, bytes_left)
                    data = f.read(to_read)
                    if not data:
                        break
                    self.wfile.write(data)
                    bytes_left -= len(data)

        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as e:
            logger.debug(f"Erro ao transmitir arquivo HTTP: {e}")


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


class MediaStreamServer:
    """Servidor HTTP embutido para disponibilizar mídias na rede local para as TVs."""

    def __init__(self, port: int = 1745, db: Optional[Any] = None):
        self.desired_port = port
        self.host_ip = get_local_ip()
        self.db = db
        self.httpd: Optional[ThreadedHTTPServer] = None
        self.server_thread: Optional[threading.Thread] = None
        self.active_tokens: Dict[str, str] = {}
        self._path_to_token: Dict[str, str] = {}
        self.actual_port: int = port
        self._lock = threading.Lock()
        if self.db is None:
            try:
                from app.core.database import MediaDatabase
                self.db = MediaDatabase()
            except Exception:
                self.db = None

    def start(self) -> int:
        if self.httpd is not None:
            return self.actual_port

        self.host_ip = get_local_ip()

        try:
            self.httpd = ThreadedHTTPServer(("", self.desired_port), RangeHTTPRequestHandler)
            self.actual_port = self.httpd.server_address[1]
        except OSError:
            self.httpd = ThreadedHTTPServer(("", 0), RangeHTTPRequestHandler)
            self.actual_port = self.httpd.server_address[1]

        self.httpd.media_server = self
        self.server_thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.server_thread.start()
        logger.info(f"Servidor de streaming iniciado em http://{self.host_ip}:{self.actual_port}/")

        if self.db:
            try:
                from app.core.metadata import MediaMetadataService
                meta_svc = MediaMetadataService.get_instance(self.db)
                meta_svc.start_background_enricher()
            except Exception as e:
                logger.debug(f"Aviso ao iniciar serviço de metadados: {e}")

        return self.actual_port

    def stop(self):
        if self.httpd:
            self.httpd.shutdown()
            self.httpd.server_close()
            self.httpd = None
            self.server_thread = None
        self.clear_tokens()

    def register_file(self, file_path: str) -> str:
        """Gera um token criptograficamente seguro e aleatório (não previsível) para a mídia."""
        self.start()
        abs_p = os.path.abspath(file_path)
        with self._lock:
            token = self._path_to_token.get(abs_p)
            if not token:
                import secrets
                token = secrets.token_urlsafe(24)
                self.active_tokens[token] = abs_p
                self._path_to_token[abs_p] = token
        return f"http://{self.host_ip}:{self.actual_port}/stream/{token}"

    def unregister_file(self, file_path: str):
        """Remove o acesso HTTP de um arquivo específico."""
        abs_p = os.path.abspath(file_path)
        with self._lock:
            token = self._path_to_token.pop(abs_p, None)
            if token:
                self.active_tokens.pop(token, None)

    def clear_tokens(self):
        """Revoga todos os tokens ativos liberados na rede."""
        with self._lock:
            self.active_tokens.clear()
            self._path_to_token.clear()

    def get_file_path(self, token: str) -> Optional[str]:
        with self._lock:
            return self.active_tokens.get(token)


@dataclass
class TVDevice:
    name: str
    host: str
    model: str
    device_type: str  # "cast" ou "dlna"
    device_id: str
    raw_device: Any = None


class TVCastManager(QObject):
    """
    Controlador de descoberta e transmissão para Smart TVs (Chromecast, LG webOS, DLNA).
    """

    device_found = Signal(object)      # TVDevice
    discovery_finished = Signal(int)    # total_found
    cast_started = Signal(str, str)    # device_name, file_name
    cast_stopped = Signal()
    status_updated = Signal(str, float, float)  # state ('PLAYING', 'PAUSED', 'IDLE'), current_sec, duration_sec
    volume_updated = Signal(float, bool)        # volume (0.0 to 1.0), is_muted
    error_occurred = Signal(str)

    _instance: Optional["TVCastManager"] = None

    @classmethod
    def get_instance(cls, db: Optional[Any] = None) -> "TVCastManager":
        if cls._instance is None:
            cls._instance = TVCastManager(db=db)
        elif db is not None and getattr(cls._instance, 'db', None) is None:
            cls._instance.db = db
            cls._instance.stream_server.db = db
        return cls._instance

    def __init__(self, parent=None, db: Optional[Any] = None):
        super().__init__(parent)
        self.db = db
        if self.db is None:
            try:
                from app.core.database import MediaDatabase
                self.db = MediaDatabase()
            except Exception:
                self.db = None
        self.stream_server = MediaStreamServer(db=self.db)
        self.discovered_devices: Dict[str, TVDevice] = {}
        self.active_cast_device: Optional[TVDevice] = None
        self.active_chromecast = None
        self.is_casting: bool = False
        self.last_state: str = "IDLE"
        self.last_position: float = 0.0
        self.last_duration: float = 0.0
        self.last_volume: float = 1.0
        self.last_muted: bool = False
        self.active_profile_id: Optional[str] = None
        self._current_file_id: Optional[int] = None
        self._current_media_url: Optional[str] = None
        self._current_file_path: Optional[str] = None
        self._browser = None
        self._discovery_thread: Optional[threading.Thread] = None
        self._stop_polling = threading.Event()

    def start_discovery(self):
        """Inicia a busca por TVs na rede local em segundo plano."""
        if self._discovery_thread and self._discovery_thread.is_alive():
            return

        self._discovery_thread = threading.Thread(target=self._run_discovery, daemon=True)
        self._discovery_thread.start()

    def _run_discovery(self):
        found_count = 0
        try:
            import pychromecast

            arp_candidates = self._get_arp_candidates()

            # 1. Sondagem ultra-rápida HTTP/Eureka nos IPs conhecidos (exibe na UI em ~50ms)
            for ip in arp_candidates:
                try:
                    import urllib.request
                    import json
                    req = urllib.request.urlopen(f"http://{ip}:8008/setup/eureka_info?params=name,device_info", timeout=0.8)
                    data = json.loads(req.read().decode())
                    name = data.get("name") or f"TV ({ip})"
                    model_str = "LG webOS TV (Google Cast)" if "lg" in name.lower() or "webos" in name.lower() else "Chromecast (Google Cast)"
                    dev_id = ip
                    device = TVDevice(
                        name=name,
                        host=ip,
                        model=model_str,
                        device_type="cast",
                        device_id=dev_id,
                        raw_device=None
                    )
                    if dev_id not in self.discovered_devices:
                        self.discovered_devices[dev_id] = device
                        found_count += 1
                        self.device_found.emit(device)
                except Exception:
                    pass

            def on_device_found(chromecast):
                nonlocal found_count
                cast_info = chromecast.cast_info
                name = chromecast.name or cast_info.friendly_name or "TV Cast"
                dev_id = str(cast_info.host)
                model = cast_info.model_name or "Google Cast / Smart TV"

                if "webos" in model.lower() or "lg" in name.lower():
                    friendly_model = "LG webOS TV (Google Cast)"
                else:
                    friendly_model = f"{model} (Google Cast)"

                device = TVDevice(
                    name=name,
                    host=cast_info.host,
                    model=friendly_model,
                    device_type="cast",
                    device_id=dev_id,
                    raw_device=chromecast
                )

                if dev_id not in self.discovered_devices:
                    self.discovered_devices[dev_id] = device
                    found_count += 1
                    self.device_found.emit(device)
                else:
                    # Atualiza com a instância viva do pychromecast
                    self.discovered_devices[dev_id].raw_device = chromecast

            try:
                chromecasts, browser = pychromecast.get_chromecasts(
                    timeout=3.5,
                    known_hosts=arp_candidates if arp_candidates else None,
                    callback=on_device_found
                )
                self._browser = browser
                for cc in chromecasts:
                    on_device_found(cc)
            except Exception as e:
                logger.debug(f"Aviso durante get_chromecasts: {e}")

        except ImportError:
            logger.warning("pychromecast não instalado.")
        except Exception as e:
            logger.error(f"Erro na descoberta de TVs: {e}")

        self.discovery_finished.emit(len(self.discovered_devices))

    def stop_discovery(self):
        """Encerra a busca mDNS/CastBrowser e libera sockets de rede em segundo plano."""
        if self._browser:
            try:
                self._browser.stop_discovery()
            except Exception:
                pass
            self._browser = None

    def _get_arp_candidates(self) -> List[str]:
        candidates = []
        try:
            if os.path.exists("/proc/net/arp"):
                with open("/proc/net/arp", "r") as f:
                    lines = f.readlines()[1:]
                    for line in lines:
                        parts = line.split()
                        if len(parts) >= 4 and parts[3] != "00:00:00:00:00:00":
                            ip = parts[0]
                            s = socket.socket()
                            s.settimeout(0.15)
                            if s.connect_ex((ip, 8008)) == 0:
                                candidates.append(ip)
                            s.close()
        except Exception:
            pass
        return candidates

    def add_manual_device(self, host: str):
        host = host.strip()
        if not host:
            return

        def _worker():
            try:
                import pychromecast

                cc = pychromecast.get_chromecast_from_host(
                    (host, 8009, None, None, None),
                    timeout=3.0
                )
                if cc:
                    dev_id = f"manual_{host}"
                    device = TVDevice(
                        name=cc.name or f"TV ({host})",
                        host=host,
                        model=cc.model_name or "Smart TV / Cast",
                        device_type="cast",
                        device_id=dev_id,
                        raw_device=cc
                    )
                    self.discovered_devices[dev_id] = device
                    self.device_found.emit(device)
            except Exception as e:
                self.error_occurred.emit(f"Não foi possível conectar ao IP {host}: {e}")

        threading.Thread(target=_worker, daemon=True).start()

    def cast_media(self, device: TVDevice, file_path: str, start_time: float = 0.0):
        if not os.path.isfile(file_path):
            self.error_occurred.emit(f"Arquivo não encontrado: {file_path}")
            return

        def _cast_thread():
            try:
                self.active_cast_device = device
                self._current_file_path = file_path
                self.last_position = start_time
                file_name = os.path.basename(file_path)

                media_url = self.stream_server.register_file(file_path)
                self._current_media_url = media_url

                _, ext = os.path.splitext(file_path)
                mime = EXTRA_MIME_TYPES.get(ext.lower(), "video/mp4")

                cast_device = device.raw_device
                if cast_device is None:
                    import pychromecast
                    cast_device = pychromecast.get_chromecast_from_host(
                        (device.host, 8009, None, None, None),
                        timeout=5.0
                    )
                    device.raw_device = cast_device

                cast_device.wait()
                self.active_chromecast = cast_device

                import pychromecast
                if cast_device.app_id != pychromecast.APP_MEDIA_RECEIVER:
                    try:
                        cast_device.start_app(pychromecast.APP_MEDIA_RECEIVER)
                        cast_device.wait()
                        time.sleep(1.0)
                    except Exception as app_err:
                        logger.debug(f"Aviso ao iniciar APP_MEDIA_RECEIVER: {app_err}")

                # Detecta legendas correspondentes (.vtt ou .srt)
                base_no_ext, _ = os.path.splitext(file_path)
                sub_url = None
                vtt_candidate = base_no_ext + ".vtt"
                srt_candidate = base_no_ext + ".srt"

                if os.path.exists(vtt_candidate):
                    # Prioriza VTT já existente do usuário sem alterá-lo
                    sub_url = self.stream_server.register_file(vtt_candidate)
                elif os.path.exists(srt_candidate):
                    # Converte SRT para VTT em cache temporário isolado (nunca grava na pasta de mídia)
                    import tempfile
                    import hashlib
                    cache_dir = os.path.join(tempfile.gettempdir(), "MediaFinder_cache", "subtitles")
                    os.makedirs(cache_dir, exist_ok=True)
                    srt_hash = hashlib.sha256(srt_candidate.encode("utf-8")).hexdigest()[:16]
                    cached_vtt = os.path.join(cache_dir, f"{srt_hash}.vtt")
                    if convert_srt_to_vtt(srt_candidate, cached_vtt):
                        sub_url = self.stream_server.register_file(cached_vtt)

                mc = cast_device.media_controller
                mc.play_media(
                    media_url,
                    content_type=mime,
                    title=file_name,
                    current_time=start_time if start_time > 0 else None,
                    stream_type="BUFFERED",
                    subtitles=sub_url,
                    subtitles_lang="pt-BR"
                )
                mc.block_until_active(timeout=8.0)

                # Busca a posição inicial caso o receiver da Smart TV inicialize no tempo zero
                if start_time > 0:
                    try:
                        time.sleep(1.2)
                        mc.seek(start_time)
                    except Exception as seek_err:
                        logger.debug(f"Aviso ao buscar posição inicial na TV: {seek_err}")

                self.is_casting = True
                self.cast_started.emit(device.name, file_name)

                self._start_status_polling()

            except Exception as e:
                self.is_casting = False
                logger.error(f"Erro ao transmitir para TV: {e}")
                self.error_occurred.emit(f"Falha ao transmitir para a TV: {e}")

        threading.Thread(target=_cast_thread, daemon=True).start()

    def cast_stream(self, device: TVDevice, stream_url: str, title: str = "Pluto TV Ao Vivo"):
        """Transmite um fluxo de rede ao vivo (HLS / m3u8) diretamente para o dispositivo Cast."""
        def _cast_thread():
            try:
                self.active_cast_device = device
                self._current_file_path = title
                self.last_position = 0.0
                self._current_media_url = stream_url

                cast_device = device.raw_device
                if cast_device is None:
                    import pychromecast
                    cast_device = pychromecast.get_chromecast_from_host(
                        (device.host, 8009, None, None, None),
                        timeout=5.0
                    )
                    device.raw_device = cast_device

                cast_device.wait()
                self.active_chromecast = cast_device

                import pychromecast
                if cast_device.app_id != pychromecast.APP_MEDIA_RECEIVER:
                    try:
                        cast_device.start_app(pychromecast.APP_MEDIA_RECEIVER)
                        cast_device.wait()
                        time.sleep(1.0)
                    except Exception as app_err:
                        logger.debug(f"Aviso ao iniciar APP_MEDIA_RECEIVER: {app_err}")

                mc = cast_device.media_controller
                mc.play_media(
                    stream_url,
                    content_type="application/x-mpegURL",
                    title=title,
                    stream_type="LIVE"
                )
                mc.block_until_active(timeout=8.0)

                self.is_casting = True
                self.cast_started.emit(device.name, title)
                self._start_status_polling()

            except Exception as e:
                self.is_casting = False
                logger.error(f"Erro ao transmitir stream para TV: {e}")
                self.error_occurred.emit(f"Falha ao transmitir stream para a TV: {e}")

        threading.Thread(target=_cast_thread, daemon=True).start()

    def _start_status_polling(self):
        self._stop_polling.clear()

        def _poll():
            while not self._stop_polling.is_set() and self.is_casting:
                try:
                    if self.active_chromecast and self.active_chromecast.media_controller:
                        mc = self.active_chromecast.media_controller
                        try:
                            mc.update_status()
                        except Exception:
                            pass
                        status = mc.status
                        if status:
                            state = status.player_state or "IDLE"
                            curr = float(status.current_time or 0.0)
                            dur = float(status.duration or 0.0)
                            self.last_state = state
                            self.last_position = curr
                            self.last_duration = dur
                            self.status_updated.emit(state, curr, dur)

                            # Sincroniza progresso com o banco se houver perfil ativo
                            if curr > 0 and self.active_profile_id and self._current_file_id and self.db:
                                try:
                                    self.db.save_playback_progress(self.active_profile_id, self._current_file_id, curr, dur)
                                except Exception:
                                    pass

                            # Encerramento natural do vídeo quando termina
                            if state == "IDLE" and curr > 0 and (dur > 0 and curr >= dur - 3.0):
                                self.is_casting = False
                                self.last_state = "IDLE"
                                if self._current_file_path and self.stream_server:
                                    self.stream_server.revoke_token(self._current_file_path)
                                self.cast_stopped.emit()
                                break

                        cast_status = self.active_chromecast.status
                        if cast_status:
                            vol = float(cast_status.volume_level or 1.0)
                            muted = bool(cast_status.volume_muted)
                            self.last_volume = vol
                            self.last_muted = muted
                            self.volume_updated.emit(vol, muted)

                except Exception:
                    pass
                time.sleep(1.0)

        t = threading.Thread(target=_poll, daemon=True)
        t.start()

    def play(self):
        self.last_state = "PLAYING"
        if self.active_chromecast and self.active_chromecast.media_controller:
            try:
                self.active_chromecast.media_controller.play()
            except Exception as e:
                logger.debug(f"Erro ao reproduzir: {e}")

    def pause(self):
        self.last_state = "PAUSED"
        if self.active_chromecast and self.active_chromecast.media_controller:
            try:
                self.active_chromecast.media_controller.pause()
            except Exception as e:
                logger.debug(f"Erro ao pausar: {e}")

    def stop_cast(self):
        self._stop_polling.set()
        if self.active_chromecast and self.active_chromecast.media_controller:
            try:
                self.active_chromecast.media_controller.stop()
            except Exception:
                pass
        self.is_casting = False
        self.last_state = "IDLE"
        if self._current_file_path and self.stream_server:
            self.stream_server.revoke_token(self._current_file_path)
        self.cast_stopped.emit()

    def seek(self, position_seconds: float):
        self.last_position = position_seconds
        if self.active_chromecast and self.active_chromecast.media_controller:
            try:
                self.active_chromecast.media_controller.seek(position_seconds)
            except Exception as e:
                logger.debug(f"Erro ao avançar: {e}")

    def set_volume(self, level: float):
        self.last_volume = max(0.0, min(1.0, level))
        if self.active_chromecast:
            try:
                self.active_chromecast.set_volume(self.last_volume)
            except Exception as e:
                logger.debug(f"Erro ao mudar volume: {e}")

    def toggle_mute(self):
        if self.active_chromecast and self.active_chromecast.status:
            try:
                curr = bool(self.active_chromecast.status.volume_muted)
                self.last_muted = not curr
                self.active_chromecast.set_volume_muted(not curr)
            except Exception as e:
                logger.debug(f"Erro ao mutar: {e}")

    def get_subtitle_tracks(self) -> List[Dict[str, Any]]:
        tracks = [{"id": -1, "name": "Desativada"}]
        if self._current_file_path:
            base_no_ext, _ = os.path.splitext(self._current_file_path)
            folder = os.path.dirname(self._current_file_path)
            base_name = os.path.basename(base_no_ext)
            
            # Legenda padrão do filme
            if os.path.exists(base_no_ext + ".srt") or os.path.exists(base_no_ext + ".vtt"):
                tracks.append({"id": 1, "name": "Português (PT-BR)"})

            # Procura legendas adicionais na pasta
            try:
                for fname in os.listdir(folder):
                    if fname.startswith(base_name) and fname.endswith((".srt", ".vtt")) and fname not in (base_name + ".srt", base_name + ".vtt"):
                        lower = fname.lower()
                        if "en" in lower or "eng" in lower:
                            tracks.append({"id": 2, "name": "Inglês (EN)"})
                        elif "es" in lower or "spa" in lower:
                            tracks.append({"id": 3, "name": "Espanhol (ES)"})
                        else:
                            clean_tag = fname[len(base_name):].rstrip(".srt").rstrip(".vtt").strip("._- ")
                            tracks.append({"id": len(tracks) + 1, "name": clean_tag.title() or "Faixa Extra"})
            except Exception:
                pass

        if self.active_chromecast and self.active_chromecast.media_controller:
            status = self.active_chromecast.media_controller.status
            if status and getattr(status, "subtitle_tracks", None):
                for t in status.subtitle_tracks:
                    t_id = t.get("trackId")
                    t_name = t.get("name") or t.get("language") or f"Legenda {t_id}"
                    if not any(x["id"] == t_id for x in tracks):
                        tracks.append({"id": t_id, "name": t_name})
        return tracks

    def get_audio_tracks(self) -> List[Dict[str, Any]]:
        return [
            {"id": 0, "name": "Áudio Principal / 5.1 Dublado"},
            {"id": 1, "name": "Áudio 2 / Original"}
        ]

    def set_subtitle_track(self, track_id: int):
        self.active_subtitle_id = track_id
        if self.active_chromecast and self.active_chromecast.media_controller:
            mc = self.active_chromecast.media_controller
            try:
                if track_id == -1:
                    mc.disable_subtitle()
                else:
                    mc.enable_subtitle(track_id)
            except Exception as e:
                logger.debug(f"Erro ao alterar legenda: {e}")

    def set_audio_track(self, track_id: int):
        self.active_audio_id = track_id
        if self.active_chromecast and self.active_chromecast.media_controller:
            mc = self.active_chromecast.media_controller
            try:
                active_ids = [track_id]
                if getattr(self, "active_subtitle_id", -1) != -1:
                    active_ids.append(self.active_subtitle_id)
                mc._send_command({"type": "EDIT_TRACKS_INFO", "activeTrackIds": active_ids}, None)
            except Exception as e:
                logger.debug(f"Erro ao alternar áudio: {e}")

