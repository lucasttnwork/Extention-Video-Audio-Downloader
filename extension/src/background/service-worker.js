/**
 * Service Worker - Background script para interceptação e gerenciamento
 */

const SERVER_URL = 'http://127.0.0.1:5050';
const NATIVE_HOST_NAME = 'com.videodownloader.host';

// Armazena vídeos detectados por tab
const tabVideos = new Map();

// Armazena streams interceptadas
const interceptedStreams = new Map();

/**
 * Atualiza o badge da extensão com a contagem de vídeos
 */
function updateBadge(tabId, count) {
  if (count > 0) {
    chrome.action.setBadgeText({ tabId, text: count.toString() });
    chrome.action.setBadgeBackgroundColor({ tabId, color: '#4CAF50' });
  } else {
    chrome.action.setBadgeText({ tabId, text: '' });
  }
}

/**
 * Verifica se é uma URL do Cloudflare Stream
 */
function isCloudflareStreamUrl(url) {
  return url.includes('cloudflarestream.com') && url.includes('/manifest/');
}

/**
 * Verifica se é uma URL do SmartPlayer/ScaleUp
 */
function isSmartPlayerUrl(url) {
  return url.includes('smartplayer.io') || url.includes('scaleup.com.br');
}

/**
 * Verifica se é uma URL de stream especial (Cloudflare, SmartPlayer, etc)
 */
function isSpecialStreamUrl(url) {
  return isCloudflareStreamUrl(url) || isSmartPlayerUrl(url);
}

/**
 * Verifica se é uma URL do Hub.la
 */
function isHublaUrl(url) {
  return url.includes('hub.la');
}

/**
 * Intercepta requisições de stream (m3u8, mpd, Cloudflare Stream, SmartPlayer)
 */
chrome.webRequest.onBeforeRequest.addListener(
  (details) => {
    const url = details.url.toLowerCase();
    const originalUrl = details.url;

    // Verifica se é um stream (inclui Cloudflare Stream, SmartPlayer, ScaleUp)
    const isStream = url.includes('.m3u8') || url.includes('.mpd') ||
                     url.includes('/manifest') || url.includes('playlist') ||
                     isCloudflareStreamUrl(url) || isSmartPlayerUrl(url);

    if (isStream) {
      const tabId = details.tabId;
      if (tabId > 0) {
        if (!interceptedStreams.has(tabId)) {
          interceptedStreams.set(tabId, []);
        }

        const streams = interceptedStreams.get(tabId);

        // Determina o tipo e fonte do stream
        let streamType = 'stream';
        let source = 'intercepted';

        if (isCloudflareStreamUrl(url)) {
          streamType = 'hls';
          source = 'cloudflare_stream';
        } else if (isSmartPlayerUrl(url)) {
          streamType = url.includes('.m3u8') ? 'hls' : 'direct';
          source = 'smartplayer';
        } else if (url.includes('.m3u8')) {
          streamType = 'hls';
        } else if (url.includes('.mpd')) {
          streamType = 'dash';
        }

        const streamData = {
          url: originalUrl,  // Usa URL original com case preservado
          type: streamType,
          source: source,
          timestamp: Date.now()
        };

        // Evita duplicatas
        if (!streams.some(s => s.url === originalUrl)) {
          streams.push(streamData);
          interceptedStreams.set(tabId, streams);

          // Log para debug de Cloudflare Stream
          if (source === 'cloudflare_stream') {
            console.log('[Video Downloader] Cloudflare Stream interceptado:', originalUrl.substring(0, 100) + '...');
          }

          // Atualiza badge
          const videos = tabVideos.get(tabId) || { videos: [], streams: [] };
          const totalCount = videos.videos.length + streams.length;
          updateBadge(tabId, totalCount);
        }
      }
    }
  },
  { urls: ['<all_urls>'] }
);

