import streamlit as st
import pickle
import pandas as pd
import sqlite3
import requests
import time
import random
from urllib.parse import quote
from streamlit_lottie import st_lottie

st.set_page_config(layout="wide", page_title="Book Recommender 📚", page_icon="📖")

GOOGLE_BOOKS_API_KEY = st.secrets["google_api_key"]
GOOGLE_API_URL = "https://www.googleapis.com/books/v1/volumes?q=intitle:{}&key=" + GOOGLE_BOOKS_API_KEY
BOOK_RECOMMENDER_LOGO = "Book-recommender-logo.png"


# --------------------------- DATABASE SETUP ---------------------------
def create_users_table():
    conn = sqlite3.connect("users_book.db")
    c = conn.cursor()
    c.execute('''
              CREATE TABLE IF NOT EXISTS users
              (
                  username
                  TEXT
                  PRIMARY
                  KEY,
                  password
                  TEXT
              )
              ''')
    conn.commit()
    conn.close()


def create_fav_and_history_tables():
    conn = sqlite3.connect("users_book.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS history
                 (
                     username
                     TEXT,
                     book_title
                     TEXT,
                     timestamp
                     DATETIME
                     DEFAULT
                     CURRENT_TIMESTAMP
                 )''')
    c.execute('''CREATE TABLE IF NOT EXISTS reviews
    (
        username
        TEXT,
        book_title
        TEXT,
        review_text
        TEXT,
        timestamp
        DATETIME
        DEFAULT
        CURRENT_TIMESTAMP,
        PRIMARY
        KEY
                 (
        username,
        book_title
                 )
        )''')
    conn.commit()
    conn.close()


# Function to add a new user to the database.
# Returns True if successful, False if username already exists (IntegrityError) or invalid.
def add_user(username, password):
    username_stripped = username.strip()
    # Validate username: must not be empty/whitespace and must contain at least one alphabetic character.
    if not username_stripped or not any(char.isalpha() for char in username_stripped):
        st.error("Username must contain at least one letter and cannot be empty or just numbers.")
        return False

    conn = sqlite3.connect("users_book.db")
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username_stripped, password))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False  # Username already exists
    finally:
        conn.close()



def validate_user(username, password):
    conn = sqlite3.connect("users_book.db")
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=? AND password=?", (username.strip(), password))
    result = c.fetchone()
    conn.close()
    return result


def add_to_history(username, book_title):
    conn = sqlite3.connect("users_book.db")
    c = conn.cursor()
    c.execute("INSERT INTO history (username, book_title) VALUES (?, ?)", (username, book_title))
    conn.commit()
    conn.close()


def get_history(username):
    conn = sqlite3.connect("users_book.db")
    c = conn.cursor()
    c.execute("SELECT book_title FROM history WHERE username=? ORDER BY timestamp DESC", (username,))
    results = c.fetchall()
    conn.close()
    return [r[0] for r in results]


# Function to clear history for a user
def clear_history(username):
    conn = sqlite3.connect("users_book.db")
    c = conn.cursor()
    c.execute("DELETE FROM history WHERE username=?", (username,))
    conn.commit()
    conn.close()


def add_review(username, book_title, review_text):
    conn = sqlite3.connect("users_book.db")
    c = conn.cursor()
    try:
        c.execute("INSERT INTO reviews (username, book_title, review_text) VALUES (?, ?, ?)",
                  (username, book_title, review_text))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        c.execute(
            "UPDATE reviews SET review_text = ?, timestamp = CURRENT_TIMESTAMP WHERE username = ? AND book_title = ?",
            (review_text, username, book_title))
        conn.commit()
        return True
    finally:
        conn.close()


def get_reviews(book_title):
    conn = sqlite3.connect("users_book.db")
    c = conn.cursor()
    c.execute("SELECT username, review_text, timestamp FROM reviews WHERE book_title=? ORDER BY timestamp DESC",
              (book_title,))
    results = c.fetchall()
    conn.close()
    return results


create_users_table()
create_fav_and_history_tables()

# --------------------------- SESSION STATE ---------------------------
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_favorites' not in st.session_state:
    # This will store favorites in session state as: {'username': [{'title': '...', 'author': '...', ...}, ...]}
    st.session_state.user_favorites = {}
if 'show_main_app' not in st.session_state:
    st.session_state.show_main_app = False  # Controls visibility of main tabs after login
if 'username' not in st.session_state:
    st.session_state.username = None
if 'show_welcome' not in st.session_state:
    st.session_state.show_welcome = False

# --------------------------- LOGIN/REGISTER ---------------------------
if not st.session_state.logged_in:
    st.title("📚 Book Recommender - Login or Register")
    tab1, tab2 = st.tabs(["🔐 Login", "📝 Register"])

    with tab1:
        username = st.text_input("Username", key="login_user")
        password = st.text_input("Password", type="password", key="login_pass")
        if st.button("Login"):
            if validate_user(username, password):
                st.success("Logged in successfully! ✅")
                st.session_state.logged_in = True
                st.session_state.username = username.strip()
                st.session_state.show_welcome = True  # Show welcome screen after successful login
                st.rerun()
            else:
                st.error("Invalid credentials.")

    with tab2:
        new_user = st.text_input("New Username")
        new_pass = st.text_input("New Password", type="password")
        if st.button("Register"):
            if new_user and new_pass:
                if add_user(new_user, new_pass):
                    st.success("User registered! Please log in. 🎉")
                else:
                    st.error("Username already exists. Please choose a different one.")
            else:
                st.warning("Please fill both fields.")
    st.stop()  # Stop execution here if not logged in

# --------------------------- Personalized Welcome Dashboard ---------------------------
if st.session_state.logged_in and st.session_state.show_welcome:
    # No custom CSS for background, reverting to Streamlit's default theme
    # Centering content using columns

    st.markdown("<br>", unsafe_allow_html=True)  # Add some space at the top

    # Center the logo
    col1_logo, col2_logo, col3_logo = st.columns([1, 1, 1])
    with col2_logo:
        st.image(BOOK_RECOMMENDER_LOGO, width=400)

    # Center the welcome title
    st.markdown(f"<h1 style='text-align: center; color: #FF4B4B;'>Welcome, {st.session_state.username}! 👋</h1>",
                unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; font-size: 1.2rem;'>Explore a world of books tailored just for you.</p>",
                unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)  # Add some space before the button

    # Center the button
    col1_btn, col2_btn, col3_btn = st.columns([1, 1, 1])
    with col2_btn:
        if st.button("Start Exploring Books! 🚀", use_container_width=True, type="primary"):
            st.session_state.show_welcome = False
            st.session_state.show_main_app = True
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)  # Add some space at the bottom
    st.stop()  # Stop here until user clicks to explore

# --------------------------- LOAD DATA ---------------------------
if st.session_state.logged_in and st.session_state.show_main_app:
    with st.spinner("Loading book data..."):
        popular_df = pickle.load(open('popular.pkl', 'rb'))
        pt = pickle.load(open('pt.pkl', 'rb'))
        similarity_scores = pickle.load(open('similarity_scores.pkl', 'rb'))
    st.success("Data loaded! Ready to recommend. ✅")

    # --------------------------- GOOGLE BOOKS API ---------------------------
    def get_book_info_from_google(title, retries=3, delay=3):
        query = quote(title)
        full_url = GOOGLE_API_URL.format(query)
        for attempt in range(retries):
            try:
                response = requests.get(full_url, timeout=5)
                if response.status_code == 200:
                    items = response.json().get('items')
                    if items:
                        volume_info = items[0].get('volumeInfo', {})
                        image_url = volume_info.get('imageLinks', {}).get('thumbnail', '')
                        # Ensure image URL uses HTTPS
                        if image_url and image_url.startswith('http://'):
                            image_url = image_url.replace('http://', 'https://')
                        return {
                            'title': volume_info.get('title', title),
                            'author': ', '.join(volume_info.get('authors', ['Unknown'])),
                            'image_url': image_url,
                            'description': volume_info.get('description', 'No description available.'),
                            'publisher': volume_info.get('publisher', 'Unknown')
                        }
                else:
                    st.warning(f"API Error: {response.status_code}")
            except Exception as e:
                if attempt < retries - 1:
                    time.sleep(delay)
                else:
                    st.error(f"API failed after {retries} attempts. Error: {e}")
        return {
            'title': title,
            'author': 'Unknown',
            'image_url': '',
            'description': 'No description available.',
            'publisher': 'Unknown'
        }

    @st.cache_data(show_spinner=False)
    def get_book_info_cached(title):
        return get_book_info_from_google(title)

    # --------------------------- MAIN UI ---------------------------
    # Updated tabs list to include new tabs
    tabs = st.tabs([
        "Discover Books",
        "Top 50 Books",
        "Search Books (Live)",
        "📚 Book Quiz / Genre Discovery",
        "🎲 Surprise Me",
        "❤️ My Favorites",  # New Tab
        "ℹ️ About This App"  # New Tab
    ])

    # --------------------------- SIDEBAR HISTORY ---------------------------
    with st.sidebar:
        st.markdown("## 👤 User Profile")
        st.image("https://cdn-icons-png.flaticon.com/512/149/149071.png", width=80)  # Default avatar
        st.write(f"Welcome, {st.session_state.username}! 👋")
        st.markdown("---")
        st.subheader("📖 Your Recent History")
        history = get_history(st.session_state.username)
        if history:
            for book in history[:10]:
                st.markdown(f"- {book}")
        else:
            st.caption("No history yet. Start exploring! 🚀")

        st.markdown("---")
        # Clear History Button
        if st.button("🗑️ Clear History"):
            clear_history(st.session_state.username)
            st.success("Your history has been cleared!")
            st.rerun()  # Refresh the sidebar history display

        st.markdown("---")
        if st.button("🚪 Logout"):
            st.session_state.logged_in = False
            st.session_state.username = None
            st.session_state.show_welcome = False
            st.session_state.show_main_app = False  # Reset main app visibility
            st.rerun()

    # --------------------------- TAB 1: DISCOVER BOOKS ---------------------------
    with tabs[0]:
        st.header('🔍 Discover Books A New World! 🌍')

        book_list = pt.index.tolist()
        selected_book = st.selectbox("Type or select a book from the dropdown", book_list)

        if st.button("Show Recommendation ✨"):
            index = book_list.index(selected_book)
            distances = sorted(list(enumerate(similarity_scores[index])), reverse=True, key=lambda x: x[1])
            recommended_books = []
            for i in distances[1:7]:
                title = pt.index[i[0]]
                info = get_book_info_cached(title)
                recommended_books.append(info)
            st.session_state.recommended_books = recommended_books
            st.session_state.details_index = None
            add_to_history(st.session_state.username, selected_book)

        if 'recommended_books' in st.session_state:
            cols = st.columns(6)
            for i, book in enumerate(st.session_state.recommended_books):
                with cols[i]:
                    st.subheader(book['title'])  # Changed to subheader for better prominence
                    if book['image_url']:
                        st.image(book['image_url'])
                    if st.button("More Details", key=f"details_btn_{i}"):
                        st.session_state.details_index = i

        if 'details_index' in st.session_state and st.session_state.details_index is not None:
            book = st.session_state.recommended_books[st.session_state.details_index]
            st.markdown("---")
            st.subheader(f"📘 {book['title']}")
            if book['image_url']:
                st.image(book['image_url'])
            st.write(f"Author: {book['author']}")  # Bolded for clarity
            st.write(f"Publisher: {book['publisher']}")  # Bolded for clarity
            st.write(f"Description: {book['description']}")  # Bolded for clarity

            # Add to Favorites button for Discover tab details
            if st.button(f"Add to Favorites ❤️", key=f"add_fav_discover_{st.session_state.details_index}"):
                if st.session_state.username not in st.session_state.user_favorites:
                    st.session_state.user_favorites[st.session_state.username] = []

                # Check for duplicates before adding
                if book['title'] not in [fav['title'] for fav in
                                         st.session_state.user_favorites[st.session_state.username]]:
                    st.session_state.user_favorites[st.session_state.username].append(book)
                    st.success(f"'{book['title']}' added to your favorites! ✅")
                else:
                    st.info(f"'{book['title']}' is already in your favorites. ℹ️")

            st.subheader("✍️ Write a Review")
            review_text = st.text_area("Your review", height=100)
            if st.button("Submit Review", key=f"submit_review_{book['title']}"):
                if review_text:
                    if add_review(st.session_state.username, book['title'], review_text):
                        st.success("Review submitted successfully! 👍")
                    else:
                        st.error("Failed to submit review.")
                else:
                    st.warning("Please write your review before submitting.")

            st.subheader("💬 User Reviews")
            reviews = get_reviews(book['title'])
            if reviews:
                for user, review, timestamp in reviews:
                    st.markdown(f"{user} on {timestamp.split()[0]}:")
                    st.write(review)
                    st.markdown("---")
            else:
                st.info("No reviews yet for this book. Be the first to write one!")

    # --------------------------- TAB 2: TOP 50 BOOKS ---------------------------
    with tabs[1]:
        st.header("🌟 Top 50 Popular Books")
        top_books = popular_df.head(50)
        for i in range(0, 50, 5):
            cols = st.columns(5)
            for j in range(5):
                idx = i + j
                if idx < len(top_books):
                    title = top_books.iloc[idx]['Book-Title']
                    info = get_book_info_cached(title)  # Ensure this is cached
                    with cols[j]:
                        st.subheader(info['title'])  # Changed to subheader
                        if info['image_url']:
                            st.image(info['image_url'])


# --------------------------- TAB 3: SEARCH BOOKS (LIVE) ---------------------------
with tabs[2]:
    st.header("🔎 Search Books from Google")
    query = st.text_input("Enter a book title, author, or keyword")

    if st.button("Search"):
        if query:
            with st.spinner("Searching Google Books..."):  # Added spinner
                response = requests.get(GOOGLE_API_URL.format(quote(query)), timeout=5)
                data = response.json()
            if "items" in data:
                for i, item in enumerate(data["items"][:6]):  # Limiting to 6 for display
                    volume_info = item.get("volumeInfo", {})
                    title = volume_info.get("title", "No Title")
                    authors = ", ".join(volume_info.get("authors", []))
                    description = volume_info.get("description", "No description")
                    rating = volume_info.get("averageRating", "N/A")
                    ratings_count = volume_info.get("ratingsCount", "N/A")
                    page_count = volume_info.get("pageCount", "N/A")
                    thumbnail = volume_info.get("imageLinks", {}).get("thumbnail", "")
                    preview_link = volume_info.get("previewLink", "")

                    col1, col2 = st.columns([1, 3])
                    with col1:
                        if thumbnail:
                            st.image(thumbnail)
                    with col2:
                        st.subheader(title)
                        st.caption(f"By {authors}")
                        st.write(description[:300] + "...")
                        st.write(f"⭐ Rating: {rating} ({ratings_count} ratings)")
                        st.write(f"📄 Pages: {page_count}")
                        if preview_link:
                            st.markdown(f"[🔗 Preview Book]({preview_link})", unsafe_allow_html=True)

                        search_book_info = {  # Prepare info for favorites
                            'title': title,
                            'author': authors,
                            'image_url': thumbnail,
                            'description': description,
                            'publisher': volume_info.get('publisher', 'Unknown')  # Add publisher if available
                        }

            else:
                st.info("No books found for your search term.")
        else:
            st.warning("Please enter a search term.")

# --------------------------- TAB 4: BOOK QUIZ ---------------------------
with tabs[3]:
    st.header("📚 Book Quiz / Genre Discovery")

    questions = [
        ("thrillers", "Do you enjoy fast-paced thrillers with suspense?"),
        ("historical", "Are you fascinated by historical events or eras?"),
        ("fantasy", "Do you like magical worlds or epic adventures?"),
        ("romance", "Are romantic storylines appealing to you?"),
        ("nonfiction", "Do you prefer real stories or learning new things?")
    ]

    if "quiz_index" not in st.session_state:
        st.session_state.quiz_index = 0
        st.session_state.quiz_answers = {}

    if st.session_state.quiz_index < len(questions):
        key, question = questions[st.session_state.quiz_index]
        st.subheader(f"Q{st.session_state.quiz_index + 1}: {question}")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Yes"):
                st.session_state.quiz_answers[key] = "Yes"
                st.session_state.quiz_index += 1
                st.rerun()
        with col2:
            if st.button("No"):
                st.session_state.quiz_answers[key] = "No"
                st.session_state.quiz_index += 1
                st.rerun()
    else:
        st.subheader("🎯 Your Book Recommendations")
        genres = {
            "thrillers": "thriller",
            "historical": "historical fiction",
            "fantasy": "fantasy",
            "romance": "romance",
            "nonfiction": "non-fiction"
        }

        selected_genres = [genres[k] for k, v in st.session_state.quiz_answers.items() if v == "Yes"]

        if selected_genres:
            for genre in selected_genres:
                st.markdown(f"---\n### 📚 Books for {genre.title()}")
                with st.spinner(f"Finding {genre} books..."):  # Added spinner
                    response = requests.get(GOOGLE_API_URL.format(quote(genre)), timeout=5)
                    data = response.json()
                if "items" in data:
                    for i, item in enumerate(data["items"][:3]):
                        volume_info = item.get("volumeInfo", {})
                        title = volume_info.get("title", "No Title")
                        authors = ", ".join(volume_info.get("authors", []))
                        thumbnail = volume_info.get("imageLinks", {}).get("thumbnail", "")
                        description = volume_info.get("description", "No description")
                        preview_link = volume_info.get("previewLink", "")

                        with st.container(border=True):  # Added container with border
                            st.subheader(title)
                            st.caption(f"By {authors}")
                            if thumbnail:
                                st.image(thumbnail, width=120)
                            st.write(description[:300] + "...")
                            if preview_link:
                                st.markdown(f"[🔗 Preview Book Here]({preview_link})", unsafe_allow_html=True)

                            quiz_book_info = {  # Prepare info for favorites
                                'title': title,
                                'author': authors,
                                'image_url': thumbnail,
                                'description': description,
                                'publisher': volume_info.get('publisher', 'Unknown')
                            }
                            if st.button(f"Add to Favorites ❤️", key=f"add_fav_quiz_{genre}_{i}"):
                                if st.session_state.username not in st.session_state.user_favorites:
                                    st.session_state.user_favorites[st.session_state.username] = []
                                if quiz_book_info['title'] not in [fav['title'] for fav in
                                                                   st.session_state.user_favorites[
                                                                       st.session_state.username]]:
                                    st.session_state.user_favorites[st.session_state.username].append(quiz_book_info)
                                    st.success(f"'{quiz_book_info['title']}' added to your favorites! ✅")
                                else:
                                    st.info(f"'{quiz_book_info['title']}' is already in your favorites. ℹ️")

                else:
                    st.info(f"No books found for genre: {genre}")
        else:
            st.warning("You didn’t say Yes to any genre. Please try again!")

        if st.button("🔄 Restart Quiz"):
            st.session_state.quiz_index = 0
            st.session_state.quiz_answers = {}
            st.rerun()

# --------------------------- TAB 5: SURPRISE ME ---------------------------
with tabs[4]:
    st.title("🎲 Surprise Me with a Book")

    # Function to fetch a random book using Google Books API
    def get_random_book():
        keywords = ["adventure", "mystery", "inspiration", "science", "life", "technology"]
        query = random.choice(keywords)
        url = f"https://www.googleapis.com/books/v1/volumes?q={query}"
        response = requests.get(url)
        data = response.json()
        if "items" in data:
            item = random.choice(data["items"])
            volume_info = item.get("volumeInfo", {})
            return {
                "title": volume_info.get("title", "No Title"),
                "authors": ", ".join(volume_info.get("authors", [])),
                "description": volume_info.get("description", "No description"),
                "thumbnail": volume_info.get("imageLinks", {}).get("thumbnail", ""),
                "preview_link": volume_info.get("previewLink", "")
            }
        return None

    motivational_quotes = [
        "✨ Believe in yourself and all that you are.",
        "🚀 The future depends on what you do today.",
        "🌟 Push yourself, because no one else is going to do it for you.",
        "🔥 Great things never come from comfort zones.",
        "💡 Don’t watch the clock; do what it does. Keep going!"
    ]

    # Initialize session state
    if "stage" not in st.session_state:
        st.session_state.stage = "ready"  # stages: ready -> spinning -> cracker -> motivation

    if st.session_state.stage == "ready":
        if st.button("🎡 Spin the Wheel!"):
            st.session_state.stage = "spinning"
            st.rerun()

    elif st.session_state.stage == "spinning":
        wheel_html = """
         <style>
         @keyframes spin {
             from { transform: rotate(0deg); }
             to { transform: rotate(1440deg); }
         }
         #wheel {
             margin: auto;
             width: 300px;
             height: 300px;
             border-radius: 50%;
             border: 8px solid #4CAF50;
             background: conic-gradient(
               #FFCDD2 0deg 30deg,
               #F8BBD0 30deg 60deg,
               #E1BEE7 60deg 90deg,
               #D1C4E9 90deg 120deg,
               #C5CAE9 120deg 150deg,
               #BBDEFB 150deg 180deg,
               #B3E5FC 180deg 210deg,
               #B2EBF2 210deg 240deg,
               #B2DFDB 240deg 270deg,
               #C8E6C9 270deg 300deg,
               #DCEDC8 300deg 330deg,
               #F0F4C3 330deg 360deg
             );
             animation: spin 4s cubic-bezier(0.33, 1, 0.68, 1) forwards;
             position: relative;
         }
         #pointer {
             position: relative;
             margin: 20px auto;
             width: 0; 
             height: 0; 
             border-left: 20px solid transparent;
             border-right: 20px solid transparent;
             border-bottom: 30px solid #FF5722;
         }
         </style>
         <div id="pointer"></div>
         <div id="wheel"></div>
         """
        st.markdown(wheel_html, unsafe_allow_html=True)
        st.write("Spinning... Please wait.")
        time.sleep(4.2)
        st.session_state.stage = "cracker"
        st.rerun()

    elif st.session_state.stage == "cracker":
        cracker_html = """
         <div style="text-align:center; margin-top: 50px;">
           <h1 style="font-size: 80px; color: #FF5722; animation: pop 1s ease-in-out 5;">
             🎉🎆✨💥🔥🎇
           </h1>
         </div>
         <style>
         @keyframes pop {
           0%, 100% { transform: scale(1); opacity: 1; }
           50% { transform: scale(1.3); opacity: 0.6; }
         }
         h1 {
           animation: pop 1s ease-in-out infinite alternate;
         }
         </style>
         """
        st.markdown(cracker_html, unsafe_allow_html=True)
        time.sleep(3)
        st.session_state.stage = "motivation"
        st.rerun()

    elif st.session_state.stage == "motivation":
        motivation = random.choice(motivational_quotes)
        st.markdown(
            f"<h1 style='text-align: center; color: #FF6F61; font-weight:bold; font-family: Verdana;'>{motivation}</h1>",
            unsafe_allow_html=True)

        book = get_random_book()
        if book:
            st.markdown("---")
            st.markdown(f"### 📚 {book['title']}")
            if book['authors']:
                st.markdown(f"Author(s): {book['authors']}")
            if book['thumbnail']:
                st.image(book['thumbnail'], width=150)
            if book['description']:
                st.write(book['description'][:300] + "...")
            if book['preview_link']:
                st.markdown(f"[Preview Book Here]({book['preview_link']})")
        else:
            st.write("No book found, try spinning again!")

        if st.button("Spin Again 🔄"):
            st.session_state.stage = "ready"
            st.rerun()
# --------------------------- NEW TAB: MY FAVORITES ---------------------------
with tabs[5]:  # This assumes it's the 6th tab (index 5)
    st.header("❤️ My Favorite Books")

    current_user_favorites = st.session_state.user_favorites.get(st.session_state.username, [])

    if current_user_favorites:
        st.write(f"You have {len(current_user_favorites)} favorite books saved:")
        for i in range(0, len(current_user_favorites), 3):  # Display 3 books per row
            cols = st.columns(3)
            for j in range(3):
                idx = i + j
                if idx < len(current_user_favorites):
                    book = current_user_favorites[idx]
                    with cols[j]:
                        with st.container(border=True):  # Adds a visual border to each book card
                            st.subheader(book.get('title', 'Unknown Title'))
                            st.caption(f"By {book.get('author', 'Unknown Author')}")
                            if book.get('image_url'):
                                st.image(book['image_url'], use_container_width=True)

                            # Provide a way to view full details if desired
                            with st.expander("Show Details"):
                                st.write(f"Publisher: {book.get('publisher', 'Unknown Publisher')}")
                                st.write(book.get('description', 'No description available.'))

                            if st.button(f"Remove from Favorites 🗑️", key=f"remove_fav_{book.get('title')}_{idx}"):
                                # Remove by title to avoid issues if order changes, assuming unique titles
                                st.session_state.user_favorites[st.session_state.username] = \
                                    [fav for fav in current_user_favorites if fav['title'] != book['title']]
                                st.success(f"'{book.get('title', 'Book')}' removed from your favorites. 🗑️")
                                st.rerun()
                else:
                    break  # No more books in this row
    else:
        st.info("You haven't added any books to your favorites yet. Click the ❤️ button on books you like!")

# --------------------------- NEW TAB: ABOUT THIS APP ---------------------------
with tabs[6]:  # This assumes it's the 7th tab (index 6)
    st.header("ℹ️ About Book Recommender")
    st.write("This application is designed to help book lovers discover new reads through various methods:")
    st.markdown("""
    -   Discover Books: Get personalized recommendations based on pre-trained similarity.
    -   Top 50 Books: Explore a curated list of the most popular titles.
    -   Search Books (Live): Find any book available in Google's vast catalog using keywords, titles, or authors.
    -   Book Quiz / Genre Discovery: Receive tailored suggestions by answering a few simple questions about your genre preferences.
    -   Surprise Me: Get a fun, random book idea when you're feeling adventurous!
    """)
    st.subheader("Data & Technology")
    st.write(
        "The app utilizes the Google Books API for live searches and detailed book information. Book recommendations are powered by a machine learning model trained on a comprehensive dataset to calculate book similarities.")
    st.write(
        "This application is built with Streamlit and Python, demonstrating a simple and interactive way to explore books.")
    st.caption("© 2025 Book Recommender. All rights reserved.")