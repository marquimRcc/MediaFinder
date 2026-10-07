# ⚡ MediaFinder — Buscador Rápido de Mídias & Central de TV Multi-HD

Utilitário desktop moderno de alta performance desenvolvido em Python e Qt (PySide6), projetado para indexar, localizar instantaneamente e reproduzir arquivos de mídia (vídeos, fotos, áudios e documentos) distribuídos em **qualquer disco rígido, SSD, HD externo, pendrive ou pasta do Windows** (ex: `C:`, `D:`, `E:`, `F:`, etc.).

---

## 🎯 Principais Recursos

- ⚡ **Busca Instantânea**: Pesquisa em tempo real com resposta em milissegundos enquanto você digita (usando engine SQLite FTS com indexação otimizada).
- 🧠 **Lembrança Automática**: Lembra da sua última pesquisa, dos filtros ativos e mantém histórico recente.
- 🎛️ **Filtros Avançados**:
  - **Categorias**: Todos, Vídeos (`.mp4`, `.mkv`, `.avi`, `.mov`...), Fotos/Imagens (`.jpg`, `.png`, `.webp`, `.psd`...), Áudios (`.mp3`, `.flac`, `.wav`...), Documentos/Projetos.
  - **Filtro por Drive/Disco**: Isole a busca em qualquer letra de unidade (`C:`, `D:`, `E:`, `F:`...) ou pesquise em todos ao mesmo tempo.
  - **Ordenação Multi-critério**: Por Nome (A-Z ou Z-A), Tamanho (Maior/Menor) e Data de Modificação recente.
- 📺 **Modo TV (Grade de Programação 24h & Canais Personalizáveis)**:
  - Janela desacoplada multi-monitor (`F8` / `Ctrl+T`) com transmissão contínua 24h por dia estilo televisão ao vivo.
  - **Gerenciador Visual de Canais (`C`)**: Crie seus próprios canais, dê nomes, escolha ícones e defina o modo de reprodução:
    - 🎲 **Aleatório (Shuffle)**: Ideal para Filmes, Curtas, Clipes e Variedades.
    - 🔢 **Sequencial (Cronológico)**: Ideal para Séries, Animes, Desenhos e Cursos (mantém rigorosamente a ordem `S01E01` → `S01E02`... sem inverter episódios).
  - **Sensibilidade à Duração Real**: A grade de programação se ajusta dinamicamente à duração real dos vídeos em reprodução, sem cortes prematuros.
  - **Suporte Multimídia Completo**: Alternância de faixas de idioma (**Dual Áudio** tecla `A`), **Legendas integradas** (`S` / `L`) e **barras retrô vintage de volume** (`↑` / `↓`).
- 🏷️ **Grupos de Mídia & Equivalência Multi-HD**:
  - Unifique pastas de discos diferentes sob uma mesma categoria (ex: unir `D:\Filmes`, `E:\Cinema 4K` e `F:\HD_Externo\Filmes` no grupo *"Filmes"*).
  - Crie categorias personalizadas (*Cursos*, *Novelas*, *Shows*, *Futebol*) que alimentam o buscador e os canais de TV de forma dinâmica.
- 🎲 **Modo Aleatório Rápido (Shuffle)**:
  - Sorteie e reproduza instantaneamente uma mídia com 1 clique (ou tecla `F4` / `Ctrl+R`), com suporte a filtros de pastas ou categorias.
- 👁️ **Painel de Pré-Visualização & Detalhes**:
  - Miniatura de imagens em alta definição, metadados completos e prévia de documentos.
- 🚀 **Integração com o Windows**:
  - Execução no player padrão (`Enter` ou 2 cliques), localização com seleção direta no Explorer (`explorer /select`) e exclusão física em lote com confirmação (`Delete`).
- 🗔 **Bandeja do Sistema (System Tray)**:
  - Acesso rápido ao lado do relógio do Windows para abrir o buscador, acionar a TV ou rodar sorteios.

---

## 📁 Guia de Organização de Pastas e Boas Práticas

O MediaFinder é totalmente flexível e funciona com qualquer estrutura de pastas. No entanto, seguir estas boas práticas garante que o **Modo TV** e os **Grupos de Mídia** identifiquem automaticamente séries, temporadas e episódios com máxima precisão:

### 1. Estrutura Recomendada para Séries, Animes e Desenhos
Para que o modo sequencial ordene cronologicamente as temporadas e episódios:

