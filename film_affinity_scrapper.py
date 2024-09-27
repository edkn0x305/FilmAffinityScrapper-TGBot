import logging
import requests
from requests.exceptions import RequestException
import emoji
from bs4 import BeautifulSoup
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

# Set up logging for the bot
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def search_filmaffinity(query):
    search_url = "https://www.filmaffinity.com/mx/search.php"
    params = {'stext': query}

    # Send the GET request to FilmAffinity's search page
    try:
        response = requests.get(search_url, params=params)
        response.raise_for_status()  # Esto lanza una excepción si el código de estado no es 200
    except RequestException as e:
        logger.error(f"Error en la solicitud HTTP: {e}")
        return None

    soup = BeautifulSoup(response.text, 'html.parser')

    # Verificar si la búsqueda devolvió directamente una página de película
    # En este caso, podemos buscar un título con el ID específico de la página de película
    movie_title = soup.find('h1', id='main-title')
    if movie_title:
        # Extraer la URL actual para usarla como movie_link
        movie_link = response.url
        title = movie_title.text.strip()

        # Extraer más detalles de la película
        year = soup.find('dd', itemprop='datePublished').text.strip() if soup.find('dd',
                                                                                   itemprop='datePublished') else "Año desconocido"

        # Si encontramos directamente la película, devolverla como un solo resultado
        return [{
            'title': title,
            'year': year,
            'link': movie_link
        }]

    # Check if the request was successful
    if response.status_code != 200:
        return None

    soup = BeautifulSoup(response.text, 'html.parser')

    # Find all search results (assuming they are inside divs with class 'se-it mt')
    results = soup.find_all('div', class_='se-it mt')
    movies = []

    # Loop through each result and extract relevant information
    for result in results:
        # Extract the movie title
        title = result.find('div', class_='mc-title').text.strip()

        # Extract the movie URL (link)
        movie_link = result.find('a')['href']

        # Extract the movie year
        year = result.find('div', class_='ye-w').text.strip()

        # Add the result to the search_results list
        movies.append({
            'title': title,
            'year': year,
            'link': f"{movie_link}"
        })

    return movies

# Convert all genres to camelCase for consistency
def to_camel_case(text):
    words = text.split()
    return words[0].lower() + ''.join(word.capitalize() for word in words[1:])

# Extract metadata from a movie page
def extract_movie_metadata(movie_url):
    try:
        response = requests.get(movie_url)
        response.raise_for_status()
    except RequestException as e:
        logger.error(f"Error al obtener la página de la película: {e}")
        return None, None, None

    if response.status_code != 200:
        return None

    soup = BeautifulSoup(response.text, 'html.parser')

    # Extract metadata (Title, Director, Year, Synopsis)
    title = soup.find('h1', id='main-title').text.strip()
    original_title = soup.find('dt', string='Título original').find_next('dd').text.strip()
    rating = soup.find('div', id='movie-rat-avg').text.strip() if soup.find('div', id='movie-rat-avg') else "No hay información."
    num_votes = soup.find('span', itemprop='ratingCount').text.strip() if soup.find('span', itemprop='ratingCount') else "No hay información"
    duration = soup.find('dd', itemprop='duration').text.strip() if soup.find('dd', itemprop='duration') else "No hay información"
    country = soup.find('dt', string="País").find_next('dd').text.strip()
    synopsis = soup.find('dd', itemprop='description').text.strip() if soup.find('dd',
                                                                                 itemprop='description') else "No hay información."
    director = soup.find('dd', class_='directors').text.strip() if soup.find('dd',
                                                                              class_='directors') else "No hay información"
    cast_list = soup.find_all('li', class_='nb')
    first_five_cast = [cast.find('div', class_='name').get_text(strip=True) for cast in cast_list]
    cast_string = ', '.join(first_five_cast)

    genres = soup.find_all('span', itemprop='genre')
    genre_list = [f"#{to_camel_case(genre.get_text(strip=True))}" for genre in genres]
    genres_string = ', '.join(genre_list)

    year = soup.find('dd', itemprop='datePublished').text.strip() if soup.find('dd',
                                                                               itemprop='datePublished') else "Unknown year"

    # Extract movie poster image
    poster = soup.find('img', itemprop='image')
    if poster:
        poster_url = poster['src']
    else:
        poster_url = None  # No se encontró imagen

    # Print the URL of the poster to verify we are capturing it correctly
    # print("Poster URL:", poster_url)

    description = (f"{emoji.emojize(':clapper_board:')} <b>Título:</b> <a href='{movie_url}'>{title} ({original_title})</a>\n"
            f"{emoji.emojize(':star:')} <b>Calificación:</b> {rating}/10 ({num_votes} votos)\n"
            f"{emoji.emojize(':calendar:')} <b>Año:</b> {year}\n"
            f"{emoji.emojize(':hourglass_not_done:')} <b>Duración</b> {duration}\n"
            f"{emoji.emojize(':world_map:')} <b>País:</b> {country}\n"
            f"{emoji.emojize(':bust_in_silhouette:')} <b>Dirección:</b> {director}\n"
            f"{emoji.emojize(':busts_in_silhouette:')} <b>Reparto:</b> {cast_string}\n"
            f"{emoji.emojize(':popcorn:')} <b>Género:</b> {genres_string}\n\n")
            #f"{emoji.emojize(':information:')} <b>Sinopsis</b> {emoji.emojize(':information:')}\n\n{synopsis}")

    return poster_url, description, synopsis


