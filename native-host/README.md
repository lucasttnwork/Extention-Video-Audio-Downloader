# Native Messaging Host - Video Downloader

Este diretório contém o Native Messaging Host que permite que a extensão controle o servidor Flask local.

## Instalação

### 1. Executar o Script de Instalação

```bash
cd native-host
./install_host.sh
```

O script irá:
- Tornar o host executável
- Criar os diretórios necessários
- Criar symlinks para Chrome e Chromium

### 2. Obter o Extension ID

1. Abra o Chrome e vá para `chrome://extensions/`
2. Ative o "Modo do desenvolvedor"
3. Clique em "Carregar sem compactação"
4. Selecione o diretório `extension/`
5. Copie o **Extension ID** (algo como: `abcdefghijklmnopqrstuvwxyz123456`)

### 3. Atualizar o Manifest

Edite o arquivo `com.videodownloader.host.json` e substitua `EXTENSION_ID_PLACEHOLDER` pelo ID real:

```json
{
  "name": "com.videodownloader.host",
  "description": "Video Downloader Native Messaging Host",
  "path": "/Users/lucasttn/Documents/Documents/Antigravity - Projects/TESTE-Video-Downloader/native-host/video_downloader_host.py",
  "type": "stdio",
  "allowed_origins": [
    "chrome-extension://SEU_EXTENSION_ID_AQUI/"
  ]
}
```

### 4. Recarregar a Extensão

Volte em `chrome://extensions/` e clique no botão de recarregar da extensão.

## Como Usar

Após a instalação:

1. Clique no ícone da extensão no Chrome
2. No popup, você verá dois novos botões ao lado do status do servidor:
   - **▶ (Play)** - Inicia o servidor
   - **■ (Stop)** - Para o servidor
3. O botão verde fica habilitado quando o servidor está offline
4. O botão vermelho fica habilitado quando o servidor está online

## Arquivos

- **`video_downloader_host.py`** - Script Python que controla o servidor
- **`com.videodownloader.host.json`** - Manifest do Native Messaging Host
- **`install_host.sh`** - Script de instalação para macOS
- **`server.pid`** - Arquivo gerado automaticamente com o PID do servidor

## Verificação

Para verificar se está funcionando:

```bash
# Ver se o servidor está rodando
lsof -i :5050

# Ver o PID armazenado
cat server.pid
```

## Solução de Problemas

### "Native host não encontrado"

1. Verifique se o manifest está instalado:
   ```bash
   ls -la "$HOME/Library/Application Support/Google/Chrome/NativeMessagingHosts/com.videodownloader.host.json"
   ```

2. Verifique se o Extension ID está correto no manifest

3. Recarregue a extensão

### Servidor não inicia

1. Verifique se o Python 3 está instalado: `python3 --version`
2. Verifique se o caminho para `server/app.py` está correto
3. Teste manualmente: `./video_downloader_host.py`

### Permissões no macOS

Se o macOS bloquear o script, vá em:
**Preferências do Sistema → Segurança e Privacidade** e permita a execução.
