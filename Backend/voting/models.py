from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import MinLengthValidator
from django.core.exceptions import ValidationError
import uuid
import os

# Create your models here.

def user_avatar_path(instance, filename):
    """Generate upload path for user avatars"""
    ext = filename.split('.')[-1]
    filename = f'{instance.id}_{uuid.uuid4().hex[:8]}.{ext}'
    return os.path.join('avatars', filename)


class User(AbstractUser):
    """Custom User model for marketeros"""
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    bio = models.TextField(max_length=500, blank=True, null=True)
    avatar = models.ImageField(upload_to=user_avatar_path, blank=True, null=True)
    
    # Campos específicos para el sistema de votación
    is_marketer = models.BooleanField(default=True)
    registration_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Usar email como username
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']
    
    class Meta:
        db_table = 'users'
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
    
    def __str__(self):
        return f'{self.first_name} {self.last_name} ({self.email})'
    
    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'
    
    @property
    def likes_received_count(self):
        return self.received_likes.count()
    
    @property
    def likes_given_count(self):
        return self.given_likes.count()
    
    @property
    def remaining_likes(self):
        return max(0, 5 - self.likes_given_count)
    
    def can_like(self, target_user):
        """Check if user can like target_user"""
        if self == target_user:
            return False, "No puedes darte like a ti mismo"
        
        if self.remaining_likes <= 0:
            return False, "Ya has usado todos tus likes disponibles"
        
        if self.given_likes.filter(target=target_user).exists():
            return False, "Ya has dado like a este usuario"
        
        return True, "Puede dar like"


class Invitation(models.Model):
    """Model for invitation codes"""
    code = models.CharField(max_length=50, unique=True)
    email = models.EmailField(blank=True, null=True)
    used = models.BooleanField(default=False)
    used_by = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True)
    created_by = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='created_invitations'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    used_at = models.DateTimeField(blank=True, null=True)
    expires_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        db_table = 'invitations'
        verbose_name = 'Invitación'
        verbose_name_plural = 'Invitaciones'
    
    def __str__(self):
        return f'Invitation {self.code} - Used: {self.used}'
    
    def is_valid(self):
        """Check if invitation is still valid"""
        if self.used:
            return False, "El código de invitación ya ha sido usado"
        
        if self.expires_at and self.expires_at < timezone.now():
            return False, "El código de invitación ha expirado"
        
        return True, "Código válido"


class Like(models.Model):
    """Model for likes between users"""
    giver = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='given_likes'
    )
    target = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='received_likes'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'likes'
        verbose_name = 'Like'
        verbose_name_plural = 'Likes'
        unique_together = ('giver', 'target')
        indexes = [
            models.Index(fields=['giver']),
            models.Index(fields=['target']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f'{self.giver.full_name} → {self.target.full_name}'
    
    def clean(self):
        """Validate like constraints"""
        if self.giver == self.target:
            raise ValidationError("No puedes darte like a ti mismo")
        
        # Verificar límite de likes
        if self.giver.likes_given_count >= 5:
            raise ValidationError("Ya has usado todos tus likes disponibles")
        
        # Verificar like duplicado
        if Like.objects.filter(giver=self.giver, target=self.target).exists():
            raise ValidationError("Ya has dado like a este usuario")
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


class UserStats(models.Model):
    """Model for caching user statistics"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='stats')
    likes_received = models.IntegerField(default=0)
    likes_given = models.IntegerField(default=0)
    rank = models.IntegerField(blank=True, null=True)
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_stats'
        verbose_name = 'Estadística de Usuario'
        verbose_name_plural = 'Estadísticas de Usuarios'
        ordering = ['-likes_received', 'user__first_name']
    
    def __str__(self):
        return f'{self.user.full_name} - {self.likes_received} likes'
    
    @classmethod
    def update_user_stats(cls, user):
        """Update stats for a specific user"""
        stats, created = cls.objects.get_or_create(user=user)
        stats.likes_received = user.likes_received_count
        stats.likes_given = user.likes_given_count
        stats.save()
        return stats
    
    @classmethod
    def update_all_rankings(cls):
        """Update rankings for all users"""
        # Obtener todos los usuarios ordenados por likes recibidos
        users_with_likes = cls.objects.select_related('user').order_by(
            '-likes_received', 'user__first_name'
        )
        
        # Asignar rankings
        current_rank = 1
        previous_likes = None
        rank_counter = 0
        
        for stats in users_with_likes:
            rank_counter += 1
            
            # Si tiene los mismos likes que el anterior, mantiene el mismo ranking
            if previous_likes is not None and stats.likes_received != previous_likes:
                current_rank = rank_counter
            
            stats.rank = current_rank if stats.likes_received > 0 else None
            stats.save(update_fields=['rank'])
            
            previous_likes = stats.likes_received


# Signals para actualizar estadísticas automáticamente
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone


@receiver(post_save, sender=Like)
def update_stats_on_like_create(sender, instance, created, **kwargs):
    """Update stats when a like is created"""
    if created:
        # Actualizar stats del que recibe el like
        UserStats.update_user_stats(instance.target)
        # Actualizar stats del que da el like
        UserStats.update_user_stats(instance.giver)
        # Actualizar rankings
        UserStats.update_all_rankings()


@receiver(post_delete, sender=Like)
def update_stats_on_like_delete(sender, instance, **kwargs):
    """Update stats when a like is deleted"""
    # Actualizar stats del que recibía el like
    UserStats.update_user_stats(instance.target)
    # Actualizar stats del que daba el like
    UserStats.update_user_stats(instance.giver)
    # Actualizar rankings
    UserStats.update_all_rankings()


@receiver(post_save, sender=User)
def create_user_stats(sender, instance, created, **kwargs):
    """Create UserStats when a new user is created"""
    if created:
        UserStats.objects.get_or_create(user=instance)


@receiver(post_save, sender=Invitation)
def mark_invitation_used(sender, instance, **kwargs):
    """Mark invitation as used when used_by is set"""
    if instance.used_by and not instance.used:
        instance.used = True
        instance.used_at = timezone.now()
        instance.save(update_fields=['used', 'used_at'])