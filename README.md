# DownloaderVideo

Gerenciador desktop para Windows com interface em português, **yt-dlp** e **FFmpeg**. Análise e transferências acontecem em processos separados da interface; cada tarefa tem opções próprias e permanece no histórico local.

## Executar pelo código-fonte

Requer Python 3.11+ (build validado com 3.12). No Windows:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r requirements-tested.txt
.venv\Scripts\python -m pip install --no-deps -e .
.venv\Scripts\python -m downloadervideo
```

Instale uma compilação confiável do [FFmpeg](https://ffmpeg.org/download.html) com `ffmpeg` e `ffprobe` no PATH ou selecione o executável em Configurações → Conexão. Sobre mostra se a ferramenta foi detectada. Mesclagem, conversão, metadados, capítulos e cortes dependem dela. Algumas plataformas, especialmente YouTube, podem exigir um [runtime JavaScript suportado pelo yt-dlp](https://github.com/yt-dlp/yt-dlp/wiki/EJS); sua ausência é informada pelo extrator, sem prometer acesso.

No Linux, após instalar FFmpeg pelo gerenciador do sistema:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-tested.txt
.venv/bin/python -m pip install --no-deps -e .
.venv/bin/python -m downloadervideo
```

`requirements-tested.txt` fixa as versões do ambiente testado, incluindo ferramentas de teste/build. Para somente dependências de execução, use `pip install .`; nesse caso o resolvedor pode selecionar versões diferentes das testadas.

## Usar

1. Cole um ou vários links, um por linha. A análise consulta o primeiro link sem bloquear a janela.
2. Escolha uma linha da tabela para usar um formato real, ou deixe automático. Linhas de vídeo sem áudio são combinadas à faixa escolhida no seletor de áudio, ou à melhor faixa disponível. O filtro pesquisa resoluções, codecs, idiomas e contêineres existentes.
3. Em **Opções deste download**, escolha saída, extração/conversão de áudio, legendas, miniaturas, metadados, capítulos, intervalo, limite de velocidade e autenticação por arquivo de cookies. A escolha de contêiner mescla fluxos compatíveis; para mudar codecs de vídeo, use a opção separada Recodificar vídeo. Legendas também podem ser convertidas para SRT, VTT ou ASS.
4. Adicione à fila. Múltiplos links usam as mesmas opções, mas IDs de formato selecionados na análise só podem ser usados no link correspondente. Para coleções, habilite playlists; limite os itens com `1:5,8`, por exemplo.
5. Acompanhe transferência e processamento em **Fila e histórico**. Cancelar encerra o processo e seus filhos FFmpeg. Repetir/retomar preserva arquivos `.part`; servidores sem suporte a retomada podem reiniciar o arquivo.
6. Use **Sobre** para consultar todos os extratores da versão instalada, capacidades, dependências, licenças e a versão mais recente do yt-dlp no PyPI oficial.

As configurações globais valem para novas tarefas; salvar também redefine as opções do próximo download. As tarefas existentes mantêm suas opções. A restauração de padrões só é persistida ao salvar.

### Opções avançadas

Objeto JSON validado com opções da API oficial, não uma linha de comandos. Exemplos:

```json
{"format": "bv*[height<=1080]+ba/b", "format_sort": ["codec:h264"], "concurrent_fragment_downloads": 4}
```

A chave `format` tem prioridade sobre a seleção da tabela. As chaves aceitas são listadas na interface. `exec`, configurações externas, plugins, downloaders externos, credenciais em cabeçalhos e comandos de shell não são aceitos. A lista é intencionalmente explícita; nem toda opção do CLI é adequada para uma interface desktop.

### Privacidade e dados locais

O banco SQLite fica em `%LOCALAPPDATA%\DownloaderVideo` no Windows e `~/.local/share/DownloaderVideo` no Linux. Contém preferências, URLs, caminhos e histórico. Não sincroniza dados nem tem telemetria. URLs podem conter tokens: trate esse diretório como privado e limpe o histórico quando necessário. Arquivos de cookies são referenciados pelo caminho; seu conteúdo não é armazenado no banco. A biblioteca yt-dlp pode atualizar o arquivo de cookies escolhido. Não use URLs contendo usuário/senha. Logs rotativos omitem títulos, URLs e conteúdo de cookies; detalhes de erros apresentados/persistidos têm URLs sem parâmetros e credenciais redigidas. `DOWNLOADERVIDEO_DATA_DIR` permite isolar os dados, inclusive nos testes.

Uma única instância é permitida por diretório de dados. No próximo início, tarefas incompletas aparecem como **Interrompido**, aguardando retomada manual. Limpar histórico não exclui arquivos. Desinstalar preserva dados e downloads.

## Testes

```powershell
.venv\Scripts\python -m pytest -q
```

No Linux sem display: `QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q`. FFmpeg/FFprobe precisam estar no PATH para os testes de integração. Os testes geram mídia sintética com vídeo e áudio e servem os arquivos por HTTP local; exercitam o yt-dlp e o FFmpeg reais, sem credenciais nem downloads de conteúdo de terceiros. Ver [relatório de validação](docs/VALIDATION.md).