# Start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="¡Bienvenid@! Envíame el título de una película y la buscaré en FilmAffinity.")


# Search movie command handler
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text

    if not query:
        await update.message.reply_text("Por favor, proporciona un título de película para buscar.")
        return

    movies = search_filmaffinity(query)

    if not movies:
        await update.message.reply_text("Lo siento, no se encontraron resultados.")
        return

    # Create inline buttons for each movie result
    buttons = []
    for i, movie in enumerate(movies[:5]):  # Show only top 5 results
        buttons.append([InlineKeyboardButton(f"{movie['title']} ({movie['year']})", callback_data=movie['link'])])

    reply_markup = InlineKeyboardMarkup(buttons)
    await update.message.reply_text(f"{emoji.emojize(':check_mark_button:')}Selecciona una película:", reply_markup=reply_markup)


# Callback query handler for movie selection
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    movie_url = query.data
    poster_url, description, synopsis = extract_movie_metadata(movie_url)

    # Add a button for the synopsis
    buttons = [[InlineKeyboardButton("Ver Sinopsis", callback_data=f"sinopsis:{movie_url}")]]
    reply_markup = InlineKeyboardMarkup(buttons)

    if description:
        # Send the image with the description in the caption
        if poster_url:
            await query.message.reply_photo(photo=poster_url, caption=description, parse_mode='HTML', reply_markup=reply_markup)
        else:
            await query.message.reply_text(text=description, parse_mode='HTML', reply_markup=reply_markup)
    else:
        await query.edit_message_text(text="Lo siento, no pude extraer los detalles de la película.")

# Callback handler for "Ver Sinopsis"
async def show_synopsis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # Extract the movie URL from the callback data
    movie_url = query.data.split(':', 1)[1]
    _, _, synopsis = extract_movie_metadata(movie_url)

    if synopsis:
        await query.message.reply_text(f"{emoji.emojize(':information:')} <b>Sinopsis: </b> {emoji.emojize(':information:')}\n\n{synopsis}", parse_mode='HTML')
    else:
        await query.message.reply_text("Lo siento, no pude extraer la sinopsis.", parse_mode='HTML')

# Main function to run the bot
def main():
    # Get the bot token from BotFather
    TOKEN = '7879240423:AAFkJVq-pbjRwIj-e21Hia8Ae3GxJ5nFrJ0'

    # Create the Application and pass it your bot's token
    application = ApplicationBuilder().token(TOKEN).build()

    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    # Solución original con el comando /search: application.add_handler(CommandHandler("search", search_movie))
    application.add_handler(CallbackQueryHandler(button, pattern="^(?!sinopsis:)"))  # Manejatodo excepto 'sinopsis:'
    application.add_handler(CallbackQueryHandler(show_synopsis, pattern="^sinopsis:"))  # Maneja solo callbacks con 'sinopsis:'


    application.run_polling()


if __name__ == '__main__':
    main()