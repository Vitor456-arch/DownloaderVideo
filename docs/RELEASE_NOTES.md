Primeira versão do DownloaderVideo para Windows x64.

### Baixar e usar

- **Instalador:** `DownloaderVideo-1.0.0-windows-x64-setup.exe`. Execute e siga a instalação por usuário.
- **ZIP portátil:** `DownloaderVideo-1.0.0-windows-x64-portable.zip`. Extraia a pasta inteira e abra `DownloaderVideo.exe`.
- Ambos incluem Python, Qt, yt-dlp, FFmpeg e FFprobe. Não é necessário instalar essas ferramentas separadamente.
- `SHA256SUMS.txt` permite conferir a integridade dos arquivos.
- `DownloaderVideo-1.0.0-source.zip` contém o código-fonte e os scripts de build.

### Recursos

Análise de mídia e formatos reais, downloads de vídeo e áudio, playlists, conversão com FFmpeg, fila simultânea, cancelamento e retomada, histórico, preferências persistentes, legendas, miniaturas e consulta dinâmica de extratores do yt-dlp.

### Validação e observações

Pacotes gerados no GitHub Actions em Windows, com testes automatizados e smoke test do executável (análise, download de vídeo e conversão para MP3). Compatibilidade de cada site depende do yt-dlp e das permissões de acesso. Algumas plataformas podem exigir cookies autorizados ou um runtime JavaScript adicional. Os arquivos não têm assinatura digital de editor; o Windows pode exibir a identificação de editor desconhecido.

Licenças e avisos de terceiros acompanham os pacotes. Consulte o README para detalhes, limitações e compilação.
