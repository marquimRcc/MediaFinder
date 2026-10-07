# ⚡ MediaFinder — Buscador Rápido de Mídias Multi-HD

Utilitário desktop moderno de alta performance desenvolvido em Python e Qt (PySide6), projetado para localizar instantaneamente arquivos de mídia (vídeos, fotos, áudios e documentos) distribuídos em múltiplos discos rígidos (como `E:\Midias`, `F:\Midias`, `H:\Midias`).

---

## 🎯 Principais Recursos

- ⚡ **Busca Instantânea**: Pesquisa em tempo real com resposta em milissegundos enquanto você digita (usando engine SQLite FTS com indexação otimizada).
- 🧠 **Lembrança Automática**: Lembra da sua última pesquisa, dos filtros ativos e mantém um histórico dropdown de termos recentes.
- 🎛️ **Filtros Avançados**:
  - **Categorias**: Todos, Vídeos (`.mp4`, `.mkv`, `.avi`, `.mov`...), Fotos/Imagens (`.jpg`, `.png`, `.webp`, `.psd`...), Áudios (`.mp3`, `.flac`, `.wav`...), Documentos/Projetos.
  - **Filtro por HD**: Isole a busca em qualquer HD (`E:`, `F:`, `H:`...) ou pesquise em todos ao mesmo tempo.
  - **Ordenação**: Por Nome (A-Z ou Z-A), Tamanho (Maior/Menor) e Data de Modificação.
- 🎲 **Modo Aleatório Rápido (Shuffle)**:
  - Sorteie e reproduza instantaneamente uma mídia aleatória com 1 clique (ou tecla `F4` / `Ctrl+R`).
  - Configure filtros de pastas específicas (ex: apenas Filmes, Séries ou Desenhos) ou categorias de mídia.
- 📺 **Modo TV (Grade de Programação 24h & Canais Totalmente Personalizáveis)**:
  - Janela desacoplada multi-monitor (`F8` / `Ctrl+T`) que continua reproduzindo mesmo se você minimizar o buscador principal.
  - **Gerenciador de Canais (`C`)**: Crie seus próprios canais, dê nomes, escolha ícones, defina modo **🎲 Aleatório (Shuffle)** ou **🔢 Sequencial Cronológico** (para maratonas de séries e animes sem inverter episódios).
  - **Sensibilidade à Duração Real**: Ajuste dinâmico de grade conforme a duração real dos vídeos carregados no player, sem cortes prematuros.
  - **7 Canais Temáticos Inclusos** (Panorama, TeleCine, Maratonando, Cartoonopolis, Anime Station, Olhar Curioso, Na Onda FM).
  - Grade horária contínua de 24h por dia com cálculo de "NO AR AGORA" e "A SEGUIR".
  - Suporte a **Dual Áudio** (tecla `A`), **Legendas integradas** (`S` / `L`) e **barras retrô vintage de volume** (`↑` / `↓`).
- 🏷️ **Grupos de Mídia & Equivalência Multi-HD**:
  - Configure categorias na tela de Configurações unindo pastas de múltiplos discos (ex: `E:\Midias\Filmes`, `F:\Midias\Filmes` e `H:\Filmes` unidos no grupo "Filmes").
  - Crie categorias personalizadas (ex: *Cursos, Novelas, Documentários*) que alimentam o buscador e os canais de TV sem precisar alterar código.
- 🗔 **Bandeja do Sistema (Windows System Tray)**:
  - Ícone na barra de tarefas do Windows (ao lado do relógio).
  - Menu de contexto com acesso rápido para abrir o buscador, acionar o Modo TV, rodar o Sorteio Aleatório ou gerenciar HDs.
- 👁️ **Painel de Pré-Visualização & Detalhes**:
  - Exibe miniatura de imagens (com resolução e dimensões).
  - Metadados completos (tamanho formatado em MB/GB, data, HD de origem e caminho).