## Distribuição Windows

```powershell
# Portátil, dependência FFmpeg externa
.\packaging\build.ps1

# Pacote completo: binários e avisos/fontes do FFmpeg preparados pelo distribuidor
.\packaging\build.ps1 `
  -FFmpegDirectory C:\dependencias\ffmpeg\bin `
  -FFmpegNoticesDirectory C:\dependencias\ffmpeg\redistribuicao `
  -Installer
```

O comando prepara uma venv, usa dependências fixadas, gera `dist\DownloaderVideo\DownloaderVideo.exe` com PyInstaller e testa o protocolo do worker do executável. `-Installer` requer [Inno Setup 6](https://jrsoftware.org/isinfo.php) e gera o instalador em `dist`. O pacote `onedir` mantém bibliotecas Qt dinâmicas substituíveis; distribua a pasta inteira, não apenas o EXE. O instalador é por usuário e não exige administrador. Não depende do caminho da máquina de desenvolvimento. Para um pacote sem configuração manual de FFmpeg, forneça ambos os diretórios ao build e valide a versão instalada em uma VM limpa.

A workflow de CI testa Linux/Windows, gera um pacote Windows **sem FFmpeg embutido**, testa seu worker e gera o instalador. Os artefatos são de desenvolvimento, sem assinatura digital. Para distribuição pública: escolha uma compilação redistribuível de FFmpeg, preserve seus avisos e fontes correspondentes, execute os testes de aceitação Windows e assine o instalador. Consulte [avisos de terceiros](THIRD_PARTY_NOTICES.md).

Não há um EXE Windows validado nesta sessão Linux. A configuração da pipeline não equivale a uma execução bem-sucedida da pipeline.

## Atualizar

A interface consulta a versão instalada e a versão mais recente do yt-dlp no PyPI, a última release do aplicativo no GitHub e as tags estáveis do FFmpeg no repositório oficial; não substitui executáveis ou dependências durante downloads. No código-fonte, feche o aplicativo, ative a venv e execute `python -m pip install --upgrade 'yt-dlp[default]'`. Depois repita os testes e atualize os pins antes de distribuir. Para a versão empacotada, produza/instale um novo pacote. Links oficiais do aplicativo e FFmpeg estão em Sobre; as consultas independentes mostram falhas de rede/limite de API sem inventar versões. O projeto ainda não tem uma release pública para comparar versões do aplicativo.

## Arquitetura

- `app.py`, `forms.py`, `theme.py`: interface PySide6/Qt, formulários reutilizáveis e estilo.
- `manager.py`: fila concorrente, estados, recuperação, cancelamento e histórico.
- `process.py`, `worker.py`: comunicação JSON por pipes e isolamento do trabalho demorado.
- `engine.py`: API oficial `YoutubeDL`, hooks reais e pós-processadores oficiais.
- `config.py`, `store.py`: validação, preferências e persistência transacional SQLite/WAL.
- `diagnostics.py`: registros rotativos sem conteúdo sensível de mídia.
- `packaging/`: empacotamento, teste do binário e instalador.

Python aproveita a API nativa do yt-dlp sem interpretar mensagens de terminal. PySide6 fornece componentes desktop, acessibilidade e processos assíncronos. SQLite evita dependências de serviços e mantém histórico consistente. Processos separados permitem cancelar também o processamento FFmpeg, algo que uma thread Python isolada não garante.

## Limitações de mídia

A lista de extratores não garante que um conteúdo está acessível. Conteúdos privados exigem autorização e, quando suportado, cookies válidos. Não há remoção de DRM. Idiomas, resoluções e codecs vêm da análise real; não há opções artificiais de 4K/8K. Um contêiner ou incorporação pode ser incompatível com os codecs da mídia: o erro real será exibido, sem marcar a tarefa como concluída. Intervalos dependem da fonte e de keyframes. Progresso é por arquivo/faixa/item; não é uma estimativa global de uma playlist inteira. Listagens de playlists/canais usam extração simplificada; consultar formatos de cada item requer análise individual. Recodificação de vídeo (MP4, MKV, WebM, AVI, MOV), conversão de áudio e mesclagem são oferecidas separadamente; recodificação pode ser lenta e reduzir a qualidade.

## Releases no GitHub

A workflow `Release Windows` roda em Windows para tags `v*`. Ela instala as versões fixadas, obtém um build LGPL de FFmpeg com URL e SHA256 fixados em `packaging/prepare_runtime.py`, executa a suíte e testa downloads no executável empacotado. Gera instalador, ZIP portátil com FFmpeg/FFprobe incluídos, ZIP do código-fonte e `SHA256SUMS.txt`. Os artefatos só são enviados à release após o build passar. O ZIP portátil deve ser extraído por inteiro; abra `DownloaderVideo.exe` dentro da pasta extraída. Não é necessário instalar Python ou FFmpeg separadamente nesses dois pacotes.
