\# 🎟️ Ticket-F — Sistema de Tickets y Gestión de Eventos



Ticket-F es una plataforma desarrollada en \*\*Django\*\* para la gestión completa de eventos, tickets, cuentas administradoras, checkout público y validación en terreno.



Permite:



\* Administración de cuentas (empresas).

\* Creación y edición de eventos.

\* Tipos de tickets, descuentos, cupones y códigos de cortesía.

\* Flujo completo de compra de tickets (checkout público).

\* Panel de órdenes y detalle de tickets.

\* Validación en terreno.

\* Panel avanzado para superadmin.



---



\# 🚀 1. Requisitos



\* \*\*Python 3.11\*\* (o compatible)

\* \*\*pip\*\*

\* \*\*virtualenv\*\* (opcional)

\* SQLite (para desarrollo)

\* Postgres (opcional para producción/AWS)



---



\# 🗂 2. Estructura del proyecto



\* `core/` → Configuración Django + settings

\* `accounts/` → Usuarios, cuentas, roles, perfiles

\* `events/` → Eventos

\* `tickets/` → Tipos de ticket, descuentos

\* `orders/` → Órdenes, tickets generados, validación

\* `public/` → Checkout público del flujo comercial

\* `templates/` → Vistas HTML

\* `core/static/` → Archivos estáticos del proyecto

\* `manage.py` → Ejecutable de Django

\* `.env.example` → Variables de entorno base

\* `requirements.txt` → Dependencias del proyecto



---



\# 📦 3. Instalación del proyecto (local)



\## 3.1. Clonar el repositorio



```bash

git clone https://github.com/TU\_USUARIO/TU\_REPO.git

cd TU\_REPO

```



\*(Reemplazar con tu repositorio real cuando lo subas)\*



---



\## 3.2. Crear entorno virtual



```bash

python -m venv .venv

```



\### Activar entorno virtual:



\*\*Windows (PowerShell):\*\*



```bash

.\\.venv\\Scripts\\Activate.ps1

```



\*\*Linux / macOS:\*\*



```bash

source .venv/bin/activate

```



---



\## 3.3. Instalar dependencias



```bash

pip install -r requirements.txt

```



---



\## 3.4. Configurar variables de entorno



El repositorio incluye:



```

.env.example

```



Duplicar el archivo como `.env`:



\### Windows:



Copiar manualmente `.env.example` → crear `.env`



\### Linux/Mac:



```bash

cp .env.example .env

```



Configurar al menos:



```env

SECRET\_KEY=CAMBIAR\_ESTE\_VALOR

DEBUG=True

ALLOWED\_HOSTS=127.0.0.1,localhost



DB\_ENGINE=sqlite

DB\_NAME=db.sqlite3

```



Para producción (AWS), cambiar a Postgres:



```env

DB\_ENGINE=postgres

DB\_NAME=nombre

DB\_USER=usuario

DB\_PASSWORD=contraseña

DB\_HOST=host

DB\_PORT=5432

```



---



\## 3.5. Aplicar migraciones



```bash

python manage.py migrate

```



---



\## 3.6. Crear un superusuario



```bash

python manage.py createsuperuser

```



---



\## 3.7. Ejecutar el servidor



```bash

python manage.py runserver

```



Abrir:



```

http://127.0.0.1:8000/

```



---



\# 🎨 4. Archivos estáticos y media



En `settings.py` se usa esta configuración:



```python

STATIC\_URL = "/static/"



STATICFILES\_DIRS = \[

&nbsp;   BASE\_DIR / "core" / "static",

]



STATIC\_ROOT = BASE\_DIR / "staticfiles"



MEDIA\_URL = "/media/"

MEDIA\_ROOT = BASE\_DIR / "media"

```



Para producción:



```bash

python manage.py collectstatic --noinput

```



---



\# 🛠 5. Variables de entorno usadas por el proyecto



\* `SECRET\_KEY`

\* `DEBUG`

\* `ALLOWED\_HOSTS`

\* `DB\_ENGINE`

\* `DB\_NAME`

\* `DB\_USER`

\* `DB\_PASSWORD`

\* `DB\_HOST`

\* `DB\_PORT`

\* Configuración de correo (si se usa email)



---



\# ☁️ 6. Deploy en AWS (resumen)



\### 6.1. Crear servidor (Elastic Beanstalk, EC2 o Lightsail)



\### 6.2. Configurar variables de entorno en AWS:



```

SECRET\_KEY=xxxxx

DEBUG=False

ALLOWED\_HOSTS=tu-dominio.com

DB\_ENGINE=postgres

DB\_NAME=xxxx

DB\_USER=xxxx

DB\_PASSWORD=xxxx

DB\_HOST=xxxx.rds.amazonaws.com

DB\_PORT=5432

```



\### 6.3. Instalar dependencias



```bash

pip install -r requirements.txt

```



\### 6.4. Migraciones



```bash

python manage.py migrate

```



\### 6.5. Recolectar estáticos



```bash

python manage.py collectstatic --noinput

```



\### 6.6. Ejecutar el proyecto con un servidor WSGI



Ejemplo:



```bash

gunicorn core.wsgi:application --bind 0.0.0.0:8000

```



---



\# 📑 7. Notas adicionales



\* El archivo `.gitignore` incluye exclusiones para `.venv`, `db.sqlite3`, `.env`, caché, media y estáticos compilados.

\* El proyecto está preparado para que se ejecute sin modificaciones en cualquier PC con Python 3.



---



\# 📄 8. Licencia



\*(Agregar una licencia si corresponde.)\*



```}

```



