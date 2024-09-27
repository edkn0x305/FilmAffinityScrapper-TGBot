# 305 CineScope Bot

305 CineScope Bot Bot es un bot de Telegram que permite a los usuarios buscar películas en FilmAffinity directamente desde Telegram. El bot devuelve metadatos detallados de las películas como el título, año, director, sinopsis y más. También permite a los usuarios acceder rápidamente a la sinopsis completa de una película seleccionada mediante un botón.

## Funcionalidades

- Búsqueda de películas en FilmAffinity por título.
- Recupera metadatos de las películas: título, año, director, reparto, género, etc.
- Muestra la sinopsis completa con solo hacer clic en un botón.
- Envía imágenes de los posters de las películas (si están disponibles).
- Maneja tanto listas de resultados como redirecciones directas a una película.

## Requisitos

Para ejecutar este bot necesitas tener instalado:

- Python 3.x
- Las siguientes bibliotecas de Python:
  - `python-telegram-bot`
  - `beautifulsoup4`
  - `requests`

Puedes instalar los paquetes requeridos ejecutando el siguiente comando:

```bash
pip install python-telegram-bot beautifulsoup4 requests
