from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta

from .models import User, Invitation, Like, UserStats
from .serializers import (
    UserRegistrationSerializer, UserLoginSerializer, UserProfileSerializer,
    UserStatsSerializer, LikeSerializer, InvitationSerializer,
    UserDetailSerializer, RankingSerializer
)


class UserRegistrationView(generics.CreateAPIView):
    """User registration endpoint"""
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Generar tokens JWT
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'user': UserProfileSerializer(user, context={'request': request}).data,
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'message': 'Usuario registrado exitosamente'
        }, status=status.HTTP_201_CREATED)


class UserLoginView(generics.GenericAPIView):
    """User login endpoint"""
    serializer_class = UserLoginSerializer
    permission_classes = [permissions.AllowAny]
    
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = serializer.validated_data['user']
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'user': UserProfileSerializer(user, context={'request': request}).data,
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'message': 'Inicio de sesión exitoso'
        })


class MarketersListView(generics.ListAPIView):
    """List all marketers with their stats"""
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        queryset = User.objects.filter(
            is_marketer=True,
            registration_completed=True
        ).select_related('stats').prefetch_related(
            'received_likes', 'given_likes'
        )
        
        # Filtros opcionales
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(email__icontains=search) |
                Q(bio__icontains=search)
            )
        
        # Ordenamiento por likes recibidos
        queryset = queryset.annotate(
            likes_count=Count('received_likes')
        ).order_by('-likes_count', 'first_name')
        
        return queryset
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        
        # Agregar información adicional
        total_marketers = queryset.count()
        current_user_stats = self.get_current_user_stats()
        
        return Response({
            'results': serializer.data,
            'total_marketers': total_marketers,
            'user_stats': current_user_stats
        })
    
    def get_current_user_stats(self):
        """Get current user statistics"""
        user = self.request.user
        return {
            'likes_given': user.likes_given_count,
            'likes_received': user.likes_received_count,
            'remaining_likes': user.remaining_likes
        }


class LikeViewSet(ModelViewSet):
    """ViewSet for managing likes"""
    serializer_class = LikeSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Like.objects.filter(
            giver=self.request.user
        ).select_related('target')
    
    def create(self, request, *args, **kwargs):
        """Create a new like"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        like = serializer.save()
        
        return Response({
            'like': LikeSerializer(like, context={'request': request}).data,
            'message': 'Like enviado exitosamente',
            'remaining_likes': request.user.remaining_likes
        }, status=status.HTTP_201_CREATED)
    
    def destroy(self, request, *args, **kwargs):
        """Remove a like"""
        like = self.get_object()
        like.delete()
        
        return Response({
            'message': 'Like eliminado exitosamente',
            'remaining_likes': request.user.remaining_likes
        })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_stats_view(request):
    """Get detailed user statistics"""
    user = request.user
    
    # Estadísticas básicas
    stats = {
        'likes_given': user.likes_given_count,
        'likes_received': user.likes_received_count,
        'remaining_likes': user.remaining_likes,
        'rank': getattr(user.stats, 'rank', None) if hasattr(user, 'stats') else None
    }
    
    # Likes dados (con detalles de los usuarios)
    given_likes = user.given_likes.select_related('target').all()
    stats['given_likes_details'] = [{
        'id': like.target.id,
        'name': like.target.full_name,
        'email': like.target.email,
        'avatar': like.target.avatar.url if like.target.avatar else None,
        'created_at': like.created_at
    } for like in given_likes]
    
    # Likes recibidos (con detalles de los usuarios)
    received_likes = user.received_likes.select_related('giver').all()
    stats['received_likes_details'] = [{
        'id': like.giver.id,
        'name': like.giver.full_name,
        'email': like.giver.email,
        'avatar': like.giver.avatar.url if like.giver.avatar else None,
        'created_at': like.created_at
    } for like in received_likes]
    
    return Response(stats)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def my_likes_view(request):
    """Get likes given by current user"""
    likes = Like.objects.filter(
        giver=request.user
    ).select_related('target')
    
    serializer = LikeSerializer(likes, many=True, context={'request': request})
    
    return Response({
        'likes': serializer.data,
        'total': likes.count(),
        'remaining': request.user.remaining_likes
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def ranking_view(request):
    """Get marketers ranking"""
    # Obtener parámetros de consulta
    limit = int(request.query_params.get('limit', 50))
    
    # Ranking basado en UserStats
    ranking = UserStats.objects.select_related('user').filter(
        user__is_marketer=True,
        user__registration_completed=True,
        likes_received__gt=0
    ).order_by('-likes_received', 'user__first_name')[:limit]
    
    serializer = RankingSerializer(ranking, many=True)
    
    return Response({
        'ranking': serializer.data,
        'total_ranked': ranking.count()
    })


class UserProfileView(generics.RetrieveUpdateAPIView):
    """User profile management"""
    serializer_class = UserDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        return self.request.user
    
    def patch(self, request, *args, **kwargs):
        """Update user profile"""
        partial = kwargs.pop('partial', True)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        return Response({
            'user': serializer.data,
            'message': 'Perfil actualizado exitosamente'
        })


class InvitationViewSet(ModelViewSet):
    """ViewSet for managing invitations (Admin only)"""
    serializer_class = InvitationSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]
    
    def get_queryset(self):
        return Invitation.objects.all().select_related(
            'created_by', 'used_by'
        ).order_by('-created_at')
    
    def create(self, request, *args, **kwargs):
        """Create new invitation"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        invitation = serializer.save()
        
        # Generar URL de invitación
        invitation_url = f"{request.build_absolute_uri('/register.html')}?code={invitation.code}"
        
        return Response({
            'invitation': InvitationSerializer(invitation).data,
            'invitation_url': invitation_url,
            'message': 'Invitación creada exitosamente'
        }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated, permissions.IsAdminUser])
