import os
import sys
import re
import sqlite3
import logging
from pathlib import Path
from contextlib import contextmanager
from typing import List, Dict, Any, Optional, Tuple, Set, Generator

logger = logging.getLogger("MediaFinder.Database")

class MediaDatabase:
    """Gerencia a base de dados SQLite e índices FTS para busca instantânea de arquivos."""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            if sys.platform == "win32":
                base_dir = os.getenv("APPDATA") or str(Path.home())
            else:
                base_dir = os.getenv("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
            db_dir = Path(base_dir) / "MediaFinder"
            db_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = str(db_dir / "media_index.db")
        else:
            self.db_path = db_path

        self._init_db()

    @staticmethod
    def _clean_drive_param(drive: str) -> str:
        """Limpa e formata o parâmetro de drive de forma compatível com Windows e Linux."""
        if not drive or drive.lower() == "all":
            return ""
        if sys.platform == "win32":
            drive_clean = drive.upper()
            if not drive_clean.endswith(":"):
                drive_clean += ":"
            return drive_clean
        # Linux / Regata OS: preserva nome do ponto de montagem ou letra
        if len(drive) == 1 and drive.isalpha():
            return drive.upper() + ":"
        elif len(drive) == 2 and drive[1] == ":" and drive[0].isalpha():
            return drive.upper()
        return drive

    @staticmethod
    def _format_fts_query(query: str) -> str:
        """Formata a query de busca em termos de prefixo seguros para o FTS5."""
        clean = re.sub(r'[^\w\s]', ' ', query)
        tokens = clean.split()
        if not tokens:
            return ""
        return " ".join(f'"{token}"*' for token in tokens)


    @contextmanager
    def _get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        # Integridade referencial e otimizações de performance SQLite
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        conn.execute("PRAGMA cache_size = -64000;") # 64MB de cache
        conn.execute("PRAGMA temp_store = MEMORY;")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Tabela principal de arquivos
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    path TEXT UNIQUE NOT NULL,
                    parent_dir TEXT NOT NULL,
                    extension TEXT NOT NULL,
                    category TEXT NOT NULL,
                    size INTEGER NOT NULL DEFAULT 0,
                    mtime REAL NOT NULL DEFAULT 0,
                    drive TEXT NOT NULL
                );
            """)

            # Índices para filtros rápidos
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_name ON files(name COLLATE NOCASE);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_category ON files(category);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_drive ON files(drive);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_mtime ON files(mtime DESC);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_size ON files(size DESC);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_ext ON files(extension);")

            # Tabela FTS5 para busca textual com suporte a prefixo
            try:
                cursor.execute("""
                    CREATE VIRTUAL TABLE IF NOT EXISTS files_fts USING fts5(
                        name,
                        path,
                        content='files',
                        content_rowid='id',
                        tokenize = 'unicode61'
                    );
                """)

                # Triggers para manter o FTS5 sincronizado automaticamente
                cursor.execute("""
                    CREATE TRIGGER IF NOT EXISTS files_ai AFTER INSERT ON files BEGIN
                        INSERT INTO files_fts(rowid, name, path) VALUES (new.id, new.name, new.path);
                    END;
                """)
                cursor.execute("""
                    CREATE TRIGGER IF NOT EXISTS files_ad AFTER DELETE ON files BEGIN
                        INSERT INTO files_fts(files_fts, rowid, name, path) VALUES('delete', old.id, old.name, old.path);
                    END;
                """)
                cursor.execute("""
                    CREATE TRIGGER IF NOT EXISTS files_au AFTER UPDATE ON files BEGIN
                        INSERT INTO files_fts(files_fts, rowid, name, path) VALUES('delete', old.id, old.name, old.path);
                        INSERT INTO files_fts(rowid, name, path) VALUES (new.id, new.name, new.path);
                    END;
                """)
            except Exception as e:
                logger.warning(f"Nota: FTS5 não pôde ser inicializado ({e}), fallback para LIKE.")

            # Tabela de perfis de usuário (Acesso Mobile / PWA)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_profiles (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    avatar TEXT NOT NULL,
                    is_kids INTEGER NOT NULL DEFAULT 0,
                    pin_hash TEXT
                );
            """)

            # Tabela de progresso de reprodução por perfil (Continuar de onde parou)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS playback_progress (
                    profile_id TEXT NOT NULL,
                    file_id INTEGER NOT NULL,
                    position_seconds REAL NOT NULL DEFAULT 0.0,
                    duration_seconds REAL NOT NULL DEFAULT 0.0,
                    updated_at REAL NOT NULL DEFAULT 0.0,
                    PRIMARY KEY (profile_id, file_id),
                    FOREIGN KEY (profile_id) REFERENCES user_profiles(id) ON DELETE CASCADE,
                    FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE
                );
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_progress_updated ON playback_progress(updated_at DESC);")

            # Tabela de metadados enriquecidos (IMDb / OMDb / TMDb)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS media_metadata (
                    file_id INTEGER PRIMARY KEY,
                    imdb_id TEXT,
                    title TEXT,
                    original_title TEXT,
                    year INTEGER,
                    rating REAL,
                    votes TEXT,
                    runtime TEXT,
                    genre TEXT,
                    rated TEXT,
                    plot TEXT,
                    director TEXT,
                    actors TEXT,
                    poster_url TEXT,
                    poster_local TEXT,
                    backdrop_url TEXT,
                    updated_at REAL NOT NULL DEFAULT 0.0,
                    FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE
                );
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_metadata_imdb ON media_metadata(imdb_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_metadata_rating ON media_metadata(rating DESC);")

            # Seed inicial de perfis se a tabela estiver vazia
            cursor.execute("SELECT COUNT(*) FROM user_profiles;")
            if cursor.fetchone()[0] == 0:
                default_profiles = [
                    ("marcos", "Marcos", "admin", 0, None),
                    ("esposa", "Esposa", "flower", 0, None),
                    ("kids", "Kids", "lion", 1, None),
                ]
                cursor.executemany(
                    "INSERT INTO user_profiles (id, name, avatar, is_kids, pin_hash) VALUES (?, ?, ?, ?, ?);",
                    default_profiles
                )

            conn.commit()

        if sys.platform != "win32" and os.path.exists(self.db_path):
            try:
                os.chmod(self.db_path, 0o600)
            except OSError:
                pass

    def upsert_files_batch(self, files_data: List[Dict[str, Any]]) -> int:
        """Insere ou atualiza registros de arquivos em lote para máxima velocidade."""
        if not files_data:
            return 0

        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = """
                INSERT INTO files (name, path, parent_dir, extension, category, size, mtime, drive)
                VALUES (:name, :path, :parent_dir, :extension, :category, :size, :mtime, :drive)
                ON CONFLICT(path) DO UPDATE SET
                    name = excluded.name,
                    parent_dir = excluded.parent_dir,
                    extension = excluded.extension,
                    category = excluded.category,
                    size = excluded.size,
                    mtime = excluded.mtime,
                    drive = excluded.drive
            """
            cursor.executemany(query, files_data)
            conn.commit()
            return cursor.rowcount

    @staticmethod
    def _escape_like_pattern(text: str) -> str:
        r"""Escapa caracteres curinga do SQL LIKE (_, %, \) para busca literal."""
        return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

    @staticmethod
    def _is_path_under_root(path_str: str, root_str: str) -> bool:
        """Verifica com rigor de plataforma se path_str é igual ou filho de root_str."""
        try:
            p_norm = os.path.normpath(path_str)
            r_norm = os.path.normpath(root_str)
            if sys.platform != "win32":
                return p_norm == r_norm or p_norm.startswith(r_norm + "/")
            else:
                return p_norm.lower() == r_norm.lower() or p_norm.lower().startswith((r_norm + "\\").lower())
        except Exception:
            return False

    def remove_missing_files(self, existing_paths_set: set, folder_root: str, skipped_dirs: Optional[Set[str]] = None) -> int:
        """Remove do banco arquivos da pasta que não existem mais no disco, preservando subpastas inacessíveis."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            clean_root = os.path.normpath(folder_root).rstrip("/\\")
            esc_root = self._escape_like_pattern(clean_root)
            prefix_fwd = esc_root + "/%"
            prefix_back = esc_root + "\\%"
            # Seleciona caminhos candidatos usando ESCAPE para evitar que '_' ou '%' virem curingas
            cursor.execute(
                "SELECT id, path FROM files WHERE path = ? OR path LIKE ? ESCAPE '\\' OR path LIKE ? ESCAPE '\\'",
                (clean_root, prefix_fwd, prefix_back)
            )
            rows = cursor.fetchall()

            skipped_prefixes = []
            for d in (skipped_dirs or set()):
                cd = os.path.normpath(d).rstrip("/\\")
                skipped_prefixes.extend([cd + "/", cd + "\\"])

            ids_to_delete = []
            for r in rows:
                p = r["path"]
                # Validação estrita em Python para garantir case-sensitivity no Linux e limites de diretório
                if not self._is_path_under_root(p, clean_root):
                    continue
                if p in existing_paths_set:
                    continue
                # Se o arquivo estava dentro de uma subpasta que não pôde ser lida por falta de permissão, preserva
                if any(p.startswith(sp) for sp in skipped_prefixes):
                    continue
                ids_to_delete.append(r["id"])

            if ids_to_delete:
                # Divide em lotes de 900 para não estourar o limite de parâmetros do sqlite
                for i in range(0, len(ids_to_delete), 900):
                    batch = ids_to_delete[i:i+900]
                    placeholders = ",".join("?" for _ in batch)
                    cursor.execute(f"DELETE FROM files WHERE id IN ({placeholders})", batch)
                return len(ids_to_delete)
            return 0

    def delete_files_by_paths(self, paths: List[str]) -> int:
        """Remove do banco múltiplos arquivos especificados por seus caminhos."""
        if not paths:
            return 0
        with self._get_connection() as conn:
            cursor = conn.cursor()
            deleted_count = 0
            for i in range(0, len(paths), 900):
                batch = paths[i:i+900]
                placeholders = ",".join("?" for _ in batch)
                cursor.execute(f"DELETE FROM files WHERE path IN ({placeholders})", batch)
                deleted_count += cursor.rowcount
            return deleted_count

    def remove_folder_records(self, folder_path: str) -> int:
        """Remove do banco todos os arquivos que pertencem a uma pasta desmarcada/removida."""
        if not folder_path:
            return 0
        clean_root = os.path.normpath(folder_path).rstrip("/\\")
        esc_root = self._escape_like_pattern(clean_root)
        prefix_fwd = esc_root + "/%"
        prefix_back = esc_root + "\\%"
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, path FROM files WHERE path = ? OR path LIKE ? ESCAPE '\\' OR path LIKE ? ESCAPE '\\'",
                (clean_root, prefix_fwd, prefix_back)
            )
            rows = cursor.fetchall()
            ids_to_delete = [
                r["id"] for r in rows
                if self._is_path_under_root(r["path"], clean_root)
            ]

            if not ids_to_delete:
                return 0

            for i in range(0, len(ids_to_delete), 900):
                batch = ids_to_delete[i:i+900]
                placeholders = ",".join("?" for _ in batch)
                cursor.execute(f"DELETE FROM files WHERE id IN ({placeholders})", batch)
            return len(ids_to_delete)


    def search_files(
        self,
        query: str = "",
        category: str = "all",
        drive: str = "all",
        sort_by: str = "name_asc",
        limit: int = 500,
        offset: int = 0
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """Realiza busca ultra rápida com múltiplos filtros e paginação."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            query = query.strip()
            where_clauses = []
            params = []

            # 1. Filtro por Categoria
            if category and category.lower() != "all":
                where_clauses.append("f.category = ?")
                params.append(category.lower())

            # 2. Filtro por Drive
            drive_clean = self._clean_drive_param(drive)
            if drive_clean:
                where_clauses.append("f.drive = ?")
                params.append(drive_clean)


            # 3. Filtro por Query (Aceleração via FTS5 com fallback transparente para LIKE)
            if query:
                fts_expr = self._format_fts_query(query)
                use_fts = False
                if fts_expr:
                    try:
                        cursor.execute("SELECT 1 FROM files_fts WHERE files_fts MATCH ? LIMIT 1", (fts_expr,))
                        if cursor.fetchone():
                            use_fts = True
                    except Exception:
                        use_fts = False

                if use_fts:
                    where_clauses.append("f.id IN (SELECT rowid FROM files_fts WHERE files_fts MATCH ?)")
                    params.append(fts_expr)
                else:
                    terms = query.split()
                    like_clauses = []
                    for term in terms:
                        like_clauses.append("(f.name LIKE ? OR f.path LIKE ?)")
                        params.extend([f"%{term}%", f"%{term}%"])
                    where_clauses.append(" AND ".join(like_clauses))

            where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

            # Ordenação
            sort_map = {
                "name_asc": "f.name COLLATE NOCASE ASC",
                "name_desc": "f.name COLLATE NOCASE DESC",
                "size_desc": "f.size DESC",
                "size_asc": "f.size ASC",
                "mtime_desc": "f.mtime DESC",
                "mtime_asc": "f.mtime ASC",
                "ext_asc": "f.extension ASC",
            }
            order_sql = sort_map.get(sort_by, "f.name COLLATE NOCASE ASC")

            count_query = f"SELECT COUNT(*) as total, COALESCE(SUM(f.size), 0) as total_size FROM files f {where_sql}"
            cursor.execute(count_query, params)
            count_row = cursor.fetchone()
            total_count = count_row["total"]
            total_size = count_row["total_size"]

            data_query = f"""
                SELECT 
                    f.id, f.name, f.path, f.parent_dir, f.extension, f.category, f.size, f.mtime, f.drive,
                    m.imdb_id, m.title as meta_title, m.original_title, m.year as meta_year,
                    m.rating as imdb_rating, m.genre as meta_genre, m.poster_url, m.poster_local, m.backdrop_url
                FROM files f
                LEFT JOIN media_metadata m ON m.file_id = f.id
                {where_sql}
                ORDER BY {order_sql}
                LIMIT ? OFFSET ?
            """
            cursor.execute(data_query, params + [limit, offset])
            rows = [dict(r) for r in cursor.fetchall()]

            return rows, total_count, total_size

    def get_random_file(
        self,
        categories: Optional[List[str]] = None,
        folders: Optional[List[str]] = None,
        drive: Optional[str] = "all",
        query: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Retorna um arquivo aleatório do banco respeitando os filtros especificados."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            where_clauses = []
            params = []

            # Filtro por categorias (ex: ['video', 'audio'])
            if categories:
                cat_clean = [c.lower() for c in categories if c.lower() != "all"]
                if cat_clean:
                    placeholders = ",".join("?" for _ in cat_clean)
                    where_clauses.append(f"f.category IN ({placeholders})")
                    params.extend(cat_clean)

            # Filtro por pastas específicas (ex: ['E:\\Midias\\Filmes', 'F:\\Desenhos'])
            if folders:
                folder_clauses = []
                for folder in folders:
                    clean_folder = os.path.normpath(folder).rstrip("/\\")
                    prefix_fwd = clean_folder + "/%"
                    prefix_back = clean_folder + "\\%"
                    folder_clauses.append("(f.path = ? OR f.path LIKE ? OR f.path LIKE ?)")
                    params.extend([clean_folder, prefix_fwd, prefix_back])
                if folder_clauses:
                    where_clauses.append(f"({' OR '.join(folder_clauses)})")

            # Filtro por Drive
            drive_clean = self._clean_drive_param(drive)
            if drive_clean:
                where_clauses.append("f.drive = ?")
                params.append(drive_clean)

            # Filtro por query se houver
            if query and query.strip():
                terms = query.strip().split()
                for term in terms:
                    where_clauses.append("(f.name LIKE ? OR f.path LIKE ?)")
                    params.extend([f"%{term}%", f"%{term}%"])

            where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

            data_query = f"""
                SELECT f.id, f.name, f.path, f.parent_dir, f.extension, f.category, f.size, f.mtime, f.drive
                FROM files f
                {where_sql}
                ORDER BY RANDOM()
                LIMIT 1
            """
            cursor.execute(data_query, params)
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_files_for_channel(
        self,
        categories: Optional[List[str]] = None,
        folders: Optional[List[str]] = None,
        drive: Optional[str] = "all",
        limit: int = 50000
    ) -> List[Dict[str, Any]]:
        """Busca arquivos indexados para preenchimento de canal de TV respeitando filtros de pastas e categorias."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            where_clauses = []
            params = []

            # Filtro por categorias (ex: ['video'], ['audio'])
            if categories:
                cat_clean = [c.lower() for c in categories if c.lower() != "all"]
                if cat_clean:
                    placeholders = ",".join("?" for _ in cat_clean)
                    where_clauses.append(f"f.category IN ({placeholders})")
                    params.extend(cat_clean)

            # Filtro por pastas específicas (ex: ['E:\\Midias\\Series', 'F:\\Midias\\Animes'])
            if folders:
                folder_clauses = []
                for folder in folders:
                    folder_str = str(folder).strip()
                    if folder_str:
                        clean_folder = os.path.normpath(folder_str).rstrip("/\\")
                        prefix_fwd = clean_folder + "/%"
                        prefix_back = clean_folder + "\\%"
                        folder_clauses.append("(f.path = ? OR f.path LIKE ? OR f.path LIKE ?)")
                        params.extend([clean_folder, prefix_fwd, prefix_back])
                if folder_clauses:
                    where_clauses.append(f"({' OR '.join(folder_clauses)})")

            # Filtro por Drive
            drive_clean = self._clean_drive_param(drive)
            if drive_clean:
                where_clauses.append("f.drive = ?")
                params.append(drive_clean)


            where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

            data_query = f"""
                SELECT f.id, f.name, f.path, f.parent_dir, f.extension, f.category, f.size, f.mtime, f.drive
                FROM files f
                {where_sql}
                ORDER BY f.parent_dir ASC, f.name ASC
                LIMIT ?
            """
            cursor.execute(data_query, params + [limit])
            return [dict(r) for r in cursor.fetchall()]


    def get_indexed_subfolders(self, limit: int = 100) -> List[str]:
        """Retorna uma lista de diretórios pai/pastas conhecidas indexadas no banco."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT parent_dir
                FROM files
                ORDER BY parent_dir ASC
                LIMIT ?
            """, (limit,))
            return [r["parent_dir"] for r in cursor.fetchall()]

    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas gerais da base indexada."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) as total_files, COALESCE(SUM(size), 0) as total_size FROM files")
            row = cursor.fetchone()
            total_files = row["total_files"]
            total_size = row["total_size"]

            cursor.execute("SELECT category, COUNT(*) as count FROM files GROUP BY category")
            cat_counts = {r["category"]: r["count"] for r in cursor.fetchall()}

            cursor.execute("SELECT drive, COUNT(*) as count FROM files GROUP BY drive")
            drive_counts = {r["drive"]: r["count"] for r in cursor.fetchall()}

            return {
                "total_files": total_files,
                "total_size": total_size,
                "categories": cat_counts,
                "drives": drive_counts
            }

    def clear_database(self) -> None:
        """Limpa todos os registros do banco de dados e compacta o arquivo."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM files;")
            try:
                cursor.execute("DELETE FROM files_fts;")
            except Exception:
                pass
            conn.commit()
        self.maintenance()

    def get_profiles(self) -> List[Dict[str, Any]]:
        """Retorna todos os perfis cadastrados com indicador se possuem PIN ativo."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, name, avatar, is_kids, (pin_hash IS NOT NULL AND pin_hash != '') as has_pin
                FROM user_profiles
                ORDER BY is_kids ASC, name ASC;
            """)
            return [dict(r) for r in cursor.fetchall()]

    def get_profile(self, profile_id: str) -> Optional[Dict[str, Any]]:
        """Retorna os dados públicos de um perfil específico."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, name, avatar, is_kids, (pin_hash IS NOT NULL AND pin_hash != '') as has_pin
                FROM user_profiles
                WHERE id = ?;
            """, (profile_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def verify_profile_pin(self, profile_id: str, pin: str) -> bool:
        """Verifica se o PIN de 4 dígitos informado é válido para o perfil."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT pin_hash FROM user_profiles WHERE id = ?;", (profile_id,))
            row = cursor.fetchone()
            if not row:
                return False  # Perfil inexistente não autoriza acesso
            if not row["pin_hash"]:
                return True  # Sem PIN configurado, liberado
            import hashlib
            computed = hashlib.sha256(str(pin).strip().encode("utf-8")).hexdigest()
            return row["pin_hash"] == computed

    def set_profile_pin(self, profile_id: str, pin: Optional[str]) -> bool:
        """Define ou limpa o PIN de segurança do perfil."""
        import hashlib
        pin_hash = hashlib.sha256(str(pin).strip().encode("utf-8")).hexdigest() if pin and str(pin).strip() else None
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE user_profiles SET pin_hash = ? WHERE id = ?;", (pin_hash, profile_id))
            conn.commit()
            return cursor.rowcount > 0

    def save_playback_progress(self, profile_id: str, file_id: int, position_seconds: float, duration_seconds: float) -> None:
        """Registra a posição atual de reprodução no perfil."""
        import time
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO playback_progress (profile_id, file_id, position_seconds, duration_seconds, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(profile_id, file_id) DO UPDATE SET
                    position_seconds = excluded.position_seconds,
                    duration_seconds = excluded.duration_seconds,
                    updated_at = excluded.updated_at;
            """, (profile_id, file_id, max(0.0, float(position_seconds)), max(0.0, float(duration_seconds)), time.time()))
            conn.commit()

    def get_playback_progress(self, profile_id: str, file_id: int) -> Optional[Dict[str, Any]]:
        """Retorna a posição e duração salvas para um arquivo e perfil."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT position_seconds, duration_seconds, updated_at
                FROM playback_progress
                WHERE profile_id = ? AND file_id = ?;
            """, (profile_id, file_id))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_continue_watching(self, profile_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Retorna mídias pausadas entre 10s e 95% do total para 'Continuar Assistindo'."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    f.id, f.name, f.path, f.category, f.size, f.extension,
                    p.position_seconds, p.duration_seconds, p.updated_at,
                    ROUND((p.position_seconds / MAX(p.duration_seconds, 1.0)) * 100, 1) as progress_percent,
                    m.imdb_id, m.title as meta_title, m.original_title, m.year as meta_year,
                    m.rating as imdb_rating, m.votes as imdb_votes, m.runtime as meta_runtime,
                    m.genre as meta_genre, m.rated as meta_rated, m.plot as meta_plot,
                    m.director as meta_director, m.actors as meta_actors,
                    m.poster_url, m.poster_local, m.backdrop_url
                FROM playback_progress p
                JOIN files f ON f.id = p.file_id
                LEFT JOIN media_metadata m ON m.file_id = f.id
                WHERE p.profile_id = ?
                  AND p.position_seconds >= 10.0
                  AND (p.duration_seconds <= 0 OR p.position_seconds < (p.duration_seconds * 0.95))
                ORDER BY p.updated_at DESC
                LIMIT ?;
            """, (profile_id, limit))
            return [dict(r) for r in cursor.fetchall()]

    def get_mobile_catalog(
        self,
        is_kids: bool = False,
        category: Optional[str] = None,
        query: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Busca catálogo paginado para web/mobile enriquecido com dados do IMDb."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            where_clauses = []
            params: List[Any] = []

            # Perfil Kids: proteção estrita contra conteúdo adulto e desconhecido
            if is_kids:
                kids_keywords = [
                    "%desenho%", "%kids%", "%infantil%", "%animacao%", "%animation%",
                    "%disney%", "%pixar%", "%cartoon%", "%barbie%", "%lego%"
                ]
                kids_conditions = " OR ".join(["(f.path LIKE ? OR f.name LIKE ?)" for _ in kids_keywords])
                kids_params = []
                for kw in kids_keywords:
                    kids_params.extend([kw, kw])

                # Regras de proteção infantil:
                # 1. NUNCA exibir títulos com classificação indicativa restritiva (14+, 16+, 18+, R, TV-MA, etc.)
                # 2. Exibir títulos com classificação verificada Livre ou 10+
                # 3. Para títulos sem classificação (ou 'Desconhecido'), exigir correspondência com termos infantis explícitos
                where_clauses.append(f"""(
                    (m.rated IN ('Livre', 'L', 'G', 'TV-Y', 'TV-G', '10+', 'PG', 'TV-PG'))
                    OR
                    ((m.rated IS NULL OR m.rated IN ('Desconhecido', '')) AND ({kids_conditions}))
                ) AND (m.rated IS NULL OR m.rated NOT IN ('14+', '16+', '18+', 'R', 'NC-17', 'TV-MA', 'TV-14'))""")
                params.extend(kids_params)

            if category and category.lower() != "all":
                where_clauses.append("f.category = ?")
                params.append(category.lower())

            if query and query.strip():
                terms = query.strip().split()
                for term in terms:
                    where_clauses.append("(f.name LIKE ? OR f.path LIKE ? OR m.title LIKE ? OR m.original_title LIKE ?)")
                    params.extend([f"%{term}%", f"%{term}%", f"%{term}%", f"%{term}%"])

            where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

            count_query = f"SELECT COUNT(*) as total FROM files f LEFT JOIN media_metadata m ON m.file_id = f.id {where_sql};"
            cursor.execute(count_query, params)
            total = cursor.fetchone()["total"]

            data_query = f"""
                SELECT 
                    f.id, f.name, f.path, f.parent_dir, f.extension, f.category, f.size, f.mtime, f.drive,
                    m.imdb_id, m.title as meta_title, m.original_title, m.year as meta_year,
                    m.rating as imdb_rating, m.votes as imdb_votes, m.runtime as meta_runtime,
                    m.genre as meta_genre, m.rated as meta_rated, m.plot as meta_plot,
                    m.director as meta_director, m.actors as meta_actors,
                    m.poster_url, m.poster_local, m.backdrop_url
                FROM files f
                LEFT JOIN media_metadata m ON m.file_id = f.id
                {where_sql}
                ORDER BY f.mtime DESC, f.name ASC
                LIMIT ? OFFSET ?;
            """
            cursor.execute(data_query, params + [limit, offset])
            rows = [dict(r) for r in cursor.fetchall()]
            return rows, total

    def get_media_metadata(self, file_id: int) -> Optional[Dict[str, Any]]:
        """Retorna os metadados do IMDb para um arquivo específico."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM media_metadata WHERE file_id = ?;", (file_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def save_media_metadata(self, file_id: int, data: Dict[str, Any]) -> None:
        """Salva ou atualiza os metadados do IMDb no banco SQLite."""
        import time
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO media_metadata (
                    file_id, imdb_id, title, original_title, year, rating,
                    votes, runtime, genre, rated, plot, director, actors,
                    poster_url, poster_local, backdrop_url, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(file_id) DO UPDATE SET
                    imdb_id = excluded.imdb_id,
                    title = excluded.title,
                    original_title = excluded.original_title,
                    year = excluded.year,
                    rating = excluded.rating,
                    votes = excluded.votes,
                    runtime = excluded.runtime,
                    genre = excluded.genre,
                    rated = excluded.rated,
                    plot = excluded.plot,
                    director = excluded.director,
                    actors = excluded.actors,
                    poster_url = excluded.poster_url,
                    poster_local = COALESCE(excluded.poster_local, media_metadata.poster_local),
                    backdrop_url = excluded.backdrop_url,
                    updated_at = excluded.updated_at;
            """, (
                file_id,
                data.get("imdb_id"),
                data.get("title"),
                data.get("original_title"),
                data.get("year"),
                data.get("rating"),
                data.get("votes"),
                data.get("runtime"),
                data.get("genre"),
                data.get("rated"),
                data.get("plot"),
                data.get("director"),
                data.get("actors"),
                data.get("poster_url"),
                data.get("poster_local"),
                data.get("backdrop_url"),
                time.time()
            ))
            conn.commit()

    def get_video_files_missing_metadata(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retorna arquivos de vídeo que ainda não possuem metadados catalogados ou enriquecidos."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT f.id, f.name, f.path
                FROM files f
                LEFT JOIN media_metadata m ON m.file_id = f.id
                WHERE f.category = 'video' AND (m.file_id IS NULL OR m.imdb_id IS NULL)
                ORDER BY f.mtime DESC
                LIMIT ?;
            """, (limit,))
            return [dict(r) for r in cursor.fetchall()]

    def maintenance(self) -> bool:
        """
        Executa manutenção periódica e compactação no banco de dados SQLite:
        - PRAGMA optimize para atualizar estatísticas de consulta do query planner
        - VACUUM para desfragmentar e reduzir o tamanho do arquivo .db em disco
        - PRAGMA wal_checkpoint(TRUNCATE) para esvaziar o log WAL
        """
        try:
            logger.info("Iniciando manutenção do banco de dados (VACUUM e PRAGMA optimize)...")
            conn = sqlite3.connect(self.db_path, timeout=60.0)
            conn.isolation_level = None  # Autocommit para viabilizar VACUUM
            cursor = conn.cursor()
            cursor.execute("PRAGMA optimize;")
            cursor.execute("VACUUM;")
            cursor.execute("PRAGMA wal_checkpoint(TRUNCATE);")
            conn.close()
            logger.info("Manutenção do banco de dados concluída com sucesso.")
            return True
        except Exception as e:
            logger.error(f"Erro durante manutenção do banco de dados: {e}")
            return False