/**
 * Listener para mensagens do content script e popup
 */
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  const tabId = sender.tab?.id;

  switch (message.type) {
    case 'VIDEOS_DETECTED':
      if (tabId) {
        const existing = tabVideos.get(tabId) || { videos: [], streams: [] };
        const newVideos = message.videos || [];
        const newStreams = message.streams || [];

        // Merge com existentes
        newVideos.forEach(v => {
          if (!existing.videos.some(ev => ev.id === v.id)) {
            existing.videos.push(v);
          }
        });

        newStreams.forEach(s => {
          if (!existing.streams.some(es => es.url === s.url)) {
            existing.streams.push(s);
          }
        });

        existing.pageUrl = message.pageUrl;
        existing.pageTitle = message.pageTitle;

        tabVideos.set(tabId, existing);

        // Atualiza badge
        const intercepted = interceptedStreams.get(tabId) || [];
        const totalCount = existing.videos.length + existing.streams.length + intercepted.length;
        updateBadge(tabId, totalCount);
      }
      sendResponse({ success: true });
      break;

    case 'GET_TAB_VIDEOS':
      chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
        if (tabs[0]) {
          const activeTabId = tabs[0].id;
          const data = tabVideos.get(activeTabId) || { videos: [], streams: [] };
          const intercepted = interceptedStreams.get(activeTabId) || [];

          // Merge intercepted streams
          intercepted.forEach(s => {
            if (!data.streams.some(ds => ds.url === s.url)) {
              data.streams.push(s);
            }
          });

          sendResponse({
            ...data,
            tabUrl: tabs[0].url,
            tabTitle: tabs[0].title
          });
        } else {
          sendResponse({ videos: [], streams: [] });
        }
      });
      return true; // Indica resposta assíncrona

    case 'SEND_DOWNLOAD':
      handleDownloadRequest(message.data)
        .then(response => sendResponse(response))
        .catch(error => sendResponse({ success: false, error: error.message }));
      return true; // Indica resposta assíncrona

    case 'CHECK_SERVER':
      checkServerStatus()
        .then(status => sendResponse(status))
        .catch(error => sendResponse({ online: false, error: error.message }));
      return true;

    case 'GET_COOKIES':
      getCookiesForUrl(message.url)
        .then(cookies => sendResponse({ cookies }))
        .catch(error => sendResponse({ cookies: [], error: error.message }));
      return true;

    case 'START_SERVER':
      startServer()
        .then(response => sendResponse(response))
        .catch(error => sendResponse({ success: false, error: error.message }));
      return true;

    case 'STOP_SERVER':
      stopServer()
        .then(response => sendResponse(response))
        .catch(error => sendResponse({ success: false, error: error.message }));
      return true;

    case 'GET_NATIVE_STATUS':
      getNativeServerStatus()
        .then(response => sendResponse(response))
        .catch(error => sendResponse({ success: false, running: false, error: error.message }));
      return true;
  }
});

/**
 * Send a message to the native host
 */
function sendNativeMessage(action) {
  return new Promise((resolve, reject) => {
    chrome.runtime.sendNativeMessage(
      NATIVE_HOST_NAME,
      { action: action },
      (response) => {
        if (chrome.runtime.lastError) {
          reject(new Error(chrome.runtime.lastError.message));
        } else {
          resolve(response);
        }
      }
    );
  });
}

/**
 * Start the Flask server via native messaging
 */
async function startServer() {
  try {
    const response = await sendNativeMessage('start');
    return response;
  } catch (error) {
    return { success: false, error: error.message };
  }
}

/**
 * Stop the Flask server via native messaging
 */
async function stopServer() {
  try {
    const response = await sendNativeMessage('stop');
    return response;
  } catch (error) {
    return { success: false, error: error.message };
  }
}

/**
 * Get server status via native messaging
 */
async function getNativeServerStatus() {
  try {
    const response = await sendNativeMessage('status');
    return response;
  } catch (error) {
    return { success: false, running: false, error: error.message };
  }
}

/**
 * Verifica status do servidor
 */
async function checkServerStatus() {
  try {
    const response = await fetch(`${SERVER_URL}/api/status`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' }
    });

    if (response.ok) {
      const data = await response.json();
      return { online: true, ...data };
    }
    return { online: false };
  } catch (error) {
    return { online: false, error: error.message };
  }
}

/**
 * Obtém cookies para uma URL (retorna lista de objetos)
 */
async function getCookiesForUrl(url) {
  try {
    const cookies = await chrome.cookies.getAll({ url });
    // Retorna lista de objetos com todas as propriedades necessárias
    return cookies.map(c => ({
      name: c.name,
      value: c.value,
      domain: c.domain,
      path: c.path,
      secure: c.secure,
      httpOnly: c.httpOnly,
      expirationDate: c.expirationDate || 0
    }));
  } catch (error) {
    console.error('[Video Downloader] Erro ao obter cookies:', error);
    return [];
  }
}

/**
 * Verifica se a URL é um stream de vídeo (não uma página)
 */
function isVideoStreamUrl(url) {
  const lower = url.toLowerCase();
  return lower.includes('.m3u8') ||
         lower.includes('.mpd') ||
         lower.includes('cloudflarestream.com') ||
         lower.includes('.mp4') ||
         lower.includes('.webm');
}

/**
 * Verifica se é uma URL inválida (blob:, data:, etc)
 */
function isInvalidUrl(url) {
  if (!url) return true;
  return url.startsWith('blob:') ||
         url.startsWith('data:') ||
         url.startsWith('chrome:') ||
         url.startsWith('about:') ||
         url.startsWith('javascript:');
}

/**
 * Verifica se é uma URL de site suportado pelo yt-dlp (YouTube, Vimeo, etc)
 */
