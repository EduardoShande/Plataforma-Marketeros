"""
Management command to setup initial data for the platform
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
import secrets
import string

from voting.models import Invitation, UserStats

User = get_user_model()


class Command(BaseCommand):
    help = 'Setup initial data for the marketeros platform'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--invitations',
            type=int,
            default=140,
            help='Number of invitations to create (default: 140)'
        )
        
        parser.add_argument(
            '--admin-email',
            type=str,
            default='admin@marketeros.com',
            help='Admin email address'
        )
        
        parser.add_argument(
            '--admin-password',
            type=str,
            default='admin123',
            help='Admin password'
        )
        
        parser.add_argument(
            '--expires-days',
            type=int,
            default=90,
            help='Days until invitations expire (default: 90)'
        )
        
        parser.add_argument(
            '--show-codes',
            action='store_true',
            help='Show all generated invitation codes'
        )
    
    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🚀 Configurando datos iniciales para la plataforma...')
        )
        
        # Crear superusuario admin
        admin_user = self.create_admin_user(
            options['admin_email'], 
            options['admin_password']
        )
        
        # Crear invitaciones
        self.create_invitations(
            options['invitations'],
            options['expires_days'],
            admin_user,
            options['show_codes']
        )
        
        # Actualizar estadísticas
        self.update_stats()
        
        # Mostrar resumen
        self.show_summary()
        
        self.stdout.write(
            self.style.SUCCESS('✅ Configuración inicial completada exitosamente!')
        )
    
    def create_admin_user(self, email, password):
        """Create admin user if it doesn't exist"""
        self.stdout.write('👤 Configurando usuario administrador...')
        
        if User.objects.filter(email=email).exists():
            self.stdout.write(
                self.style.WARNING(f'⚠️  El usuario {email} ya existe.')
            )
            return User.objects.get(email=email)
        
        admin_user = User.objects.create_superuser(
            username=email,
            email=email,
            password=password,
            first_name='Admin',
            last_name='Sistema',
            is_marketer=False,
            registration_completed=True
        )
        
        self.stdout.write(
            self.style.SUCCESS(f'✅ Usuario administrador creado: {email}')
        )
        self.stdout.write(f'   Contraseña: {password}')
        
        return admin_user
    
    def create_invitations(self, count, expires_days, admin_user, show_codes):
        """Create invitation codes"""
        self.stdout.write(f'🎟️  Creando {count} códigos de invitación...')
        
        if not admin_user:
            self.stdout.write(
                self.style.ERROR('❌ No se encontró usuario administrador.')
            )
            return
        
        expires_at = timezone.now() + timedelta(days=expires_days)
        created_count = 0
        all_codes = []
        
        for i in range(count):
            # Generar código único
            code = self.generate_unique_code()
            
            invitation = Invitation.objects.create(
                code=code,
                created_by=admin_user,
                expires_at=expires_at
            )
            
            all_codes.append(code)
            created_count += 1
            
            # Mostrar progreso cada 25 invitaciones
            if created_count % 25 == 0:
                self.stdout.write(f'   📝 Creadas {created_count}/{count} invitaciones...')
        
        self.stdout.write(
            self.style.SUCCESS(f'✅ {created_count} invitaciones creadas exitosamente!')
        )
        self.stdout.write(f'   📅 Expiran en: {expires_days} días')
        
        # Mostrar códigos según la opción
        if show_codes:
            self.stdout.write('\n📋 TODOS LOS CÓDIGOS GENERADOS:')
            for i, code in enumerate(all_codes, 1):
                url = f'register.html?code={code}'
                self.stdout.write(f'   {i:3d}. {code} -> {url}')
        else:
            # Mostrar solo algunos códigos de ejemplo
            sample_codes = all_codes[:10] if len(all_codes) >= 10 else all_codes
            self.stdout.write('\n📋 Códigos de ejemplo (primeros 10):')
            for i, code in enumerate(sample_codes, 1):
                url = f'register.html?code={code}'
                self.stdout.write(f'   {i:2d}. {code} -> {url}')
            
            if len(all_codes) > 10:
                self.stdout.write(f'   ... y {len(all_codes) - 10} códigos más')
                self.stdout.write('   💡 Usa --show-codes para ver todos los códigos')
    
    def generate_unique_code(self):
        """Generate unique invitation code"""
        attempts = 0
        max_attempts = 1000
        
        while attempts < max_attempts:
            # Formato: XXXX-XXXX-XXXX para mayor legibilidad
            code = '-'.join([
                ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(4))
                for _ in range(3)
            ])
            
            if not Invitation.objects.filter(code=code).exists():
                return code
            
            attempts += 1
        
        # Si no se puede generar un código único, usar UUID
        import uuid
        return str(uuid.uuid4()).upper()[:12]
    
    def update_stats(self):
        """Update or create user statistics"""
        self.stdout.write('📊 Actualizando estadísticas de usuarios...')
        
        users = User.objects.filter(is_marketer=True)
        stats_count = 0
        
        for user in users:
            UserStats.update_user_stats(user)
            stats_count += 1
        
        # Actualizar rankings solo si hay usuarios
        if stats_count > 0:
            UserStats.update_all_rankings()
        
        self.stdout.write(
            self.style.SUCCESS(f'✅ Estadísticas actualizadas para {stats_count} usuarios')
        )
    
    def show_summary(self):
        """Show platform summary"""
        total_users = User.objects.filter(is_marketer=True).count()
        active_users = User.objects.filter(
            is_marketer=True, 
            registration_completed=True
        ).count()
        total_invitations = Invitation.objects.count()
        unused_invitations = Invitation.objects.filter(used=False).count()
        
        # Obtener total de likes de forma segura
        try:
            from django.apps import apps
            Like = apps.get_model('voting', 'Like')
            total_likes = Like.objects.count()
        except:
            total_likes = 0
        
        self.stdout.write('\n📈 RESUMEN DE LA PLATAFORMA:')
        self.stdout.write('=' * 50)
        self.stdout.write(f'   👥 Total usuarios marketeros: {total_users}')
        self.stdout.write(f'   ✅ Usuarios activos: {active_users}')
        self.stdout.write(f'   🎟️  Total invitaciones: {total_invitations}')
        self.stdout.write(f'   📫 Invitaciones disponibles: {unused_invitations}')
        self.stdout.write(f'   ❤️  Total likes dados: {total_likes}')
        
        # URLs útiles
        self.stdout.write('\n🔗 URLs IMPORTANTES:')
        self.stdout.write('=' * 50)
        self.stdout.write('   • Admin Panel: http://localhost:8000/admin/')
        self.stdout.write('   • API Root: http://localhost:8000/api/')
        self.stdout.write('   • Marketers API: http://localhost:8000/api/marketers/')
        self.stdout.write('   • Frontend: http://localhost:8080 (o tu servidor local)')
        
        # Información de acceso
        self.stdout.write('\n🔑 ACCESO ADMINISTRATIVO:')
        self.stdout.write('=' * 50)
        self.stdout.write('   • Email: admin@marketeros.com')
        self.stdout.write('   • Password: admin123')
        
        # Próximos pasos
        self.stdout.write('\n🚀 PRÓXIMOS PASOS:')
        self.stdout.write('=' * 50)
        self.stdout.write('   1. python manage.py runserver')
        self.stdout.write('   2. Abre el frontend en tu navegador')
        self.stdout.write('   3. Usa los códigos de invitación para registrar usuarios')
        self.stdout.write('   4. Prueba el sistema de likes y rankings')
        
        # Comandos útiles adicionales
        self.stdout.write('\n🛠️  COMANDOS ÚTILES:')
        self.stdout.write('=' * 50)
        self.stdout.write('   • Ver todos los códigos:')
        self.stdout.write('     python manage.py setup_initial_data --show-codes')
        self.stdout.write('   • Crear más invitaciones:')
        self.stdout.write('     python manage.py setup_initial_data --invitations 50')
        self.stdout.write('   • Acceder al shell Django:')
        self.stdout.write('     python manage.py shell')
        
        self.stdout.write('\n🎉 ¡PLATAFORMA LISTA PARA USAR!')