# Suporte a Streaming/Cast (Google Cast), Compatibilidade Linux/Regata OS e Melhorias de Segurança

## 📌 Resumo das Alterações
Este Pull Request introduz suporte completo para transmissão e controle de mídias em Smart TVs e reprodutores compatíveis com **Google Cast (Chromecast, Google TV e Smart TVs com Cast integrado)**, adiciona compatibilidade multiplataforma nativa para distribuições Linux (incluindo Regata OS e ambientes baseados em KDE/GNOME), além de reforçar a segurança do sistema operacional, integridade do catálogo e conformidade com padrões de rede.

---

## 🚀 Principais Funcionalidades e Correções

### 1. Transmissão e Streaming para Smart TVs (`Google Cast / Chromecast`)
- **Servidor HTTP embutido (`app/core/streamer.py`)**:
  - Implementação de servidor multi-thread com conformidade estrita ao **HTTP Range Requests (RFC 7233 / RFC 9110 e Status 206 Partial Content)**, incluindo limitação correta de intervalos (*range clamping*) e suporte a requisições pre-flight `OPTIONS` (CORS).
  - Buffer de streaming ajustado para **512 KB**, garantindo reprodução fluida e sem congelamentos em vídeos pesados (1080p/4K).
  - Execução padrão na porta **`1745`** (compatível com regras de portas abertas do KDE Connect no Linux sem exigir privilégios root).
- **Descoberta rápida e encerramento limpo (`TVCastManager`)**:
  - Descoberta híbrida ultrarrápida combinando sondagem assíncrona Eureka (HTTP 8008/8009) e protocolo Google Cast (`pychromecast`).
  - Encerramento correto dos sockets de descoberta (`stop_discovery()`) ao fechar o diálogo.
  - Inicialização automática do `Default Media Receiver` (`CC1AD845`) caso o Chromecast esteja na tela inicial ou em outro app.
- **Suporte a legendas sem sobrescrever arquivos do usuário**:
  - Conversão inteligente de legendas `.srt` para **WebVTT (`.vtt`)** com detecção automática de charset (`Windows-1252`, `ISO-8859-1`, `UTF-8`).
  - As legendas convertidas são salvas em **diretório de cache temporário isolado** (`tempfile`), preservando integralmente qualquer `.vtt` existente ou pastas de mídia somente-leitura.
- **Controle Remoto e Gerenciamento de Sessão (`app/ui/cast_dialog.py`)**:
  - Controles de Play, Pause, Stop, Seek e Volume/Mudo.
  - Revogação automática de tokens HTTP de streaming tanto ao pressionar Parar quanto ao término natural da reprodução do arquivo.

### 2. Integridade de Dados e Catálogo do SQLite
- **Delimitação estrita de pastas**:
  - Correção de consultas `LIKE` no banco de dados para incluir separadores explícitos (`/` e `\`), prevenindo que a remoção ou filtragem de uma pasta como `/media/Filmes` afete incorretamente pastas irmãs como `/media/FilmesAntigos`.
- **Limpeza de pastas vazias e preservação de permissões**:
  - O `scanner.py` agora remove registros obsoletos do catálogo mesmo quando uma pasta monitorada fica totalmente vazia.
  - Subdiretórios com erro temporário de permissão de leitura (`PermissionError`) são preservados no catálogo, impedindo a exclusão acidental de itens inacessíveis no momento.

### 3. Hardening e Segurança do Sistema Operacional (OS Security)
- **Prevenção contra Execução Arbitrária de Código**:
  - Validação de segurança em `app/utils/system_ops.py`: bloqueia a execução direta via `open_file()` de binários e scripts executáveis (`.exe`, `.bat`, `.cmd`, `.sh`, `.bin`, `.appimage`, `.desktop`, `.vbs`, `.ps1`, etc.).
  - Em vez de executar o código no SO, o aplicativo redireciona com segurança para a localização do arquivo no gerenciador de arquivos (`reveal_in_explorer`).
- **Exclusão Segura via Lixeira com Consentimento Explícito**:
  - Integração com `send2trash`. Ao acionar `Delete`, os arquivos são enviados para a Lixeira do sistema.
  - Caso o sistema de arquivos não suporte lixeira (ex: pendrives FAT32/exFAT ou montagens NFS/SMB), o aplicativo **não apaga silenciosamente**: ele exibe um aviso claro solicitando confirmação explícita do usuário antes de qualquer exclusão definitiva.
- **Proteção contra Diretórios Virtuais do Linux**:
  - Bloqueio de varredura nos sistemas de arquivos virtuais de kernel (`/proc`, `/sys`, `/dev`, `/run`), evitando loops infinitos e travamentos de I/O.
- **Tokens Criptográficos Aleatórios**:
  - Uso de `secrets.token_urlsafe(24)` (192 bits de entropia aleatória) para URLs de streaming, impedindo previsibilidade ou força-bruta por scripts na rede local.
- **Proteção contra Decompression Bomb (Pillow)**:
  - Limite de descompressão em `Image.MAX_IMAGE_PIXELS = 80_000_000` para mitigar ataques de esgotamento de memória RAM (*Memory Exhaustion/DoS*).
- **Permissões Estritas em Arquivos de Configuração e Banco**:
  - Aplicação de permissão `0600` em `config.json` e `media_index.db` no Linux.

### 4. Empacotamento e Testes
- **Otimização do PyInstaller**:
  - Remoção de `--collect-all=PySide6` e exclusão de módulos não utilizados (QtWebEngine, Qt3D, QtQuick, QtDesigner), reduzindo drasticamente o tamanho do executável.
- **Isolamento da Suíte de Testes**:
  - `test_engine.py` isola automaticamente `XDG_CONFIG_HOME`, `XDG_DATA_HOME` e `APPDATA` em diretórios temporários, garantindo que a execução dos testes nunca altere os arquivos e histórico reais do usuário.

---

## 🧪 Validação
- **Testes automatizados (`test_engine.py`)**:
  - Testes de HTTP Range Requests (200 OK, 206 Partial Content e clamping per RFC 7233).
  - Testes de requisição `OPTIONS` (CORS).
  - Validação de isolamento de tokens e revogação.
  - Testes de filtros de caminho multiplataforma (`/` e `\`).
  - Todos os testes aprovados com sucesso.
