/**
 * Popup Script - Interface e lógica do popup
 */

document.addEventListener('DOMContentLoaded', () => {
  // Elementos DOM
  const serverStatusEl = document.getElementById('serverStatus');
  const pageTitleEl = document.getElementById('pageTitle');
  const videosListEl = document.getElementById('videosList');
  const btnRefresh = document.getElementById('btnRefresh');
  const manualUrlInput = document.getElementById('manualUrl');
  const btnManualDownload = document.getElementById('btnManualDownload');
  const optionsModal = document.getElementById('optionsModal');
  const qualitySelect = document.getElementById('qualitySelect');
  const formatSelect = document.getElementById('formatSelect');
  const btnCancelDownload = document.getElementById('btnCancelDownload');
  const btnConfirmDownload = document.getElementById('btnConfirmDownload');
  const downloadsListEl = document.getElementById('downloadsList');
  const btnOpenFolder = document.getElementById('btnOpenFolder');
  const btnClearHistory = document.getElementById('btnClearHistory');
  const pathValueEl = document.getElementById('pathValue');
  const btnStartServer = document.getElementById('btnStartServer');
  const btnStopServer = document.getElementById('btnStopServer');

  const SERVER_URL = 'http://127.0.0.1:5050';

  // Estado
  let currentDownloadUrl = null;
  let currentPageUrl = null;
  let currentPageTitle = null;
  let mainVideoStream = null; // Stream principal de vídeo detectado
  let mainAudioStream = null; // Stream principal de áudio detectado (para SmartPlayer)

  /**
   * Verifica se é uma URL de imagem (para filtrar)
   */
  function isImageUrl(url) {
    const imageExtensions = ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.ico', '.bmp'];
    const lower = url.toLowerCase();
    return imageExtensions.some(ext => lower.includes(ext));
  }

  /**
   * Verifica se é uma URL de vídeo/stream válida
   */
  function isValidVideoUrl(url) {
    if (!url || isImageUrl(url)) return false;
    const lower = url.toLowerCase();
    // Aceita apenas URLs de vídeo/stream
    return lower.includes('.mp4') ||
           lower.includes('.m3u8') ||
           lower.includes('.mpd') ||
           lower.includes('.webm') ||
           lower.includes('smartplayer.io') ||
           lower.includes('cloudflarestream.com') ||
           lower.includes('scaleup.com.br');
  }

  /**
   * Classifica stream por prioridade (para encontrar o principal)
   * Maior = melhor
   */
  function getStreamPriority(stream) {
    const url = stream.url.toLowerCase();
    let priority = 0;

    // SmartPlayer/ScaleUp - alta prioridade
    if (url.includes('smartplayer.io') || url.includes('scaleup.com.br')) {
      priority += 100;
      // Prefere versões de vídeo (não áudio)
      if (!url.includes('_en_') && !url.includes('_192k')) {
        priority += 50;
      }
      // Prefere MP4 sobre m3u8 para download direto
      if (url.includes('.mp4')) {
        priority += 20;
      }
    }

    // Cloudflare Stream
    if (url.includes('cloudflarestream.com')) {
      priority += 100;
    }

    // m3u8 genérico
    if (url.includes('.m3u8')) {
      priority += 30;
    }

    // MP4 direto
    if (url.includes('.mp4')) {
      priority += 40;
    }

    return priority;
  }

  /**
   * Verifica se é uma URL de áudio do SmartPlayer
   */
  function isSmartPlayerAudioUrl(url) {
    const lower = url.toLowerCase();
    return (lower.includes('smartplayer.io') || lower.includes('scaleup.com.br')) &&
           (lower.includes('_en_') || lower.includes('_192k') || lower.includes('_audio'));
  }

  /**
   * Verifica se é uma URL de vídeo do SmartPlayer (não áudio)
   */
  function isSmartPlayerVideoUrl(url) {
    const lower = url.toLowerCase();
    return (lower.includes('smartplayer.io') || lower.includes('scaleup.com.br')) &&
           !isSmartPlayerAudioUrl(url);
  }

  /**
   * Encontra o stream principal de vídeo
   */
  function findMainVideoStream(streams) {
    // Filtra apenas URLs de vídeo válidas (exclui streams de áudio do SmartPlayer)
    const videoStreams = streams.filter(s =>
      isValidVideoUrl(s.url) && !isSmartPlayerAudioUrl(s.url)
    );

    if (videoStreams.length === 0) return null;

    // Ordena por prioridade (maior primeiro)
    videoStreams.sort((a, b) => getStreamPriority(b) - getStreamPriority(a));

    return videoStreams[0];
  }

  /**
   * Encontra o stream de áudio do SmartPlayer
   */
  function findSmartPlayerAudioStream(streams) {
    const audioStreams = streams.filter(s => isSmartPlayerAudioUrl(s.url));

    if (audioStreams.length === 0) return null;

    // Prefere MP4 sobre m3u8
    audioStreams.sort((a, b) => {
      const aHasMp4 = a.url.toLowerCase().includes('.mp4');
      const bHasMp4 = b.url.toLowerCase().includes('.mp4');
      if (aHasMp4 && !bHasMp4) return -1;
      if (!aHasMp4 && bHasMp4) return 1;
      return 0;
    });

    return audioStreams[0];
  }

  /**
   * Verifica status do servidor
   */
  async function checkServerStatus() {
    const indicator = serverStatusEl.querySelector('.status-indicator');
    const text = serverStatusEl.querySelector('.status-text');

    try {
      const response = await chrome.runtime.sendMessage({ type: 'CHECK_SERVER' });

      if (response.online) {
        indicator.classList.remove('offline');
        indicator.classList.add('online');
        text.textContent = 'Servidor Online';
        updateServerButtons(true);

        // Atualiza o caminho de downloads
        if (response.download_dir) {
          updateDownloadPath(response.download_dir);
        }
      } else {
        indicator.classList.remove('online');
        indicator.classList.add('offline');
        text.textContent = 'Servidor Offline';
        updateServerButtons(false);
      }
    } catch (error) {
      indicator.classList.remove('online');
      indicator.classList.add('offline');
      text.textContent = 'Erro de conexão';
      updateServerButtons(false);
    }
  }

  /**
   * Update server button states based on server status
   */
  function updateServerButtons(isOnline) {
    if (isOnline) {
      btnStartServer.disabled = true;
      btnStopServer.disabled = false;
    } else {
      btnStartServer.disabled = false;
      btnStopServer.disabled = true;
    }
  }

  /**
   * Aguarda até que o servidor esteja offline
   * @param {number} maxAttempts - Número máximo de tentativas
   * @param {number} intervalMs - Intervalo entre tentativas em ms
   * @returns {Promise<boolean>} - True se servidor está offline
   */
  async function waitForServerOffline(maxAttempts = 10, intervalMs = 1000) {
    for (let i = 0; i < maxAttempts; i++) {
      // Verifica imediatamente na primeira tentativa, depois aguarda
      if (i > 0) {
        await new Promise(resolve => setTimeout(resolve, intervalMs));
      }

      try {
        const response = await chrome.runtime.sendMessage({ type: 'CHECK_SERVER' });
        console.log(`[POLLING ${i + 1}/${maxAttempts}] Server online:`, response.online);
        if (!response.online) {
          return true; // Servidor está offline
        }
      } catch (error) {
        console.log(`[POLLING ${i + 1}/${maxAttempts}] Erro (servidor offline):`, error.message);
        return true; // Erro ao verificar = servidor offline
      }
    }
    return false; // Timeout
  }

  /**
   * Start the server
   */
  async function startServer() {
    try {
      btnStartServer.disabled = true;
      btnStartServer.classList.add('loading');

      const response = await chrome.runtime.sendMessage({ type: 'START_SERVER' });

      if (response.success) {
        showToast('Servidor iniciado!', 'success');
        setTimeout(checkServerStatus, 2000);
      } else {
        showToast(response.error || 'Erro ao iniciar servidor', 'error');
        btnStartServer.disabled = false;
      }
    } catch (error) {
      showToast('Erro: Native host não encontrado', 'error');
      btnStartServer.disabled = false;
    } finally {
      btnStartServer.classList.remove('loading');
    }
  }

  /**
   * Stop the server
   */
  async function stopServer() {
    const indicator = serverStatusEl.querySelector('.status-indicator');
    const text = serverStatusEl.querySelector('.status-text');

    console.log('[STOP] Iniciando processo de parada...');

    try {
      // Desabilita ambos os botões e mostra loading
      btnStopServer.disabled = true;
      btnStartServer.disabled = true;
      btnStopServer.classList.add('loading');

      // Atualiza status visual
      text.textContent = 'Parando servidor...';

      // Envia comando de stop
      console.log('[STOP] Enviando comando STOP_SERVER...');
      const response = await chrome.runtime.sendMessage({ type: 'STOP_SERVER' });
      console.log('[STOP] Resposta do native host:', response);

      if (!response.success) {
        throw new Error(response.error || 'Erro ao parar servidor');
      }

      // Aguarda confirmação de que servidor parou (até 15 segundos, verificando a cada 500ms)
      console.log('[STOP] Iniciando polling para verificar se servidor parou...');
      const stopped = await waitForServerOffline(30, 500);
      console.log('[STOP] Resultado do polling:', stopped ? 'OFFLINE' : 'AINDA ONLINE');

      if (stopped) {
        // Sucesso: servidor confirmadamente offline
        showToast('Servidor parado!', 'success');
        await checkServerStatus(); // Atualiza UI
      } else {
        // Timeout: servidor não parou em 10 segundos
        showToast('Servidor não respondeu. Pode ainda estar ativo.', 'warning');
        btnStopServer.disabled = false; // Permite nova tentativa
        await checkServerStatus(); // Verifica estado real
      }
    } catch (error) {
      console.error('[STOP] Erro:', error);
      showToast(`Erro: ${error.message}`, 'error');
      btnStopServer.disabled = false; // Re-habilita para tentar novamente
      await checkServerStatus(); // Atualiza estado real
    } finally {
      btnStopServer.classList.remove('loading');
      btnStartServer.disabled = false; // Re-habilita Start
      console.log('[STOP] Processo de parada finalizado');
    }
  }

  /**
   * Carrega vídeos da aba atual
   */
  async function loadVideos() {
    try {
      // Primeiro tenta obter do service worker
      const swResponse = await chrome.runtime.sendMessage({ type: 'GET_TAB_VIDEOS' });

      // Depois tenta obter do content script
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

      if (tab) {
        currentPageUrl = tab.url;
        currentPageTitle = tab.title;
        pageTitleEl.textContent = tab.title || tab.url;

        // Tenta comunicar com content script
        try {
          const csResponse = await chrome.tabs.sendMessage(tab.id, { type: 'GET_VIDEOS' });

          // Merge dos resultados
          const allVideos = [...(swResponse.videos || [])];
          const allStreams = [...(swResponse.streams || [])];

          // Adiciona vídeos do content script
          if (csResponse.videos) {
            csResponse.videos.forEach(v => {
              if (!allVideos.some(av => av.id === v.id)) {
                allVideos.push(v);
              }
            });
          }

          // Adiciona streams do content script
          if (csResponse.streams) {
            csResponse.streams.forEach(s => {
              if (!allStreams.some(as => as.url === s.url)) {
                allStreams.push(s);
              }
            });
          }

          renderVideos(allVideos, allStreams);
        } catch (e) {
          // Content script não disponível, usa apenas dados do service worker
          renderVideos(swResponse.videos || [], swResponse.streams || []);
        }
      }
    } catch (error) {
      console.error('Erro ao carregar vídeos:', error);
      renderVideos([], []);
    }
  }

  /**
   * Normaliza URL para comparação (remove variações que são o mesmo vídeo)
   */
  function normalizeUrl(url) {
    try {
      const u = new URL(url);
      // Para Cloudflare Stream, o path contém o JWT - usar apenas o path base
      if (u.hostname.includes('cloudflarestream.com')) {
        // Extrai apenas o padrão: /JWT/manifest/video.m3u8
        const pathMatch = u.pathname.match(/\/[^\/]+\/manifest\/video\.m3u8/);
        if (pathMatch) {
          return u.hostname + pathMatch[0];
        }
      }
      // Para outras URLs, usar origin + pathname (sem query params)
      return u.origin + u.pathname;
    } catch {
      return url.toLowerCase();
    }
  }

  /**
   * Renderiza interface simplificada de download
   */
  function renderVideos(videos, streams) {
    videosListEl.innerHTML = '';

    // Combina vídeos e streams em uma lista
    const allItems = [];

    // Adiciona vídeos detectados (elementos <video>)
    videos.forEach(video => {
      video.sources.forEach(source => {
        if (isValidVideoUrl(source.url)) {
          allItems.push({
            url: source.url,
            type: source.type,
            source: 'video_element'
          });
        }
      });
    });

    // Adiciona streams interceptados
    streams.forEach(stream => {
      if (isValidVideoUrl(stream.url)) {
        const normalizedNew = normalizeUrl(stream.url);
        if (!allItems.some(i => normalizeUrl(i.url) === normalizedNew)) {
          allItems.push({
            url: stream.url,
            type: stream.type,
            source: stream.source || 'intercepted'
          });
        }
      }
    });

    // Remove duplicatas
    const uniqueItems = allItems.filter((item, index, self) =>
      index === self.findIndex(i => normalizeUrl(i.url) === normalizeUrl(item.url))
    );

    // Encontra o stream principal de vídeo e áudio
    mainVideoStream = findMainVideoStream(uniqueItems);
    mainAudioStream = findSmartPlayerAudioStream(uniqueItems);

    console.log('[Video Downloader] Streams encontrados:', {
      video: mainVideoStream?.url?.substring(0, 80),
      audio: mainAudioStream?.url?.substring(0, 80)
    });

    if (!mainVideoStream) {
      videosListEl.innerHTML = `
        <div class="empty-state">
          <p>Nenhum vídeo detectado nesta página.</p>
          <p class="hint">Aguarde o vídeo carregar e clique em atualizar.</p>
        </div>
      `;
      return;
    }

    // Renderiza interface simplificada com 2 opções
    const videoEl = document.createElement('div');
    videoEl.className = 'video-item simplified';

    const streamSource = getSourceLabel(mainVideoStream);

    videoEl.innerHTML = `
      <div class="video-info-simplified">
        <div class="video-detected">
          <span class="video-badge">${streamSource}</span>
          <span class="video-status">Vídeo detectado</span>
        </div>
        <div class="download-options">
          <button class="btn-download-option video" data-format="mp4" title="Baixar vídeo MP4">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polygon points="23 7 16 12 23 17 23 7"/>
              <rect x="1" y="5" width="15" height="14" rx="2" ry="2"/>
            </svg>
            <span>Vídeo MP4</span>
          </button>
          <button class="btn-download-option audio" data-format="mp3" title="Baixar áudio MP3">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M9 18V5l12-2v13"/>
              <circle cx="6" cy="18" r="3"/>
              <circle cx="18" cy="16" r="3"/>
            </svg>
            <span>Áudio MP3</span>
          </button>
        </div>
      </div>
    `;

    // Event listeners para os botões
    const btnVideo = videoEl.querySelector('.btn-download-option.video');
    const btnAudio = videoEl.querySelector('.btn-download-option.audio');

    btnVideo.addEventListener('click', () => {
      sendDownloadDirect(mainVideoStream.url, 'mp4');
    });

    btnAudio.addEventListener('click', () => {
      // Para SmartPlayer/ScaleUp, usa o stream de áudio se disponível
      // pois eles separam vídeo e áudio em arquivos diferentes
      const audioUrl = mainAudioStream ? mainAudioStream.url : mainVideoStream.url;
      console.log('[Video Downloader] Iniciando download MP3 com URL:', audioUrl?.substring(0, 80));
      sendDownloadDirect(audioUrl, 'mp3');
    });

    videosListEl.appendChild(videoEl);
  }

  /**
   * Retorna label da fonte do stream
   */
  function getSourceLabel(stream) {
    const url = stream.url.toLowerCase();
    if (url.includes('smartplayer.io')) return 'SmartPlayer';
    if (url.includes('scaleup.com.br')) return 'ScaleUp';
    if (url.includes('cloudflarestream.com')) return 'Cloudflare';
    if (url.includes('.m3u8')) return 'HLS';
    if (url.includes('.mp4')) return 'MP4';
    return 'Stream';
  }

  /**
   * Envia download direto (sem modal)
   */
  async function sendDownloadDirect(url, format) {
    try {
      const response = await chrome.runtime.sendMessage({
        type: 'SEND_DOWNLOAD',
        data: {
          url: url,
          title: currentPageTitle || 'video',
          pageUrl: currentPageUrl,
          format: format
        }
      });

      if (response.success) {
        showToast(`Download ${format.toUpperCase()} iniciado!`, 'success');
        // Atualiza lista de downloads imediatamente
        loadDownloads();
      } else {
        showToast(response.error || 'Erro ao iniciar download', 'error');
      }
    } catch (error) {
      showToast('Erro de comunicação com o servidor', 'error');
    }
  }

  /**
   * Carrega a fila de downloads do servidor
   */
  async function loadDownloads() {
    try {
      const response = await fetch(`${SERVER_URL}/api/queue`);
      if (!response.ok) return;

      const data = await response.json();
      renderDownloads(data.downloads || []);
    } catch (error) {
      console.error('Erro ao carregar downloads:', error);
    }
  }

  /**
   * Renderiza a lista de downloads
   */
  function renderDownloads(downloads) {
    if (!downloads || downloads.length === 0) {
      downloadsListEl.innerHTML = '<div class="empty-downloads">Nenhum download ativo</div>';
      return;
    }

    // Ordena: ativos primeiro, depois completados
    const sorted = downloads.sort((a, b) => {
      const order = { 'downloading': 0, 'processing': 1, 'pending': 2, 'completed': 3, 'error': 4 };
      return (order[a.status] || 5) - (order[b.status] || 5);
    });

    // Limita a 5 downloads mais recentes
    const recent = sorted.slice(0, 5);

    downloadsListEl.innerHTML = recent.map(dl => {
      const statusClass = getStatusClass(dl.status);
      const statusText = getStatusText(dl.status);
      const progress = dl.progress || 0;
      const filename = dl.filename || truncateTitle(dl.title || 'Download');

      return `
        <div class="download-item ${statusClass}">
          <div class="download-info">
            <span class="download-name" title="${dl.filename || dl.title}">${filename}</span>
            <span class="download-status">${statusText}</span>
          </div>
          ${dl.status === 'downloading' || dl.status === 'processing' ? `
            <div class="download-progress">
              <div class="progress-bar">
                <div class="progress-fill" style="width: ${progress}%"></div>
              </div>
              <span class="progress-text">${Math.round(progress)}%</span>
            </div>
          ` : ''}
          ${dl.status === 'completed' ? `
            <div class="download-complete">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="20 6 9 17 4 12"/>
              </svg>
            </div>
          ` : ''}
          ${dl.status === 'error' ? `
            <div class="download-error" title="${dl.error || 'Erro desconhecido'}">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"/>
                <line x1="15" y1="9" x2="9" y2="15"/>
                <line x1="9" y1="9" x2="15" y2="15"/>
              </svg>
            </div>
          ` : ''}
        </div>
      `;
    }).join('');
  }

  /**
   * Trunca título do download
   */
  function truncateTitle(title) {
    if (title.length > 30) {
      return title.substring(0, 27) + '...';
    }
    return title;
  }

  /**
   * Retorna classe CSS para status
   */
  function getStatusClass(status) {
    const classes = {
      'pending': 'status-pending',
      'downloading': 'status-downloading',
      'processing': 'status-processing',
      'completed': 'status-completed',
      'error': 'status-error',
      'cancelled': 'status-cancelled'
    };
    return classes[status] || '';
  }

  /**
   * Retorna texto do status
   */
  function getStatusText(status) {
    const texts = {
      'pending': 'Aguardando...',
      'downloading': 'Baixando...',
      'processing': 'Processando...',
      'completed': 'Concluído',
      'error': 'Erro',
      'cancelled': 'Cancelado'
    };
    return texts[status] || status;
  }

  /**
   * Abre a pasta de downloads
   */
  async function openDownloadsFolder() {
    try {
      const response = await fetch(`${SERVER_URL}/api/open-folder`, {
        method: 'POST'
      });
      const data = await response.json();

      if (data.success) {
        showToast('Pasta aberta!', 'success');
      } else {
        showToast('Erro ao abrir pasta', 'error');
      }
    } catch (error) {
      showToast('Servidor offline', 'error');
    }
  }

  /**
   * Limpa o histórico de downloads
   */
  async function clearDownloadHistory() {
    try {
      const response = await fetch(`${SERVER_URL}/api/clear`, {
        method: 'POST'
      });
      const data = await response.json();

      if (data.success) {
        showToast('Histórico limpo!', 'success');
        loadDownloads();
      } else {
        showToast('Erro ao limpar histórico', 'error');
      }
    } catch (error) {
      showToast('Servidor offline', 'error');
    }
  }

  /**
   * Atualiza o caminho da pasta de downloads
   */
  function updateDownloadPath(path) {
    if (pathValueEl && path) {
      // Mostra apenas o final do caminho
      const parts = path.split('/');
      const shortPath = parts.slice(-2).join('/');
      pathValueEl.textContent = '~/' + shortPath;
      pathValueEl.title = path;
    }
  }

  /**
   * Retorna classe CSS baseada no tipo
   */
  function getTypeClass(type) {
    if (type === 'hls' || type.includes('m3u8')) return 'hls';
    if (type === 'dash' || type.includes('mpd')) return 'dash';
    if (type === 'stream') return 'stream';
    return 'direct';
  }

  /**
   * Retorna label do tipo
   */
  function getTypeLabel(type) {
    if (type === 'hls' || type.includes('m3u8')) return 'HLS';
    if (type === 'dash' || type.includes('mpd')) return 'DASH';
    if (type === 'stream') return 'Stream';
    if (type === 'direct' || type === 'current') return 'Direto';
    return type.toUpperCase();
  }

  /**
   * Trunca URL para exibição
   */
  function truncateUrl(url) {
    try {
      const urlObj = new URL(url);
      const path = urlObj.pathname;
      const filename = path.split('/').pop() || path;

      if (filename.length > 40) {
        return filename.substring(0, 37) + '...';
      }
      return filename || urlObj.hostname;
    } catch {
      return url.substring(0, 40) + (url.length > 40 ? '...' : '');
    }
  }

  /**
   * Constrói texto de metadados
   */
  function buildMetaText(item) {
    const parts = [];

    if (item.meta) {
      parts.push(item.meta);
    }

    if (item.duration && item.duration > 0) {
      const minutes = Math.floor(item.duration / 60);
      const seconds = Math.floor(item.duration % 60);
      parts.push(`${minutes}:${seconds.toString().padStart(2, '0')}`);
    }

    return parts.join(' • ');
  }

  /**
   * Abre modal de opções de download
   */
  function openDownloadModal(url) {
    currentDownloadUrl = url;
    optionsModal.classList.add('active');
  }

  /**
   * Fecha modal de opções
   */
  function closeDownloadModal() {
    optionsModal.classList.remove('active');
    currentDownloadUrl = null;
  }

  /**
   * Envia download para o servidor
   */
  async function sendDownload(url) {
    const quality = qualitySelect.value;
    const format = formatSelect.value;

    try {
      const response = await chrome.runtime.sendMessage({
        type: 'SEND_DOWNLOAD',
        data: {
          url: url,
          title: currentPageTitle || 'video',
          pageUrl: currentPageUrl,
          quality: quality,
          format: format
        }
      });

      if (response.success) {
        showToast('Download adicionado à fila!', 'success');
      } else {
        showToast(response.error || 'Erro ao iniciar download', 'error');
      }
    } catch (error) {
      showToast('Erro de comunicação com o servidor', 'error');
    }

    closeDownloadModal();
  }

  /**
   * Exibe toast notification
   */
  function showToast(message, type = 'info') {
    // Remove toast existente
    const existingToast = document.querySelector('.toast');
    if (existingToast) {
      existingToast.remove();
    }

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);

    // Força reflow
    toast.offsetHeight;

    toast.classList.add('show');

    setTimeout(() => {
      toast.classList.remove('show');
      setTimeout(() => toast.remove(), 300);
    }, 3000);
  }

  // Event Listeners
  btnRefresh.addEventListener('click', () => {
    loadVideos();
    showToast('Lista atualizada');
  });

  btnManualDownload.addEventListener('click', () => {
    const url = manualUrlInput.value.trim();
    if (url) {
      openDownloadModal(url);
    }
  });

  manualUrlInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
      const url = manualUrlInput.value.trim();
      if (url) {
        openDownloadModal(url);
      }
    }
  });

  btnCancelDownload.addEventListener('click', closeDownloadModal);

  btnConfirmDownload.addEventListener('click', () => {
    if (currentDownloadUrl) {
      sendDownload(currentDownloadUrl);
    }
  });

  // Fecha modal ao clicar fora
  optionsModal.addEventListener('click', (e) => {
    if (e.target === optionsModal) {
      closeDownloadModal();
    }
  });

  // Botão de abrir pasta de downloads
  if (btnOpenFolder) {
    btnOpenFolder.addEventListener('click', openDownloadsFolder);
  }

  // Botão de limpar histórico de downloads
  if (btnClearHistory) {
    btnClearHistory.addEventListener('click', clearDownloadHistory);
  }

  // Botões de controle do servidor
  btnStartServer.addEventListener('click', startServer);
  btnStopServer.addEventListener('click', stopServer);

  // Inicialização
  checkServerStatus();
  loadVideos();
  loadDownloads();

  // Verifica status do servidor periodicamente
  setInterval(checkServerStatus, 5000);

  // Atualiza lista de downloads a cada 2 segundos
  setInterval(loadDownloads, 2000);
});
