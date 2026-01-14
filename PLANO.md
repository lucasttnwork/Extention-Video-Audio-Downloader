# Plano: Video Downloader com Extensão de Navegador

## Visão Geral

Sistema para download de vídeos composto por:
1. **Extensão de navegador** (Chrome/Opera GX) - detecta vídeos na página
2. **Servidor Python local** (Flask) - processa downloads com yt-dlp
3. **GUI Desktop** (PySide6) - gerencia downloads com interface gráfica

```
┌─────────────────┐       HTTP/REST       ┌──────────────────┐
│   Extensão do   │ ──────────────────►   │  Servidor Flask  │
│   Navegador     │                       │  (Python)        │
│   (detecta)     │ ◄──────────────────   │                  │
└─────────────────┘                       └────────┬─────────┘
                                                   │
                                                   ▼
                                          ┌──────────────────┐
                                          │  yt-dlp + FFmpeg │
                                          │  (download)      │
                                          └────────┬─────────┘
                                                   │
                                                   ▼
                                          ┌──────────────────┐
                                          │   GUI PySide6    │
                                          │   (gerenciador)  │
                                          └──────────────────┘
```

---

## Estrutura de Arquivos

```
video-downloader/
├── extension/                    # Extensão Chrome/Opera
│   ├── manifest.json
│   ├── icons/
│   ├── src/
│   │   ├── background/
│   │   │   └── service-worker.js
│   │   ├── content/
│   │   │   └── content-script.js
│   │   └── popup/
│   │       ├── popup.html
│   │       ├── popup.js
│   │       └── popup.css
│
├── server/                       # Backend Python
│   ├── app.py                    # Flask app principal
│   ├── requirements.txt
│   ├── config.py
│   └── core/
│       ├── download_manager.py   # Gerenciador de downloads
│       ├── downloader.py         # Wrapper yt-dlp
│       └── auth_handler.py       # Gerenciamento de cookies
│
├── gui/                          # Interface Gráfica
│   ├── main.py
│   ├── requirements.txt
│   └── windows/
│       └── main_window.py
│
└── README.md
```

---

## Stack Tecnológica

| Componente | Tecnologia | Justificativa |
|------------|------------|---------------|
| Backend | Flask + Flask-CORS | Simples, leve, ideal para servidor local |
| Downloads | yt-dlp | Suporta 1000+ sites, ativamente mantido |
| Processamento | FFmpeg | Merge de áudio/vídeo, conversão |
| GUI | PySide6 | Qt6 oficial, licença LGPL permissiva |
| Cookies | browser-cookie3 | Extrai cookies de Chrome/Firefox/Opera |

---

## Passos de Implementação

### Fase 1: Servidor Backend

**Arquivos a criar:**
- `server/requirements.txt`
- `server/config.py`
- `server/app.py`
- `server/core/downloader.py`
- `server/core/download_manager.py`
- `server/core/auth_handler.py`

**Tarefas:**
1. Criar estrutura básica Flask com CORS
2. Implementar endpoints REST:
   - `GET /api/status` - status do servidor
   - `POST /api/download` - iniciar download
   - `GET /api/queue` - listar downloads
   - `POST /api/download/<id>/cancel` - cancelar
3. Implementar wrapper yt-dlp com callbacks de progresso
4. Criar gerenciador de fila com threading
5. Implementar handler de cookies/autenticação

### Fase 2: Extensão do Navegador

**Arquivos a criar:**
- `extension/manifest.json`
- `extension/src/background/service-worker.js`
- `extension/src/content/content-script.js`
- `extension/src/popup/popup.html`
- `extension/src/popup/popup.js`
- `extension/src/popup/popup.css`

**Tarefas:**
1. Criar manifest.json (Manifest V3)
2. Implementar content script para detectar elementos `<video>`
3. Implementar service worker para interceptar streams HLS/DASH
4. Criar popup com lista de vídeos detectados
5. Implementar extração e envio de cookies
6. Criar cliente API para comunicar com servidor local

### Fase 3: GUI Desktop

**Arquivos a criar:**
- `gui/requirements.txt`
- `gui/main.py`
- `gui/windows/main_window.py`

**Tarefas:**
1. Criar janela principal com PySide6
2. Implementar lista de downloads com progresso
3. Adicionar indicador de status do servidor
4. Criar system tray para rodar em background
5. Implementar notificações de conclusão

### Fase 4: Integração e Testes

**Tarefas:**
1. Testar fluxo completo extensão → servidor → download
2. Testar com sites específicos (Instagram, TikTok, Twitter)
3. Testar autenticação com cookies
4. Ajustar detectores específicos por site

---

## Fluxo de Download

1. Usuário navega para página com vídeo
2. Content script detecta elementos `<video>` e streams
3. Service worker intercepta requisições m3u8/mpd
4. Badge da extensão indica vídeos encontrados
5. Usuário clica no ícone da extensão
6. Popup mostra vídeos disponíveis
7. Usuário seleciona vídeo e qualidade
8. Extensão extrai cookies da sessão atual
9. Extensão envia `POST /api/download` com URL + cookies
10. Servidor adiciona à fila e processa com yt-dlp
11. GUI mostra progresso em tempo real
12. Notificação quando download completo

---

## Dependências Python

```
# server/requirements.txt
yt-dlp>=2024.12.01
Flask>=3.0.0
Flask-CORS>=4.0.0
browser-cookie3>=0.19.0
requests>=2.31.0

# gui/requirements.txt
PySide6>=6.6.0
requests>=2.31.0
```

---

## Requisitos do Sistema

- Python 3.10+
- FFmpeg instalado no sistema
- Chrome ou Opera GX
- macOS (Darwin)

---

## Considerações de Segurança

- Servidor bind apenas em `127.0.0.1` (localhost)
- Cookies armazenados temporariamente e deletados após uso
- CORS configurado apenas para extensão
- Validação de URLs antes de processar
