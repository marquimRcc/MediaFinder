# MediaFinder

Buscador de arquivos e gerenciador multimídia desktop de alta performance desenvolvido em Python e Qt (PySide6), projetado para indexar, consultar e reproduzir coleções distribuídas em múltiplos discos rígidos, SSDs, unidades externas e diretórios montados no Windows.

---

## Funcionalidades

### Mecanismo de Busca e Indexação
- **Busca em Tempo Real**: Consulta instantânea com debounce de 150ms utilizando SQLite FTS5 (`unicode61`) e índices compostos.
- **Varredura Assíncrona**: Scanner em thread dedicada (`QThread`) sem congelamento da interface gráfica.
- **Histórico e Persistência**: Restauração automática de filtros, termos de pesquisa e histórico recente.

### Filtros e Agrupamentos
- **Filtragem por Categoria**: Vídeos, Imagens, Áudios e Documentos com contadores dinâmicos.
- **Isolamento por Unidade**: Filtragem por letra de unidade ou pesquisa unificada em todas as fontes monitoradas.
- **Grupos de Mídia**: Criação de equivalências entre diretórios de discos distintos (ex.: unificação de pastas em múltiplas unidades sob a categoria "Filmes").
- **Ordenação Multi-critério**: Ordenação por nome, tamanho e data de modificação.

### Modo TV e Transmissão Contínua
- **Player Integrado**: Reprodução contínua 24h em janela independente desacoplada.
- **Ordem Cronológica ou Aleatória**:
  - *Sequencial*: Ordenação cronológica rigorosa para séries e animes (`S01E01`, `S01E02`...).
  - *Aleatório (Shuffle)*: Distribuição pseudo-aleatória sem repetições consecutivas.
- **Sincronização Dinâmica**: Ajuste automático da grade de programação baseado na duração real dos arquivos.
- **Controles Multimídia**: Alternância de trilhas de áudio (Dual Áudio), legendas embutidas e controle de volume.

### Painel de Pré-Visualização e Utilitários
- **Prévia Integrada**: Renderização assíncrona de miniaturas para imagens e leitura rápida de metadados e arquivos de texto (`.txt`, `.nfo`, `.srt`, `.json`).
- **Integração com Windows Explorer**: Abertura no player padrão do sistema ou localização direta via `explorer /select`.
- **Modo Aleatório Rápido**: Sorteio instantâneo de mídias por atalho de teclado (`F4`).
- **Gerenciamento de Arquivos**: Exclusão física com exibição detalhada do espaço em disco a ser liberado.

---

## Guia Rápido de Uso

