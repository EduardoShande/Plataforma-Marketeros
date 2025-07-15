# Plataforma Marketeros - Sistema de Votación

Una plataforma web privada y exclusiva para que 140 marketeros seleccionados puedan conocerse, interactuar y votarse mutuamente con un sistema de likes limitado.

## 🚀 Características Principales

### Frontend
- **HTML, CSS y JavaScript Vanilla** separados por archivos
- **Diseño responsivo** (mobile-first)
- **Interfaz moderna** con animaciones y transiciones suaves
- **Sistema de autenticación** con tokens JWT
- **Dashboard interactivo** con filtros y búsqueda
- **Modal de perfiles** detallados
- **Sistema de notificaciones** en tiempo real

### Backend
- **Django REST Framework** con autenticación JWT
- **Base de datos SQLite3** (fácil desarrollo)
- **Sistema de invitaciones** con códigos únicos
- **Validaciones estrictas** de likes (máximo 5, sin autovoto, sin repetición)
- **Rankings automáticos** basados en likes recibidos
- **Panel de administración** completo
- **API REST** bien documentada

### Sistema de Likes
- ✅ **Máximo 5 likes** por usuario
- ✅ **No autovoto** permitido
- ✅ **Sin likes duplicados** al mismo usuario
- ✅ **Contador en tiempo real** de likes dados/recibidos
- ✅ **Ranking automático** por popularidad

## 📁 Estructura del Proyecto

```
marketeros-platform/
├── frontend/
│   ├── index.html              # Dashboard principal
│   ├── login.html              # Página de login
│   ├── register.html           # Página de registro
│   ├── styles.css              # Estilos generales
│   ├── login.css               # Estilos de autenticación
│   ├── dashboard.css           # Estilos del dashboard
│   ├── auth.js                 # Manejo de autenticación
│   ├── main.js                 # Funcionalidad principal
│   └── like.js                 # Sistema de likes
├── backend/
│   ├── marketeros_backend/     # Proyecto Django
│   ├── voting/                 # App principal
│   │   ├── models.py           # Modelos de datos
│   │   ├── serializers.py      # Serializers API
│   │   ├── views.py            # Vistas API
│   │   ├── urls.py             # URLs de la app
│   │   └── admin.py            # Panel de administración
│   ├── manage.py               # Comando Django
│   ├── requirements.txt        # Dependencias Python
│   └── db.sqlite3              # Base de datos
└── README.md                   # Este archivo
```

## 🛠️ Instalación y Configuración

### 1. Configurar el Backend

```bash
# Crear entorno virtual
python -m venv marketeros_env

# Activar entorno virtual
# Windows:
marketeros_env\Scripts\activate
# Mac/Linux:
source marketeros_env/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Crear proyecto Django
django-admin startproject marketeros_backend
cd marketeros_backend

# Crear app
python manage.py startapp voting
```

### 2. Configurar Base de Datos

```bash
# Crear migraciones
python manage.py makemigrations

# Aplicar migraciones
python manage.py migrate

# Crear datos iniciales (invitaciones y admin)
python manage.py setup_initial_data

# Crear superusuario adicional (opcional)
python manage.py createsuperuser
```

### 3. Ejecutar el Servidor

```bash
# Ejecutar servidor Django
python manage.py runserver
```

El backend estará disponible en: `http://localhost:8000`

### 4. Configurar el Frontend

1. Coloca todos los archivos HTML, CSS y JS en una carpeta `frontend/`
2. Abre `login.html` en tu navegador o usa un servidor local como Live Server
3. También puedes usar Python para servir archivos estáticos:

```bash
# Desde la carpeta frontend/
python -m http.server 8080
```

El frontend estará disponible en: `http://localhost:8080`

## 🔑 Uso de la Plataforma

### Para Administradores

1. **Acceso al Panel de Administración**:
   - URL: `http://localhost:8000/admin/`
   - Usuario: `admin@marketeros.com`
   - Contraseña: `admin123`

2. **Generar Invitaciones**:
   ```bash
   # Crear 140 invitaciones
   python manage.py setup_initial_data --invitations 140
   ```

3. **Gestionar Usuarios**:
   - Ver estadísticas de usuarios
   - Crear/eliminar invitaciones
   - Moderar contenido
   - Resetear likes (si es necesario)