function isSupportedSite(url) {
  const supportedDomains = [
    'youtube.com', 'youtu.be',
    'vimeo.com',
    'dailymotion.com',
    'twitch.tv',
    'twitter.com', 'x.com',
    'facebook.com', 'fb.watch',
    'instagram.com',
    'tiktok.com'
  ];
  try {
    const hostname = new URL(url).hostname.toLowerCase();
    return supportedDomains.some(d => hostname.includes(d));
  } catch {
    return false;
  }
}

/**
 * Envia requisição de download para o servidor
 */
async function handleDownloadRequest(data) {
  try {
    // Obtém cookies para a URL (lista de objetos)
    let cookies = [];
    if (data.pageUrl) {
      cookies = await getCookiesForUrl(data.pageUrl);
    }
    // Também tenta obter cookies da URL do vídeo
    if (data.url && data.url !== data.pageUrl && !isInvalidUrl(data.url)) {
      const videoCookies = await getCookiesForUrl(data.url);
      // Merge sem duplicatas
      videoCookies.forEach(vc => {
        if (!cookies.some(c => c.name === vc.name && c.domain === vc.domain)) {
          cookies.push(vc);
        }
      });
    }

    // Determina qual URL usar para o download
    let downloadUrl = data.url;
    let videoUrl = null;

    // STREAMS ESPECIAIS (Cloudflare, SmartPlayer): Usa a URL do stream diretamente
    // pois são URLs diretas para o vídeo/áudio
    if (isSpecialStreamUrl(data.url)) {
      console.log('[Video Downloader] Stream especial detectado:',
        isCloudflareStreamUrl(data.url) ? 'Cloudflare' : 'SmartPlayer');
      // Para SmartPlayer, a URL do stream é direta e pode ser baixada
      downloadUrl = data.url;
      videoUrl = null;
    }
    // Se a URL é inválida (blob:, etc) ou é de um site suportado pelo yt-dlp,
    // usa a URL da página ao invés da URL do elemento de vídeo
    else if (isInvalidUrl(data.url) || isSupportedSite(data.pageUrl)) {
      downloadUrl = data.pageUrl;
      // Só inclui videoUrl se for um stream válido (não blob:)
      if (!isInvalidUrl(data.url) && isVideoStreamUrl(data.url)) {
        videoUrl = data.url;
      }
    } else if (isVideoStreamUrl(data.url)) {
      // É um stream direto (m3u8, mp4, etc) - usa a URL do stream
      downloadUrl = data.url;
    } else if (isHublaUrl(data.pageUrl)) {
      // Hub.la - usa a URL da página
      downloadUrl = data.pageUrl;
      if (!isInvalidUrl(data.url)) {
        videoUrl = data.url;
      }
    }

    const payload = {
      url: downloadUrl,
      videoUrl: videoUrl,
      title: data.title || 'video',
      cookies: cookies,
      outputFormat: data.format || 'mp4'
    };

    console.log('[Video Downloader] Enviando download:', {
      url: payload.url,
      videoUrl: payload.videoUrl ? payload.videoUrl.substring(0, 80) + '...' : null,
      title: payload.title,
      originalUrl: data.url,
      pageUrl: data.pageUrl,
      format: data.format,
      outputFormat: payload.outputFormat
    });

    const response = await fetch(`${SERVER_URL}/api/download`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    const result = await response.json();

    if (response.ok) {
      // Notificação de sucesso
      chrome.notifications.create({
        type: 'basic',
        iconUrl: 'icons/icon128.png',  // Caminho relativo à raiz da extensão
        title: 'Download Iniciado',
        message: `${data.title || 'Vídeo'} adicionado à fila de download`
      });
    } else if (result.extraction_required) {
      // Hub.la precisa de extração
      chrome.notifications.create({
        type: 'basic',
        iconUrl: 'icons/icon128.png',
        title: 'Aguarde o vídeo carregar',
        message: result.hint || 'Aguarde o vídeo carregar na página e tente novamente'
      });
    }

    return result;
  } catch (error) {
    console.error('[Video Downloader] Erro ao enviar download:', error);
    return { success: false, error: error.message };
  }
}

/**
 * Limpa dados quando a tab é fechada
 */
chrome.tabs.onRemoved.addListener((tabId) => {
  tabVideos.delete(tabId);
  interceptedStreams.delete(tabId);
});

/**
 * Limpa dados quando a tab navega para outra URL
 */
chrome.tabs.onUpdated.addListener((tabId, changeInfo) => {
  if (changeInfo.status === 'loading') {
    tabVideos.delete(tabId);
    interceptedStreams.delete(tabId);
    updateBadge(tabId, 0);
  }
});

// Log de inicialização
console.log('[Video Downloader] Service worker iniciado');