### 1. Configurando Pastas e Fontes Monitoradas
1. Na janela principal, clique no botão **Pastas** (`⚙️ Pastas`) no topo superior direito.
2. Na aba **Pastas & Unidades Monitoradas**, clique em **Adicionar Pasta / Unidade...** e selecione os diretórios raiz ou pontos de montagem desejados (ex.: `D:\Midias`, `E:\`, `\\Servidor\Midias`).
3. O MediaFinder iniciará a varredura recursiva em segundo plano. Para forçar uma nova varredura completa a qualquer momento, clique em **Reindexar Tudo Agora** (ou pressione `F5`).

### 2. Pesquisando e Filtrando Mídias
- **Busca por Nome**: Digite qualquer termo na barra de pesquisa superior. A consulta é executada instantaneamente enquanto você digita.
- **Chips de Categoria**: Filtre rapidamente por tipo de arquivo clicando em *Vídeos*, *Imagens*, *Áudios* ou *Documentos*.
- **Unidade / Origem**: Utilize o seletor suspenso para isolar a busca em uma unidade específica (ex.: `Drive E:`) ou manter a busca global em `Todas as Unidades`.
- **Painel de Prévia**: Pressione `Ctrl + P` para abrir o painel lateral com metadados, dimensões/resolução e miniatura da mídia selecionada.

### 3. Criando Categorias e Equivalências (Multi-Unidades)
Caso seus arquivos estejam distribuídos em diferentes discos ou diretórios:
1. Abra **Configurações** (`⚙️ Pastas`) e acesse a aba **Grupos de Mídia & Categorias**.
2. Selecione ou crie um grupo (ex.: `Filmes`, `Séries`, `Cursos`).
3. Adicione as pastas correspondentes de cada unidade (ex.: `D:\Filmes`, `E:\Cinema_4K`, `F:\Downloads\Filmes`).
4. Essas pastas passarão a ser tratadas como uma coleção única, tanto na filtragem quanto na grade do Modo TV.

### 4. Utilizando o Modo TV
1. Pressione `F8` (ou `Ctrl + T`) para abrir a janela desacoplada do Modo TV.
2. Navegue pelos canais usando as teclas `←` / `→` ou os números de `1` a `9`.
3. Pressione a tecla **C** para abrir o **Gerenciador de Canais**, onde é possível:
   - Criar e renomear canais temáticos.
   - Vincular grupos de mídia ou subpastas específicas.
   - Definir o modo de transmissão: **Aleatório (Shuffle)** para filmes/variedades ou **Sequencial** para séries/animes.
4. Ajuste o volume com `↑` / `↓`, alterne faixas de áudio com `A` e ative legendas com `S` ou `L`.

### 5. Sorteio Rápido e Gerenciamento
- **Sorteio Instantâneo**: Pressione `F4` (ou `Ctrl + R`) para sortear e abrir imediatamente uma mídia aleatória respeitando a categoria atualmente filtrada.
- **Exclusão de Arquivos**: Selecione um ou mais itens na tabela de resultados e pressione `Delete` para excluí-los fisicamente do disco com confirmação do espaço total liberado.

---

## Organização de Pastas e Boas Práticas

O mecanismo de busca do MediaFinder é recursivo e analisa todos os níveis de subpastas automaticamente. Para obter o melhor aproveitamento dos recursos de ordenação e detecção do Modo TV, recomenda-se a seguinte estrutura:

### 1. Conteúdo Episódico (Séries, Animes, Desenhos e Cursos)

```
Séries/
└── Breaking Bad/
    ├── Temporada 01/
    │   ├── Breaking Bad S01E01.mkv
    │   ├── Breaking Bad S01E02.mkv
    │   └── ...
    └── Temporada 02/
        ├── Breaking Bad S02E01.mkv
        └── ...
```

**Padrões de nomenclatura reconhecidos automaticamente:**
- Códigos de temporada e episódio: `S01E02`, `s1e2`, `1x05`, `01x05`
- Textos descritivos: `Episódio 03`, `Ep 03`, `Capitulo 12`, `Parte 2`
- Numeração sequencial no final do arquivo: `Naruto 01.mp4`, `Curso_Modulo 02.mp4`

### 2. Filmes e Mídias Avulsas

O MediaFinder suporta tanto arquivos soltos na raiz quanto filmes organizados em subpastas individuais com legendas ou extras:

```
Filmes/
├── Interestelar (2014)/
│   ├── Interestelar (2014).mkv
│   └── Interestelar (2014).srt
├── Matrix (1999)/
│   ├── Matrix (1999).mp4
│   └── poster.jpg
├── Ficção Científica/
│   ├── Blade Runner 2049 (2017).mkv
│   └── A Chegada (2016).mkv
└── O Poderoso Chefao.avi
```

---

## Atalhos de Teclado

### Interface Principal
| Atalho | Ação |
|---|---|
| `Ctrl + F` / `F3` | Focar no campo de busca |
| `F4` / `Ctrl + R` | Executar sorteio aleatório |
| `F8` / `Ctrl + T` | Abrir janela do Modo TV |
| `Ctrl + P` | Alternar exibição do painel de prévia |
| `Ctrl + A` | Selecionar todos os itens da tabela |
| `Enter` | Abrir arquivo no reprodutor padrão |
| `Delete` | Excluir arquivos selecionados |
| `F5` | Atualizar e reindexar diretórios |

### Janela do Modo TV
| Atalho | Ação |
|---|---|
| `←` / `→` ou `Page Up/Down` | Trocar de canal (`CH-` / `CH+`) |
| `↑` / `↓` ou `+` / `-` | Ajustar volume (+/- 5%) |
| `1` a `9` | Sintonizar canal diretamente pelo número |
| `Espaço` | Alternar Reprodução / Pausa |
| `C` | Abrir gerenciador de canais |
| `A` | Alternar faixa de áudio (Dual Áudio) |
| `S` / `L` | Alternar faixa de legendas |
| `G` / `Tab` | Alternar exibição da grade de programação |
| `F` / `F11` | Alternar modo tela cheia |
| `Esc` | Sair do modo tela cheia / fechar TV |

---

## Instalação e Execução

### Opção 1: Executável Portátil (Windows)
Baixe a versão compilada diretamente na página de [Releases](https://github.com/xToshiro/MediaFinder/releases). Não requer instalação prévia do Python ou de dependências externas.

### Opção 2: Execução a partir do Código-Fonte

1. Clone o repositório:
```bash
git clone https://github.com/xToshiro/MediaFinder.git
cd MediaFinder
```

2. Instale as dependências:
```bash
pip install -r requirements.txt
```

3. Inicie a aplicação:
```bash
python main.py
```

### Compilação do Executável

Para compilar o binário localmente utilizando o PyInstaller:
```bash
python build_exe.py
```
O executável standalone será gerado no diretório `dist/MediaFinder.exe`.

---

## Arquitetura e Tecnologias

- **Linguagem**: Python 3.10+
- **Interface Gráfica**: PySide6 (Qt 6.7+)
- **Banco de Dados**: SQLite com WAL (Write-Ahead Logging) e FTS5 (Full-Text Search)
- **Manipulação de Imagens**: Pillow (PIL)
- **Executável Windows**: PyInstaller

---

## Licença

Este projeto está licenciado sob os termos da licença GNU General Public License v3.0 (GPLv3). Consulte o arquivo [LICENSE](LICENSE) para obter mais informações.
