from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from . import views

# Router para ViewSets
router = DefaultRouter()
router.register(r'likes', views.LikeViewSet, basename='likes')
router.register(r'invitations', views.InvitationViewSet, basename='invitations')

app_name = 'voting'

urlpatterns = [
    # Autenticación
    path('auth/register/', views.UserRegistrationView.as_view(), name='register'),
    path('auth/login/', views.UserLoginView.as_view(), name='login'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Validación de invitaciones
    path('auth/validate-invitation/', views.validate_invitation_view, name='validate_invitation'),
    
    # Usuarios y perfiles
    path('profile/', views.UserProfileView.as_view(), name='user_profile'),
    path('marketers/', views.MarketersListView.as_view(), name='marketers_list'),
    path('marketers/<int:user_id>/', views.user_detail_view, name='user_detail'),
    path('search/', views.search_marketers_view, name='search_marketers'),
    
    # Estadísticas de usuario
    path('user/stats/', views.user_stats_view, name='user_stats'),
    path('likes/my-likes/', views.my_likes_view, name='my_likes'),
    path('likes/toggle/', views.toggle_like_view, name='toggle_like'),
    
    # Rankings
    path('marketers/ranking/', views.ranking_view, name='ranking'),
    path('rankings/update/', views.update_rankings_view, name='update_rankings'),
    
    # Feed de actividad
    path('activity/', views.activity_feed_view, name='activity_feed'),
    
    # Administración (solo admins)
    path('admin/stats/', views.admin_stats_view, name='admin_stats'),
    path('admin/invitations/bulk/', views.bulk_create_invitations, name='bulk_invitations'),
    path('admin/likes/reset/', views.reset_all_likes_view, name='reset_likes'),
    
    # Incluir rutas del router
    path('', include(router.urls)),
]