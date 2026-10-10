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
  activeCastPlutoChannel: null,
  hlsInstance: null,
  progressInterval: null,
  currentPlayingFileId: null,
  selectedCategory: 'video',
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
        document.getElementById('btn-hero-cast').onclick = () => this.openCastDevicesModal(item.id, item.position_seconds);

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

  escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  },

  clearSearch() {
    const input = document.getElementById('search-input');
    const clearBtn = document.getElementById('btn-search-clear');
    if (input) input.value = '';
    if (clearBtn) clearBtn.style.display = 'none';
    this.searchQuery = '';
    this.loadCatalog();
    this.loadContinueWatching();
  },

  clearKidsSearch() {
    const input = document.getElementById('kids-search-input');
    const clearBtn = document.getElementById('kids-btn-search-clear');
    if (input) input.value = '';
    if (clearBtn) clearBtn.style.display = 'none';
    this.searchQuery = '';
    this.loadKidsContent();
  },

  async loadCatalog() {
    if (this.selectedCategory === 'pluto') {
      return this.loadPlutoCatalog();
    }

    try {
      const isSearching = !!(this.searchQuery && this.searchQuery.trim());
      const heroSection = document.getElementById('hero-continue');
      const recentSection = document.getElementById('carousel-recent')?.closest('section');

      // Se estiver buscando, esconde banner e carrossel de recentes para focar na lista pesquisada
      if (isSearching) {
        if (heroSection) heroSection.style.display = 'none';
        if (recentSection) recentSection.style.display = 'none';
      } else {
        if (recentSection) recentSection.style.display = 'block';
      }

      const cat = `&category=${this.selectedCategory || 'video'}`;
      const query = isSearching ? `&query=${encodeURIComponent(this.searchQuery.trim())}` : '';
      const res = await fetch(`/api/catalog?profile=${this.currentProfile.id}${cat}${query}&limit=60`);
      const data = await res.json();
      const container = document.getElementById('catalog-grid');
      container.innerHTML = '';

      if (!data.items || data.items.length === 0) {
        if (isSearching) {
          container.innerHTML = `
            <div class="search-empty-state">
              <div class="empty-icon">🔍</div>
              <div class="empty-title">Nenhum resultado para "${this.escapeHtml(this.searchQuery)}"</div>
              <div class="empty-desc">Não encontramos vídeos ou arquivos com este nome no seu acervo local.</div>
              <button class="btn-clear-search" id="btn-empty-clear">Limpar busca e ver tudo</button>
            </div>
          `;
          document.getElementById('btn-empty-clear')?.addEventListener('click', () => this.clearSearch());
        } else {
          container.innerHTML = '<div style="color: var(--text-muted); padding: 20px; text-align: center;">Nenhum arquivo encontrado nesta categoria.</div>';
        }
        return;
      }

      data.items.forEach(item => {
        container.appendChild(this.createMediaCard(item));
      });
    } catch (e) {
      console.error('Erro ao carregar catálogo:', e);
    }
  },

  async loadPlutoCatalog() {
    try {
      const isSearching = !!(this.searchQuery && this.searchQuery.trim());
      const heroSection = document.getElementById('hero-continue');
      const recentSection = document.getElementById('carousel-recent')?.closest('section');

      if (heroSection) heroSection.style.display = 'none';
      if (recentSection) recentSection.style.display = 'none';

      const isKids = this.currentProfile && this.currentProfile.is_kids ? '1' : '0';
      const res = await fetch(`/api/pluto/channels?profile=${this.currentProfile ? this.currentProfile.id : ''}&is_kids=${isKids}`);
      const data = await res.json();
      let channels = data.channels || [];

      if (isSearching) {
        const q = this.searchQuery.trim().toLowerCase();
        channels = channels.filter(c =>
          (c.name && c.name.toLowerCase().includes(q)) ||
          (c.category && c.category.toLowerCase().includes(q)) ||
          (c.summary && c.summary.toLowerCase().includes(q))
        );
      }

      const container = document.getElementById('catalog-grid');
      container.innerHTML = '';

      if (channels.length === 0) {
        if (isSearching) {
          container.innerHTML = `
            <div class="search-empty-state">
              <div class="empty-icon">🪐</div>
              <div class="empty-title">Nenhum canal da Pluto TV para "${this.escapeHtml(this.searchQuery)}"</div>
              <div class="empty-desc">Tente buscar por outro canal, categoria ou gênero.</div>
              <button class="btn-clear-search" id="btn-empty-clear">Limpar busca e ver canais</button>
            </div>
          `;
          document.getElementById('btn-empty-clear')?.addEventListener('click', () => this.clearSearch());
        } else {
          container.innerHTML = '<div style="color: var(--text-muted); padding: 20px; text-align: center;">Nenhum canal Pluto TV disponível no momento.</div>';
        }
        return;
      }

      channels.forEach(ch => {
        container.appendChild(this.createPlutoCard(ch));
      });
    } catch (e) {
      console.error('Erro ao carregar canais Pluto TV:', e);
    }
  },

  createPlutoCard(channel, isKids = false) {
    const card = document.createElement('div');
    card.className = 'media-card';
    card.onclick = () => this.openPlutoDetails(channel);

    const poster = document.createElement('div');
    poster.className = 'media-poster';

    const fallbackIcon = document.createElement('div');
    fallbackIcon.className = 'media-poster-fallback';
    fallbackIcon.textContent = '🪐';

    const imgSrc = channel.logo || channel.thumbnail;
    if (imgSrc) {
      const img = document.createElement('img');
      img.src = imgSrc;
      img.alt = channel.name;
      img.className = 'pluto-logo';
      img.loading = 'lazy';
      img.onerror = () => {
        img.style.display = 'none';
        fallbackIcon.style.display = 'block';
      };
      poster.appendChild(img);
      fallbackIcon.style.display = 'none';
    }
    poster.appendChild(fallbackIcon);

    const liveBadge = document.createElement('span');
    liveBadge.className = 'badge-live-card';
    liveBadge.textContent = '🔴 AO VIVO';
    poster.appendChild(liveBadge);

    if (channel.number) {
      const chBadge = document.createElement('span');
      chBadge.className = 'badge-channel-card';
      chBadge.textContent = `CH ${channel.number}`;
      poster.appendChild(chBadge);
    }

    const title = document.createElement('div');
    title.className = 'media-card-title';
    title.textContent = channel.name;

    const meta = document.createElement('div');
    meta.className = 'media-card-meta';
    meta.textContent = `Pluto TV • ${channel.category || 'Geral'}`;

    card.appendChild(poster);
    card.appendChild(title);
    card.appendChild(meta);
    return card;
  },

  openPlutoDetails(channel) {
    const modal = document.getElementById('modal-details');
    modal.classList.add('active');

    document.getElementById('details-title').textContent = channel.name;
    document.getElementById('details-original-title').textContent = 'Pluto TV Brasil (Transmissão Oficial Ao Vivo)';

    const imdbEl = document.getElementById('details-imdb-badge');
    imdbEl.textContent = '🔴 AO VIVO';
    imdbEl.style.display = 'inline-flex';
    imdbEl.style.backgroundColor = '#dc2626';
    imdbEl.style.color = '#ffffff';

    const ratedEl = document.getElementById('details-rated-badge');
    ratedEl.textContent = channel.number ? `CH ${channel.number}` : 'FREE';
    ratedEl.style.display = 'inline-block';

    document.getElementById('details-year').textContent = '24/7';
    document.getElementById('details-runtime').textContent = 'Ao Vivo';
    document.getElementById('details-genre').textContent = channel.category || 'Streaming Gratuito';
    document.getElementById('details-plot').textContent = channel.summary || 'Assista a este canal ao vivo da Pluto TV gratuitamente no MediaFinder com streaming direto ou transmissão na TV.';

    const posterSrc = channel.logo || channel.thumbnail;
    const posterImg = document.getElementById('details-poster-img');
    const posterFallback = document.getElementById('details-poster-fallback');
    if (posterSrc) {
      posterImg.src = posterSrc;
      posterImg.style.display = 'block';
      posterFallback.style.display = 'none';
    } else {
      posterImg.style.display = 'none';
      posterFallback.style.display = 'block';
    }

    const backdrop = document.getElementById('details-backdrop');
    const backdropSrc = channel.thumbnail || channel.featured_image || posterSrc;
    if (backdropSrc) {
      backdrop.style.backgroundImage = `url('${backdropSrc}')`;
    } else {
      backdrop.style.backgroundImage = 'none';
    }

    document.getElementById('details-director').textContent = '';
    document.getElementById('details-cast-section').style.display = 'none';

    const playBtn = document.getElementById('btn-details-play');
    const castBtn = document.getElementById('btn-details-cast');
    const playLabel = document.getElementById('btn-details-play-label');
    const castLabel = document.getElementById('btn-details-cast-label');
    const restartContainer = document.getElementById('details-restart-container');

    if (playLabel) playLabel.textContent = 'Assistir no Celular';
    if (castLabel) castLabel.textContent = 'Transmitir na TV';
    if (restartContainer) restartContainer.style.display = 'none';

    playBtn.onclick = () => {
      this.closeMediaDetails();
      this.playPlutoStream(channel.stream_url, channel.name);
    };

    castBtn.onclick = () => {
      this.closeMediaDetails();
      this.openCastDevicesModal(null, null, channel);
    };
  },

  playPlutoStream(streamUrl, channelName) {
    this.currentPlayingFileId = null;
    const modal = document.getElementById('modal-player');
    const video = document.getElementById('html5-video');

    if (this.hlsInstance) {
      this.hlsInstance.destroy();
      this.hlsInstance = null;
    }

    modal.classList.add('active');

    if (video.canPlayType('application/vnd.apple.mpegurl')) {
      video.src = streamUrl;
      video.play().catch(() => {});
    } else if (window.Hls && Hls.isSupported()) {
      this.hlsInstance = new Hls({ enableWorker: true });
      this.hlsInstance.loadSource(streamUrl);
      this.hlsInstance.attachMedia(video);
      this.hlsInstance.on(Hls.Events.MANIFEST_PARSED, () => {
        video.play().catch(() => {});
      });
    } else {
      video.src = streamUrl;
      video.play().catch(() => {});
    }
  },

  async loadKidsContent() {
    try {
      const isSearching = !!(this.searchQuery && this.searchQuery.trim());
      const cartoonSec = document.getElementById('kids-carousel-cartoons')?.closest('section');
      const plutoKidsSec = document.getElementById('kids-pluto-section');
      if (cartoonSec) cartoonSec.style.display = isSearching ? 'none' : 'block';
      if (plutoKidsSec) plutoKidsSec.style.display = isSearching ? 'none' : 'block';

      // Carrega canais da Pluto TV Kids (Ao Vivo)
      const plutoKidsContainer = document.getElementById('kids-carousel-pluto');
      if (plutoKidsContainer && !isSearching) {
        plutoKidsContainer.innerHTML = '';
        fetch('/api/pluto/channels?is_kids=1')
          .then(r => r.json())
          .then(data => {
            (data.channels || []).forEach(ch => {
              plutoKidsContainer.appendChild(this.createPlutoCard(ch, true));
            });
          })
          .catch(e => console.debug('Erro ao carregar Pluto Kids:', e));
      }

      const query = isSearching ? `&query=${encodeURIComponent(this.searchQuery.trim())}` : '';
      const res = await fetch(`/api/catalog?profile=kids&is_kids=1${query}&limit=60`);
      const data = await res.json();

      const cartoonsContainer = document.getElementById('kids-carousel-cartoons');
      const gridContainer = document.getElementById('kids-catalog-grid');
      if (cartoonsContainer) cartoonsContainer.innerHTML = '';
      gridContainer.innerHTML = '';

      const items = data.items || [];
      if (items.length === 0) {
        gridContainer.innerHTML = `
          <div class="search-empty-state">
            <div class="empty-icon">🦁</div>
            <div class="empty-title">Nenhum desenho para "${this.escapeHtml(this.searchQuery)}"</div>
            <div class="empty-desc">Tente procurar com outro nome infantil.</div>
            <button class="btn-clear-search" id="kids-btn-empty-clear">Limpar busca e ver todos</button>
          </div>
        `;
        document.getElementById('kids-btn-empty-clear')?.addEventListener('click', () => this.clearKidsSearch());
        return;
      }

      if (isSearching) {
        items.forEach(item => {
          gridContainer.appendChild(this.createMediaCard(item, true));
        });
      } else {
        items.slice(0, 10).forEach(item => {
          cartoonsContainer.appendChild(this.createMediaCard(item, true));
        });
        items.slice(10).forEach(item => {
          gridContainer.appendChild(this.createMediaCard(item, true));
        });
      }
    } catch (e) {
      console.error('Erro ao carregar catálogo kids:', e);
    }
  },

  createMediaCard(item, isKids = false) {
    const card = document.createElement('div');
    card.className = 'media-card';
    card.onclick = () => this.openMediaDetails(item.id);

    const poster = document.createElement('div');
    poster.className = 'media-poster';

    const posterSrc = item.poster_local || item.poster_url;
    const fallbackIcon = document.createElement('div');
    fallbackIcon.className = 'media-poster-fallback';
    fallbackIcon.textContent = isKids ? '🦁' : (item.category === 'audio' ? '🎵' : '🎬');

    if (posterSrc) {
      const img = document.createElement('img');
      img.src = posterSrc;
      img.alt = item.meta_title || item.name;
      img.loading = 'lazy';
      img.onerror = () => {
        img.style.display = 'none';
        fallbackIcon.style.display = 'block';
      };
      poster.appendChild(img);
      fallbackIcon.style.display = 'none';
    }
    poster.appendChild(fallbackIcon);

    if (item.imdb_rating) {
      const badge = document.createElement('span');
      badge.className = 'badge-imdb-card';
      badge.textContent = `★ ${item.imdb_rating}`;
      poster.appendChild(badge);
    }

    if (item.meta_rated && item.meta_rated !== 'Livre') {
      const badgeRated = document.createElement('span');
      badgeRated.className = 'badge-rated-card';
      badgeRated.textContent = item.meta_rated;
      poster.appendChild(badgeRated);
    }

    const title = document.createElement('div');
    title.className = 'media-card-title';
    title.textContent = item.meta_title || this.cleanTitle(item.name);

    const meta = document.createElement('div');
    meta.className = 'media-card-meta';
    const yearStr = item.meta_year ? `${item.meta_year}` : '';
    const genreStr = item.meta_genre ? item.meta_genre.split(',')[0].trim() : (item.extension.toUpperCase().replace('.', ''));
    meta.textContent = yearStr ? `${yearStr} • ${genreStr}` : genreStr;

    card.appendChild(poster);
    card.appendChild(title);
    card.appendChild(meta);
    return card;
  },

  cleanTitle(filename) {
    return filename.replace(/\.[^/.]+$/, '').replace(/[._]/g, ' ');
  },

  async openMediaDetails(fileId) {
    try {
      const modal = document.getElementById('modal-details');
      modal.classList.add('active');

      document.getElementById('details-title').textContent = 'Carregando...';
      document.getElementById('details-original-title').textContent = '';
      document.getElementById('details-plot').textContent = 'Consultando informações no IMDb...';
      document.getElementById('details-poster-img').style.display = 'none';
      document.getElementById('details-poster-fallback').style.display = 'block';
      document.getElementById('details-imdb-badge').style.display = 'none';
      document.getElementById('details-rated-badge').style.display = 'none';
      document.getElementById('details-cast-list').innerHTML = '';
      const restartContainer = document.getElementById('details-restart-container');
      if (restartContainer) restartContainer.style.display = 'none';

      const profileParam = this.currentProfile ? `&profile=${encodeURIComponent(this.currentProfile.id)}` : '';
      const res = await fetch(`/api/media/details?id=${fileId}${profileParam}`);
      const data = await res.json();

      document.getElementById('details-title').textContent = data.title || 'Filme';
      document.getElementById('details-original-title').textContent = data.original_title && data.original_title !== data.title ? data.original_title : '';

      if (data.rating) {
        const imdbEl = document.getElementById('details-imdb-badge');
        imdbEl.textContent = `★ ${data.rating}${data.votes ? ' (' + data.votes + ')' : ''}`;
        imdbEl.style.display = 'inline-flex';
      }

      if (data.rated) {
        const ratedEl = document.getElementById('details-rated-badge');
        ratedEl.textContent = data.rated;
        ratedEl.style.display = 'inline-block';
      }

      document.getElementById('details-year').textContent = data.year || '';
      document.getElementById('details-runtime').textContent = data.runtime || '';
      document.getElementById('details-genre').textContent = data.genre || '';
      document.getElementById('details-plot').textContent = data.plot || 'Nenhuma sinopse disponível para este arquivo de vídeo.';

      const posterSrc = data.poster_local || data.poster_url;
      const posterImg = document.getElementById('details-poster-img');
      const posterFallback = document.getElementById('details-poster-fallback');
      if (posterSrc) {
        posterImg.src = posterSrc;
        posterImg.style.display = 'block';
        posterFallback.style.display = 'none';
      } else {
        posterImg.style.display = 'none';
        posterFallback.style.display = 'block';
      }

      const backdrop = document.getElementById('details-backdrop');
      if (data.backdrop_url || posterSrc) {
        backdrop.style.backgroundImage = `url('${data.backdrop_url || posterSrc}')`;
      } else {
        backdrop.style.backgroundImage = 'none';
      }

      document.getElementById('details-director').textContent = data.director ? `Direção: ${data.director}` : '';

      const castList = document.getElementById('details-cast-list');
      castList.innerHTML = '';
      if (data.actors) {
        const actors = data.actors.split(',').map(a => a.trim());
        actors.forEach(actor => {
          const chip = document.createElement('div');
          chip.className = 'cast-chip';
          chip.innerHTML = `
            <div class="cast-avatar">🎭</div>
            <div class="cast-name">${actor}</div>
          `;
          castList.appendChild(chip);
        });
        document.getElementById('details-cast-section').style.display = 'block';
      } else {
        document.getElementById('details-cast-section').style.display = 'none';
      }

      const playBtn = document.getElementById('btn-details-play');
      const castBtn = document.getElementById('btn-details-cast');
      const playLabel = document.getElementById('btn-details-play-label');
      const castLabel = document.getElementById('btn-details-cast-label');
      const restartBtn = document.getElementById('btn-details-restart');

      const savedPos = (data.saved_position && data.saved_position >= 10.0) ? data.saved_position : null;

      if (savedPos) {
        const timeFormatted = this.formatTime(savedPos);
        if (playLabel) playLabel.textContent = `Continuar (${timeFormatted})`;
        if (castLabel) castLabel.textContent = `Continuar na TV (${timeFormatted})`;
        if (restartContainer) restartContainer.style.display = 'flex';
      } else {
        if (playLabel) playLabel.textContent = 'Assistir no Celular';
        if (castLabel) castLabel.textContent = 'Transmitir na TV';
        if (restartContainer) restartContainer.style.display = 'none';
      }

      playBtn.onclick = () => {
        this.closeMediaDetails();
        this.playLocal(data.file_id || fileId, savedPos);
      };
      castBtn.onclick = () => {
        this.closeMediaDetails();
        this.openCastDevicesModal(data.file_id || fileId, savedPos);
      };
      if (restartBtn) {
        restartBtn.onclick = () => {
          this.closeMediaDetails();
          this.playLocal(data.file_id || fileId, 0.001);
        };
      }

    } catch (e) {
      console.error('Erro ao abrir detalhes do filme:', e);
    }
  },

  closeMediaDetails() {
    document.getElementById('modal-details').classList.remove('active');
  },

  // =========================================================================
  // REPRODUÇÃO LOCAL NO CELULAR (HTML5 VIDEO)
  // =========================================================================
  async playLocal(fileId, startTime = null) {
    this.currentPlayingFileId = fileId;
    const modal = document.getElementById('modal-player');
    const video = document.getElementById('html5-video');

    let resumeTime = (typeof startTime === 'number' && startTime > 0) ? startTime : 0;
    // Se não foi passado startTime (ou for null), busca progresso salvo no backend
    if ((startTime === null || startTime === undefined) && this.currentProfile) {
      try {
        const res = await fetch(`/api/playback/progress?profile=${encodeURIComponent(this.currentProfile.id)}&file_id=${fileId}`);
        const prog = await res.json();
        if (prog && prog.position_seconds >= 10.0 && (!prog.duration_seconds || prog.position_seconds < prog.duration_seconds * 0.95)) {
          resumeTime = prog.position_seconds;
        }
      } catch (e) {
        console.debug('Erro ao carregar progresso salvo:', e);
      }
    }

    video.src = `/api/media/${fileId}/stream`;
    modal.classList.add('active');

    let seekApplied = false;
    const applySeek = () => {
      if (resumeTime > 0 && !seekApplied) {
        video.currentTime = resumeTime;
        seekApplied = true;
      }
      video.play().catch(() => {});
    };

    video.onloadedmetadata = applySeek;
    video.oncanplay = applySeek;

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

    if (this.hlsInstance) {
      this.hlsInstance.destroy();
      this.hlsInstance = null;
    }

    if (this.currentPlayingFileId && video.duration > 0) {
      this.saveProgress(this.currentPlayingFileId, video.currentTime, video.duration);
    }

    video.pause();
    video.src = '';
    modal.classList.remove('active');
    clearInterval(this.progressInterval);
    if (this.selectedCategory !== 'pluto') {
      this.loadContinueWatching();
    }
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
  async openCastDevicesModal(fileId, startTime = null, plutoChannel = null) {
    this.activeCastFileId = fileId;
    this.activeCastStartTime = startTime;
    this.activeCastPlutoChannel = plutoChannel;
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
      const payload = {
        device_id: deviceId,
        profile_id: this.currentProfile ? this.currentProfile.id : 'marcos'
      };

      if (this.activeCastPlutoChannel) {
        payload.channel_id = this.activeCastPlutoChannel.id;
        payload.stream_url = this.activeCastPlutoChannel.stream_url;
        payload.channel_name = this.activeCastPlutoChannel.name;
      } else {
        payload.file_id = this.activeCastFileId;
        if (this.activeCastStartTime !== null && this.activeCastStartTime !== undefined) {
          payload.start_time = this.activeCastStartTime;
        }
      }

      const res = await fetch('/api/cast/play', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
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

        // Atualiza pôster e nota IMDb no controle remoto
        const rImg = document.getElementById('remote-poster-img');
        const rIcon = document.getElementById('remote-poster-icon');
        const rBadge = document.getElementById('remote-imdb-badge');
        if (rImg && status.file_name && rImg.dataset.file !== status.file_name) {
          rImg.dataset.file = status.file_name;
          fetch(`/api/catalog?query=${encodeURIComponent(this.cleanTitle(status.file_name))}&limit=1`)
            .then(r => r.json())
            .then(d => {
              if (d.items && d.items.length > 0) {
                const it = d.items[0];
                const p = it.poster_local || it.poster_url;
                if (p) {
                  rImg.src = p;
                  rImg.style.display = 'block';
                  if (rIcon) rIcon.style.display = 'none';
                }
                if (it.imdb_rating && rBadge) {
                  rBadge.textContent = `★ ${it.imdb_rating}`;
                  rBadge.style.display = 'inline-block';
                }
              }
            }).catch(() => {});
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
    const closeDetBtn = document.getElementById('btn-close-details');
    if (closeDetBtn) closeDetBtn.onclick = () => this.closeMediaDetails();

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

    // Busca na Home (Adulto/Geral)
    const searchForm = document.getElementById('search-form');
    const searchInput = document.getElementById('search-input');
    const clearBtn = document.getElementById('btn-search-clear');

    const executeSearch = (val) => {
      this.searchQuery = (val || '').trim();
      if (clearBtn) clearBtn.style.display = this.searchQuery ? 'flex' : 'none';
      if (searchInput) searchInput.blur(); // Fecha o teclado virtual no celular
      this.loadCatalog();
    };

    if (searchForm) {
      searchForm.onsubmit = (e) => {
        e.preventDefault();
        executeSearch(searchInput ? searchInput.value : '');
      };
    }

    if (searchInput) {
      searchInput.oninput = (e) => {
        const val = e.target.value;
        if (clearBtn) clearBtn.style.display = val.trim() ? 'flex' : 'none';
        clearTimeout(this.searchDebounceTimer);
        this.searchDebounceTimer = setTimeout(() => {
          this.searchQuery = val.trim();
          this.loadCatalog();
        }, 350);
      };
      searchInput.onkeydown = (e) => {
        if (e.key === 'Enter') {
          e.preventDefault();
          executeSearch(searchInput.value);
        }
      };
    }

    if (clearBtn) {
      clearBtn.onclick = () => this.clearSearch();
    }

    // Busca no Espaço Kids
    const kidsSearchForm = document.getElementById('kids-search-form');
    const kidsSearchInput = document.getElementById('kids-search-input');
    const kidsClearBtn = document.getElementById('kids-btn-search-clear');

    const executeKidsSearch = (val) => {
      this.searchQuery = (val || '').trim();
      if (kidsClearBtn) kidsClearBtn.style.display = this.searchQuery ? 'flex' : 'none';
      if (kidsSearchInput) kidsSearchInput.blur(); // Fecha o teclado virtual
      this.loadKidsContent();
    };

    if (kidsSearchForm) {
      kidsSearchForm.onsubmit = (e) => {
        e.preventDefault();
        executeKidsSearch(kidsSearchInput ? kidsSearchInput.value : '');
      };
    }

    if (kidsSearchInput) {
      kidsSearchInput.oninput = (e) => {
        const val = e.target.value;
        if (kidsClearBtn) kidsClearBtn.style.display = val.trim() ? 'flex' : 'none';
        clearTimeout(this.searchDebounceTimer);
        this.searchDebounceTimer = setTimeout(() => {
          this.searchQuery = val.trim();
          this.loadKidsContent();
        }, 350);
      };
      kidsSearchInput.onkeydown = (e) => {
        if (e.key === 'Enter') {
          e.preventDefault();
          executeKidsSearch(kidsSearchInput.value);
        }
      };
    }

    if (kidsClearBtn) {
      kidsClearBtn.onclick = () => this.clearKidsSearch();
    }
  }
};

document.addEventListener('DOMContentLoaded', () => App.init());
