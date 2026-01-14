/**
 * Content Script - Detecta vídeos na página
 */

(function() {
  'use strict';

  const detectedVideos = new Map();
  let videoIdCounter = 0;

  /**
   * Verifica se estamos em uma página Hub.la
   */
  function isHublaPage() {
    return window.location.hostname.includes('hub.la');
  }

  /**
   * Lista de plataformas conhecidas que usam players especiais (Cloudflare Stream, SmartPlayer, etc)
   */
  const SPECIAL_PLAYER_PLATFORMS = [
    'hub.la',
    'codigoviral.com.br',
    'hotmart.com',
    'eduzz.com',
    'kiwify.com.br',
    'monetizze.com.br',
    'areademembros.com'
  ];

  /**
   * Padrões de URLs de streaming conhecidos
   */
  const STREAM_URL_PATTERNS = {
    cloudflare: /https?:\/\/customer-[a-z0-9]+\.cloudflarestream\.com\/[A-Za-z0-9_-]+\/manifest\/video\.m3u8/gi,
    smartplayer: /https?:\/\/stream\.smartplayer\.io\/[a-f0-9]+\/[a-f0-9]+\/[^"'\s]+\.(mp4|m3u8)/gi,
    scaleup: /https?:\/\/stream\.scaleup\.com\.br\/player\/v1\/playlists\/[^"'\s]+\.m3u8/gi
  };

  /**
   * Verifica se estamos em uma plataforma que usa players especiais
   */
  function isSpecialPlayerPlatform() {
    const hostname = window.location.hostname;
    return SPECIAL_PLAYER_PLATFORMS.some(p => hostname.includes(p));
  }

  /**
   * Alias para compatibilidade
   */
  function isCloudflareStreamPlatform() {
    return isSpecialPlayerPlatform();
  }

  /**
   * Gera um ID único para cada vídeo
   */
  function generateVideoId() {
    return `video_${Date.now()}_${++videoIdCounter}`;
  }

  /**
   * Verifica se é uma URL válida para download (não blob:, data:, etc)
   */
  function isValidDownloadUrl(url) {
    if (!url) return false;
    // Rejeita blob:, data:, chrome:, about:, javascript:
    if (url.startsWith('blob:') ||
        url.startsWith('data:') ||
        url.startsWith('chrome:') ||
        url.startsWith('about:') ||
        url.startsWith('javascript:')) {
      return false;
    }
    return url.startsWith('http://') || url.startsWith('https://');
  }

  /**
   * Extrai informações de um elemento de vídeo
   */
  function extractVideoInfo(videoElement) {
    const sources = [];

    // URL direta do vídeo (ignora blob: URLs)
    if (videoElement.src && isValidDownloadUrl(videoElement.src)) {
      sources.push({
        url: videoElement.src,
        type: 'direct'
      });
    }

    // Elementos <source> dentro do vídeo
    const sourceElements = videoElement.querySelectorAll('source');
    sourceElements.forEach(source => {
      if (source.src && isValidDownloadUrl(source.src)) {
        sources.push({
          url: source.src,
          type: source.type || 'unknown'
        });
      }
    });

    // currentSrc (URL atual sendo reproduzida) - ignora blob: URLs
    if (videoElement.currentSrc &&
        isValidDownloadUrl(videoElement.currentSrc) &&
        !sources.some(s => s.url === videoElement.currentSrc)) {
      sources.push({
        url: videoElement.currentSrc,
        type: 'current'
      });
    }

    return {
      sources,
      poster: videoElement.poster || null,
      duration: videoElement.duration || 0,
      width: videoElement.videoWidth || videoElement.width || 0,
      height: videoElement.videoHeight || videoElement.height || 0
    };
  }

  /**
   * Detecta vídeos na página
   */
  function detectVideos() {
    const videos = document.querySelectorAll('video');
    const newVideos = [];

    videos.forEach(video => {
      // Verifica se já processamos este vídeo
      if (video.dataset.videoDownloaderId) {
        return;
      }

      const info = extractVideoInfo(video);

      // Só adiciona se tiver pelo menos uma fonte
      if (info.sources.length > 0) {
        const id = generateVideoId();
        video.dataset.videoDownloaderId = id;

        const videoData = {
          id,
          pageUrl: window.location.href,
          pageTitle: document.title,
          ...info,
          timestamp: Date.now()
        };

        detectedVideos.set(id, videoData);
        newVideos.push(videoData);
      }
    });

    return newVideos;
  }

  /**
   * Detecta URLs de stream (m3u8, mpd) no código da página
   */
  function detectStreamUrls() {
    const streams = [];
    const pageContent = document.documentElement.innerHTML;

    // Padrões para detectar streams
    const patterns = [
      // HLS streams
      /https?:\/\/[^\s"'<>]+\.m3u8[^\s"'<>]*/gi,
      // DASH streams
      /https?:\/\/[^\s"'<>]+\.mpd[^\s"'<>]*/gi,
      // URLs de vídeo comuns
      /https?:\/\/[^\s"'<>]+\.(mp4|webm|mov)[^\s"'<>]*/gi
    ];

    patterns.forEach(pattern => {
      const matches = pageContent.match(pattern);
      if (matches) {
        matches.forEach(url => {
          // Limpa a URL
          const cleanUrl = url.replace(/['"\\]/g, '').split('?')[0] +
            (url.includes('?') ? '?' + url.split('?')[1]?.replace(/['"\\]/g, '') : '');

          if (!streams.some(s => s.url === cleanUrl)) {
            streams.push({
              url: cleanUrl,
              type: cleanUrl.includes('.m3u8') ? 'hls' :
                    cleanUrl.includes('.mpd') ? 'dash' : 'direct'
            });
          }
        });
      }
    });

    return streams;
  }

  /**
   * Detecta vídeos de players especiais (Cloudflare Stream, SmartPlayer, ScaleUp)
   * Funciona para Hub.la, Código Viral, Hotmart, e outras plataformas de cursos
   */
  function detectCloudflareStreamVideos() {
    const streams = [];

    // Verifica se é uma plataforma conhecida OU se a página contém URLs de streaming
    const isKnownPlatform = isSpecialPlayerPlatform();
    const pageContent = document.documentElement.innerHTML;
    const hasCloudflareContent = pageContent.includes('cloudflarestream.com');
    const hasSmartPlayerContent = pageContent.includes('smartplayer.io') || pageContent.includes('scaleup.com.br');

    // Se não é plataforma conhecida E não tem conteúdo de streaming, retorna vazio
    if (!isKnownPlatform && !hasCloudflareContent && !hasSmartPlayerContent) {
      return streams;
    }

    // Padrão para URLs do Cloudflare Stream com JWT
    const cloudflarePattern = STREAM_URL_PATTERNS.cloudflare;

    // Busca no HTML da página
    const htmlMatches = pageContent.match(cloudflarePattern);
    if (htmlMatches) {
      htmlMatches.forEach(url => {
        if (!streams.some(s => s.url === url)) {
          streams.push({
            url: url,
            type: 'hls',
            source: 'cloudflare_stream'
          });
        }
      });
    }

    // Busca em scripts inline
    const scripts = document.querySelectorAll('script:not([src])');
    scripts.forEach(script => {
      const matches = script.textContent.match(cloudflarePattern);
      if (matches) {
        matches.forEach(url => {
          if (!streams.some(s => s.url === url)) {
            streams.push({
              url: url,
              type: 'hls',
              source: 'cloudflare_stream'
            });
          }
        });
      }
    });

    // Busca em iframes do Cloudflare Stream
    const iframes = document.querySelectorAll('iframe[src*="cloudflarestream"]');
    iframes.forEach(iframe => {
      const src = iframe.src;
      if (src) {
        // Extrai o video ID do iframe
        const videoIdMatch = src.match(/\/([a-f0-9]{32})/i);
        if (videoIdMatch) {
          streams.push({
            url: src,
            type: 'cloudflare_iframe',
            source: 'cloudflare_stream',
            videoId: videoIdMatch[1]
          });
        }
      }
    });

    // Busca em elementos de vídeo com stream do Cloudflare
    const videos = document.querySelectorAll('video');
    videos.forEach(video => {
      const src = video.src || video.currentSrc;
      if (src && src.includes('cloudflarestream')) {
        if (!streams.some(s => s.url === src)) {
          streams.push({
            url: src,
            type: 'hls',
            source: 'cloudflare_stream'
          });
        }
      }
    });

    // Tenta extrair info de variáveis globais (Next.js, etc)
    try {
      if (window.__NEXT_DATA__) {
        const nextData = JSON.stringify(window.__NEXT_DATA__);
        const matches = nextData.match(cloudflarePattern);
        if (matches) {
          matches.forEach(url => {
            if (!streams.some(s => s.url === url)) {
              streams.push({
                url: url,
                type: 'hls',
                source: 'cloudflare_nextdata'
              });
            }
          });
        }
      }
    } catch (e) {
      // Ignora erros de acesso a variáveis
    }

    // Detecta SmartPlayer streams (mp4 e m3u8)
    const smartplayerMatches = pageContent.match(STREAM_URL_PATTERNS.smartplayer);
    if (smartplayerMatches) {
      smartplayerMatches.forEach(url => {
        // Limpa a URL de caracteres extras
        const cleanUrl = url.replace(/['"\\]/g, '');
        if (!streams.some(s => s.url === cleanUrl)) {
          // Prioriza URLs de áudio (192k) para extração de MP3
          const isAudio = cleanUrl.includes('_en_') || cleanUrl.includes('_192k');
          streams.push({
            url: cleanUrl,
            type: cleanUrl.includes('.m3u8') ? 'hls' : 'direct',
            source: 'smartplayer',
            isAudio: isAudio
          });
        }
      });
    }

    // Detecta ScaleUp playlists (m3u8)
    const scaleupMatches = pageContent.match(STREAM_URL_PATTERNS.scaleup);
    if (scaleupMatches) {
      scaleupMatches.forEach(url => {
        const cleanUrl = url.replace(/['"\\]/g, '');
        if (!streams.some(s => s.url === cleanUrl)) {
          streams.push({
            url: cleanUrl,
            type: 'hls',
            source: 'scaleup'
          });
        }
      });
    }

    return streams;
  }

  /**
   * Extrai título do vídeo em plataformas de cursos
   */
  function getVideoTitle() {
    // Tenta diferentes seletores comuns para título de aulas
    const selectors = [
      'h1',
      '[class*="title"]',
      '[class*="lesson-title"]',
      '[class*="video-title"]',
      '[class*="aula"]',
      '[class*="modulo"]'
    ];

    for (const selector of selectors) {
      const el = document.querySelector(selector);
      if (el && el.textContent.trim()) {
        return el.textContent.trim();
      }
    }

    return document.title;
  }

  /**
   * Obtém todos os vídeos detectados
   */
  function getAllVideos() {
    return Array.from(detectedVideos.values());
  }

  /**
   * Observer para detectar novos vídeos adicionados dinamicamente
   */
  const observer = new MutationObserver((mutations) => {
    let hasNewVideos = false;

    mutations.forEach(mutation => {
      mutation.addedNodes.forEach(node => {
        if (node.nodeType === Node.ELEMENT_NODE) {
          if (node.tagName === 'VIDEO' || node.querySelector?.('video')) {
            hasNewVideos = true;
          }
        }
      });
    });

    if (hasNewVideos) {
      const newVideos = detectVideos();
      if (newVideos.length > 0) {
        // Notifica o service worker sobre novos vídeos
        chrome.runtime.sendMessage({
          type: 'VIDEOS_DETECTED',
          videos: newVideos,
          pageUrl: window.location.href
        });
      }
    }
  });

  // Inicia observação do DOM
  observer.observe(document.body, {
    childList: true,
    subtree: true
  });

  // Detecta vídeos iniciais
  const initialVideos = detectVideos();
  const streamUrls = detectStreamUrls();
  const cloudflareVideos = detectCloudflareStreamVideos();

  // Combina todos os streams encontrados
  const allStreams = [...streamUrls];
  cloudflareVideos.forEach(cv => {
    if (!allStreams.some(s => s.url === cv.url)) {
      allStreams.push(cv);
    }
  });

  // Verifica se é uma plataforma de streaming (Hub.la, Código Viral, etc)
  const isStreamingPlatform = isCloudflareStreamPlatform() || isHublaPage();

  // Envia vídeos detectados para o service worker
  if (initialVideos.length > 0 || allStreams.length > 0) {
    chrome.runtime.sendMessage({
      type: 'VIDEOS_DETECTED',
      videos: initialVideos,
      streams: allStreams,
      pageUrl: window.location.href,
      pageTitle: isStreamingPlatform ? getVideoTitle() : document.title,
      isCloudflareStreamPlatform: isStreamingPlatform
    });
  }

  // Listener para mensagens do popup/service worker
  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type === 'GET_VIDEOS') {
      // Re-detecta vídeos para garantir dados atualizados
      detectVideos();
      const streams = detectStreamUrls();
      const cfStreams = detectCloudflareStreamVideos();

      // Combina streams
      const allStreams = [...streams];
      cfStreams.forEach(cf => {
        if (!allStreams.some(s => s.url === cf.url)) {
          allStreams.push(cf);
        }
      });

      const isStreamingPlatform = isCloudflareStreamPlatform() || isHublaPage();

      sendResponse({
        videos: getAllVideos(),
        streams: allStreams,
        pageUrl: window.location.href,
        pageTitle: isStreamingPlatform ? getVideoTitle() : document.title,
        isCloudflareStreamPlatform: isStreamingPlatform
      });
    }
    return true;
  });

  // Log para debug
  console.log('[Video Downloader] Content script carregado', {
    videos: initialVideos.length,
    streams: streamUrls.length,
    cloudflareVideos: cloudflareVideos.length,
    isCloudflareStreamPlatform: isCloudflareStreamPlatform()
  });
})();
