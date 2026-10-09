/**
 * MediaFinder Mobile / PWA Client
 * Vanilla JavaScript puro, reativo e otimizado para dispositivos móveis
 */

const App = {
  profiles: [],
  currentProfile: null,
  pendingProfile: null,
  pinBuffer: '',
  castPollTimer: null,
  activeCastFileId: null,
  progressInterval: null,
  currentPlayingFileId: null,
  selectedCategory: 'all',
  searchQuery: '',

  // Ícones de avatar
  avatarMap: {
    admin: '👑',
    flower: '🌸',
    lion: '🦁',
    star: '⭐',
    rocket: '🚀',
    cat: '🐱'
  },

  async init() {
    this.registerPWA();
    this.setupEventListeners();
    await this.loadProfiles();

    // Recupera perfil salvo no localStorage
    const savedProfileId = localStorage.getItem('mf_profile_id');
    const matched = this.profiles.find(p => p.id === savedProfileId);
    if (matched && !matched.has_pin) {
      this.selectProfile(matched);
    } else {
      this.showScreen('profiles');
    }

    // Checa status de transmissão a cada 4 segundos
    this.checkCastStatus();
    setInterval(() => this.checkCastStatus(), 4000);
  },

  registerPWA() {
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.register('/sw.js').catch(err => {
        console.debug('ServiceWorker não registrado:', err);
      });
    }
  },

  // =========================================================================
  // NAVEGAÇÃO E TELAS
  // =========================================================================
  showScreen(screenName) {
    document.querySelectorAll('.view-screen').forEach(s => s.classList.remove('active'));
    document.body.classList.remove('theme-kids');

    const topNav = document.getElementById('top-nav');

    if (screenName === 'profiles') {
      document.getElementById('view-profiles').classList.add('active');
      topNav.style.display = 'none';
      return;
    }

    topNav.style.display = 'flex';

    if (screenName === 'kids') {
      document.getElementById('view-kids').classList.add('active');
      document.body.classList.add('theme-kids');
      this.loadKidsContent();
    } else {
      document.getElementById('view-home').classList.add('active');
      this.loadHomeContent();
    }

    this.updateNavProfileChip();
  },

  updateNavProfileChip() {
    if (!this.currentProfile) return;
    const avatarEl = document.getElementById('nav-avatar');
    const nameEl = document.getElementById('nav-profile-name');
    avatarEl.textContent = this.avatarMap[this.currentProfile.avatar] || '👤';
    nameEl.textContent = this.currentProfile.name;
  },

  // =========================================================================
  // PERFIS E PIN DE SEGURANÇA
  // =========================================================================
  async loadProfiles() {
    try {
      const res = await fetch('/api/profiles');
      this.profiles = await res.json();
      this.renderProfilesGrid();
    } catch (e) {
      console.error('Erro ao carregar perfis:', e);
    }
  },

  renderProfilesGrid() {
    const container = document.getElementById('profiles-container');
    container.innerHTML = '';

    this.profiles.forEach(p => {
      const card = document.createElement('div');
      card.className = `profile-card ${p.id === 'marcos' ? 'admin' : ''} ${p.is_kids ? 'kids' : ''}`;
      card.onclick = () => this.handleProfileClick(p);

      const avatarBox = document.createElement('div');
      avatarBox.className = 'profile-avatar-box';
      avatarBox.textContent = this.avatarMap[p.avatar] || '👤';

      if (p.has_pin) {
        const lock = document.createElement('div');
        lock.className = 'profile-lock-icon';
        lock.textContent = '🔒';
        avatarBox.appendChild(lock);
      }

      const name = document.createElement('div');
      name.className = 'profile-name';
      name.textContent = p.name;

      card.appendChild(avatarBox);
      card.appendChild(name);
      container.appendChild(card);
    });
  },

  handleProfileClick(profile) {
    if (profile.has_pin) {
      this.pendingProfile = profile;
      this.openPinModal(`Digite o PIN para acessar o perfil de ${profile.name}`);
    } else {
      this.selectProfile(profile);
    }
  },

  selectProfile(profile) {
    this.currentProfile = profile;
    localStorage.setItem('mf_profile_id', profile.id);
    if (profile.is_kids) {
      this.showScreen('kids');
    } else {
      this.showScreen('home');
    }
  },

  openPinModal(desc) {
    this.pinBuffer = '';
    this.updatePinDots();
    document.getElementById('pin-modal-desc').textContent = desc || 'Este perfil está protegido por senha';
    document.getElementById('modal-pin').classList.add('active');
  },

  closePinModal() {
    document.getElementById('modal-pin').classList.remove('active');
    this.pinBuffer = '';
    this.pendingProfile = null;
  },

  updatePinDots() {
    for (let i = 0; i < 4; i++) {
      const dot = document.getElementById(`p-dot-${i}`);
      if (i < this.pinBuffer.length) {
        dot.classList.add('filled');
      } else {
        dot.classList.remove('filled');
      }
    }
  },

  async handlePinInput(key) {
    if (this.pinBuffer.length < 4) {
      this.pinBuffer += key;
      this.updatePinDots();
    }

    if (this.pinBuffer.length === 4) {
      // Valida o PIN no backend
      const targetId = this.pendingProfile ? this.pendingProfile.id : (this.currentProfile ? this.currentProfile.id : 'marcos');
      try {
        const res = await fetch('/api/profiles/verify-pin', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ profile_id: targetId, pin: this.pinBuffer })
        });
        const data = await res.json();
        if (data.success) {
          const target = this.pendingProfile;
          this.closePinModal();
          if (target) {
            this.selectProfile(target);
          } else {
            // Saindo do modo kids para seleção de perfis
            this.showScreen('profiles');
          }
        } else {
          navigator.vibrate?.([100, 50, 100]);
          this.pinBuffer = '';
          this.updatePinDots();
          alert('PIN incorreto!');
        }
      } catch (err) {
        alert('Erro de comunicação com o servidor.');
        this.pinBuffer = '';
        this.updatePinDots();
      }
    }
  },

  // =========================================================================
  // CARREGAMENTO DE CONTEÚDO (ADULTO E KIDS)
  // =========================================================================
  async loadHomeContent() {
    await Promise.all([
      this.loadContinueWatching(),
      this.loadRecentMedia(),
      this.loadCatalog()
    ]);
  },

  async loadContinueWatching() {
    if (!this.currentProfile) return;
    try {
      const res = await fetch(`/api/continue?profile=${this.currentProfile.id}`);
      const items = await res.json();
      const heroEl = document.getElementById('hero-continue');

      if (items && items.length > 0) {
        const item = items[0];
        document.getElementById('hero-title').textContent = this.cleanTitle(item.name);
        document.getElementById('hero-time-text').textContent = `Pausado em ${item.progress_percent}%`;

        const remainSec = Math.max(0, item.duration_seconds - item.position_seconds);
        const remainMin = Math.round(remainSec / 60);
        document.getElementById('hero-duration-text').textContent = remainMin > 0 ? `Restam ${remainMin} min` : '';
        document.getElementById('hero-progress-bar').style.width = `${item.progress_percent}%`;

        document.getElementById('btn-hero-play-local').onclick = () => this.playLocal(item.id, item.position_seconds);
        document.getElementById('btn-hero-cast').onclick = () => this.openCastDevicesModal(item.id);

        heroEl.style.display = 'block';
      } else {
        heroEl.style.display = 'none';
      }
    } catch (e) {
      console.error('Erro ao carregar continuar assistindo:', e);
    }
  },

  async loadRecentMedia() {
    try {
      const res = await fetch(`/api/catalog?profile=${this.currentProfile.id}&category=video&limit=10`);
      const data = await res.json();
      const container = document.getElementById('carousel-recent');
      container.innerHTML = '';

      (data.items || []).forEach(item => {
        container.appendChild(this.createMediaCard(item));
      });
    } catch (e) {
      console.error('Erro ao carregar recentes:', e);
    }
  },

  async loadCatalog() {
    try {
      const cat = this.selectedCategory === 'all' ? '' : `&category=${this.selectedCategory}`;
      const query = this.searchQuery ? `&query=${encodeURIComponent(this.searchQuery)}` : '';
      const res = await fetch(`/api/catalog?profile=${this.currentProfile.id}${cat}${query}&limit=30`);
      const data = await res.json();
      const container = document.getElementById('catalog-grid');
      container.innerHTML = '';

      (data.items || []).forEach(item => {
        container.appendChild(this.createMediaCard(item));
      });
    } catch (e) {
      console.error('Erro ao carregar catálogo:', e);
    }
  },

  async loadKidsContent() {
    try {
      const query = this.searchQuery ? `&query=${encodeURIComponent(this.searchQuery)}` : '';
      const res = await fetch(`/api/catalog?profile=kids&is_kids=1${query}&limit=30`);
      const data = await res.json();

      const cartoonsContainer = document.getElementById('kids-carousel-cartoons');
      const gridContainer = document.getElementById('kids-catalog-grid');
      cartoonsContainer.innerHTML = '';
      gridContainer.innerHTML = '';

      const items = data.items || [];
      items.slice(0, 10).forEach(item => {
        cartoonsContainer.appendChild(this.createMediaCard(item, true));
      });
      items.slice(10).forEach(item => {
        gridContainer.appendChild(this.createMediaCard(item, true));
      });
    } catch (e) {
      console.error('Erro ao carregar catálogo kids:', e);
    }
  },

  createMediaCard(item, isKids = false) {
    const card = document.createElement('div');
    card.className = 'media-card';
    card.onclick = () => this.showMediaActions(item);

    const poster = document.createElement('div');
    poster.className = 'media-poster';
    poster.textContent = isKids ? '🦁' : (item.category === 'audio' ? '🎵' : '🎬');

    const title = document.createElement('div');
    title.className = 'media-card-title';
    title.textContent = this.cleanTitle(item.name);

    const meta = document.createElement('div');
    meta.className = 'media-card-meta';
    meta.textContent = item.extension.toUpperCase().replace('.', '');

    card.appendChild(poster);
    card.appendChild(title);
    card.appendChild(meta);
    return card;
  },

  cleanTitle(filename) {
    return filename.replace(/\.[^/.]+$/, '').replace(/[._]/g, ' ');
  },

  showMediaActions(item) {
    // Opções de ação rápida: Assistir no celular ou na TV
    const choice = confirm(`"${this.cleanTitle(item.name)}"\n\nDeseja Transmitir para a Smart TV?\n(Clique em Cancelar para assistir direto no Celular)`);
    if (choice) {
      this.openCastDevicesModal(item.id);
    } else {
      this.playLocal(item.id);
    }
  },

  // =========================================================================
  // REPRODUÇÃO LOCAL NO CELULAR (HTML5 VIDEO)
  // =========================================================================
  playLocal(fileId, startTime = 0) {
    this.currentPlayingFileId = fileId;
    const modal = document.getElementById('modal-player');
    const video = document.getElementById('html5-video');

    video.src = `/api/media/${fileId}/stream`;
    modal.classList.add('active');

    video.onloadedmetadata = () => {
      if (startTime > 0) {
        video.currentTime = startTime;
      }
      video.play().catch(() => {});
    };

    // Salva progresso a cada 5 segundos
    clearInterval(this.progressInterval);
    this.progressInterval = setInterval(() => {
      if (!video.paused && video.duration > 0) {
        this.saveProgress(fileId, video.currentTime, video.duration);
      }
    }, 5000);
  },

  closeLocalPlayer() {
    const modal = document.getElementById('modal-player');
    const video = document.getElementById('html5-video');

    if (this.currentPlayingFileId && video.duration > 0) {
      this.saveProgress(this.currentPlayingFileId, video.currentTime, video.duration);
    }

    video.pause();
    video.src = '';
    modal.classList.remove('active');
    clearInterval(this.progressInterval);
    this.loadContinueWatching();
  },

  async saveProgress(fileId, pos, dur) {
    if (!this.currentProfile) return;
    try {
      await fetch('/api/playback/progress', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          profile_id: this.currentProfile.id,
          file_id: fileId,
          position: pos,
          duration: dur
        })
      });
    } catch (e) {
      console.debug('Erro ao salvar progresso:', e);
    }
  },

  // =========================================================================
  // CONTROLE REMOTO CAST PARA SMART TV
  // =========================================================================
  async openCastDevicesModal(fileId) {
    this.activeCastFileId = fileId;
    const modal = document.getElementById('modal-devices');
    modal.classList.add('active');
    await this.fetchDevices();
  },

  async fetchDevices() {
    const listEl = document.getElementById('devices-list');
    listEl.innerHTML = '<div style="color: var(--text-muted); text-align: center; padding: 12px;">Buscando televisores na rede...</div>';

    try {
      const res = await fetch('/api/cast/devices');
      const devices = await res.json();
      listEl.innerHTML = '';

      if (!devices || devices.length === 0) {
        listEl.innerHTML = '<div style="color: var(--text-muted); text-align: center; padding: 12px;">Nenhuma TV detectada. Verifique se a TV está ligada na mesma rede Wi-Fi.</div>';
        return;
      }

      devices.forEach(dev => {
        const btn = document.createElement('button');
        btn.className = 'btn-secondary';
        btn.style.width = '100%';
        btn.style.textAlign = 'left';
        btn.style.padding = '14px';
        btn.innerHTML = `<strong>📺 ${dev.name}</strong><br><small style="color: var(--text-muted);">${dev.model || dev.host}</small>`;
        btn.onclick = () => this.startCast(dev.id);
        listEl.appendChild(btn);
      });
    } catch (e) {
      listEl.innerHTML = '<div style="color: #ef4444; text-align: center;">Erro ao buscar dispositivos.</div>';
    }
  },

  async startCast(deviceId) {
    try {
      const res = await fetch('/api/cast/play', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          device_id: deviceId,
          file_id: this.activeCastFileId,
          profile_id: this.currentProfile ? this.currentProfile.id : 'marcos'
        })
      });
      const data = await res.json();
      if (data.success) {
        document.getElementById('modal-devices').classList.remove('active');
        this.openRemoteModal();
      } else {
        alert(data.error || 'Falha ao iniciar transmissão');
      }
    } catch (e) {
      alert('Erro de rede ao conectar com a TV');
    }
  },

  openRemoteModal() {
    document.getElementById('modal-remote').classList.add('active');
    this.pollCastRemote();
  },

  closeRemoteModal() {
    document.getElementById('modal-remote').classList.remove('active');
  },

  async pollCastRemote() {
    try {
      const res = await fetch('/api/cast/status');
      const status = await res.json();

      if (status.is_casting) {
        document.getElementById('btn-cast-toggle').classList.add('cast-active');
        document.getElementById('remote-device-label').textContent = status.device || 'Smart TV';
        document.getElementById('remote-media-title').textContent = this.cleanTitle(status.file_name || 'Reproduzindo');

        const scrubber = document.getElementById('remote-scrubber');
        const dur = status.duration || 0;
        const cur = status.current_time || 0;

        scrubber.max = dur;
        scrubber.value = cur;
        document.getElementById('remote-time-current').textContent = this.formatTime(cur);
        document.getElementById('remote-time-total').textContent = this.formatTime(dur);

        document.getElementById('btn-remote-play-pause').textContent = status.state === 'PLAYING' ? '⏸' : '▶';
        document.getElementById('remote-volume-slider').value = Math.round((status.volume || 1.0) * 100);

        // Atualiza opções de áudio se disponíveis
        const audioSel = document.getElementById('remote-audio-select');
        if (audioSel && status.audio_tracks && (!audioSel.dataset.loaded || audioSel.dataset.loaded !== status.file_name)) {
          audioSel.innerHTML = '';
          status.audio_tracks.forEach(track => {
            const opt = document.createElement('option');
            opt.value = track.id;
            opt.textContent = track.name;
            if (track.id === status.active_audio_id) opt.selected = true;
            audioSel.appendChild(opt);
          });
          audioSel.dataset.loaded = status.file_name;
        }

        // Atualiza opções de legenda se disponíveis
        const subSel = document.getElementById('remote-subtitle-select');
        if (subSel && status.subtitle_tracks && (!subSel.dataset.loaded || subSel.dataset.loaded !== status.file_name)) {
          subSel.innerHTML = '';
          status.subtitle_tracks.forEach(track => {
            const opt = document.createElement('option');
            opt.value = track.id;
            opt.textContent = track.name;
            if (track.id === status.active_subtitle_id) opt.selected = true;
            subSel.appendChild(opt);
          });
          subSel.dataset.loaded = status.file_name;
        }
      } else {
        document.getElementById('btn-cast-toggle').classList.remove('cast-active');
      }
    } catch (e) {
      console.debug('Erro ao consultar status do cast:', e);
    }
  },

  async checkCastStatus() {
    try {
      const res = await fetch('/api/cast/status');
      const status = await res.json();
      const castBtn = document.getElementById('btn-cast-toggle');
      if (status.is_casting) {
        castBtn.classList.add('cast-active');
      } else {
        castBtn.classList.remove('cast-active');
      }
    } catch (e) {}
  },

  async sendRemoteControl(action, value = null) {
    try {
      await fetch('/api/cast/control', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action, value })
      });
      setTimeout(() => this.pollCastRemote(), 300);
    } catch (e) {
      console.error('Erro ao enviar controle remoto:', e);
    }
  },

  formatTime(seconds) {
    if (!seconds || isNaN(seconds)) return '00:00:00';
    const s = Math.floor(seconds);
    const hrs = Math.floor(s / 3600);
    const mins = Math.floor((s % 3600) / 60);
    const secs = s % 60;
    return `${hrs.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  },

  // =========================================================================
  // LISTENERS DE EVENTOS
  // =========================================================================
  setupEventListeners() {
    // Troca de Perfil
    document.getElementById('btn-profile-chip').onclick = () => {
      if (this.currentProfile && this.currentProfile.is_kids) {
        // Exige PIN para sair do modo infantil!
        this.openPinModal('Digite o PIN de segurança para sair do Espaço Kids');
      } else {
        this.showScreen('profiles');
      }
    };

    // Botão de Cast no Header
    document.getElementById('btn-cast-toggle').onclick = () => {
      fetch('/api/cast/status').then(r => r.json()).then(st => {
        if (st.is_casting) {
          this.openRemoteModal();
        } else {
          this.openCastDevicesModal(null);
        }
      });
    };

    // Fechar modais
    document.getElementById('btn-close-devices').onclick = () => {
      document.getElementById('modal-devices').classList.remove('active');
    };
    document.getElementById('btn-refresh-devices').onclick = () => this.fetchDevices();
    document.getElementById('btn-close-remote').onclick = () => this.closeRemoteModal();
    document.getElementById('btn-player-close').onclick = () => this.closeLocalPlayer();

    // Controles Remotos
    document.getElementById('btn-remote-play-pause').onclick = () => {
      const cur = document.getElementById('btn-remote-play-pause').textContent;
      this.sendRemoteControl(cur === '⏸' ? 'pause' : 'play');
    };
    document.getElementById('btn-remote-rev').onclick = () => {
      const cur = parseFloat(document.getElementById('remote-scrubber').value) || 0;
      this.sendRemoteControl('seek', Math.max(0, cur - 10));
    };
    document.getElementById('btn-remote-fwd').onclick = () => {
      const cur = parseFloat(document.getElementById('remote-scrubber').value) || 0;
      this.sendRemoteControl('seek', cur + 30);
    };
    document.getElementById('remote-scrubber').onchange = (e) => {
      this.sendRemoteControl('seek', parseFloat(e.target.value));
    };
    document.getElementById('remote-volume-slider').onchange = (e) => {
      this.sendRemoteControl('volume', parseFloat(e.target.value) / 100.0);
    };
    document.getElementById('btn-remote-disconnect').onclick = () => {
      this.sendRemoteControl('stop');
      this.closeRemoteModal();
    };

    // Seletores de Áudio e Legenda
    const audioSelect = document.getElementById('remote-audio-select');
    if (audioSelect) {
      audioSelect.onchange = (e) => {
        this.sendRemoteControl('audio_track', parseInt(e.target.value));
      };
    }
    const subSelect = document.getElementById('remote-subtitle-select');
    if (subSelect) {
      subSelect.onchange = (e) => {
        this.sendRemoteControl('subtitle_track', parseInt(e.target.value));
      };
    }

    // Teclado PIN
    document.querySelectorAll('.key-btn[data-key]').forEach(btn => {
      btn.onclick = () => this.handlePinInput(btn.getAttribute('data-key'));
    });
    document.getElementById('btn-pin-cancel').onclick = () => this.closePinModal();
    document.getElementById('btn-pin-backspace').onclick = () => {
      this.pinBuffer = this.pinBuffer.slice(0, -1);
      this.updatePinDots();
    };

    // Filtros de Categoria (Pills)
    document.querySelectorAll('#filter-pills .pill').forEach(pill => {
      pill.onclick = () => {
        document.querySelectorAll('#filter-pills .pill').forEach(p => p.classList.remove('active'));
        pill.classList.add('active');
        this.selectedCategory = pill.getAttribute('data-category');
        this.loadCatalog();
      };
    });

    // Busca com debounce
    const handleSearch = (e) => {
      clearTimeout(this.searchDebounceTimer);
      this.searchDebounceTimer = setTimeout(() => {
        this.searchQuery = e.target.value.trim();
        if (this.currentProfile && this.currentProfile.is_kids) {
          this.loadKidsContent();
        } else {
          this.loadCatalog();
        }
      }, 350);
    };

    document.getElementById('search-input').oninput = handleSearch;
    document.getElementById('kids-search-input').oninput = handleSearch;
  }
};

document.addEventListener('DOMContentLoaded', () => App.init());