### Para Marketeros

1. **Registro**:
   - Recibir enlace de invitación con código único
   - Completar registro con información personal
   - Subir foto de perfil

2. **Uso de la Plataforma**:
   - Explorar perfiles de otros marketeros
   - Dar hasta 5 likes estratégicamente
   - Ver ranking de popularidad
   - Buscar marketeros por nombre o especialidad

## 📊 API Endpoints

### Autenticación
- `POST /api/auth/register/` - Registro de usuario
- `POST /api/auth/login/` - Inicio de sesión
- `POST /api/auth/refresh/` - Renovar token
- `GET /api/auth/validate-invitation/` - Validar código

### Usuarios
- `GET /api/marketers/` - Lista de marketeros
- `GET /api/profile/` - Perfil del usuario actual
- `PUT /api/profile/` - Actualizar perfil
- `GET /api/user/stats/` - Estadísticas del usuario

### Likes
- `POST /api/likes/` - Dar like
- `DELETE /api/likes/{id}/` - Quitar like
- `GET /api/likes/my-likes/` - Mis likes dados
- `POST /api/likes/toggle/` - Alternar like

### Rankings
- `GET /api/marketers/ranking/` - Ranking de marketeros
- `POST /api/rankings/update/` - Actualizar rankings

### Administración
- `GET /api/admin/stats/` - Estadísticas del admin
- `POST /api/admin/invitations/bulk/` - Crear invitaciones masivas
- `POST /api/admin/likes/reset/` - Resetear todos los likes

## 🔧 Configuración Avanzada

### Variables de Entorno

Crea un archivo `.env` en el directorio del proyecto:

```env
DEBUG=True
SECRET_KEY=tu-clave-secreta-super-segura
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=sqlite:///db.sqlite3
CORS_ALLOWED_ORIGINS=http://localhost:8080,http://127.0.0.1:8080
```

### Configuración de Producción

Para producción, asegúrate de:

1. Configurar `DEBUG=False`
2. Usar una base de datos más robusta (PostgreSQL)
3. Configurar CORS apropiadamente
4. Usar un servidor web (Nginx + Gunicorn)
5. Configurar HTTPS
6. Establecer variables de entorno seguras

## 🎨 Personalización

### Estilos CSS
- Modifica `styles.css` para cambiar colores y tipografía
- Personaliza `dashboard.css` para el diseño de tarjetas
- Ajusta `login.css` para las páginas de autenticación

### Funcionalidad JavaScript
- `auth.js`: Lógica de autenticación y tokens
- `main.js`: Funcionalidad del dashboard y filtros
- `like.js`: Sistema de likes y validaciones

### Backend Django
- `models.py`: Estructura de datos y validaciones
- `views.py`: Lógica de la API
- `serializers.py`: Transformación de datos

## 🐛 Solución de Problemas

### Error CORS
```javascript
// Verificar configuración en settings.py
CORS_ALLOWED_ORIGINS = [
    "http://localhost:8080",
    "http://127.0.0.1:8080"
]
```

### Error de Migración
```bash
# Eliminar migraciones y base de datos
rm voting/migrations/0*.py
rm db.sqlite3

# Crear nuevas migraciones
python manage.py makemigrations
python manage.py migrate
```

### Error de JWT Token
```javascript
// Verificar token en localStorage
console.log(localStorage.getItem('authToken'));

// Limpiar token si está corrupto
localStorage.removeItem('authToken');
```

## 📝 To-Do / Mejoras Futuras

- [ ] Sistema de notificaciones push
- [ ] Chat entre marketeros
- [ ] Integración con redes sociales
- [ ] Exportación de datos
- [ ] Sistema de badges/logros
- [ ] Filtros avanzados de búsqueda
- [ ] Modo oscuro
- [ ] PWA (Progressive Web App)

## 🤝 Contribución

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit tus cambios (`git commit -am 'Agregar nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Crear un Pull Request

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo `LICENSE` para más detalles.

## 👥 Equipo

Desarrollado para una comunidad exclusiva de 140 marketeros seleccionados.

---

**¡Disfruta conectando con los mejores marketeros! 🚀**