```
📁 Séries/
   └── 📁 Breaking Bad/
       ├── 📁 Temporada 01/
       │   ├── Breaking Bad S01E01.mkv
       │   ├── Breaking Bad S01E02.mkv
       │   └── ...
       └── 📁 Temporada 02/
           ├── Breaking Bad S02E01.mkv
           └── ...

📁 Animes/
   └── 📁 Naruto/
       ├── Naruto - Episódio 01.mp4
       ├── Naruto - Episódio 02.mp4
       └── ...
```

> 💡 **Padrões de nomes reconhecidos automaticamente**:
> - `S01E02` ou `s1e2`
> - `1x05` ou `01x05`
> - `Episódio 03`, `Ep 03`, `Capitulo 12`, `Parte 2`
> - `Nome do Anime 025.mp4`

---

### 2. Estrutura Recomendada para Filmes e Mídias Avulsas
Para filmes e vídeos únicos, você pode colocá-los diretamente em pastas dedicadas ou organizá-los por gênero/ano:

```
📁 Filmes/
   ├── Interestelar (2014).mkv
   ├── Matrix (1999).mp4
   └── O Poderoso Chefao.avi
```

---

### 3. Equivalência Multi-HD (Pastas em Discos Diferentes)
Se o seu catálogo estiver espalhado em vários discos rígidos ou SSDs:
- **Disco D:** `D:\Midias\Filmes`
- **Disco E:** `E:\Filmes_Antigos`
- **Disco F:** `F:\Downloads\Filmes`

Basta abrir as **Configurações (⚙️)** no MediaFinder, ir na aba **"🏷️ Grupos de Mídia"**, selecionar o grupo **Filmes** e adicionar essas 3 pastas. O MediaFinder e o Modo TV passarão a tratá-las como uma única coleção unificada!

---

## ⌨️ Atalhos de Teclado Úteis

### 🔍 Buscador Principal
| Atalho | Ação |
|---|---|
| `Ctrl + F` ou `F3` | Focar na barra de pesquisa |
| `F4` ou `Ctrl + R` | Sorteio do **Modo Aleatório Rápido** |
| `F8` ou `Ctrl + T` | Abrir o **Modo TV (Canais ao Vivo)** |
| `Delete` | Excluir arquivos selecionados do disco |
| `Ctrl + A` | Selecionar todos os arquivos da lista |
| `Ctrl + P` | Ocultar / Mostrar painel de prévia |
| `Enter` | Abrir arquivo no reprodutor padrão |
| `F5` | Reindexar / Atualizar mídias dos discos |

### 📺 Janela do Modo TV
| Tecla / Botão | Ação no Modo TV |
|---|---|
| `←` / `→` ou `Page Up/Down` | Trocar de canal (`CH-` / `CH+`) com transição suave |
| `↑` / `↓` ou `+` / `-` | Ajustar volume (+/- 5%) com barras retrô vintage |
| `1` a `9` | Sintonizar canal diretamente pelo número |
| `Espaço` / `Play / Pause` | Pausar / Continuar reprodução |
| `C` | Abrir **Gerenciador de Canais & Pastas** |
| `R` ou `F5` | Gerar uma nova grade de 24h aleatória |
| `A` | Alternar faixa de áudio (**Dual Áudio**) |
| `S` ou `L` | Alternar faixas de legendas embutidas |
| `G` ou `Tab` | Ocultar / Mostrar grade lateral de programação |
| `F` ou `F11` | Alternar Tela Cheia |
| `Esc` | Sair da Tela Cheia / Fechar TV |

---

## 🚀 Como Executar

### Opção 1: Executável Portátil Standalone (.exe)
Basta executar o arquivo gerado:
```bash
dist\MediaFinder.exe
```
*(Não precisa de Python instalado)*

### Opção 2: Pelo Código Python
1. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
2. Execute o script principal ou dê duplo clique em `iniciar.bat`:
   ```bash
   python main.py
   ```

### Para Recriar o Executável (.exe)
```bash
python build_exe.py
```
O executável `.exe` será gerado automaticamente na pasta `dist/`.

---

## 🛠️ Tecnologias
- **Interface**: PySide6 (Qt 6) com Dark Theme moderno e responsivo.
- **Engine de Busca**: SQLite com modo WAL, índices de alta performance e FTS5.
- **Processamento de Miniaturas**: Pillow (PIL) com cache assíncrono.
- **Player Multimídia**: QtMultimedia com aceleração por hardware e suporte a streams multi-áudio/legendas.
- **Empacotador**: PyInstaller.
