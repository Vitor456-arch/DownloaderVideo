# Validação

Ambiente: Linux, Python 3.12.14, PySide6 6.12.0, yt-dlp 2026.10.26, FFmpeg do sistema.

## Verificações executadas

Resultado da suíte: **30 testes aprovados** nesta sessão. A suíte não contém testes desativados para ocultar falhas.

A suíte automatizada usa HTTP local, yt-dlp real e FFmpeg real. Não substitui essas ferramentas por resultados simulados. O teste unitário da resposta de atualização usa uma resposta controlada; a consulta de atualização ao PyPI também foi executada separadamente com sucesso (versão instalada e última versão: 2026.10.26).

- URLs inválidas, esquemas proibidos e URLs com credenciais.
- Rejeição de comandos e chaves avançadas não permitidas.
- Validação de intervalos, nomes e combinações incompatíveis.
- Preferências persistidas, recuperação de tarefas interrompidas e limpeza de histórico.
- Análise real de mídia, seleção de formato, download de vídeo e verificação dos fluxos via FFprobe.
- Extração e conversão real para MP3, verificada via FFprobe.
- Recodificação real para WebM e download de um intervalo, com duração verificada.
- Manifesto DASH local com faixas separadas: consulta de resolução, seleção de IDs e mesclagem real de áudio/vídeo em MKV.
- Playlist HTML local com dois itens, análise e download de ambos.
- Erro HTTP 404 e falha real de pós-processamento de arquivo inválido.
- Detecção de FFmpeg e tratamento de ausência.
- Protocolo de processos e listagem de mais de mil extratores instalados.
- Limite da fila, término de pós-processamento e histórico com caminhos existentes.
- Cancelamento de download real com preservação de `.part`, repetição e conclusão.
- Cancelamento de análise e timer da interface funcionando durante trabalho demorado.
- Janela real em modo offscreen, análise por processo, tabela populada, configurações e busca de extratores.
- Redação de credenciais em mensagens de erro.

O empacotamento PyInstaller Linux também foi executado e seu worker carregou a lista real de extratores. O smoke test empacotado passou: análise, download de vídeo e conversão para MP3 via HTTP local. Foi necessário incluir no build Linux o recurso de confiança TLS adicional usado pelo Python gerenciado; a verificação de certificados permaneceu ativa.

As consultas ao PyPI funcionaram. As consultas online à API do GitHub foram bloqueadas por HTTP 403 do proxy do ambiente, antes de alcançar os endpoints. O tratamento de respostas de versões e tags foi verificado por teste unitário. A adição de `api.github.com` foi salva no rascunho de rede; depende de salvar/publicar a configuração para vigorar. Não se afirma que as consultas à API funcionaram nesta instância.

## Aceitação necessária no Windows

Não executada nesta sessão: build/instalador Windows, inicialização por atalho, integração com Explorador, troca de bibliotecas Qt, taskkill de FFmpeg no Windows, DPI e leitores de tela, instalação/desinstalação/upgrade em VM limpa e assinatura digital. A pipeline executa testes e um smoke test do worker empacotado quando enviada ao GitHub, mas sua existência não comprova que foi executada.

A validação de todas as plataformas do yt-dlp é externa ao projeto. Não foram testados conteúdo privado, cookies reais, restrições regionais, streaming ao vivo, DRM, todas as combinações de contêiner/codec, legendas e miniaturas de serviços externos. Não é alegada compatibilidade universal. Nenhuma mídia de terceiros é baixada nos testes.

Antes de publicar, testar manualmente no Windows: mídia autorizada de uma plataforma real; playlist com falha em um item; legendas e miniaturas em formatos compatíveis; metadados e capítulos; corte; fila concorrente; fechamento durante conversão; retomada após reinício; caminhos com acentos/espaços; falta de FFmpeg; falta de rede; permissões de destino; cookies autorizados; abertura dos arquivos finais. Conferir avisos/fontes das dependências incluídas e assinar o instalador.
