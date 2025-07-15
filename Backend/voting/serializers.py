from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
import base64
import uuid
from .models import User, Invitation, Like, UserStats


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration"""
    password = serializers.CharField(write_only=True, validators=[validate_password])
    confirm_password = serializers.CharField(write_only=True)
    invitation_code = serializers.CharField(write_only=True)
    avatar = serializers.CharField(required=False, allow_blank=True)  # Base64 encoded image
    
    class Meta:
        model = User
        fields = (
            'email', 'first_name', 'last_name', 'bio', 
            'password', 'confirm_password', 'invitation_code', 'avatar'
        )
    
    def validate(self, attrs):
        """Validate registration data"""
        # Validar contraseñas
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError("Las contraseñas no coinciden")
        
        # Validar código de invitación
        invitation_code = attrs.get('invitation_code')
        try:
            invitation = Invitation.objects.get(code=invitation_code)
            is_valid, message = invitation.is_valid()
            if not is_valid:
                raise serializers.ValidationError(f"Código de invitación inválido: {message}")
            attrs['invitation'] = invitation
        except Invitation.DoesNotExist:
            raise serializers.ValidationError("Código de invitación no existe")
        
        return attrs
    
    def create(self, validated_data):
        """Create new user"""
        # Remover campos que no van al modelo User
        validated_data.pop('confirm_password')
        invitation = validated_data.pop('invitation')
        avatar_data = validated_data.pop('avatar', None)
        
        # Crear usuario
        user = User.objects.create_user(
            username=validated_data['email'],
            **validated_data
        )
        
        # Procesar avatar si se proporcionó
        if avatar_data:
            try:
                self._save_avatar(user, avatar_data)
            except Exception as e:
                print(f"Error saving avatar: {e}")
        
        # Marcar invitación como usada
        invitation.used_by = user
        invitation.used = True
        invitation.used_at = timezone.now()
        invitation.save()
        
        user.registration_completed = True
        user.save()
        
        return user
    
    def _save_avatar(self, user, base64_data):
        """Save base64 encoded avatar"""
        try:
            format, imgstr = base64_data.split(';base64,')
            ext = format.split('/')[-1]
            
            # Generar nombre único
            filename = f"{user.id}_{uuid.uuid4().hex[:8]}.{ext}"
            
            # Decodificar imagen
            data = base64.b64decode(imgstr)
            
            # Guardar archivo
            from django.core.files.base import ContentFile
            user.avatar.save(filename, ContentFile(data), save=True)
            
        except Exception as e:
            raise serializers.ValidationError(f"Error procesando imagen: {str(e)}")


class UserLoginSerializer(serializers.Serializer):
    """Serializer for user login"""
    email = serializers.EmailField()
    password = serializers.CharField()
    
    def validate(self, attrs):
        """Validate login credentials"""
        email = attrs.get('email')
        password = attrs.get('password')
        
        if email and password:
            user = authenticate(
                request=self.context.get('request'),
                username=email,
                password=password
            )
            
            if not user:
                raise serializers.ValidationError("Credenciales inválidas")
            
            if not user.is_active:
                raise serializers.ValidationError("Cuenta desactivada")
            
            attrs['user'] = user
            return attrs
        else:
            raise serializers.ValidationError("Email y contraseña son requeridos")


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile display"""
    likes_received = serializers.IntegerField(source='likes_received_count', read_only=True)
    likes_given = serializers.IntegerField(source='likes_given_count', read_only=True)
    remaining_likes = serializers.IntegerField(read_only=True)
    rank = serializers.SerializerMethodField()
    has_liked = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = (
            'id', 'email', 'first_name', 'last_name', 'bio', 'avatar',
            'likes_received', 'likes_given', 'remaining_likes', 'rank',
            'has_liked', 'created_at'
        )
        read_only_fields = ('id', 'email', 'created_at')
    
    def get_rank(self, obj):
        """Get user rank"""
        try:
            return obj.stats.rank
        except UserStats.DoesNotExist:
            return None
    
    def get_has_liked(self, obj):
        """Check if current user has liked this user"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Like.objects.filter(
                giver=request.user, 
                target=obj
            ).exists()
        return False


class UserStatsSerializer(serializers.ModelSerializer):
    """Serializer for user statistics"""
    full_name = serializers.CharField(source='user.full_name', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    avatar = serializers.ImageField(source='user.avatar', read_only=True)
    
    class Meta:
        model = UserStats
        fields = (
            'full_name', 'email', 'avatar', 'likes_received', 
            'likes_given', 'rank', 'last_updated'
        )


class LikeSerializer(serializers.ModelSerializer):
    """Serializer for likes"""
    giver_name = serializers.CharField(source='giver.full_name', read_only=True)
    target_name = serializers.CharField(source='target.full_name', read_only=True)
    target_avatar = serializers.ImageField(source='target.avatar', read_only=True)
    marketer_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = Like
        fields = (
            'id', 'giver_name', 'target_name', 'target_avatar',
            'marketer_id', 'created_at'
        )
        read_only_fields = ('id', 'created_at')
    
    def validate_marketer_id(self, value):
        """Validate target user exists"""
        try:
            user = User.objects.get(id=value)
            return user
        except User.DoesNotExist:
            raise serializers.ValidationError("Usuario no encontrado")
    
    def validate(self, attrs):
        """Validate like constraints"""
        giver = self.context['request'].user
        target = attrs['marketer_id']
        
        # Verificar que no sea el mismo usuario
        if giver == target:
            raise serializers.ValidationError("No puedes darte like a ti mismo")
        
        # Verificar límite de likes
        if giver.likes_given_count >= 5:
            raise serializers.ValidationError("Ya has usado todos tus likes disponibles")
        
        # Verificar like duplicado
        if Like.objects.filter(giver=giver, target=target).exists():
            raise serializers.ValidationError("Ya has dado like a este usuario")
        
        attrs['target'] = target
        return attrs
    
    def create(self, validated_data):
        """Create new like"""
        validated_data['giver'] = self.context['request'].user
        validated_data.pop('marketer_id')
        return super().create(validated_data)


class InvitationSerializer(serializers.ModelSerializer):
    """Serializer for invitations"""
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)
    used_by_name = serializers.CharField(source='used_by.full_name', read_only=True)
    is_valid = serializers.SerializerMethodField()
    
    class Meta:
        model = Invitation
        fields = (
            'id', 'code', 'email', 'used', 'created_by_name', 'used_by_name',
            'created_at', 'used_at', 'expires_at', 'is_valid'
        )
        read_only_fields = ('id', 'created_at', 'used_at')
    
    def get_is_valid(self, obj):
        """Check if invitation is valid"""
        is_valid, _ = obj.is_valid()
        return is_valid
    
    def create(self, validated_data):
        """Create new invitation"""
        validated_data['created_by'] = self.context['request'].user
        
        # Generar código único si no se proporcionó
        if 'code' not in validated_data:
            validated_data['code'] = self._generate_unique_code()
        
        return super().create(validated_data)
    
    def _generate_unique_code(self):
        """Generate unique invitation code"""
        import secrets
        import string
        
        while True:
            code = ''.join(secrets.choice(
                string.ascii_uppercase + string.digits
            ) for _ in range(12))
            
            if not Invitation.objects.filter(code=code).exists():
                return code


class UserDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for user information"""
    stats = UserStatsSerializer(read_only=True)
    given_likes = serializers.SerializerMethodField()
    received_likes = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = (
            'id', 'email', 'first_name', 'last_name', 'bio', 'avatar',
            'is_marketer', 'registration_completed', 'created_at',
            'stats', 'given_likes', 'received_likes'
        )
        read_only_fields = ('id', 'email', 'created_at')
    
    def get_given_likes(self, obj):
        """Get users liked by this user"""
        likes = obj.given_likes.select_related('target').all()
        return [{
            'id': like.target.id,
            'name': like.target.full_name,
            'avatar': like.target.avatar.url if like.target.avatar else None,
            'created_at': like.created_at
        } for like in likes]
    
    def get_received_likes(self, obj):
        """Get users who liked this user"""
        likes = obj.received_likes.select_related('giver').all()
        return [{
            'id': like.giver.id,
            'name': like.giver.full_name,
            'avatar': like.giver.avatar.url if like.giver.avatar else None,
            'created_at': like.created_at
        } for like in likes]


class RankingSerializer(serializers.Serializer):
    """Serializer for ranking data"""
    user_id = serializers.IntegerField()
    full_name = serializers.CharField()
    email = serializers.EmailField()
    avatar = serializers.ImageField()
    likes_count = serializers.IntegerField()
    rank = serializers.IntegerField()
    
    def to_representation(self, instance):
        """Custom representation for ranking"""
        if isinstance(instance, UserStats):
            return {
                'user_id': instance.user.id,
                'full_name': instance.user.full_name,
                'email': instance.user.email,
                'avatar': instance.user.avatar.url if instance.user.avatar else None,
                'likes_count': instance.likes_received,
                'rank': instance.rank
            }
        return super().to_representation(instance)