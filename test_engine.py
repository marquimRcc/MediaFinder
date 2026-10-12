import os
import sys
import tempfile
import time
from pathlib import Path

# Suporte a caracteres UTF-8 no console Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Isola o ambiente de testes em diretório temporário para NUNCA tocar nas configurações reais do usuário
_test_tmp_dir = tempfile.TemporaryDirectory()
os.environ["XDG_CONFIG_HOME"] = os.path.join(_test_tmp_dir.name, "config")
os.environ["XDG_DATA_HOME"] = os.path.join(_test_tmp_dir.name, "share")
os.environ["APPDATA"] = os.path.join(_test_tmp_dir.name, "appdata")

from app.core.config import AppConfig
from app.core.database import MediaDatabase
from app.core.scanner import IndexWorker
from app.core.tv_schedule import TVScheduleManager
from app.utils.media_helpers import get_category_for_extension, format_file_size, get_drive_letter

def run_tests():
    print("Iniciando testes unitários e de integração (ambiente isolado)...")

    # 1. Teste de helpers
    assert get_category_for_extension(".mp4") == "video"
    assert get_category_for_extension(".PNG") == "image"
    assert get_category_for_extension(".mp3") == "audio"
    assert get_category_for_extension(".pdf") == "document"
    assert format_file_size(1024 * 1024 * 50) == "50.0 MB"
    print("✓ Media helpers validados.")

    # 2. Teste do Banco de Dados com SQLite em arquivo temporário
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        test_db_path = tmp.name

    try:
        db = MediaDatabase(test_db_path)
        
        # Inserção em lote
        test_files = [
            {
                "name": "filme_acao_2026.mp4",
                "path": "E:\\Midias\\Filmes\\filme_acao_2026.mp4",
                "parent_dir": "E:\\Midias\\Filmes",
                "extension": ".mp4",
                "category": "video",
                "size": 1024 * 1024 * 1500, # 1.5 GB
                "mtime": time.time(),
                "drive": "E:"
            },
            {
                "name": "foto_viagem.jpg",
                "path": "F:\\Midias\\Fotos\\foto_viagem.jpg",
                "parent_dir": "F:\\Midias\\Fotos",
                "extension": ".jpg",
                "category": "image",
                "size": 1024 * 1024 * 5, # 5 MB
                "mtime": time.time(),
                "drive": "F:"
            },
            {
                "name": "musica_rock.flac",
                "path": "H:\\Midias\\Musicas\\musica_rock.flac",
                "parent_dir": "H:\\Midias\\Musicas",
                "extension": ".flac",
                "category": "audio",
                "size": 1024 * 1024 * 30, # 30 MB
                "mtime": time.time(),
                "drive": "H:"
            }
        ]

        db.upsert_files_batch(test_files)
        
        # Teste de busca por termo
        results, total, size = db.search_files(query="acao")
        assert total == 1
        assert results[0]["name"] == "filme_acao_2026.mp4"

        # Teste de busca por categoria
        results, total, size = db.search_files(category="image")
        assert total == 1
        assert results[0]["name"] == "foto_viagem.jpg"

        # Teste de busca por drive
        results, total, size = db.search_files(drive="H:")
        assert total == 1
        assert results[0]["name"] == "musica_rock.flac"

        # Teste de estatísticas
        stats = db.get_stats()
        assert stats["total_files"] == 3
        assert "video" in stats["categories"]
        assert "E:" in stats["drives"]

        # Teste de sorteio aleatório (Modo Aleatório Rápido)
        rand_video = db.get_random_file(categories=["video"])
        assert rand_video is not None
        assert rand_video["category"] == "video"

        rand_folder = db.get_random_file(folders=["F:\\Midias\\Fotos"])
        assert rand_folder is not None
        assert rand_folder["name"] == "foto_viagem.jpg"

        subfolders = db.get_indexed_subfolders()
        assert len(subfolders) == 3

        # Teste do Modo TV (TVScheduleManager, canais sequenciais e customizados)
        tv_mgr = TVScheduleManager(db)
        assert len(tv_mgr.channels) >= 7
        tv_mgr.build_schedules_for_today()
        ch1 = tv_mgr.channels[0]
        assert len(ch1.schedule) > 0
        current_item = ch1.get_current_item()
        assert current_item is not None

        # Teste de get_files_for_channel
        ch_files = db.get_files_for_channel(categories=["video"], folders=["E:\\Midias\\Filmes"])
        assert len(ch_files) == 1
        assert ch_files[0]["name"] == "filme_acao_2026.mp4"

        # Teste de exclusão em lote
        deleted = db.delete_files_by_paths(["H:\\Midias\\Musicas\\musica_rock.flac"])
        assert deleted == 1
        stats_after = db.get_stats()
        assert stats_after["total_files"] == 2

        print("✓ Banco de dados, consultas SQLite/FTS, Modo Aleatório, Modo TV e Exclusão em Lote validados.")
    finally:
        try:
            if os.path.exists(test_db_path):
                os.remove(test_db_path)
        except Exception:
            pass

    # 3. Teste de Configuração
    config = AppConfig()
    config.add_search_history("teste_busca_01")
    assert "teste_busca_01" in config.get_search_history()
    tv_chans = config.get_tv_channels()
    assert len(tv_chans) >= 7
    assert any(c["mode"] == "sequential" for c in tv_chans)
    assert any(c["mode"] == "random" for c in tv_chans)

    # Teste de Grupos de Mídia Multi-HD
    groups = config.get_folder_groups()
    assert "Filmes" in groups
    assert "Séries" in groups
    resolved = config.resolve_channel_folders(folders=["D:\\Custom"], folder_groups=["Filmes"])
    assert "D:\\Custom" in resolved
    print("✓ Persistência de configuração, canais de TV e Grupos Multi-HD validada.")


    # 4. Validação e Instanciação de Todos os Componentes de UI
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)

    from app.ui.preview_panel import PreviewPanel
    from app.ui.tv_player_widget import TVPlayerWidget
    from app.ui.tv_mode_window import TVModeWindow
    from app.ui.channel_config_dialog import ChannelConfigDialog
    from app.ui.random_dialog import RandomMediaDialog
    from app.ui.settings_dialog import SettingsDialog
    from app.ui.main_window import MainWindow

    # 4.1 PreviewPanel
    p = PreviewPanel()
    p.set_file_data({"name": "test.jpg", "path": "c:\\test.jpg", "category": "image", "extension": ".jpg", "size": 100, "mtime": 0, "drive": "C:"})
    p.set_file_data(None)

    # 4.2 TVPlayerWidget com OSD e Transições
    tv_player = TVPlayerWidget()
    tv_player.load_media("c:\\dummy.mp4", "Dummy Live", 120, channel_number=1, channel_name="Cinema")
    tv_player.trigger_channel_transition(1, "Cinema")
    tv_player.show_channel_osd(2, "Séries & Animes", "Rick and Morty")
    tv_player.show_volume_osd(70)
    tv_player.set_volume_relative(+5)
    tv_player.set_volume_relative(-10)
    tv_player.toggle_mute()
    tv_player.toggle_mute()
    tv_player.cycle_audio_track()
    tv_player.cycle_subtitle_track()
    tv_player.set_audio_track(0)
    tv_player.set_subtitle_track(-1)
    tv_player.show_track_osd("ÁUDIO", "Português 5.1")
    tv_player.show_track_osd("LEGENDA", "Português")

    # 4.3 TVModeWindow e Diálogos com banco temporário
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as ui_tmp:
        ui_db_path = ui_tmp.name

    try:
        ui_db = MediaDatabase(ui_db_path)
        tv_window = TVModeWindow(ui_db, config)
        assert tv_window is not None
        tv_window._tune_number_direct(1)
        tv_window._next_channel()
        tv_window._prev_channel()
        tv_window.toggle_sidebar()
        tv_window.toggle_sidebar()
        tv_window.regenerate_all_schedules()

        # Teste de resolução de duração real no Modo TV
        if tv_window.current_playing_item:
            old_dur = tv_window.current_playing_item.duration_seconds
            tv_window._on_media_duration_resolved(tv_window.current_playing_item.file_path, 7200)

        # 4.4 ChannelConfigDialog
        ch_dialog = ChannelConfigDialog(config)
        assert ch_dialog is not None
        ch_dialog._add_new_channel()
        ch_dialog._move_channel_up()
        ch_dialog._move_channel_down()

        # 4.5 RandomMediaDialog
        rand_dialog = RandomMediaDialog(config, ui_db)
        assert rand_dialog is not None

        # 4.6 SettingsDialog
        sett_dialog = SettingsDialog(config, ui_db)
        assert sett_dialog is not None

        # 4.7 MainWindow e IndexWorker
        main_win = MainWindow()
        assert main_win is not None

        # Teste do IndexWorker com pasta temporária
        with tempfile.TemporaryDirectory() as scan_dir:
            sample_file = os.path.join(scan_dir, "sample_video.mp4")
            with open(sample_file, "wb") as f:
                f.write(b"0" * 1024)

            worker = IndexWorker(folders=[scan_dir], db=ui_db)
            worker.run() # Execução síncrona do worker para validar run()
            stats_worker = ui_db.get_stats()
            assert stats_worker["total_files"] >= 1

            # 4.8 Servidor de Streaming HTTP e Range Requests
            from app.core.streamer import MediaStreamServer, TVCastManager, TVDevice
            from app.ui.cast_dialog import CastDialog
            import urllib.request

            stream_server = MediaStreamServer(port=0)
            port = stream_server.start()
            assert port > 0
            url = stream_server.register_file(sample_file)
            assert f":{port}/stream/" in url

            # Teste GET normal
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req) as resp:
                assert resp.status == 200
                data = resp.read()
                assert len(data) == 1024

            # Teste Range Request (Status 206 Partial Content)
            range_req = urllib.request.Request(url, headers={"Range": "bytes=0-99"})
            with urllib.request.urlopen(range_req) as resp:
                assert resp.status == 206
                assert resp.headers.get("Content-Range") == "bytes 0-99/1024"
                assert len(resp.read()) == 100

            # Teste Range Request maior que o arquivo (RFC 7233 - deve clampar ao final sem dar erro 416)
            range_clamped = urllib.request.Request(url, headers={"Range": "bytes=0-99999"})
            with urllib.request.urlopen(range_clamped) as resp:
                assert resp.status == 206
                assert resp.headers.get("Content-Range") == "bytes 0-1023/1024"
                assert len(resp.read()) == 1024

            # Teste OPTIONS Request (pre-flight CORS)
            options_req = urllib.request.Request(url, method="OPTIONS")
            with urllib.request.urlopen(options_req) as resp:
                assert resp.status == 204
                assert "OPTIONS" in resp.headers.get("Access-Control-Allow-Methods", "")

            stream_server.stop()

            # 4.9 TVCastManager, CastDialog e RemoteAccessDialog
            cast_mgr = TVCastManager.get_instance()
            assert cast_mgr is not None
            cast_dialog = CastDialog(sample_file)
            assert cast_dialog is not None
            assert cast_dialog.list_devices is not None

            from app.ui.remote_dialog import RemoteAccessDialog
            rem_dialog = RemoteAccessDialog()
            assert rem_dialog is not None
            assert rem_dialog.url.startswith("http://")
            assert rem_dialog.lbl_qr is not None
            rem_dialog._copy_url()
            assert rem_dialog.btn_copy.text() == "✓ Copiado!"

            # 4.10 Testes de Segurança (Validação de Executáveis e Revogação de Tokens)
            from app.utils.system_ops import is_dangerous_file
            assert is_dangerous_file("script.sh") is True
            assert is_dangerous_file("app.exe") is True
            assert is_dangerous_file("malicious.desktop") is True
            assert is_dangerous_file("trojan.bat") is True
            assert is_dangerous_file("filme.mp4") is False
            assert is_dangerous_file("foto.png") is False

            # Validação de revogação de tokens
            stream_server.start()
            s_token_url = stream_server.register_file(sample_file)
            token_key = s_token_url.split("/")[-1]
            assert stream_server.get_file_path(token_key) is not None
            stream_server.clear_tokens()
            assert stream_server.get_file_path(token_key) is None
            stream_server.stop()

            # 4.11 Validação do Acesso Remoto Mobile (PWA, Perfis, Kids, Continuar Assistindo e REST API)
            import json
            web_server = MediaStreamServer(port=0, db=ui_db)
            w_port = web_server.start()
            base_url = f"http://{web_server.host_ip}:{w_port}"

            # Teste GET / (HTML do PWA)
            with urllib.request.urlopen(f"{base_url}/") as resp:
                assert resp.status == 200
                html = resp.read().decode("utf-8")
                assert "MediaFinder Mobile" in html
                assert "view-profiles" in html
                assert "view-kids" in html

            # Teste GET /manifest.json
            with urllib.request.urlopen(f"{base_url}/manifest.json") as resp:
                assert resp.status == 200
                assert "application/json" in resp.headers.get("Content-Type", "")

            # Teste GET /sw.js
            with urllib.request.urlopen(f"{base_url}/sw.js") as resp:
                assert resp.status == 200

            # Teste GET /static/styles.css
            with urllib.request.urlopen(f"{base_url}/static/styles.css") as resp:
                assert resp.status == 200
                assert "--bg-primary" in resp.read().decode("utf-8")

            # Teste de Segurança contra Path Traversal
            try:
                urllib.request.urlopen(f"{base_url}/static/../../../../etc/passwd")
                assert False, "Deveria ter bloqueado path traversal"
            except urllib.error.HTTPError as e:
                assert e.code == 404

            # Teste GET /api/profiles
            with urllib.request.urlopen(f"{base_url}/api/profiles") as resp:
                assert resp.status == 200
                profiles = json.loads(resp.read().decode("utf-8"))
                assert len(profiles) >= 3
                assert any(p["id"] == "marcos" for p in profiles)
                assert any(p["id"] == "kids" and p["is_kids"] == 1 for p in profiles)

            # Teste POST /api/profiles/set-pin e /api/profiles/verify-pin
            post_pin_req = urllib.request.Request(
                f"{base_url}/api/profiles/set-pin",
                data=json.dumps({"profile_id": "marcos", "pin": "1234"}).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(post_pin_req) as resp:
                assert json.loads(resp.read().decode("utf-8"))["success"] is True

            verify_ok = urllib.request.Request(
                f"{base_url}/api/profiles/verify-pin",
                data=json.dumps({"profile_id": "marcos", "pin": "1234"}).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(verify_ok) as resp:
                assert json.loads(resp.read().decode("utf-8"))["success"] is True

            verify_err = urllib.request.Request(
                f"{base_url}/api/profiles/verify-pin",
                data=json.dumps({"profile_id": "marcos", "pin": "9999"}).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(verify_err) as resp:
                assert json.loads(resp.read().decode("utf-8"))["success"] is False

            # Teste de Continuar Assistindo (Progresso)
            video_test = ui_db.get_random_file(categories=["video"])
            assert video_test is not None
            v_id = video_test["id"]

            post_prog = urllib.request.Request(
                f"{base_url}/api/playback/progress",
                data=json.dumps({"profile_id": "marcos", "file_id": v_id, "position": 600.0, "duration": 1800.0}).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(post_prog) as resp:
                assert json.loads(resp.read().decode("utf-8"))["success"] is True

            # GET /api/continue
            with urllib.request.urlopen(f"{base_url}/api/continue?profile=marcos") as resp:
                cont_items = json.loads(resp.read().decode("utf-8"))
                assert len(cont_items) >= 1
                assert cont_items[0]["id"] == v_id
                assert cont_items[0]["progress_percent"] == 33.3

            # GET /api/cast/status
            with urllib.request.urlopen(f"{base_url}/api/cast/status") as resp:
                cast_st = json.loads(resp.read().decode("utf-8"))
                assert "is_casting" in cast_st
                assert "state" in cast_st
                assert "audio_tracks" in cast_st
                assert "subtitle_tracks" in cast_st

            # POST /api/cast/control (áudio e legenda)
            post_sub = urllib.request.Request(
                f"{base_url}/api/cast/control",
                data=json.dumps({"action": "subtitle_track", "value": -1}).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(post_sub) as resp:
                assert json.loads(resp.read().decode("utf-8"))["success"] is True

            post_aud = urllib.request.Request(
                f"{base_url}/api/cast/control",
                data=json.dumps({"action": "audio_track", "value": 0}).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            # Teste de Metadados IMDb e OMDb
            from app.core.metadata import clean_movie_title, translate_parental_rating, MediaMetadataService
            c_name, c_yr = clean_movie_title("Meu.Mestre.Minha.Vida.1989.1080p.mkv")
            assert c_name == "Meu Mestre Minha Vida"
            assert c_yr == 1989
            assert translate_parental_rating("PG-13") == "14+"
            assert translate_parental_rating("G") == "Livre"

            # Salvar metadados de teste
            ui_db.save_media_metadata(v_id, {
                "imdb_id": "tt0097722",
                "title": "Meu Mestre Minha Vida",
                "original_title": "Lean on Me",
                "year": 1989,
                "rating": 7.4,
                "votes": "23,396",
                "runtime": "108 min",
                "genre": "Biography, Drama",
                "rated": "14+",
                "plot": "Sinopse de teste do Dr. Joe Clark",
                "director": "John G. Avildsen",
                "actors": "Morgan Freeman, Beverly Todd",
                "poster_url": "https://m.media-amazon.com/test.jpg"
            })
            retrieved_meta = ui_db.get_media_metadata(v_id)
            assert retrieved_meta is not None
            assert retrieved_meta["rating"] == 7.4
            assert retrieved_meta["imdb_id"] == "tt0097722"

            # GET /api/media/details
            with urllib.request.urlopen(f"{base_url}/api/media/details?id={v_id}") as resp:
                details = json.loads(resp.read().decode("utf-8"))
                assert details["title"] == "Meu Mestre Minha Vida"
                assert details["rating"] == 7.4
                assert details["director"] == "John G. Avildsen"
                assert details["rated"] == "14+"

            # GET /api/catalog enriquecido com dados do IMDb
            with urllib.request.urlopen(f"{base_url}/api/catalog?profile=marcos&limit=10") as resp:
                cat_resp = json.loads(resp.read().decode("utf-8"))
                found_item = next((x for x in cat_resp["items"] if x["id"] == v_id), None)
                assert found_item is not None
                assert found_item["imdb_rating"] == 7.4
                assert found_item["meta_year"] == 1989

            # Testes da integração com a Pluto TV
            from app.core.pluto_tv import PlutoTVService
            pluto_svc = PlutoTVService.get_instance()
            pluto_channels = pluto_svc.get_channels()
            assert len(pluto_channels) > 0, "Deveria carregar lista de canais da Pluto TV"
            first_ch = pluto_channels[0]
            assert "id" in first_ch
            assert "name" in first_ch
            assert "stream_url" in first_ch
            assert ".m3u8" in first_ch["stream_url"]

            # GET /api/pluto/channels
            with urllib.request.urlopen(f"{base_url}/api/pluto/channels") as resp:
                pluto_resp = json.loads(resp.read().decode("utf-8"))
                assert "channels" in pluto_resp
                assert "categories" in pluto_resp
                assert len(pluto_resp["channels"]) > 0

            # GET /api/pluto/channels?is_kids=1
            with urllib.request.urlopen(f"{base_url}/api/pluto/channels?is_kids=1") as resp:
                pluto_kids_resp = json.loads(resp.read().decode("utf-8"))
                assert "channels" in pluto_kids_resp
                assert len(pluto_kids_resp["channels"]) > 0

            # GET /api/pluto/stream?id=...
            with urllib.request.urlopen(f"{base_url}/api/pluto/stream?id={first_ch['id']}") as resp:
                pluto_stream_resp = json.loads(resp.read().decode("utf-8"))
                assert pluto_stream_resp["channel_id"] == first_ch["id"]
                assert ".m3u8" in pluto_stream_resp["stream_url"]

            web_server.stop()

        # Validação do IPTVService e canais FAST / Multi-fontes
        from app.core.iptv import IPTVService
        iptv_svc = IPTVService.get_instance()
        iptv_channels = iptv_svc.get_channels()
        iptv_categories = iptv_svc.get_categories()
        assert len(iptv_channels) >= 5, "Deveria ter carregado canais de IPTV"
        assert len(iptv_categories) >= 3, "Deveria ter categorias de canais"

        # Teste de alternância para FAST essenciais
        fast_chans = iptv_svc.set_active_source("fast_essentials")
        assert len(fast_chans) == 12, "Deveria conter os 12 canais FAST essenciais"
        filtered_news = iptv_svc.get_channels(category="Notícias")
        assert any("Record News" in c["name"] for c in filtered_news), "Deveria conter Record News em Notícias"

        # Teste do parser M3U e fonte customizada com arquivo temporário
        sample_m3u = """#EXTM3U
#EXTINF:-1 tvg-id="teste1" tvg-name="Canal Teste" tvg-logo="http://logo.png" group-title="Movies",Canal Teste Filmes
https://exemplo.com/filme.m3u8
#EXTINF:-1 tvg-id="teste2" tvg-name="Canal HBO Teste" group-title="Entertainment",HBO Simulado
https://exemplo.com/hbo.m3u8
"""
        with tempfile.NamedTemporaryFile("w", suffix=".m3u", delete=False, encoding="utf-8") as tf:
            tf.write(sample_m3u)
            temp_m3u_path = tf.name

        try:
            ok, count, msg = iptv_svc.set_custom_source(temp_m3u_path, "Lista Custom Teste")
            assert ok is True, f"Falha ao carregar lista customizada: {msg}"
            assert count == 2, f"Deveria ter 2 canais carregados, obteve {count}"
            custom_chans = iptv_svc.set_active_source("custom")
            assert len(custom_chans) == 2
            assert any("HBO Simulado" in c["name"] for c in custom_chans)
        finally:
            if os.path.exists(temp_m3u_path):
                os.remove(temp_m3u_path)

        # Restaura para GitHub Brasil
        iptv_svc.set_active_source("github_br")

        # Teste do diálogo de importação M3U
        from app.ui.iptv_dialog import ImportM3UDialog
        dlg_iptv = ImportM3UDialog()
        assert dlg_iptv is not None
        dlg_iptv.close()

        print("✓ Todos os componentes, streaming HTTP 206, metadados IMDb, Pluto TV, IPTV Multi-fontes M3U, diálogos e IndexWorker validados com sucesso!")
    finally:
        try:
            if os.path.exists(ui_db_path):
                os.remove(ui_db_path)
        except Exception:
            pass

    print("\nTODOS OS TESTES PASSARAM COM SUCESSO!")

if __name__ == "__main__":
    run_tests()

