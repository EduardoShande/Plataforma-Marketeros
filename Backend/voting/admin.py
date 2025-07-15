from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.db.models import Count
from django.urls import reverse
from django.utils.safestring import mark_safe

from .models import User, Invitation, Like, UserStats

# Register your models here.

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin interface for User model"""
    list_display = (
        'email', 'first_name', 'last_name', 'is_marketer', 
        'registration_completed', 'likes_received_display', 
        'likes_given_display', 'rank_display', 'avatar_display'
    )
    list_filter = (
        'is_marketer', 'registration_completed', 'is_active', 
        'is_staff', 'created_at'
    )
    search_fields = ('email', 'first_name', 'last_name', 'bio')
    ordering = ('-created_at',)
    
    fieldsets = (
        (None, {
            'fields': ('username', 'email', 'password')
        }),
        ('Información Personal', {
            'fields': ('first_name', 'last_name', 'bio', 'avatar')
        }),
        ('Configuración de Marketero', {
            'fields': ('is_marketer', 'registration_completed')
        }),
        ('Permisos', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',)
        }),
        ('Fechas importantes', {
            'fields': ('last_login', 'date_joined', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at', 'last_login', 'date_joined')
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('stats').annotate(
            likes_received_count=Count('received_likes'),
            likes_given_count=Count('given_likes')
        )
    
    def likes_received_display(self, obj):
        """Display likes received count"""
        count = getattr(obj, 'likes_received_count', obj.likes_received_count)
        return f"{count} ❤️"
    likes_received_display.short_description = "Likes Recibidos"
    likes_received_display.admin_order_field = 'likes_received_count'
    
    def likes_given_display(self, obj):
        """Display likes given count"""
        count = getattr(obj, 'likes_given_count', obj.likes_given_count)
        remaining = 5 - count
        return f"{count}/5 (quedan {remaining})"
    likes_given_display.short_description = "Likes Dados"
    likes_given_display.admin_order_field = 'likes_given_count'
    
    def rank_display(self, obj):
        """Display user rank"""
        if hasattr(obj, 'stats') and obj.stats.rank:
            rank = obj.stats.rank
            if rank == 1:
                return f"🥇 #{rank}"
            elif rank == 2:
                return f"🥈 #{rank}"
            elif rank == 3:
                return f"🥉 #{rank}"
            else:
                return f"#{rank}"
        return "-"
    rank_display.short_description = "Ranking"
    
    def avatar_display(self, obj):
        """Display avatar thumbnail"""
        if obj.avatar:
            return format_html(
                '<img src="{}" width="40" height="40" style="border-radius: 50%;" />',
                obj.avatar.url
            )
        return "Sin avatar"
    avatar_display.short_description = "Avatar"
    
    actions = ['make_marketer', 'remove_marketer', 'complete_registration']
    
    def make_marketer(self, request, queryset):
        """Mark users as marketers"""
        updated = queryset.update(is_marketer=True)
        self.message_user(request, f'{updated} usuarios marcados como marketeros.')
    make_marketer.short_description = "Marcar como marketeros"
    
    def remove_marketer(self, request, queryset):
        """Remove marketer status"""
        updated = queryset.update(is_marketer=False)
        self.message_user(request, f'{updated} usuarios removidos como marketeros.')
    remove_marketer.short_description = "Remover como marketeros"
    
    def complete_registration(self, request, queryset):
        """Complete user registration"""
        updated = queryset.update(registration_completed=True)
        self.message_user(request, f'{updated} registros completados.')
    complete_registration.short_description = "Completar registro"


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    """Admin interface for Invitation model"""
    list_display = (
        'code', 'email', 'used', 'used_by_display', 'created_by_display',
        'created_at', 'expires_at', 'status_display'
    )
    list_filter = ('used', 'created_at', 'expires_at')
    search_fields = ('code', 'email', 'used_by__email', 'created_by__email')
    ordering = ('-created_at',)
    
    fieldsets = (
        (None, {
            'fields': ('code', 'email', 'created_by')
        }),
        ('Estado', {
            'fields': ('used', 'used_by', 'used_at')
        }),
        ('Fechas', {
            'fields': ('created_at', 'expires_at')
        }),
    )
    
    readonly_fields = ('created_at', 'used_at')
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('created_by', 'used_by')
    
    def used_by_display(self, obj):
        """Display who used the invitation"""
        if obj.used_by:
            url = reverse('admin:voting_user_change', args=[obj.used_by.pk])
            return format_html('<a href="{}">{}</a>', url, obj.used_by.full_name)
        return "-"
    used_by_display.short_description = "Usado por"
    
    def created_by_display(self, obj):
        """Display who created the invitation"""
        url = reverse('admin:voting_user_change', args=[obj.created_by.pk])
        return format_html('<a href="{}">{}</a>', url, obj.created_by.full_name)
    created_by_display.short_description = "Creado por"
    
    def status_display(self, obj):
        """Display invitation status"""
        is_valid, message = obj.is_valid()
        if obj.used:
            return format_html('<span style="color: red;">✖ Usado</span>')
        elif is_valid:
            return format_html('<span style="color: green;">✓ Válido</span>')
        else:
            return format_html('<span style="color: orange;">⚠ Expirado</span>')
    status_display.short_description = "Estado"
    
    actions = ['generate_invitation_urls', 'expire_invitations']
    
    def generate_invitation_urls(self, request, queryset):
        """Generate invitation URLs"""
        urls = []
        for invitation in queryset:
            if not invitation.used:
                url = f"{request.build_absolute_uri('/register.html')}?code={invitation.code}"
                urls.append(f"{invitation.code}: {url}")
        
        if urls:
            self.message_user(
                request, 
                mark_safe("URLs generadas:<br>" + "<br>".join(urls))
            )
        else:
            self.message_user(request, "No hay invitaciones válidas seleccionadas.")
    generate_invitation_urls.short_description = "Generar URLs de invitación"
    
    def expire_invitations(self, request, queryset):
        """Expire selected invitations"""
        from django.utils import timezone
        updated = queryset.filter(used=False).update(expires_at=timezone.now())
        self.message_user(request, f'{updated} invitaciones expiradas.')
    expire_invitations.short_description = "Expirar invitaciones"


@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    """Admin interface for Like model"""
    list_display = (
        'giver_display', 'target_display', 'created_at'
    )
    list_filter = ('created_at',)
    search_fields = (
        'giver__first_name', 'giver__last_name', 'giver__email',
        'target__first_name', 'target__last_name', 'target__email'
    )
    ordering = ('-created_at',)
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('giver', 'target')
    
    def giver_display(self, obj):
        """Display giver with link"""
        url = reverse('admin:voting_user_change', args=[obj.giver.pk])
        return format_html('<a href="{}">{}</a>', url, obj.giver.full_name)
    giver_display.short_description = "Quien da like"
    
    def target_display(self, obj):
        """Display target with link"""
        url = reverse('admin:voting_user_change', args=[obj.target.pk])
        return format_html('<a href="{}">{}</a>', url, obj.target.full_name)
    target_display.short_description = "Quien recibe like"
    
    def has_add_permission(self, request):
        """Disable adding likes through admin"""
        return False


@admin.register(UserStats)
class UserStatsAdmin(admin.ModelAdmin):
    """Admin interface for UserStats model"""
    list_display = (
        'user_display', 'likes_received', 'likes_given', 
        'rank_display', 'last_updated'
    )
    list_filter = ('last_updated',)
    search_fields = ('user__first_name', 'user__last_name', 'user__email')
    ordering = ('rank', '-likes_received')
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')
    
    def user_display(self, obj):
        """Display user with link"""
        url = reverse('admin:voting_user_change', args=[obj.user.pk])
        return format_html('<a href="{}">{}</a>', url, obj.user.full_name)
    user_display.short_description = "Usuario"
    
    def rank_display(self, obj):
        """Display rank with emoji"""
        if obj.rank:
            if obj.rank == 1:
                return f"🥇 #{obj.rank}"
            elif obj.rank == 2:
                return f"🥈 #{obj.rank}"
            elif obj.rank == 3:
                return f"🥉 #{obj.rank}"
            else:
                return f"#{obj.rank}"
        return "-"
    rank_display.short_description = "Ranking"
    
    actions = ['update_stats', 'update_rankings']
    
    def update_stats(self, request, queryset):
        """Update stats for selected users"""
        count = 0
        for stats in queryset:
            UserStats.update_user_stats(stats.user)
            count += 1
        self.message_user(request, f'{count} estadísticas actualizadas.')
    update_stats.short_description = "Actualizar estadísticas"
    
    def update_rankings(self, request, queryset):
        """Update all rankings"""
        UserStats.update_all_rankings()
        self.message_user(request, 'Rankings actualizados para todos los usuarios.')
    update_rankings.short_description = "Actualizar rankings"
    
    def has_add_permission(self, request):
        """Disable adding stats through admin"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Disable deleting stats through admin"""
        return False


# Personalizar el sitio de administración
admin.site.site_header = "Administración - Plataforma Marketeros"
admin.site.site_title = "Admin Marketeros"
admin.site.index_title = "Panel de Control"