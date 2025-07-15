// like.js - Manejo específico de sistema de likes
class LikeManager {
    constructor() {
        this.maxLikes = 5;
        this.userLikes = [];
        this.likesGiven = 0;
        this.init();
    }

    async init() {
        await this.loadUserLikes();
        this.updateLikeCounters();
    }

    async loadUserLikes() {
        try {
            const response = await authManager.makeAuthenticatedRequest(
                `${authManager.baseURL}/likes/my-likes/`
            );

            if (response && response.ok) {
                const data = await response.json();
                this.userLikes = data.likes || [];
                this.likesGiven = this.userLikes.length;
            }
        } catch (error) {
            console.error('Error loading user likes:', error);
        }
    }

    async giveLike(marketerId) {
        // Validaciones previas
        if (this.likesGiven >= this.maxLikes) {
            throw new Error('Ya has usado todos tus likes disponibles');
        }

        if (this.hasLikedMarketer(marketerId)) {
            throw new Error('Ya has dado like a este marketero');
        }

        if (await this.isOwnProfile(marketerId)) {
            throw new Error('No puedes darte like a ti mismo');
        }

        try {
            const response = await authManager.makeAuthenticatedRequest(
                `${authManager.baseURL}/likes/`,
                {
                    method: 'POST',
                    body: JSON.stringify({ 
                        marketer_id: marketerId 
                    })
                }
            );

            if (response && response.ok) {
                const likeData = await response.json();
                
                // Actualizar estado local
                this.userLikes.push({
                    id: likeData.id,
                    marketer_id: marketerId,
                    created_at: new Date().toISOString()
                });
                
                this.likesGiven++;
                this.updateLikeCounters();
                
                return likeData;
            } else {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Error al enviar like');
            }
        } catch (error) {
            console.error('Error giving like:', error);
            throw error;
        }
    }

    async removeLike(marketerId) {
        const like = this.userLikes.find(l => l.marketer_id == marketerId);
        if (!like) {
            throw new Error('No has dado like a este marketero');
        }

        try {
            const response = await authManager.makeAuthenticatedRequest(
                `${authManager.baseURL}/likes/${like.id}/`,
                {
                    method: 'DELETE'
                }
            );

            if (response && response.ok) {
                // Actualizar estado local
                this.userLikes = this.userLikes.filter(l => l.id !== like.id);
                this.likesGiven--;
                this.updateLikeCounters();
                
                return true;
            } else {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Error al quitar like');
            }
        } catch (error) {
            console.error('Error removing like:', error);
            throw error;
        }
    }

    hasLikedMarketer(marketerId) {
        return this.userLikes.some(like => like.marketer_id == marketerId);
    }

    async isOwnProfile(marketerId) {
        const currentUser = authManager.getCurrentUser();
        return currentUser && currentUser.id == marketerId;
    }

    getRemainingLikes() {
        return this.maxLikes - this.likesGiven;
    }

    getLikedMarketerIds() {
        return this.userLikes.map(like => like.marketer_id);
    }

    updateLikeCounters() {
        // Actualizar contadores en la UI
        const likesGivenElement = document.getElementById('likesGiven');
        const remainingLikesElement = document.getElementById('remainingLikes');

        if (likesGivenElement) {
            likesGivenElement.textContent = this.likesGiven;
        }

        if (remainingLikesElement) {
            remainingLikesElement.textContent = this.getRemainingLikes();
        }

        // Actualizar estado de botones de like
        this.updateLikeButtons();
    }

    updateLikeButtons() {
        const likeButtons = document.querySelectorAll('.like-btn');
        const currentUser = authManager.getCurrentUser();
        
        likeButtons.forEach(button => {
            const marketerId = button.dataset.marketerId;
            if (!marketerId) return;

            const isOwnProfile = currentUser && currentUser.id == marketerId;
            const hasLiked = this.hasLikedMarketer(marketerId);
            const canLike = !isOwnProfile && !hasLiked && this.getRemainingLikes() > 0;

            // Resetear clases
            button.classList.remove('liked', 'disabled');
            button.disabled = false;

            if (isOwnProfile) {
                button.textContent = 'Tu perfil';
                button.classList.add('disabled');
                button.disabled = true;
            } else if (hasLiked) {
                button.textContent = '❤️ Ya diste like';
                button.classList.add('liked');
                button.disabled = true;
            } else if (!canLike) {
                button.textContent = 'Sin likes disponibles';
                button.classList.add('disabled');
                button.disabled = true;
            } else {
                button.textContent = '❤️ Dar Like';
            }
        });
    }

