// main.js - Funcionalidad principal del dashboard
class Dashboard {
    constructor() {
        this.marketers = [];
        this.currentFilter = 'all';
        this.userStats = {
            likesGiven: 0,
            likesReceived: 0,
            remainingLikes: 5
        };
        this.init();
    }

    async init() {
        if (!authManager.isAuthenticated()) {
            authManager.redirectToLogin();
            return;
        }

        this.bindEvents();
        this.updateUserInfo();
        await this.loadMarketers();
        await this.loadUserStats();
    }

    bindEvents() {
        // Filtros
        const filterButtons = document.querySelectorAll('.filter-btn');
        filterButtons.forEach(btn => {
            btn.addEventListener('click', (e) => this.handleFilter(e));
        });

        // Búsqueda
        const searchInput = document.getElementById('searchInput');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => this.handleSearch(e));
        }

        // Modal
        const modal = document.getElementById('profileModal');
        const closeModal = document.getElementById('closeModal');
        
        if (closeModal) {
            closeModal.addEventListener('click', () => this.closeModal());
        }

        if (modal) {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    this.closeModal();
                }
            });
        }

        // Escape key para cerrar modal
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeModal();
            }
        });
    }

    updateUserInfo() {
        const user = authManager.getCurrentUser();
        const userNameElement = document.getElementById('userName');
        
        if (user && userNameElement) {
            userNameElement.textContent = `${user.first_name} ${user.last_name}`;
        }
    }

    async loadMarketers() {
        const loadingIndicator = document.getElementById('loadingIndicator');
        const marketersGrid = document.getElementById('marketersGrid');
        
        try {
            if (loadingIndicator) loadingIndicator.style.display = 'block';
            if (marketersGrid) marketersGrid.innerHTML = '';

            const response = await authManager.makeAuthenticatedRequest(
                `${authManager.baseURL}/marketers/`
            );

            if (response && response.ok) {
                const data = await response.json();
                this.marketers = data.results || data;
                this.renderMarketers();
                this.updateTotalMembers();
            } else {
                this.showError('Error al cargar los marketeros');
            }
        } catch (error) {
            console.error('Error loading marketers:', error);
            this.showError('Error de conexión al cargar marketeros');
        } finally {
            if (loadingIndicator) loadingIndicator.style.display = 'none';
        }
    }

    async loadUserStats() {
        try {
            const response = await authManager.makeAuthenticatedRequest(
                `${authManager.baseURL}/user/stats/`
            );

            if (response && response.ok) {
                const stats = await response.json();
                this.userStats = stats;
                this.updateStatsDisplay();
            }
        } catch (error) {
            console.error('Error loading user stats:', error);
        }
    }

    renderMarketers() {
        const marketersGrid = document.getElementById('marketersGrid');
        const currentUser = authManager.getCurrentUser();
        
        if (!marketersGrid) return;

        let filteredMarketers = this.getFilteredMarketers();

        if (filteredMarketers.length === 0) {
            marketersGrid.innerHTML = this.getEmptyStateHTML();
            return;
        }

        const cardsHTML = filteredMarketers.map(marketer => {
            const isOwnProfile = currentUser && marketer.id === currentUser.id;
            const hasLiked = marketer.has_liked || false;
            const canLike = !isOwnProfile && !hasLiked && this.userStats.remainingLikes > 0;
            
            return this.createMarketerCardHTML(marketer, isOwnProfile, hasLiked, canLike);
        }).join('');

        marketersGrid.innerHTML = cardsHTML;
        this.bindCardEvents();
    }

    createMarketerCardHTML(marketer, isOwnProfile, hasLiked, canLike) {
        const rankBadge = this.getRankBadge(marketer.rank);
        const avatarUrl = marketer.avatar || 'https://via.placeholder.com/60x60?text=Avatar';
        
        return `
            <div class="marketer-card ${isOwnProfile ? 'own-profile' : ''} ${hasLiked ? 'liked' : ''}" 
                 data-marketer-id="${marketer.id}">
                <div class="marketer-header">
                    <img src="${avatarUrl}" alt="${marketer.first_name}" class="marketer-avatar">
                    <div class="marketer-info">
                        <h3>${marketer.first_name} ${marketer.last_name}</h3>
                        <p>${marketer.email}</p>
                    </div>
                </div>
                
                <div class="marketer-bio">
                    ${marketer.bio || 'Sin descripción disponible'}
                </div>
                
                <div class="marketer-stats">
                    <span class="likes-count">${marketer.likes_count || 0}</span>
                    ${rankBadge}
                </div>
                
                <div class="marketer-actions">
                    ${isOwnProfile ? 
                        '<button class="like-btn disabled">Tu perfil</button>' :
                        `<button class="like-btn ${hasLiked ? 'liked' : ''}" 
                                ${!canLike ? 'disabled' : ''}
                                data-marketer-id="${marketer.id}">
                            ${hasLiked ? 'Ya diste like' : 'Dar Like'}
                        </button>`
                    }
                    <button class="view-btn" data-marketer-id="${marketer.id}">
                        Ver Perfil
                    </button>
                </div>
            </div>
        `;
    }

    getRankBadge(rank) {
        if (!rank || rank > 10) return '';
        
        let badgeClass = 'rank-badge';
        if (rank === 1) badgeClass += ' gold';
        else if (rank === 2) badgeClass += ' silver';
        else if (rank === 3) badgeClass += ' bronze';
        
        return `<span class="${badgeClass}">#${rank}</span>`;
    }

    bindCardEvents() {
        // Botones de like
        const likeButtons = document.querySelectorAll('.like-btn:not(.disabled)');
        likeButtons.forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const marketerId = btn.dataset.marketerId;
                this.handleLike(marketerId, btn);
            });
        });

        // Botones de ver perfil y cards clickeables
        const viewButtons = document.querySelectorAll('.view-btn');
        const marketerCards = document.querySelectorAll('.marketer-card');
        
        viewButtons.forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const marketerId = btn.dataset.marketerId;
                this.showMarketerModal(marketerId);
            });
        });

        marketerCards.forEach(card => {
            card.addEventListener('click', () => {
                const marketerId = card.dataset.marketerId;
                this.showMarketerModal(marketerId);
            });
        });
    }

    async handleLike(marketerId, button) {
        if (this.userStats.remainingLikes <= 0) {
            this.showError('Ya has usado todos tus likes disponibles');
            return;
        }

        try {
            button.disabled = true;
            button.textContent = 'Enviando...';

            const response = await authManager.makeAuthenticatedRequest(
                `${authManager.baseURL}/likes/`,
                {
                    method: 'POST',
                    body: JSON.stringify({ marketer_id: marketerId })
                }
            );

            if (response && response.ok) {
                // Actualizar el estado local
                const marketer = this.marketers.find(m => m.id == marketerId);
                if (marketer) {
                    marketer.has_liked = true;
                    marketer.likes_count = (marketer.likes_count || 0) + 1;
                }

                this.userStats.remainingLikes--;
                this.userStats.likesGiven++;
                
                this.updateStatsDisplay();
                this.renderMarketers();
                
                this.showSuccess('¡Like enviado exitosamente!');
            } else {
                const errorData = await response.json();
                this.showError(errorData.detail || 'Error al enviar like');
            }
        } catch (error) {
            console.error('Error sending like:', error);
            this.showError('Error de conexión al enviar like');
        }
    }

    showMarketerModal(marketerId) {
        const marketer = this.marketers.find(m => m.id == marketerId);
        if (!marketer) return;

        const modal = document.getElementById('profileModal');
        const modalAvatar = document.getElementById('modalAvatar');
        const modalName = document.getElementById('modalName');
        const modalEmail = document.getElementById('modalEmail');
        const modalBio = document.getElementById('modalBio');
        const modalLikes = document.getElementById('modalLikes');
        const modalLikeBtn = document.getElementById('modalLikeBtn');

        if (modalAvatar) modalAvatar.src = marketer.avatar || 'https://via.placeholder.com/80x80?text=Avatar';
        if (modalName) modalName.textContent = `${marketer.first_name} ${marketer.last_name}`;
        if (modalEmail) modalEmail.textContent = marketer.email;
        if (modalBio) modalBio.textContent = marketer.bio || 'Sin descripción disponible';
        if (modalLikes) modalLikes.textContent = `${marketer.likes_count || 0} likes`;

        // Configurar botón de like en modal
        if (modalLikeBtn) {
            const currentUser = authManager.getCurrentUser();
            const isOwnProfile = currentUser && marketer.id === currentUser.id;
            const hasLiked = marketer.has_liked;
            const canLike = !isOwnProfile && !hasLiked && this.userStats.remainingLikes > 0;

            if (isOwnProfile) {
                modalLikeBtn.textContent = 'Tu perfil';
                modalLikeBtn.disabled = true;
            } else if (hasLiked) {
                modalLikeBtn.textContent = '❤️ Ya diste like';
                modalLikeBtn.disabled = true;
                modalLikeBtn.className = 'btn-primary liked';
            } else if (canLike) {
                modalLikeBtn.textContent = '❤️ Dar Like';
                modalLikeBtn.disabled = false;
                modalLikeBtn.className = 'btn-primary';
                modalLikeBtn.onclick = () => {
                    this.handleLike(marketerId, modalLikeBtn);
                    this.closeModal();
                };
            } else {
                modalLikeBtn.textContent = 'Sin likes disponibles';
                modalLikeBtn.disabled = true;
            }
        }

        if (modal) modal.style.display = 'block';
    }

    closeModal() {
        const modal = document.getElementById('profileModal');
        if (modal) modal.style.display = 'none';
    }

    handleFilter(e) {
        const filterButtons = document.querySelectorAll('.filter-btn');
        filterButtons.forEach(btn => btn.classList.remove('active'));
        
        e.target.classList.add('active');
        this.currentFilter = e.target.dataset.filter;
        this.renderMarketers();
    }

    handleSearch(e) {
        this.searchTerm = e.target.value.toLowerCase();
        this.renderMarketers();
    }

    getFilteredMarketers() {
        let filtered = [...this.marketers];
        const currentUser = authManager.getCurrentUser();

        // Aplicar filtro
        switch (this.currentFilter) {
            case 'liked':
                filtered = filtered.filter(m => m.has_liked);
                break;
            case 'top':
                filtered = filtered.filter(m => m.rank && m.rank <= 10);
                filtered.sort((a, b) => (a.rank || 999) - (b.rank || 999));
                break;
            case 'all':
            default:
                // Ordenar por likes recibidos
                filtered.sort((a, b) => (b.likes_count || 0) - (a.likes_count || 0));
                break;
        }

        // Aplicar búsqueda
        if (this.searchTerm) {
            filtered = filtered.filter(marketer => {
                const fullName = `${marketer.first_name} ${marketer.last_name}`.toLowerCase();
                const email = marketer.email.toLowerCase();
                const bio = (marketer.bio || '').toLowerCase();
                
                return fullName.includes(this.searchTerm) || 
                       email.includes(this.searchTerm) || 
                       bio.includes(this.searchTerm);
            });
        }

        return filtered;
    }

    getEmptyStateHTML() {
        return `
            <div class="empty-state">
                <h3>No se encontraron marketeros</h3>
                <p>Intenta cambiar los filtros o el término de búsqueda</p>
            </div>
        `;
    }

    updateStatsDisplay() {
        const elements = {
            likesGiven: document.getElementById('likesGiven'),
            myLikes: document.getElementById('myLikes'),
            remainingLikes: document.getElementById('remainingLikes')
        };

        if (elements.likesGiven) {
            elements.likesGiven.textContent = this.userStats.likesGiven || 0;
        }
        if (elements.myLikes) {
            elements.myLikes.textContent = this.userStats.likesReceived || 0;
        }
        if (elements.remainingLikes) {
            elements.remainingLikes.textContent = this.userStats.remainingLikes || 0;
        }
    }

    updateTotalMembers() {
        const totalMembersElement = document.getElementById('totalMembers');
        if (totalMembersElement) {
            totalMembersElement.textContent = this.marketers.length;
        }
    }

    showError(message) {
        // Crear notificación temporal
        const notification = document.createElement('div');
        notification.className = 'notification error';
        notification.textContent = message;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #e74c3c;
            color: white;
            padding: 15px 20px;
            border-radius: 10px;
            z-index: 1000;
            animation: slideIn 0.3s ease;
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.remove();
        }, 3000);
    }

    showSuccess(message) {
        const notification = document.createElement('div');
        notification.className = 'notification success';
        notification.textContent = message;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #27ae60;
            color: white;
            padding: 15px 20px;
            border-radius: 10px;
            z-index: 1000;
            animation: slideIn 0.3s ease;
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.remove();
        }, 3000);
    }
}

// Inicializar dashboard cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', () => {
    new Dashboard();
});