- 🚀 **Ações Diretas no Windows**:
  - **Abrir Arquivo**: Executa no player/aplicativo padrão do Windows (duplo clique ou botão).
  - **Localizar no Explorer**: Abre a pasta com o arquivo **já selecionado/destacado** (`explorer /select`).
  - **Copiar Caminho / Pasta**: Botões rápidos para copiar para a área de transferência.
  - **Seleção Múltipla e Exclusão em Lote**: Marque vários arquivos (`Ctrl+Clique`, `Shift+Clique`, `Ctrl+A`) e exclua permanentemente das pastas nos HDs com a tecla `Delete` ou menu de contexto.
- 📁 **Gerenciador de HDs e Pastas**:
  - Adicione e remova qualquer pasta ou HD de forma visual na tela de Configurações.
  - Indexação multi-thread em segundo plano sem travar a interface.

---

## ⌨️ Atalhos de Teclado Úteis

### 🔍 Buscador Principal & Resultados
| Atalho | Ação |
|---|---|
| `Ctrl + F` ou `F3` | Focar na barra de pesquisa e selecionar texto |
| `F4` ou `Ctrl + R` | Sorteio instantâneo do **Modo Aleatório Rápido** |
| `F8` ou `Ctrl + T` | Abrir o **Modo TV (Canais ao Vivo)** |
| `Delete` | Excluir arquivos selecionados fisicamente do disco com confirmação |
| `Ctrl + A` | Selecionar todos os arquivos da lista atual |
| `Ctrl + P` | Alternar/Ocultar painel de prévia lateral |
| `Enter` | Abrir o arquivo selecionado no player padrão |
| `Setas Cima / Baixo` | Navegar pela tabela de resultados |
| `F5` | Reindexar / Atualizar arquivos dos HDs |
| `Botão Direito` | Menu com ações rápidas (Abrir, Explorer, Copiar, Excluir) |

### 📺 Janela do Modo TV (Player e Canais)
| Tecla / Botão | Ação no Modo TV |
|---|---|
| `Setas Esquerda / Direita` | Trocar de canal (`CH-` / `CH+`) com transição suave e OSD |
| `Setas Cima / Baixo` | Ajustar volume (+/- 5%) com exibição de barras vintage |
| `1` a `7` | Sintonizar diretamente no canal numérico |
| `Espaço` / `Play / Pause` | Pausar / Continuar reprodução |
| `Stop` | Parar reprodução |
| `Next / Prev Track` | Avançar / Voltar canal de TV |
| `M` / `Volume Mute` | Silenciar / Reativar som (Mute) |
| `A` | Alternar faixa de áudio (**Dual Áudio**) |
| `S` ou `L` | Alternar faixas de legendas |
| `G` ou `Tab` | Ocultar / Mostrar painel lateral com a grade diária |
| `R` ou `F5` | Gerar uma nova grade de 24h aleatória |
| `F` ou `F11` | Alternar Modo Tela Cheia |
| `Esc` | Sair da Tela Cheia / Fechar janela da TV |


---

## 🚀 Como Executar

### Opção 1: Pelo Executável Standalone (.exe)
Você pode rodar diretamente o executável gerado na pasta `dist/`:
```bash
dist\MediaFinder.exe
```
*(Não precisa de Python instalado para rodar o .exe)*

### Opção 2: Pelo Python
1. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
2. Inicie dando 2 cliques em `iniciar.bat` ou executando:
   ```bash
   python main.py
   ```

### Para Recriar o Executável (.exe)
```bash
python build_exe.py
```
O arquivo `.exe` será gerado automaticamente dentro da pasta `dist/`.

---

## 🛠️ Tecnologias
- **Interface**: PySide6 (Qt 6) com tema escuro personalizado.
- **Engine**: SQLite com índices otimizados e FTS.
- **Processamento de Imagens**: Pillow (PIL) com thumbnailing em cache.
- **Empacotador**: PyInstaller.