    // Método para obtener estadísticas detalladas
    async getDetailedStats() {
        try {
            const response = await authManager.makeAuthenticatedRequest(
                `${authManager.baseURL}/likes/stats/`
            );

            if (response && response.ok) {
                return await response.json();
            }
        } catch (error) {
            console.error('Error getting detailed stats:', error);
        }
        
        return null;
    }

    // Método para obtener ranking de marketeros
    async getMarketersRanking() {
        try {
            const response = await authManager.makeAuthenticatedRequest(
                `${authManager.baseURL}/marketers/ranking/`
            );

            if (response && response.ok) {
                return await response.json();
            }
        } catch (error) {
            console.error('Error getting ranking:', error);
        }
        
        return [];
    }

    // Validar límites antes de enviar like
    validateLikeAction(marketerId) {
        const errors = [];

        if (this.likesGiven >= this.maxLikes) {
            errors.push('Ya has usado todos tus likes disponibles');
        }

        if (this.hasLikedMarketer(marketerId)) {
            errors.push('Ya has dado like a este marketero');
        }

        const currentUser = authManager.getCurrentUser();
        if (currentUser && currentUser.id == marketerId) {
            errors.push('No puedes darte like a ti mismo');
        }

        return {
            isValid: errors.length === 0,
            errors: errors
        };
    }

    // Método para obtener likes dados por el usuario
    getGivenLikes() {
        return this.userLikes;
    }

    // Método para obtener un like específico
    getLike(marketerId) {
        return this.userLikes.find(like => like.marketer_id == marketerId);
    }

    // Método para resetear likes (admin only)
    async resetAllLikes() {
        try {
            const response = await authManager.makeAuthenticatedRequest(
                `${authManager.baseURL}/likes/reset/`,
                {
                    method: 'POST'
                }
            );

            if (response && response.ok) {
                this.userLikes = [];
                this.likesGiven = 0;
                this.updateLikeCounters();
                return true;
            }
        } catch (error) {
            console.error('Error resetting likes:', error);
        }
        
        return false;
    }
}

// Utilidades para manejo de eventos de likes
class LikeEventHandlers {
    static async handleLikeClick(event) {
        event.preventDefault();
        event.stopPropagation();
        
        const button = event.target;
        const marketerId = button.dataset.marketerId;
        
        if (!marketerId || button.disabled) return;

        const likeManager = window.likeManager;
        if (!likeManager) return;

        // Validar acción
        const validation = likeManager.validateLikeAction(marketerId);
        if (!validation.isValid) {
            LikeEventHandlers.showError(validation.errors.join(', '));
            return;
        }

        // Deshabilitar botón temporalmente
        const originalText = button.textContent;
        button.disabled = true;
        button.textContent = 'Enviando...';

        try {
            await likeManager.giveLike(marketerId);
            
            // Mostrar feedback positivo
            LikeEventHandlers.showSuccess('¡Like enviado exitosamente!');
            
            // Actualizar UI si es necesario
            if (window.dashboard) {
                window.dashboard.refreshMarketerCard(marketerId);
            }
            
        } catch (error) {
            LikeEventHandlers.showError(error.message);
            
            // Restaurar botón
            button.disabled = false;
            button.textContent = originalText;
        }
    }

    static showError(message) {
        const notification = LikeEventHandlers.createNotification(message, 'error');
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.remove();
        }, 4000);
    }

    static showSuccess(message) {
        const notification = LikeEventHandlers.createNotification(message, 'success');
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.remove();
        }, 3000);
    }

    static createNotification(message, type) {
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.textContent = message;
        
        const bgColor = type === 'error' ? '#e74c3c' : '#27ae60';
        
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: ${bgColor};
            color: white;
            padding: 15px 20px;
            border-radius: 10px;
            z-index: 1000;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            animation: slideInRight 0.3s ease-out;
            max-width: 300px;
            word-wrap: break-word;
        `;
        
        return notification;
    }
}

// Crear instancia global del manejador de likes
document.addEventListener('DOMContentLoaded', () => {
    window.likeManager = new LikeManager();
});

// Agregar estilos de animación si no existen
if (!document.getElementById('like-animations')) {
    const style = document.createElement('style');
    style.id = 'like-animations';
    style.textContent = `
        @keyframes slideInRight {
            from {
                transform: translateX(100%);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
        
        .like-btn {
            position: relative;
            overflow: hidden;
        }
        
        .like-btn.sending::after {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(
                90deg,
                transparent,
                rgba(255, 255, 255, 0.3),
                transparent
            );
            animation: shimmer 1s infinite;
        }
        
        @keyframes shimmer {
            0% { left: -100%; }
            100% { left: 100%; }
        }
    `;
    document.head.appendChild(style);
}