def reset_all_likes_view(request):
    """Reset all likes (Admin only)"""
    if not request.user.is_superuser:
        return Response({
            'error': 'Solo los superusuarios pueden resetear todos los likes'
        }, status=status.HTTP_403_FORBIDDEN)
    
    # Confirmar acción
    confirm = request.data.get('confirm', False)
    if not confirm:
        return Response({
            'error': 'Debe confirmar la acción enviando confirm: true'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Eliminar todos los likes
    deleted_count, _ = Like.objects.all().delete()
    
    # Resetear estadísticas
    UserStats.objects.all().update(
        likes_received=0,
        likes_given=0,
        rank=None
    )
    
    return Response({
        'message': f'Se eliminaron {deleted_count} likes exitosamente',
        'deleted_likes': deleted_count
    })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def update_rankings_view(request):
    """Force update of all user rankings"""
    try:
        UserStats.update_all_rankings()
        return Response({
            'message': 'Rankings actualizados exitosamente'
        })
    except Exception as e:
        return Response({
            'error': f'Error actualizando rankings: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_detail_view(request, user_id):
    """Get detailed information about a specific user"""
    try:
        user = User.objects.select_related('stats').prefetch_related(
            'received_likes__giver',
            'given_likes__target'
        ).get(id=user_id, is_marketer=True, registration_completed=True)
    except User.DoesNotExist:
        return Response({
            'error': 'Usuario no encontrado'
        }, status=status.HTTP_404_NOT_FOUND)
    
    serializer = UserDetailSerializer(user, context={'request': request})
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def validate_invitation_view(request):
    """Validate invitation code without using it"""
    code = request.query_params.get('code')
    if not code:
        return Response({
            'error': 'Código de invitación requerido'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        invitation = Invitation.objects.get(code=code)
        is_valid, message = invitation.is_valid()
        
        return Response({
            'valid': is_valid,
            'message': message,
            'email': invitation.email if is_valid else None
        })
    except Invitation.DoesNotExist:
        return Response({
            'valid': False,
            'message': 'Código de invitación no existe'
        })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def search_marketers_view(request):
    """Search marketers by name, email or bio"""
    query = request.query_params.get('q', '').strip()
    if len(query) < 2:
        return Response({
            'error': 'La búsqueda debe tener al menos 2 caracteres'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    marketers = User.objects.filter(
        Q(first_name__icontains=query) |
        Q(last_name__icontains=query) |
        Q(email__icontains=query) |
        Q(bio__icontains=query),
        is_marketer=True,
        registration_completed=True
    ).select_related('stats').annotate(
        likes_count=Count('received_likes')
    ).order_by('-likes_count', 'first_name')[:20]
    
    serializer = UserProfileSerializer(
        marketers, many=True, context={'request': request}
    )
    
    return Response({
        'results': serializer.data,
        'query': query,
        'count': marketers.count()
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def activity_feed_view(request):
    """Get recent activity feed"""
    # Últimos likes recibidos por el usuario actual
    recent_received = Like.objects.filter(
        target=request.user
    ).select_related('giver').order_by('-created_at')[:10]
    
    # Últimos likes dados por el usuario actual
    recent_given = Like.objects.filter(
        giver=request.user
    ).select_related('target').order_by('-created_at')[:10]
    
    # Actividad general reciente (opcional)
    recent_activity = Like.objects.select_related(
        'giver', 'target'
    ).order_by('-created_at')[:20]
    
    return Response({
        'recent_received': [{
            'id': like.id,
            'from': {
                'id': like.giver.id,
                'name': like.giver.full_name,
                'avatar': like.giver.avatar.url if like.giver.avatar else None
            },
            'created_at': like.created_at
        } for like in recent_received],
        'recent_given': [{
            'id': like.id,
            'to': {
                'id': like.target.id,
                'name': like.target.full_name,
                'avatar': like.target.avatar.url if like.target.avatar else None
            },
            'created_at': like.created_at
        } for like in recent_given],
        'recent_activity': [{
            'id': like.id,
            'from': {
                'id': like.giver.id,
                'name': like.giver.full_name,
                'avatar': like.giver.avatar.url if like.giver.avatar else None
            },
            'to': {
                'id': like.target.id,
                'name': like.target.full_name,
                'avatar': like.target.avatar.url if like.target.avatar else None
            },
            'created_at': like.created_at
        } for like in recent_activity]
    })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def toggle_like_view(request):
    """Toggle like for a user (give or remove)"""
    marketer_id = request.data.get('marketer_id')
    if not marketer_id:
        return Response({
            'error': 'marketer_id es requerido'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        target_user = User.objects.get(
            id=marketer_id, 
            is_marketer=True, 
            registration_completed=True
        )
    except User.DoesNotExist:
        return Response({
            'error': 'Usuario no encontrado'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Verificar si ya existe el like
    existing_like = Like.objects.filter(
        giver=request.user, 
        target=target_user
    ).first()
    
    if existing_like:
        # Remover like existente
        existing_like.delete()
        action = 'removed'
        message = 'Like eliminado exitosamente'
    else:
        # Crear nuevo like
        can_like, error_message = request.user.can_like(target_user)
        if not can_like:
            return Response({
                'error': error_message
            }, status=status.HTTP_400_BAD_REQUEST)
        
        Like.objects.create(giver=request.user, target=target_user)
        action = 'added'
        message = 'Like enviado exitosamente'
    
    return Response({
        'action': action,
        'message': message,
        'remaining_likes': request.user.remaining_likes,
        'target_likes_count': target_user.likes_received_count
    })


# Error handlers personalizados
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json


@csrf_exempt
def custom_404_view(request, exception=None):
    """Custom 404 handler for API"""
    return JsonResponse({
        'error': 'Endpoint no encontrado',
        'status_code': 404
    }, status=404)


@csrf_exempt
def custom_500_view(request):
    """Custom 500 handler for API"""
    return JsonResponse({
        'error': 'Error interno del servidor',
        'status_code': 500
    }, status=500)
def bulk_create_invitations(request):
    """Create multiple invitations at once"""
    count = request.data.get('count', 1)
    emails = request.data.get('emails', [])
    expires_days = request.data.get('expires_days', 30)
    
    if count < 1 or count > 100:
        return Response({
            'error': 'El número debe estar entre 1 y 100'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    expires_at = timezone.now() + timedelta(days=expires_days)
    created_invitations = []
    
    # Crear invitaciones
    for i in range(count):
        email = emails[i] if i < len(emails) else None
        
        invitation = Invitation.objects.create(
            created_by=request.user,
            email=email,
            expires_at=expires_at
        )
        
        # Generar código único
        import secrets
        import string
        while True:
            code = ''.join(secrets.choice(
                string.ascii_uppercase + string.digits
            ) for _ in range(12))
            
            if not Invitation.objects.filter(code=code).exists():
                invitation.code = code
                invitation.save()
                break
        
        created_invitations.append(invitation)
    
    # Serializar resultados
    serializer = InvitationSerializer(created_invitations, many=True)
    
    return Response({
        'invitations': serializer.data,
        'count': len(created_invitations),
        'message': f'{len(created_invitations)} invitaciones creadas exitosamente'
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated, permissions.IsAdminUser])
def admin_stats_view(request):
    """Get admin statistics"""
    total_users = User.objects.filter(is_marketer=True).count()
    active_users = User.objects.filter(
        is_marketer=True, 
        registration_completed=True
    ).count()
    total_likes = Like.objects.count()
    total_invitations = Invitation.objects.count()
    used_invitations = Invitation.objects.filter(used=True).count()
    
    # Usuarios más activos (que más likes han dado)
    most_active_givers = User.objects.annotate(
        given_count=Count('given_likes')
    ).filter(given_count__gt=0).order_by('-given_count')[:5]
    
    # Usuarios más populares (que más likes han recibido)
    most_popular = User.objects.annotate(
        received_count=Count('received_likes')
    ).filter(received_count__gt=0).order_by('-received_count')[:5]
    
    return Response({
        'total_users': total_users,
        'active_users': active_users,
        'total_likes': total_likes,
        'total_invitations': total_invitations,
        'used_invitations': used_invitations,
        'unused_invitations': total_invitations - used_invitations,
        'most_active_givers': UserProfileSerializer(
            most_active_givers, many=True, context={'request': request}
        ).data,
        'most_popular': UserProfileSerializer(
            most_popular, many=True, context={'request': request}
        ).data
    })
