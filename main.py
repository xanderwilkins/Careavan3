from nicegui import ui, app, events
from starlette.requests import Request
from starlette.responses import RedirectResponse
from starlette.staticfiles import StaticFiles

from datetime import datetime, timezone, timedelta
from PIL import Image
from uuid import uuid4
import bcrypt
import base64
import sqlite3
import json
import io

SESSION_COOKIE = 'careavan_session'
DATABASE_PATH = 'careavan.db'

#oLOCATIONS = {
#    "3425 Bee Caves Rd, Austin, TX 78746": "Master Martial Arts at Westlake Hills",
#    "8100 Bee Caves Rd, Austin, TX 78746": "Jett Garner Martial Arts",
#    "5446 W US Hwy 290 Service Rd #108, Austin, TX 78735": "Elite Martial Arts"
#}
#
#wsLOCATIONS = {
#    "3425 Bee Caves Rd, Austin, TX 78746": {
#        "name": "Master Martial Arts at Westlake Hills",
#        "categories": ["sports", "yoga"]
#    },
#    "8100 Bee Caves Rd, Austin, TX 78746": {
#        "name": "Jett Garner Martial Arts",
#        "categories": ["sports", "yoga"]
#    },
#    "5446 W US Hwy 290 Service Rd #108, Austin, TX 78735": {
#        "name": "Elite Martial Arts",
#        "categories": ["sports", "yoga"]
#    }
#}

TRAITS = ['Sports', 'Music', 'Art', 'Reading', 'Writing', 'Cooking', 'Gardening', 'Hiking', 'Camping', 'Fishing', 'Swimming', 'Biking', 'Walking', 'Yoga', 'Meditation', 'Reading', 'Writing', 'Cooking', 'Gardening', 'Hiking', 'Camping', 'Fishing', 'Swimming', 'Biking', 'Walking', 'Yoga', 'Meditation']

LOCATIONS = {
    "3425 Bee Caves Rd, Austin, TX 78746": [
        "Master Martial Arts at Westlake Hills",
        "https://images1.loopnet.com/i2/k4skNKBK8J7L6A2siQe2NtnzEVW1bvWJ9a2c0oz0tBs/110/3425-Bee-Caves-Rd-Austin-TX-Primary-Photo-1-Large.jpg",
        ["art", "yoga"]
    ],
    "8100 Bee Caves Rd, Austin, TX 78746": [
        "Jett Garner Martial Arts",
        "https://images1.loopnet.com/i2/UnyKlXTX1J0H39VPzVc43otIsTWTFAbyp1qptSDS5sQ/112/image.jpg",
        ["sports", "yoga"]
    ],
    "5446 W US Hwy 290 Service Rd #108, Austin, TX 78735": [
        "Elite Martial Arts",
        "https://images1.loopnet.com/i2/Mj07MUVsMaTeAVEa_7lUW4o7DrpY93llKa_5XYjPkyk/116/5446-W-Highway-290-W-Austin-TX-Primary-Photo-1-LargeHighDefinition.jpg",
        ["sports", "yoga"]
    ]
}


with sqlite3.connect(DATABASE_PATH) as con:
    cur = con.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            family_id TEXT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            points INTEGER DEFAULT 0,
            established_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,      -- Unique ID for this specific session
            user_id TEXT NOT NULL,          -- The UUID of the user this session belongs to
            expires_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS families (
            family_id TEXT PRIMARY KEY,
            admin_user_id TEXT NOT NULL,
            adult_ids TEXT NOT NULL,
            trip_ids TEXT NOT NULL,
            traits TEXT NOT NULL -- JSON list of traits for the family
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS trips (
            trip_id TEXT PRIMARY KEY,
            admin_family_id TEXT NOT NULL,
            family_ids TEXT NOT NULL,
            status BOOLEAN NOT NULL,
            visibility TEXT NOT NULL CHECK (visibility IN ('public', 'private')),
            location TEXT NOT NULL, -- Current location of the trip
            destination TEXT NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL
        )
    ''')

    con.commit()

#def _app_footer():
#    with ui.footer(elevated=True).classes('bg-indigo-700 print-hide p-2'):
#        with ui.row().classes('mx-auto items-center justify-center gap-x-3'):
#            ui.button('', icon='explore', on_click=lambda: ui.navigate.to('/explore')).props('flat text-color="white"')
#            ui.button('', icon='list', on_click=lambda: ui.navigate.to('/trips')).props('flat text-color="white"')
#            ui.button('', icon='diversity_1', on_click=lambda: ui.navigate.to('/family')).props('flat text-color="white"')
#            ui.button('', icon='settings', on_click=lambda: ui.navigate.to('/settings')).props('flat text-color="white"')

#def _app_footer():
#    with ui.footer(elevated=True).classes('bg-indigo-700 print-hide p-2'):
#        with ui.row().classes('mx-auto items-center justify-center gap-x-6'):
#            with ui.column().classes('items-center'):
#                ui.button('', icon='explore', on_click=lambda: ui.navigate.to('/explore')).props('flat text-color="white"')
#                ui.label('Explore').classes('text-white text-xs')
#            with ui.column().classes('items-center'):
#                ui.button('', icon='list', on_click=lambda: ui.navigate.to('/trips')).props('flat text-color="white"')
#                ui.label('Trips').classes('text-white text-xs')
#            with ui.column().classes('items-center'):
#                ui.button('', icon='diversity_1', on_click=lambda: ui.navigate.to('/family')).props('flat text-color="white"')
#                ui.label('Family').classes('text-white text-xs')
#            with ui.column().classes('items-center'):
#                ui.button('', icon='settings', on_click=lambda: ui.navigate.to('/settings')).props('flat text-color="white"')
#                ui.label('Settings').classes('text-white text-xs')

def _app_footer():
    with ui.footer(elevated=True).classes('bg-indigo-700 print-hide p-2'):
        with ui.row().classes('mx-auto items-center justify-center gap-x-2'):
            with ui.column().classes('items-center gap-y-1'):
                ui.button('', icon='search', on_click=lambda: ui.navigate.to('/discover')).props('flat text-color="white"')
                ui.label('Discover').classes('text-white text-xs m-0 p-0')
            with ui.column().classes('items-center gap-y-1'):
                ui.button('', icon='list', on_click=lambda: ui.navigate.to('/trips')).props('flat text-color="white"')
                ui.label('My Trips').classes('text-white text-xs m-0 p-0')
            with ui.column().classes('items-center gap-y-1'):
                ui.button('', icon='diversity_1', on_click=lambda: ui.navigate.to('/family')).props('flat text-color="white"')
                ui.label('My Family').classes('text-white text-xs m-0 p-0')
            with ui.column().classes('items-center gap-y-1'):
                ui.button('', icon='person', on_click=lambda: ui.navigate.to('/settings')).props('flat text-color="white"')
                ui.label('Me').classes('text-white text-xs m-0 p-0')


@app.get('/_create_session')
async def create_session(request: Request):
    user_id = request.query_params.get('user_id')
    session_id = str(uuid4())

    response = RedirectResponse(url='/trips', status_code=302)
    response.set_cookie(SESSION_COOKIE, session_id, secure=True, httponly=True, path='/', max_age=86400)

    with sqlite3.connect(DATABASE_PATH) as con:
        cur = con.cursor()
        expires_at = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        cur.execute('INSERT INTO sessions (session_id, user_id, expires_at) VALUES (?, ?, ?)',
                    (session_id, user_id, expires_at))
        con.commit()
    return response

@app.get('/_delete_session')
async def delete_session(request: Request):
    session_id = request.cookies.get(SESSION_COOKIE)

    response = RedirectResponse(url='/login', status_code=302)
    response.delete_cookie(SESSION_COOKIE, path='/')

    with sqlite3.connect(DATABASE_PATH) as con:
        cur = con.cursor()
        cur.execute('DELETE FROM sessions WHERE session_id=?', (session_id,))
        con.commit()
    return response

async def verify_session(session_id: str) -> bool:
    if not session_id:
        return False
    
    with sqlite3.connect(DATABASE_PATH) as con:
        cur = con.cursor()
        cur.execute('SELECT expires_at FROM sessions WHERE session_id=?', (session_id,))
        row = cur.fetchone()

        if not row or not row[0]:
            return False
        try:
            expires_at = datetime.fromisoformat(row[0])
        except Exception:
            return False
        return expires_at > datetime.now(timezone.utc)

async def retrieve_user_id_from_session_id(session_id: str) -> str:
    with sqlite3.connect(DATABASE_PATH) as con:
        cur = con.cursor()
        cur.execute('SELECT user_id FROM sessions WHERE session_id=?', (session_id,))
        result = cur.fetchone()

        return result[0] if result else None

@ui.page('/')
async def main_page(request: Request):
    ui.navigate.to('/trips')

@ui.page('/register')
async def register_page(request: Request):
    session_id = request.cookies.get(SESSION_COOKIE)

    if await verify_session(session_id) != False:
        ui.label('There\'s no need to register. You are already logged in.').classes('text-2xl font-bold mb-6 text-center text-primary')
        ui.button('Go to trips', on_click=lambda: ui.navigate.to('/trips')).classes('w-full')
        return
    
    ui.label('Register').classes('text-2xl font-bold mb-6 text-center text-indigo')

    email_input = ui.input('Email').props('type=email outlined clearable').classes('w-full mb-3')
    password_input = ui.input('Password', password=True, password_toggle_button=True).props('outlined clearable').classes('w-full mb-3')
    first_name_input = ui.input('First Name').props('outlined clearable').classes('w-full mb-3')
    last_name_input = ui.input('Last Name').props('outlined clearable').classes('w-full mb-3')
    #role_input = ui.select(['Parent', 'Child'], label='Role').props('outlined').classes('w-full mb-6')

    async def on_register_click():
        if not all([f.value for f in [email_input, password_input, first_name_input, last_name_input]]):
            ui.notification('All fields are required.', color='green')
            return
        
        if len(password_input.value) < 6:
            ui.notification('Password must be at least 6 characters.', color='green')
            return
        
        with sqlite3.connect(DATABASE_PATH) as con:
            cur = con.cursor()
            ui.notification('Working on it...', color='green')

            cur.execute('SELECT 1 FROM users WHERE email=?', (email_input.value,))
            if cur.fetchone():
                ui.notification('Email already exists.', color='green')
                return
            user_id = str(uuid4())
            now_iso = datetime.now(timezone.utc).isoformat()
            
            cur.execute('''INSERT INTO users (user_id, family_id, email, password, first_name, last_name, points, established_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                        (user_id, '', email_input.value, bcrypt.hashpw(password_input.value.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'), first_name_input.value, last_name_input.value, 0, now_iso))
            con.commit()
            ui.notification('Registration successful! Creating session...', color='green')

            ui.navigate.to('/_create_session?user_id=' + user_id)
    
    ui.button('Register', on_click=on_register_click, color='indigo').classes('w-full')
    ui.button('Already have an account? Login', on_click=lambda: ui.navigate.to('/login'), color='indigo').props('flat dense').classes('w-full')

@ui.page('/login')
async def login_page(request: Request):
    session_id = request.cookies.get(SESSION_COOKIE)

    if await verify_session(session_id) != False:
        ui.label('There\'s no need to login. You are already logged in.').classes('text-2xl font-bold mb-6 text-center text-primary')
        ui.button('Go to trips', on_click=lambda: ui.navigate.to('/trips')).classes('w-full')
        return
    
    ui.label('Login').classes('text-2xl font-bold mb-6 text-center text-indigo')

    email_input = ui.input('Email').props('type=email outlined clearable').classes('w-full mb-3')
    password_input = ui.input('Password', password=True, password_toggle_button=True).props('outlined clearable').classes('w-full mb-3')

    async def on_login_click():
        if not all([f.value for f in [email_input, password_input]]):
            ui.notification('All fields are required.', color='red')
            return
        
        with sqlite3.connect(DATABASE_PATH) as con:
            cur = con.cursor()

            ui.notification('Working on it.', color='green')

            cur.execute('SELECT user_id, password FROM users WHERE email=?', (email_input.value,))
            user = cur.fetchone()

            if user and bcrypt.checkpw(password_input.value.encode('utf-8'), user[1].encode('utf-8')):
                user_id = user[0]
                ui.navigate.to('/_create_session?user_id=' + user_id)

                ui.notification('Logged in successfully.', color='green')
            else:
                ui.notification('Invalid email or password.', color='red')
    
    ui.button('Login', on_click=on_login_click, color='indigo').classes('w-full')
    ui.button('Don\'t have an account? Register', on_click=lambda: ui.navigate.to('/register')).props('flat dense').classes('w-full mt-3 text-indigo')

#@ui.page('/discover')
#async def discover_page(request: Request):
#    _app_footer()
#
#    session_id = request.cookies.get(SESSION_COOKIE)
#    
#    if not await verify_session(session_id):
#        ui.label('You need to login first.').classes('text-2xl font-bold mb-6 text-center text-indigo')
#        ui.button('Login', on_click=lambda: ui.navigate.to('/login')).classes('w-full')
#        return
#    
#    user_id = await retrieve_user_id_from_session_id(session_id)
#
#    with sqlite3.connect(DATABASE_PATH) as con:
#        cur = con.cursor()
#        cur.execute('SELECT family_id FROM users WHERE user_id=?', (user_id,))
#        family_id = cur.fetchone()
#        if family_id and family_id[0]:
#            family_id = family_id[0]
#        else:
#            ui.label('You are not in a family.').classes('text-2xl font-bold mb-6 text-center text-indigo')
#            return
#    ui.label('Trips').classes('text-2xl font-bold mb-6 text-center text-indigo')
#    ui.label('Public trips for Westlake Highschool.')
#    selected_traits = ui.select(TRAITS, multiple=True, value=TRAITS[:2], label='Traits') \
#        .classes('w-full').props('use-chips')
#    selected_traits = [trait.lower() for trait in selected_traits]
#    #with ui.card().tight():
#    #    ui.image('https://picsum.photos/id/684/640/360')
#    #    with ui.card_section():
#    #        ui.label('Lorem ipsum dolor sit amet, consectetur adipiscing elit, ...')
#    #        ui.label('Trips under this location: 3').classes('w-full text-indigo')
#    #        ui.button('View Location', color='indigo').classes('w-full')
#    
#    #with ui.list().props('dense separator').classes('w-full'):
#    #    for address, name in LOCATIONS.items():
#    #        ui.item(f"Name: {name}  Address: {address}")#.classes('w-full')
#    #with ui.list().props('dense separator').classes('w-full'):
#    for address, (name, image, categories) in LOCATIONS.items():
#        if not selected_traits or any(trait in categories for trait in selected_traits):
#            #ui.item(f"Name: {name}  Address: {address}")
#            with ui.card().tight():
#                ui.image('https://picsum.photos/id/684/640/360')
#                with ui.card_section():
#                    ui.label('Lorem ipsum dolor sit amet, consectetur adipiscing elit, ...')
#                    ui.label('Trips under this location: 3').classes('w-full text-indigo')
#                    ui.button('View Location', color='indigo').classes('w-full')
#                    #ui.item(f"Name: {name}  Address: {address}  Categories: {', '.join(categories)}")
#                    #print(f"{name} ({address}) - Categories: {', '.join(categories)}")
#                    ui.item(f"Name: {name}")
#                    ui.item(f"Address: {address}")
#                    ui.item(f"Categories: {', '.join(categories)}")
#@ui.page('/discover')
#async def discover_page(request: Request):
#    _app_footer()
#
#    session_id = request.cookies.get(SESSION_COOKIE)
#    
#    if not await verify_session(session_id):
#        ui.label('You need to login first.').classes('text-2xl font-bold mb-6 text-center text-indigo')
#        ui.button('Login', on_click=lambda: ui.navigate.to('/login')).classes('w-full')
#        return
#    
#    # Session is valid, continue with page content
#    ui.label('Discover Trips').classes('text-2xl font-bold mb-6 text-center text-indigo')
#    ui.label('Find public trips and locations based on your family\'s interests.')
#
#    # This function will clear and rebuild the list of location cards.
#    def update_location_list():
#        # Step 1: Clear all existing cards from the container.
#        location_container.clear()
#
#        # Get the currently selected traits and normalize to lowercase.
#        selected_traits = [trait.lower() for trait in trait_selector.value or []]
#        
#        locations_found = 0
#
#        # Step 2: Re-populate the container with the filtered cards.
#        with location_container:
#            # Loop through all locations
#            for address, (name, image, categories) in LOCATIONS.items():
#                # The filtering logic remains the same:
#                # Show if NO traits are selected OR if ANY selected trait matches.
#                if not selected_traits or any(trait in categories for trait in selected_traits):
#                    locations_found += 1
#                    with ui.card().tight().classes('w-full'):
#                        ui.image('https://picsum.photos/id/684/640/360') # Placeholder image
#                        with ui.card_section():
#                            ui.label(name).classes('text-lg font-bold')
#                            ui.label(address).classes('text-sm text-gray-600')
#                            
#                            with ui.row().classes('mt-2'):
#                                for category in categories:
#                                    ui.chip(category.capitalize(), color='indigo', text_color='white').props('dense size=sm')
#
#                            ui.label('Trips at this location: 3').classes('w-full text-indigo pt-2') # Placeholder
#                            ui.button('View Location', color='indigo').classes('w-full mt-2')
#            
#            if locations_found == 0:
#                ui.label('No locations match your selected traits.').classes('text-center text-gray-500 p-4')
#
#    # --- UI Element Definitions ---
#
#    # Define the selector. When it changes, it will call our update function.
#    trait_selector = ui.select(
#        TRAITS, 
#        multiple=True, 
#        value=[], 
#        label='Filter by Traits',
#        on_change=update_location_list  # This is the crucial link
#    ).classes('w-full').props('use-chips clearable')
#
#    # Define a persistent container that we will clear and refill.
#    location_container = ui.column().classes('w-full gap-4 pt-4')
#
#    # --- Initial Page Load ---
#
#    # Call the function once to populate the list when the page is first loaded.
#    update_location_list()
@ui.page('/discover')
async def discover_page(request: Request):
    _app_footer()

    session_id = request.cookies.get(SESSION_COOKIE)
    
    if not await verify_session(session_id):
        ui.label('You need to login first.').classes('text-2xl font-bold mb-6 text-center text-indigo')
        ui.button('Login', on_click=lambda: ui.navigate.to('/login'), color='indigo').classes('w-full')
        ui.button('Don\'t have an account? Register', on_click=lambda: ui.navigate.to('/register')).props('flat dense').classes('w-full mt-3 text-indigo')
        return
    
    # --- NEW: Fetch Family Traits for Default Selection ---
    default_traits = []  # Start with an empty list as a safe default
    user_id = await retrieve_user_id_from_session_id(session_id)

    with sqlite3.connect(DATABASE_PATH) as con:
        cur = con.cursor()
        # First, get the family_id for the current user
        cur.execute('SELECT family_id FROM users WHERE user_id=?', (user_id,))
        family_id_row = cur.fetchone()

        # If the user is in a family, get that family's common traits
        if family_id_row and family_id_row[0]:
            family_id = family_id_row[0]
            cur.execute('SELECT traits FROM families WHERE family_id=?', (family_id,))
            traits_row = cur.fetchone()

            # The traits are stored as a JSON string, so we need to load them
            if traits_row and traits_row[0]:
                try:
                    default_traits = json.loads(traits_row[0])
                except json.JSONDecodeError:
                    print(f"Warning: Could not decode traits for family {family_id}")
                    default_traits = [] # Fallback to empty if JSON is invalid

    # Session is valid, continue with page content
    ui.label('Discover Trips').classes('text-2xl font-bold mb-6 text-center text-indigo')
    ui.label('Find public trips and locations. We\'ve pre-selected your family\'s common traits!')

    # This function will clear and rebuild the list of location cards.
    def update_location_list():
        location_container.clear()
        selected_traits = [trait.lower() for trait in trait_selector.value or []]
        locations_found = 0

        with location_container:
            for address, (name, image, categories) in LOCATIONS.items():
                if not selected_traits or any(trait in categories for trait in selected_traits):
                    locations_found += 1
                    with ui.card().tight().classes('w-full max-w-xl mx-auto'):
                        #ui.image('https://picsum.photos/id/684/640/360')
                        ui.image(image)
                        with ui.card_section().classes('w-full'):
                            ui.label(name).classes('text-lg font-bold')
                            ui.label(address).classes('text-sm text-gray-600')
                            
                            with ui.row().classes('mt-2'):
                                for category in categories:
                                    ui.chip(category.capitalize(), color='indigo', text_color='white').props('dense size=sm')

                            #ui.label('Trips at this location: 3').classes('w-full text-indigo pt-2')
                            ui.button('View Destination', on_click=lambda current_address=address: ui.navigate.to('/discover/' + current_address), color='indigo').classes('w-full mt-2')
                            ui.button('Copy Destination Address', on_click=lambda current_address=address: ui.clipboard.write(current_address), color='indigo').classes('w-full mt-2')
            
            if locations_found == 0:
                ui.label('No locations match your selected traits.').classes('text-center text-gray-500 p-4')

    # --- UI Element Definitions ---

    # MODIFIED: The `value` parameter is now set to `default_traits`
    trait_selector = ui.select(
        TRAITS, 
        multiple=True, 
        value=default_traits,  # This pre-selects the traits from the database
        label='Filter by Traits',
        on_change=update_location_list
    ).classes('w-full').props('use-chips clearable')

    # This container will be cleared and refilled
    location_container = ui.column().classes('w-full gap-4 pt-4')

    # --- Initial Page Load ---

    # Call the function once to populate the list when the page is first loaded.
    # It will automatically use the pre-selected traits.
    update_location_list()

@ui.page('/discover/{item_path:path}')
async def trip_edit_page(request: Request, item_path: str):
    _app_footer()

    session_id = request.cookies.get(SESSION_COOKIE)

    if not await verify_session(session_id):
        ui.label('You need to login first.').classes('text-2xl font-bold mb-6 text-center text-indigo')
        ui.button('Login', on_click=lambda: ui.navigate.to('/login'), color='indigo').classes('w-full')
        ui.button('Don\'t have an account? Register', on_click=lambda: ui.navigate.to('/register')).props('flat dense').classes('w-full mt-3 text-indigo')
        return

    user_id = await retrieve_user_id_from_session_id(session_id)

    with ui.header(elevated=True).classes('bg-indigo'):
        with ui.row().classes('items-center w-full'):
            ui.button(
                icon='arrow_back',
                on_click=lambda: ui.run_javascript('history.back()')
            ).props('flat round color="white"').classes('mr-2')
            ui.label(f'Destination Address: {item_path}').classes('text-lg')
    ui.button('Copy Destination Address', on_click=lambda current_address=item_path: ui.clipboard.write(current_address), color='indigo').classes('w-full mt-2')
    with ui.list().props('bordered separator').classes('w-full mt-4 mx-0 px-0 rounded-lg'):
        ui.item_label('Public trips under this destination:').props('header').classes('text-bold')
        ui.separator()

        with sqlite3.connect(DATABASE_PATH) as con:
            cur = con.cursor()
            cur.execute("SELECT trip_id, admin_family_id, family_ids, status, visibility, location, destination, date, time FROM trips WHERE destination=? AND visibility='public'", (item_path,))
            #trip_ids = [row[0] for row in cur.fetchall()]

            rows = cur.fetchall()

            trip_ids = []
            admin_family_ids = []
            family_ids_list = []
            statuses = []
            visibilities = []
            locations = []
            destinations = []
            dates = []
            times = []

            for row in rows:
                trip_id, admin_family_id, family_ids, status, visibility, location, destination, date, time = row
                trip_ids.append(trip_id)
                admin_family_ids.append(admin_family_id)
                family_ids_list.append(family_ids)
                statuses.append(status)
                visibilities.append(visibility)
                locations.append(location)
                destinations.append(destination)
                dates.append(date)
                times.append(time)
                #with ui.item().classes('relative overflow-hidden max-h-40'):
                #    ui.label(str(trip_id))
                #    ui.button('Copy Trip ID', on_click=lambda current_id=trip_id: ui.clipboard.write(current_id), color='indigo')
                with sqlite3.connect(DATABASE_PATH) as con:
                    cur = con.cursor()
                    #cur.execute("SELECT last_name FROM users WHERE user_id=?", (admin_family_id,))
                    cur.execute("SELECT last_name FROM users WHERE user_id=(SELECT admin_user_id FROM families WHERE family_id=?)", (admin_family_id,))
                    admin_name = cur.fetchone()
                    if admin_name:
                        last_name = admin_name[0]
                    else:
                        admin_name = "Unknown"
                        last_name = "Unkown"
                with ui.item().classes('relative overflow-hidden max-h-40 flex justify-between items-center'):
                    ui.label(f"Public trip by the {last_name} family. • Starts at: {date} / {time}").classes('text-left')  # left aligned by default, explicit here
                    ui.button('Copy Trip ID', on_click=lambda current_id=trip_id: ui.clipboard.write(current_id), color='indigo')
            #for row in rows:
            #    trip_id, admin_family_id, family_ids, status, visibility, location, destination, date, time = row
            #    trip_ids.append(trip_id)
            #    admin_family_ids.append(admin_family_id)
            #    family_ids_list.append(family_ids)
            #    statuses.append(status)
            #    visibilities.append(visibility)
            #    locations.append(location)
            #    destinations.append(destination)
            #    dates.append(date)
            #    times.append(time)

        #for trip in trips:
        #    # trip schema: (trip_id, admin_family_id, family_ids, child_ids, status, visibility, location, destination, description, date, time, image)
        #    trip_id = trip[0]
        #    admin_family_id = trip[1]
        #    family_ids = trip[2]
        #    status = trip[3]
        #    visibility = trip[4]
        #    location = trip[5]
        #    destination = trip[6]
        #    date = trip[7]
        #    time = trip[8]
        #    #ui.card().classes('mb-3 w-full')
        #    #with ui.row().classes('items-center justify-between'):
        #    #    with ui.column():
        #    #        ui.label(f"Destination: {destination}").classes('font-bold')
        #    #        ui.label(f"Description: {description}")
        #    #        ui.label(f"Date: {date}  Time: {time}")
        #    #        ui.label(f"Visibility: {str(visibility).upper()}  Status: {'Active' if status else 'Inactive'}")
        #    #    with ui.column().classes('items-end'):
        #    #        ui.button('Start', on_click=lambda tid=trip_id: on_start_trip_click(tid), color='green').classes('mb-1')
        #    #        ui.button('End', on_click=lambda tid=trip_id: on_end_trip_click(tid), color='red').classes('mb-1')
        #    #        ui.button('Leave', on_click=lambda tid=trip_id: on_leave_trip_click(tid), color='orange')
        #    with ui.item().classes('relative overflow-hidden max-h-40'):
        #        ui.image(LOCATIONS[destination][1]) \
        #            .classes('absolute inset-0 w-full h-full object-cover opacity-25 pointer-events-none select-none')



@ui.page('/trips')
async def trips_page(request: Request):
    _app_footer()

    session_id = request.cookies.get(SESSION_COOKIE)

    if not await verify_session(session_id):
        ui.label('You need to login first.').classes('text-2xl font-bold mb-6 text-center text-indigo')
        ui.button('Login', on_click=lambda: ui.navigate.to('/login'), color='indigo').classes('w-full')
        ui.button('Don\'t have an account? Register', on_click=lambda: ui.navigate.to('/register')).props('flat dense').classes('w-full mt-3 text-indigo')
        return

    user_id = await retrieve_user_id_from_session_id(session_id)

    with sqlite3.connect(DATABASE_PATH) as con:
        cur = con.cursor()
        cur.execute('SELECT family_id FROM users WHERE user_id=?', (user_id,))
        family_id = cur.fetchone()
        if family_id and family_id[0]:
            family_id = family_id[0]
        else:
            ui.label('You are not in a family.').classes('text-2xl font-bold mb-6 text-center text-indigo')
            return

    image_base64_string = None

    async def create_trip():
        nonlocal image_base64_string
        
        if not visibility_input.value:
            ui.notification('Visibility is required.', color='green')
            return
        
        if not date_input.value:
            ui.notification('Date is required.', color='green')
            return
        
        if not time_input.value:
            ui.notification('Time is required.', color='green')
            return

        with sqlite3.connect(DATABASE_PATH) as con:
            cur = con.cursor()
            new_trip_id = str(uuid4())
            cur.execute(
                'INSERT INTO trips (trip_id, admin_family_id, family_ids, status, visibility, location, destination, date, time) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (new_trip_id, family_id, json.dumps([family_id]), False, visibility_input.value.lower(), '', destination_input.value, date_input.value, time_input.value)
            )
            cur.execute('SELECT trip_ids FROM families WHERE family_id=?', (family_id,))
            row = cur.fetchone()
            if row and row[0]:
                trip_ids = json.loads(row[0])
            else:
                trip_ids = []
            trip_ids.append(new_trip_id)
            cur.execute('UPDATE families SET trip_ids=? WHERE family_id=?', (json.dumps(trip_ids), family_id))
            con.commit()
            ui.notification('Trip created successfully!', color='green')
            ui.navigate.reload()
    
    async def join_trip():
        # Validation: Check if trip_id_input is present and valid
        trip_id = trip_id_input.value.strip() if trip_id_input.value else ''
        if not trip_id:
            ui.notification('Trip ID is required.', color='green')
            return
        if len(trip_id) < 3:
            ui.notification('Trip ID must be at least 3 characters.', color='green')
            return

        with sqlite3.connect(DATABASE_PATH) as con:
            ui.notification('Joining a trip...', color='green')
            cur = con.cursor()
            # Only select adult_ids, since admin_id is already known or can be checked separately
            cur.execute('SELECT adult_ids FROM families WHERE family_id=?', (family_id,))
            row = cur.fetchone()
            is_parent = False
            if row:
                adult_ids = json.loads(row[0])
                # Check if user is admin or in adult_ids
                cur.execute('SELECT admin_user_id FROM families WHERE family_id=?', (family_id,))
                admin_id_row = cur.fetchone()
                admin_id = admin_id_row[0] if admin_id_row else None
                if user_id == admin_id or user_id in adult_ids:
                    is_parent = True
            if not is_parent:
                ui.notification('You are not a parent in this family.', color='red')
                return

            # Check if trip exists
            cur.execute('SELECT family_ids FROM trips WHERE trip_id=?', (trip_id,))
            row = cur.fetchone()
            if not row:
                ui.notification('Trip not found.', color='red')
                return
            family_ids = json.loads(row[0])
            if family_id in family_ids:
                ui.notification('Your family is already attending this trip.', color='orange')
                return

            # All checks passed, join the trip
            family_ids.append(family_id)
            cur.execute('UPDATE trips SET family_ids=? WHERE trip_id=?', (json.dumps(family_ids), trip_id))

            # Also add the trip to the family's trip_ids if not already present
            cur.execute('SELECT trip_ids FROM families WHERE family_id=?', (family_id,))
            row = cur.fetchone()
            if row and row[0]:
                trip_ids = json.loads(row[0])
            else:
                trip_ids = []
            if trip_id not in trip_ids:
                trip_ids.append(trip_id)
                cur.execute('UPDATE families SET trip_ids=? WHERE family_id=?', (json.dumps(trip_ids), family_id))

            con.commit()
            ui.notification('Trip joined successfully!', color='green')
            ui.timer(0.1, ui.navigate.reload, once=True)

    ui.label('Trips').classes('text-2xl font-bold mb-6 text-center text-indigo')

    with ui.tabs().classes('w-full') as tabs:
        attending_trips = ui.tab('Attending', icon='person')
        create = ui.tab('Create', icon='add_circle')
        join = ui.tab('Join', icon='merge')
    with ui.tab_panels(tabs, value=attending_trips).classes('w-full'):
        with ui.tab_panel(attending_trips):
            ui.label('These are trips your family is attending.')
            ui.label('You are a parent. You can create and join trips on behalf of your family.')
            ui.button('Refresh', on_click=ui.navigate.reload, color='indigo').classes('w-full')
            
            with ui.list().props('bordered separator').classes('w-full mt-4 mx-0 px-0 rounded-lg'):
                ui.item_label('Attending Trips').props('header').classes('text-bold')
                ui.separator()
                async def on_start_trip_click(trip_id):
                    with sqlite3.connect(DATABASE_PATH) as con:
                        cur = con.cursor()
                        cur.execute('UPDATE trips SET status=? WHERE trip_id=?', (True, trip_id))
                        con.commit()
                        ui.notification('Starting trip...', color='green')
                        ui.navigate.to('/trips/drive/' + str(trip_id))
                
                async def on_end_trip_click(trip_id):
                    with sqlite3.connect(DATABASE_PATH) as con:
                        cur = con.cursor()
                        # get admin_family_id from trips table
                        cur.execute('SELECT admin_family_id FROM trips WHERE trip_id=?', (trip_id,))
                        admin_family_id = cur.fetchone()
                        if admin_family_id:  # Make sure it's not None
                            cur.execute('SELECT family_ids FROM trips WHERE trip_id=?', (trip_id,))
                            family_ids = cur.fetchone()
                            if family_ids:
                                family_ids = json.loads(family_ids[0])
                                for family_id in family_ids:
                                    cur.execute('SELECT trip_ids FROM families WHERE family_id=?', (family_id,))
                                    trip_ids = cur.fetchone()
                                    if trip_ids:
                                        trip_ids = json.loads(trip_ids[0])
                                        trip_ids.remove(trip_id)
                                        cur.execute('UPDATE families SET trip_ids=? WHERE family_id=?', (json.dumps(trip_ids), family_id))
                            cur.execute('DELETE FROM trips WHERE trip_id=? AND admin_family_id=?', (trip_id, admin_family_id[0]))

                            con.commit()

                            ui.notification('Trip stopped and finished.', color='green')
                            ui.navigate.to("/trips")
                        else:
                            ui.notification('Trip not found.', color='red')
                async def on_leave_trip_click(trip_id):
                    ui.notification('Leaving trip...')
                    with sqlite3.connect(DATABASE_PATH) as con:
                        cur = con.cursor()
                        cur.execute('SELECT family_ids FROM trips WHERE trip_id=?', (trip_id,))
                        row = cur.fetchone()
                        if not row:
                            ui.notification('Trip not found.', color='red')
                            return
                        family_ids = json.loads(row[0])
                        if family_id not in family_ids:
                            ui.notification('Your family is not attending this trip.', color='red')
                            return
                        family_ids.remove(family_id)
                        cur.execute('UPDATE trips SET family_ids=? WHERE trip_id=?', (json.dumps(family_ids), trip_id))
                        cur.execute('SELECT trip_ids FROM families WHERE family_id=?', (family_id,))
                        row = cur.fetchone()
                        trip_ids = json.loads(row[0])
                        trip_ids.remove(trip_id)
                        cur.execute('UPDATE families SET trip_ids=? WHERE family_id=?', (json.dumps(trip_ids), family_id))
                        con.commit()
                        ui.notification('Left trip successfully!', color='green')
                        ui.timer(0.1, ui.navigate.reload, once=True)
                #trip_id TEXT PRIMARY KEY,
                #admin_family_id TEXT NOT NULL,
                #family_ids TEXT NOT NULL,
                #status BOOLEAN NOT NULL,
                #visibility TEXT NOT NULL CHECK (visibility IN ('public', 'private')),
                #location TEXT NOT NULL, -- Current location of the trip
                #destination TEXT NOT NULL,
                #description TEXT NOT NULL,
                #date TEXT NOT NULL,
                #time TEXT NOT NULL,
                #image TEXT NOT NULL -- Required image for the trip
                with sqlite3.connect(DATABASE_PATH) as con:
                    cur = con.cursor()
                    cur.execute("SELECT trip_ids FROM families WHERE family_id=?", (family_id,))
                    row = cur.fetchone()
                    if row and row[0]:
                        trip_ids = json.loads(row[0])
                    else:
                        trip_ids = []
                    trips = []
                    if trip_ids:
                        # Build the correct number of placeholders for the IN clause
                        placeholders = ','.join(['?'] * len(trip_ids))
                        query = f"SELECT * FROM trips WHERE trip_id IN ({placeholders}) ORDER BY date ASC"
                        cur.execute(query, trip_ids)
                        trips = cur.fetchall()
                for trip in trips:
                    # trip schema: (trip_id, admin_family_id, family_ids, child_ids, status, visibility, location, destination, description, date, time, image)
                    trip_id = trip[0]
                    admin_family_id = trip[1]
                    family_ids = trip[2]
                    status = trip[3]
                    visibility = trip[4]
                    location = trip[5]
                    destination = trip[6]
                    date = trip[7]
                    time = trip[8]
                    #ui.card().classes('mb-3 w-full')
                    #with ui.row().classes('items-center justify-between'):
                    #    with ui.column():
                    #        ui.label(f"Destination: {destination}").classes('font-bold')
                    #        ui.label(f"Description: {description}")
                    #        ui.label(f"Date: {date}  Time: {time}")
                    #        ui.label(f"Visibility: {str(visibility).upper()}  Status: {'Active' if status else 'Inactive'}")
                    #    with ui.column().classes('items-end'):
                    #        ui.button('Start', on_click=lambda tid=trip_id: on_start_trip_click(tid), color='green').classes('mb-1')
                    #        ui.button('End', on_click=lambda tid=trip_id: on_end_trip_click(tid), color='red').classes('mb-1')
                    #        ui.button('Leave', on_click=lambda tid=trip_id: on_leave_trip_click(tid), color='orange')
                    with ui.item().classes('relative overflow-hidden max-h-40'):
                        ui.image(LOCATIONS[destination][1]) \
                            .classes('absolute inset-0 w-full h-full object-cover opacity-25 pointer-events-none select-none')
                        #else:
                        #    ui.label('No image available').classes('absolute inset-0 flex items-center justify-center text-gray-500 opacity-50 w-full h-full')
                        with ui.row().classes('relative z-10 p-0 w-full items-center justify-between'):
                            #with ui.row().classes('items-center gap-0'):
                            #    with ui.item_section().props('avatar'):
                            #        ui.icon('directions_car')
                            #with ui.column().classes('items-center gap-0'):
                            with ui.column().classes('items-center gap-0 flex-shrink max-w-[150px] sm:max-w-[200px]'):
                                ui.item_label(destination).classes('text-xs')
                                ui.item_label(f'{date} • {time}').props('caption')
                                #ui.item_label(f'{description}').props('caption')
                                if family_id == admin_family_id:
                                    ui.item_label('Made by your family.').props('caption')
                                else:
                                    ui.item_label('Your family is attending.').props('caption')
                            with ui.column().classes('items-end gap-1'):
                                ui.item_label('Active' if status == 1 else 'Inactive').props('caption').classes('text-black')
                                ui.chip('View', icon='article', on_click=lambda tid=trip_id: ui.navigate.to(f'/trips/view/{tid}')).props('flat color="blue-200" size=sm')
                                if family_id == admin_family_id:
                                    ui.chip('Edit', icon='edit', on_click=lambda tid=trip_id: ui.navigate.to(f'/trips/edit/{tid}')).props('flat color="orange-200" size=sm')
                                    if status == 1:
                                        ui.chip('Driver Dashboard', icon='directions_car', on_click=lambda tid=trip_id: ui.navigate.to(f'/trips/drive/{tid}')).props('flat color="green-400" size=sm')
                                        ui.chip('Stop and Delete', icon='dangerous', on_click=lambda tid=trip_id: on_end_trip_click(tid)).props('flat color="red-400" size=sm')
                                    else:
                                        ui.chip('Start', icon='flag', on_click=lambda e, tid=trip_id: on_start_trip_click(tid)).props('flat color="green-400" size=sm')
                                        ui.chip('Delete', icon='dangerous', on_click=lambda tid=trip_id: on_end_trip_click(tid)).props('flat color="red-400" size=sm')
                                else:
                                    ui.chip('Leave Trip', icon='exit_to_app', on_click=lambda tid=trip_id: on_leave_trip_click(tid)).props('flat color="red-200" size=sm')
                        #ui.separator()
        with ui.tab_panel(create):
            ui.label("Create a new trip on behalf of your family.")
            ui.label("Please enter the exact street address of the location for destination.")

            destination_input = ui.select(options=list(LOCATIONS.keys()), with_input=True,
                on_change=lambda e: ui.notify(e.value)).classes('w-full')
            
            with ui.input('Date').classes('w-full') as date_input:
                with ui.menu().props('no-parent-event') as menu:
                    with ui.date().props(''':options="date => { const today = new Date(new Date().setHours(0, 0, 0, 0)); const limit = new Date(today); limit.setDate(today.getDate() + 7); return new Date(date) >= today && new Date(date) < limit; }"''').bind_value(date_input):
                        with ui.row().classes('justify-end'):
                            ui.button('Close', on_click=menu.close).props('flat')
                with date_input.add_slot('append'):
                    ui.icon('edit_calendar').on('click', menu.open).classes('cursor-pointer')
                        
            with ui.input('Time').classes('w-full') as time_input:
                with ui.menu().props('no-parent-event') as menu:
                    with ui.time().bind_value(time_input):
                        with ui.row().classes('justify-end'):
                            ui.button('Close', on_click=menu.close).props('flat')
                with time_input.add_slot('append'):
                    ui.icon('access_time').on('click', menu.open).classes('cursor-pointer')
            #with sqlite3.connect(DATABASE_PATH) as con:
            #    cur = con.cursor()
            #    cur.execute('SELECT child_ids FROM families WHERE family_id=?', (family_id,))
            #    child_ids = cur.fetchone()
            #    if child_ids:
            #        child_ids = json.loads(child_ids[0])
            #    else:
            #        child_ids = []
            #ui.select(names, multiple=True, value=names[:2], label='comma-separated') \
            #child_ids = ['John', 'Jane', 'Jim', 'Jill']
            
            visibility_input = ui.select(['Public', 'Private'], label='Visibility').props('outlined').classes('w-full mb-3')
            ui.button('Create Trip', on_click=create_trip, color='indigo').classes('w-full')
        with ui.tab_panel(join):
            ui.label('Join Trip')
            trip_id_input = ui.input(label='Trip ID').props('outlined clearable').classes('w-full mb-3')
            ui.button('Join Trip', on_click=join_trip, color='indigo').classes('w-full')

@ui.page('/trips/view/{item_path:path}')
async def trip_view_page(request: Request, item_path: str):
    # Top bar
    with ui.header(elevated=True).classes('bg-indigo'):
        with ui.row().classes('items-center w-full'):
            ui.button(
                icon='arrow_back',
                on_click=lambda: ui.run_javascript('history.back()')
            ).props('flat round color="white"').classes('mr-2')
            ui.label(f'Trip: {item_path}').classes('text-lg')
    ui.button('Copy Trip ID to Clipboard', on_click=lambda: ui.clipboard.write(item_path), color='indigo')

    leaflet_map = ui.leaflet(center=(51.505, -0.09), zoom=15, options={'attributionControl': True}).classes('h-96 w-full')

    leaflet_map.clear_layers()

    leaflet_map.tile_layer(
        url_template=r'https://{s}.basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}{r}.png',
        options={
            'maxZoom': 19,
            'attribution': '<a href="http://example.com">Careavan</a>™ 💜'
        },
    )

    location_marker = leaflet_map.marker(latlng=(51.505, -0.09), options={'draggable': False})

    # Live stats
    ui.label('Live Stats').classes('text-xl font-bold mb-6 text-center text-indigo')
    current_location_label = ui.label('The current location is:').classes('text-sm mb-2')

    visibility_label = ui.label('Visibility:').classes('text-sm mb-2')

    async def update_visibility():
        with sqlite3.connect(DATABASE_PATH) as con:
            cur = con.cursor()
            cur.execute('SELECT visibility FROM trips WHERE trip_id=?', (item_path,))
            row = cur.fetchone()

            if row and row[0]:
                visibility_label.set_text(f'Visibility: {row[0].capitalize()}')
            else:
                visibility_label.set_text('Visibility: Unknown')
    await update_visibility()

    async def update_location():
        with sqlite3.connect(DATABASE_PATH) as con:
            cur = con.cursor()

            cur.execute('SELECT location FROM trips WHERE trip_id=?', (item_path,))
            row = cur.fetchone()

            if row and row[0]:
                try:
                    lat_str, lon_str = [s.strip() for s in row[0].split(',')]

                    lat, lon = float(lat_str), float(lon_str)

                    location_marker.latlng = (lat, lon)

                    leaflet_map.center = (lat, lon)

                    current_location_label.set_text(f'The current location is: {lat:.5f}, {lon:.5f}')
                except Exception as e:
                    print(f"Failed to update location: {e} (row[0]={row[0]})")

                    ui.notification('Failed to update location')
            else:
                current_location_label.set_text('The current location is: Unknown')
    
    with sqlite3.connect(DATABASE_PATH) as con:
        cur = con.cursor()
        cur.execute('SELECT destination, date, time, visibility FROM trips WHERE trip_id=?', (item_path,))
        row = cur.fetchone()

    await update_location()  # Initial call to set the location immediately
    ui.timer(5.0, update_location, once=False)

@ui.page('/trips/edit/{item_path:path}')
async def trip_edit_page(request: Request, item_path: str):
    with ui.header(elevated=True).classes('bg-indigo'):
        with ui.row().classes('items-center w-full'):
            ui.button(
                icon='arrow_back',
                on_click=lambda: ui.run_javascript('history.back()')
            ).props('flat round color="white"').classes('mr-2')

            ui.label(f'Edit Trip: {item_path}').classes('text-lg')

    #name_input = ui.input(label='Name').props('outlined clearable').classes('w-full mb-3')
    destination_input = ui.input(label='Destination 🗺️').props('outlined clearable').classes('w-full mb-3')
    with ui.input('Date').classes('w-full') as date:
        with ui.menu().props('no-parent-event') as menu:
            with ui.date().props(''':options="date => { const today = new Date(new Date().setHours(0, 0, 0, 0)); const limit = new Date(today); limit.setDate(today.getDate() + 7); return new Date(date) >= today && new Date(date) < limit; }"''').bind_value(date):
                with ui.row().classes('justify-end'):
                    ui.button('Close', on_click=menu.close).props('flat')
        with date.add_slot('append'):
            ui.icon('edit_calendar').on('click', menu.open).classes('cursor-pointer')

    with ui.input('Time').classes('w-full') as time:
        with ui.menu().props('no-parent-event') as menu:
            with ui.time().bind_value(time):
                with ui.row().classes('justify-end'):
                    ui.button('Close', on_click=menu.close).props('flat')
        with time.add_slot('append'):
            ui.icon('access_time').on('click', menu.open).classes('cursor-pointer')
    
    visibility_input = ui.select(['Public', 'Private'], label='Visibility').props('outlined').classes('w-full mb-3')  # Dropdown for selecting visibility of the trip.

    #child_ids_input = ui.select(child_ids, multiple=True, value=[], label='Select which of your children are attending this trip') \
    #                .classes('w-full')
    #ui.label('This is not the ideal way to do this, but it works for now.')

    async def get_trip_info():
        try:
            with sqlite3.connect(DATABASE_PATH) as con:
                cur = con.cursor()
                cur.execute('SELECT destination, date, time, visibility FROM trips WHERE trip_id=?', (item_path,))
                row = cur.fetchone()
                if row:
                    destination_input.value = row[0]
                    date.value = row[1]
                    time.value = row[2]
                    visibility_input.value = row[3].capitalize()
                    
                    ui.notification('Trip loaded successfully.', color='green')
                else:
                    ui.notification('Trip not found.', color='red')
        except Exception as e:
            ui.notification(f'Failed to load trip: {str(e)}', color='red')
    await get_trip_info()

    async def update_trip_info():
        try:
            with sqlite3.connect(DATABASE_PATH) as con:
                cur = con.cursor()
                cur.execute(
                    'UPDATE trips SET destination=?, date=?, time=?, visibility=? WHERE trip_id=?',
                    (
                        destination_input.value,
                        date.value,
                        time.value,
                        visibility_input.value.lower(),  # store as lowercase for consistency
                        item_path
                    )
                )
                con.commit()
                ui.notification('Trip updated successfully.', color='green')
        except Exception as e:
            ui.notification(f'Failed to update trip: {str(e)}', color='red')
    
    with ui.row().classes('justify-end gap-x-2 mt-4'):
        #ui.button("Reset", on_click=reset_general_fields).props('flat')
        #ui.button("Save Changes", on_click=update_general_fields, color='primary')
        ui.button("Reset", on_click=get_trip_info, color='indigo').props('flat')
        ui.button("Save Changes", on_click=update_trip_info, color='indigo')

@ui.page('/trips/drive/{item_path:path}')
async def trip_drive_page(request: Request, item_path: str):
    session_id = request.cookies.get(SESSION_COOKIE)
    
    status_label = ui.label('').classes('text-sm mb-2')

    with sqlite3.connect(DATABASE_PATH) as con:
        cur = con.cursor()
        current_user_id = await retrieve_user_id_from_session_id(session_id)
        cur.execute('SELECT family_id FROM users WHERE user_id=?', (current_user_id,))
        row = cur.fetchone()

        if not row or not row[0]:
            ui.notification('You are not in a family.', color='red')
            return
        
        family_id = row[0]
        cur.execute('SELECT adult_ids FROM families WHERE family_id=?', (family_id,))
        row = cur.fetchone()

        if not row:
            ui.notification('Family not found.', color='red')
            return
        
        adult_ids = json.loads(row[0])

        if current_user_id not in adult_ids:
            ui.notification('You are not authorized to drive this trip.', color='red')
            return
        
        cur.execute('SELECT trip_id FROM trips WHERE trip_id=? AND admin_family_id=?', (item_path, family_id))
        row = cur.fetchone()

        if not row or not row[0]:
            ui.notification('This trip is not owned by your family.', color='red')
            return
        
        cur.execute('SELECT status FROM trips WHERE trip_id=?', (item_path,))
        row = cur.fetchone()
        
        if row[0] != True:
            ui.notification('This trip is not active.', color='red')
            return

    # UI header
    with ui.header(elevated=True).classes('bg-indigo'):
        with ui.row().classes('items-center w-full'):
            ui.button(
                icon='arrow_back',
                on_click=lambda: ui.run_javascript('history.back()')
            ).props('flat round color="white"').classes('mr-2')
            ui.label(f'Driving for Trip: {item_path}').classes('text-lg')

    ui.label('You are driving this trip. Anyone in your family can open this page and location will update from their device if allowed.').classes('text-sm mb-2')

    # Map setup
    leaflet_map = ui.leaflet(center=(51.505, -0.09), zoom=15, options={'attributionControl': True}).classes('h-96 w-full')
    leaflet_map.clear_layers()
    leaflet_map.tile_layer(
        url_template=r'https://{s}.basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}{r}.png',
        options={
            'maxZoom': 19,
            'attribution': '<a href="http://example.com">Careavan</a>™ 💜'
        },
    )
    location_marker = leaflet_map.marker(latlng=(51.505, -0.09), options={'draggable': False})
    current_location_label = ui.label('The current location is:').classes('text-sm mb-2')

    # Poll the trip's location from the DB and update the map for all viewers
    async def update_location():
        with sqlite3.connect(DATABASE_PATH) as con:
            cur = con.cursor()
            cur.execute('SELECT location FROM trips WHERE trip_id=?', (item_path,))
            row = cur.fetchone()
            if row and row[0]:
                try:
                    lat_str, lon_str = [s.strip() for s in row[0].split(',')]
                    lat, lon = float(lat_str), float(lon_str)
                    location_marker.latlng = (lat, lon)
                    leaflet_map.center = (lat, lon)
                    current_location_label.set_text(f'The current location is: {lat:.5f}, {lon:.5f}')
                except Exception as e:
                    print(f"Failed to update location: {e} (row[0]={row[0]})")
                    ui.notification('Failed to update location')
            else:
                current_location_label.set_text('The current location is: Unknown')
    
    await update_location()  # Initial call to set the location immediately
    ui.timer(1.0, update_location, once=False)

    # If the user allows, update the trip's location in the DB every 10 seconds
    async def send_location_to_db():
        try:
            response = await ui.run_javascript('''
                return await new Promise((resolve, reject) => {
                    if (!navigator.geolocation) {
                        reject(new Error('Geolocation is not supported by your browser'));
                    } else {
                        navigator.geolocation.getCurrentPosition(
                            (position) => {
                                resolve({
                                    latitude: position.coords.latitude,
                                    longitude: position.coords.longitude,
                                });
                            },
                            () => {
                                reject(new Error('Unable to retrieve your location'));
                            }
                        );
                    }
                });
            ''', timeout=5.0)
            lat, lon = response["latitude"], response["longitude"]
            with sqlite3.connect(DATABASE_PATH) as con:
                cur = con.cursor()
                cur.execute('UPDATE trips SET location=? WHERE trip_id=?', (f"{lat},{lon}", item_path))

                con.commit()
        except Exception as e:
            print(f"Location update error: {e}")

    # Start auto-tracking location if possible
    ui.timer(5.0, send_location_to_db, once=False)
    
    async def stop_and_finish_trip():
        with sqlite3.connect(DATABASE_PATH) as con:
            cur = con.cursor()
            # get admin_family_id from trips table
            cur.execute('SELECT admin_family_id FROM trips WHERE trip_id=?', (item_path,))
            admin_family_id = cur.fetchone()
            if admin_family_id:  # Make sure it's not None
                cur.execute('SELECT family_ids FROM trips WHERE trip_id=?', (item_path,))
                family_ids = cur.fetchone()
                if family_ids:
                    family_ids = json.loads(family_ids[0])
                    for family_id in family_ids:
                        cur.execute('SELECT trip_ids FROM families WHERE family_id=?', (family_id,))
                        trip_ids = cur.fetchone()
                        if trip_ids:
                            trip_ids = json.loads(trip_ids[0])
                            trip_ids.remove(item_path)
                            cur.execute('UPDATE families SET trip_ids=? WHERE family_id=?', (json.dumps(trip_ids), family_id))
                cur.execute('DELETE FROM trips WHERE trip_id=? AND admin_family_id=?', (item_path, admin_family_id[0]))

                con.commit()

                ui.notification('Trip stopped and finished.', color='green')
                ui.navigate.reload()
            else:
                ui.notification('Trip not found.', color='red')
    
    ui.button('Stop and Finish Trip', on_click=stop_and_finish_trip).props('primary color="red"').classes('w-full')

@ui.page('/family')
async def family_page(request: Request):
    _app_footer()

    session_id = request.cookies.get(SESSION_COOKIE)

    if not await verify_session(session_id):
        ui.label('You need to login first.').classes('text-2xl font-bold mb-6 text-center text-indigo')
        ui.button('Login', on_click=lambda: ui.navigate.to('/login'), color='indigo').classes('w-full')
        ui.button('Don\'t have an account? Register', on_click=lambda: ui.navigate.to('/register')).props('flat dense').classes('w-full mt-3 text-indigo')
        return

    user_id = await retrieve_user_id_from_session_id(session_id)

    async def is_admin():
        with sqlite3.connect(DATABASE_PATH) as con:
            cur = con.cursor()
            cur.execute('SELECT family_id FROM users WHERE user_id=?', (user_id,))
            family_id_tuple = cur.fetchone()
            if not family_id_tuple or not family_id_tuple[0]:
                return False
            
            family_id_str = family_id_tuple[0]
            cur.execute('SELECT admin_user_id FROM families WHERE family_id=?', (family_id_str,))
            admin_id_tuple = cur.fetchone()
            if not admin_id_tuple:
                return False
            
            admin_id = admin_id_tuple[0]
            return admin_id == user_id

    async def create_family():
        with sqlite3.connect(DATABASE_PATH) as con:
            cur = con.cursor()
            cur.execute('SELECT family_id FROM users WHERE user_id=?', (user_id,))
            family_id = cur.fetchone() or None

            if family_id and family_id[0]:
                ui.notification('You\'re already in a family.', color='green')
                return
            
            with sqlite3.connect(DATABASE_PATH) as con_inner:
                cur_inner = con_inner.cursor()
                family_id_new = str(uuid4())
                cur_inner.execute('INSERT INTO families (family_id, admin_user_id, adult_ids, trip_ids, traits) VALUES (?, ?, ?, ?, ?)',
                            (family_id_new, user_id, json.dumps([user_id]), json.dumps([]), json.dumps([])))
                cur_inner.execute('UPDATE users SET family_id=? WHERE user_id=?',
                            (family_id_new, user_id))
                con_inner.commit()
                ui.notification('Family created successfully!', color='green')
                ui.timer(0.1, ui.navigate.reload, once=True)

    async def delete_family():
        if not await is_admin():
            ui.notification('You are not the admin of this family.', color='red')
            return
        
        with sqlite3.connect(DATABASE_PATH) as con:
            cur = con.cursor()
            
            # 1. Get the family_id of the current user's family
            cur.execute('SELECT family_id FROM users WHERE user_id=?', (user_id,))
            family_id_tuple = cur.fetchone()
            
            if not family_id_tuple or not family_id_tuple[0]:
                ui.notification('You\'re not in a family.', color='green')
                return
            
            family_id_to_delete = family_id_tuple[0]
    
            # 2. Get all trip_ids associated with this family BEFORE deleting the family
            # We need this to potentially clean up trips where this family was an attendee
            cur.execute('SELECT trip_ids FROM families WHERE family_id=?', (family_id_to_delete,))
            trip_ids_row = cur.fetchone()
            family_trip_ids = json.loads(trip_ids_row[0]) if trip_ids_row and trip_ids_row[0] else []
            if family_trip_ids == []:
                # 3. Delete the family record itself
                cur.execute('DELETE FROM families WHERE family_id=?', (family_id_to_delete,))

                # 4. Update all users whose family_id matches the deleted family_id
                cur.execute('UPDATE users SET family_id=? WHERE family_id=?', ('', family_id_to_delete))
                con.commit()
                ui.notification('Family deleted successfully.', color='green')
                ui.timer(0.1, ui.navigate.reload, once=True)
            else:
                ui.notification('Please leave all trips before deleting the family.', color='red')
    
    async def join_family():
        with sqlite3.connect(DATABASE_PATH) as con:
            cur = con.cursor()
            cur.execute('SELECT family_id FROM users WHERE user_id=?', (user_id,))
            user_family_id_data = cur.fetchone()
            if user_family_id_data and user_family_id_data[0] != '':
                ui.notification('You are already in a family. Please leave the family before joining a new one.', color='red')
                return
        family_id_to_join = family_code_input.value.strip()
        if not family_id_to_join:
            ui.notification('Please enter a family ID to join.', color='green')
            return
        with sqlite3.connect(DATABASE_PATH) as con:
            cur = con.cursor()
            cur.execute('SELECT * FROM families WHERE family_id=?', (family_id_to_join,))
            family_data = cur.fetchone()
            if not family_data:
                ui.notification('Family ID does not exist.', color='green')
                return
            cur.execute('UPDATE users SET family_id=? WHERE user_id=?',
                        (family_id_to_join, user_id))
            adult_ids = json.loads(family_data[2])
            if user_id not in adult_ids:
                adult_ids.append(user_id)
            cur.execute('UPDATE families SET adult_ids=? WHERE family_id=?',
                        (json.dumps(adult_ids), family_id_to_join))
            con.commit()
            ui.notification('You have joined the family successfully!', color='green')
            ui.timer(0.1, ui.navigate.reload, once=True)
    
    async def leave_family():
        with sqlite3.connect(DATABASE_PATH) as con:
            user_id = await retrieve_user_id_from_session_id(session_id)
            cur = con.cursor()
            cur.execute('SELECT family_id FROM users WHERE user_id=?', (user_id,))
            family_id_tuple = cur.fetchone() 
            if not family_id_tuple or not family_id_tuple[0]:
                ui.notification('You are not in a family.', color='red')
                return
            current_family_id = family_id_tuple[0] 
            cur.execute('SELECT admin_user_id FROM families WHERE family_id=?', (current_family_id,))
            admin_id_tuple = cur.fetchone() 
            if admin_id_tuple and admin_id_tuple[0] == user_id:
                ui.notification('You are the admin of the family. You cannot leave. Transfer admin rights or delete the family.', color='red')
                return
            cur.execute('UPDATE users SET family_id=? WHERE user_id=?', ('', user_id))
            cur.execute('SELECT adult_ids FROM families WHERE family_id=?', (current_family_id,))
            family_data = cur.fetchone()
            if family_data:
                adult_ids = json.loads(family_data[0])
                if user_id in adult_ids:
                    adult_ids.remove(user_id)
                cur.execute('UPDATE families SET adult_ids=? WHERE family_id=?',
                            (json.dumps(adult_ids), current_family_id))
            con.commit()
            ui.notification('You have left the family successfully!', color='green')
            ui.timer(0.1, ui.navigate.reload, once=True)
    
    async def remove_member(user_to_delete_id: str):
        ui.notification('Removal in progress...', color='green')
        current_logged_in_user_id = await retrieve_user_id_from_session_id(session_id)
        with sqlite3.connect(DATABASE_PATH) as con:
            cur = con.cursor()
            cur.execute('SELECT family_id FROM users WHERE user_id=?', (current_logged_in_user_id,))
            family_id_tuple = cur.fetchone()
            if not family_id_tuple or not family_id_tuple[0]:
                ui.notification('You (admin) are not in a family.', color='red')
                return
            current_family_id = family_id_tuple[0]
            cur.execute('SELECT admin_user_id FROM families WHERE family_id=?', (current_family_id,))
            admin_id_tuple = cur.fetchone()
            if not admin_id_tuple or admin_id_tuple[0] != current_logged_in_user_id:
                ui.notification('You are not the admin of this family.', color='red')
                return
            if user_to_delete_id == current_logged_in_user_id:
                ui.notification('Admin cannot remove themselves. Transfer admin rights first or delete the family.', color='red')
                return
            cur.execute('SELECT adult_ids FROM families WHERE family_id=?', (current_family_id,))
            family_data = cur.fetchone()
            if family_data:
                adult_ids = json.loads(family_data[0])
                found_and_removed = False
                if user_to_delete_id in adult_ids:
                    adult_ids.remove(user_to_delete_id)
                    found_and_removed = True
                if not found_and_removed:
                    ui.notification('User not found in the family lists.', color='red')
                    return
                cur.execute('UPDATE families SET adult_ids=? WHERE family_id=?',
                            (json.dumps(adult_ids), current_family_id))
                cur.execute('UPDATE users SET family_id=? WHERE user_id=?', ('', user_to_delete_id))
                con.commit()
                ui.notification('User removed successfully!', color='green')
                ui.timer(0.1, ui.navigate.reload, once=True)
            else:
                ui.notification('Family data was not found.', color='red')

    async def transfer_admin(new_admin_id: str):
        ui.notification('Transferring admin...', color='green')
        current_user_id = await retrieve_user_id_from_session_id(session_id)
        with sqlite3.connect(DATABASE_PATH) as con:
            cur = con.cursor()
            cur.execute('SELECT family_id FROM users WHERE user_id=?', (current_user_id,))
            family_id_tuple = cur.fetchone()
            if not family_id_tuple or not family_id_tuple[0]:
                ui.notification('You are not in a family.', color='red')
                return
            current_family_id = family_id_tuple[0]
            cur.execute('SELECT admin_user_id FROM families WHERE family_id=?', (current_family_id,))
            admin_id_tuple = cur.fetchone()
            if not admin_id_tuple or admin_id_tuple[0] != current_user_id:
                ui.notification('You are not the admin of this family.', color='red')
                return
            cur.execute('SELECT adult_ids FROM families WHERE family_id=?', (current_family_id,))
            family_data = cur.fetchone()
            if family_data:
                adult_ids = json.loads(family_data[0])
                if new_admin_id not in adult_ids:
                    ui.notification('The selected user is not an adult member of this family.', color='red')
                    return
                if new_admin_id == current_user_id:
                    ui.notification('You are already the admin.', color='red')
                    return
                cur.execute('UPDATE families SET admin_user_id=? WHERE family_id=?', (new_admin_id, current_family_id))
                con.commit()
                cur.execute('SELECT first_name, last_name FROM users WHERE user_id=?', (new_admin_id,))
                new_admin_details = cur.fetchone()
                new_admin_name_display = f"{new_admin_details[0]} {new_admin_details[1]}" if new_admin_details else new_admin_id
                ui.notification(f'Admin transferred successfully to {new_admin_name_display}.', color='green')
                ui.timer(0.1, ui.navigate.reload, once=True)
            else:
                ui.notification('Family data not found.', color='red')

    async def save_traits():
        with sqlite3.connect(DATABASE_PATH) as con:
            cur = con.cursor()
            cur.execute('UPDATE families SET traits=? WHERE family_id=?', (json.dumps(traits_input.value), family_id))
            con.commit()
            ui.notification('Traits saved successfully!', color='green')
            ui.timer(0.1, ui.navigate.reload, once=True)

    with sqlite3.connect(DATABASE_PATH) as con:
        cur = con.cursor()
        cur.execute('SELECT family_id FROM users WHERE user_id=?', (user_id,))
        family_id_tuple = cur.fetchone()

    if not family_id_tuple or not family_id_tuple[0]:
        ui.label('You are not part of a family.').classes('text-2xl font-bold mb-6 text-center text-indigo')
        ui.button('Create Family', on_click=create_family, color='indigo').classes('w-full')
        with ui.row():
            family_code_input = ui.input('Family Code', placeholder='Enter family code to join').props('outlined clearable').classes('w-half mb-3')
            ui.button('Join Family', on_click=join_family, color='indigo').classes('w-half')
        return
    else:
        family_id = family_id_tuple[0]
        
        ui.label(f'Family Management').classes('text-2xl font-bold mb-6 text-center text-indigo')
        with ui.tabs().classes('w-full') as tabs:
            family_dashboard = ui.tab('Dashboard', icon='dashboard')
            common_traits = ui.tab('Common Traits', icon='menu')
        with ui.tab_panels(tabs, value=family_dashboard).classes('w-full'):
            with ui.tab_panel(family_dashboard):
                if await is_admin():
                    ui.label('You are the admin of this family.')
                else:
                    ui.label('You are NOT the admin of this family.')
                ui.button('Refresh', on_click=ui.navigate.reload, color='indigo').classes('w-full')
                with sqlite3.connect(DATABASE_PATH) as con:
                    cur = con.cursor()
                    cur.execute('SELECT admin_user_id, adult_ids FROM families WHERE family_id=?', (family_id,))
                    family_info_row = cur.fetchone()
                
                if family_info_row:
                    admin_user_id = family_info_row[0]
                    adult_ids = json.loads(family_info_row[1])
                    with ui.list().props('bordered separator').classes('w-full rounded-lg'):
                        ui.item_label('Family Members').props('header').classes('text-bold')
                        ui.separator()
                        for member in adult_ids:
                            with sqlite3.connect(DATABASE_PATH) as con:
                                cur = con.cursor()
                                cur.execute('SELECT user_id, first_name, last_name FROM users WHERE user_id=?', (member,))
                                member_user_data = cur.fetchone()
                            if member_user_data:
                                with ui.item():
                                    with ui.item_section().props('avatar'):
                                        ui.icon('shield' if member_user_data[0] == admin_user_id else 'person')
                                    with ui.item_section():
                                            ui.item_label(f'{member_user_data[1]} {member_user_data[2]}')
                                            ui.item_label('Adult Admin' if member_user_data[0] == admin_user_id else 'Adult').props('caption')
                                    if await is_admin() and member_user_data[0] != user_id:
                                            with ui.item_section().props('side').classes('gap-xs'):
                                                ui.chip('Transfer Admin', icon='dangerous', on_click=lambda mid=member_user_data[0]: transfer_admin(mid)).props('flat dense color="warning" size=sm')
                                                ui.chip('Remove', icon='dangerous', on_click=lambda mid=member_user_data[0]: remove_member(mid)).props('flat dense color="red" size=sm')
                if await is_admin():
                    ui.button('Delete Family', on_click=delete_family, color='red').classes('w-full')
                else:
                    ui.button('Leave Family', on_click=leave_family, color='red').classes('w-full')
                ui.button('Copy Family ID to clipboard', on_click=lambda: ui.clipboard.write(family_id), color='indigo').classes('w-full')
                ui.label(f'Family ID: {family_id}')
            with ui.tab_panel(common_traits):
                with ui.column().classes('items-center w-full p-4'):
                    with sqlite3.connect(DATABASE_PATH) as con:
                        cur = con.cursor()
                        cur.execute('SELECT traits FROM families WHERE family_id=?', (family_id,))
                        traits_row = cur.fetchone()
                        traits = []
                        if traits_row and traits_row[0]:
                            traits = json.loads(traits_row[0])
                            ui.label(f'Traits: {traits}')
                        else:
                            ui.label('No traits found.')
                    names = ['Sports', 'Music', 'Art', 'Reading', 'Writing', 'Cooking', 'Gardening', 'Hiking', 'Camping', 'Fishing', 'Swimming', 'Biking', 'Walking', 'Yoga', 'Meditation', 'Reading', 'Writing', 'Cooking', 'Gardening', 'Hiking', 'Camping', 'Fishing', 'Swimming', 'Biking', 'Walking', 'Yoga', 'Meditation']
                    traits_input = ui.select(names, multiple=True, value=traits, label='Select Family Traits') \
                        .classes('w-full')
                    
                    with ui.row():
                        ui.button("Reset", on_click=ui.navigate.reload, color='indigo').props('flat')
                        ui.button("Save Changes", on_click=save_traits, color='indigo')
                    ui.label('Because of the way NiceGUI works, the easiest way to make a reset button with ui.select is to reload the page.')


@ui.page('/settings')
async def settings_page(request: Request):
    _app_footer()

    session_id = request.cookies.get(SESSION_COOKIE)

    if not await verify_session(session_id):
        ui.label('You need to login first.').classes('text-2xl font-bold mb-6 text-center text-indigo')
        ui.button('Login', on_click=lambda: ui.navigate.to('/login'), color='indigo').classes('w-full')
        ui.button('Don\'t have an account? Register', on_click=lambda: ui.navigate.to('/register')).props('flat dense').classes('w-full mt-3 text-indigo')
        return

    user_id = await retrieve_user_id_from_session_id(session_id)

    ui.label(f'Settings for {user_id}').classes('text-2xl font-bold mb-6 text-center text-indigo')

    with ui.tabs().classes('w-full') as tabs:
        general_tab = ui.tab('General', icon='person')
        security_tab = ui.tab('Security', icon='lock')
    with ui.tab_panels(tabs, value=general_tab).classes('w-full mt-4'):
        with ui.tab_panel(general_tab):
            email_input = ui.input('Email').props('type=email outlined clearable').classes('w-full mb-3')
            first_name_input = ui.input('First Name').props('outlined clearable').classes('w-full mb-3')
            last_name_input = ui.input('Last Name').props('outlined clearable').classes('w-full mb-3')

            async def load_general_fields():
                with sqlite3.connect(DATABASE_PATH) as con:
                    cur = con.cursor()
                    cur.execute('SELECT first_name, last_name, email FROM users WHERE user_id=?', (user_id,))
                    user = cur.fetchone()

                if not user:
                    ui.label('User not found.').classes('text-2xl font-bold mb-6 text-center text-indigo')
                    return

                first_name_input.value = user[0]
                last_name_input.value = user[1]
                email_input.value = user[2]

                ui.notification('Fields reset.', color='green')

            await load_general_fields()

            async def save_general_fields():
                if not all([f.value for f in [first_name_input, last_name_input]]):
                    ui.notification('All fields are required.', color='red')
                    return

                with sqlite3.connect(DATABASE_PATH) as con: # Make sure user isn't already in a family.
                    cur = con.cursor() # Make sure user isn't already in a family.
                    cur.execute(' SELECT family_id FROM users WHERE user_id=?', (user_id,))
                    family_id = cur.fetchone()
                    if family_id and family_id[0] != '':
                        ui.notification('You are in a family. Please leave the family before changing your general settings.', color='red')
                        return

                with sqlite3.connect(DATABASE_PATH) as con:
                    ui.notification('Working on it...', color='green')
                    cur = con.cursor()
                    cur.execute('UPDATE users SET first_name=?, last_name=? WHERE user_id=?',
                                (first_name_input.value, last_name_input.value, user_id))
                    con.commit()
                    ui.notification('Updated Successfully!', color='green')
            
            with ui.row():
                ui.button("Reset", on_click=load_general_fields, color='indigo').props('flat')
                ui.button("Save Changes", on_click=save_general_fields, color='indigo')
        
        with ui.tab_panel(security_tab):
            old_password_input = ui.input('Old Password', password=True, password_toggle_button=True).props('outlined clearable').classes('w-full mb-3')
            new_password_input = ui.input('New Password', password=True, password_toggle_button=True).props('outlined clearable').classes('w-full mb-3')
            confirm_new_password_input = ui.input('Confirm New Password', password=True, password_toggle_button=True).props('outlined clearable').classes('w-full mb-6')

            async def load_security_fields():
                old_password_input.value = ''
                new_password_input.value = ''
                confirm_new_password_input.value = ''

                ui.notification('Fields reset.', color='green')
            
            await load_security_fields()

            async def save_security_fields():
                if not all([f.value for f in [old_password_input, new_password_input, confirm_new_password_input]]):
                    ui.notification('All fields are required.', color='red')
                    return
                if new_password_input.value != confirm_new_password_input.value:
                    ui.notification('New passwords do not match.', color='red')
                    return
                if len(new_password_input.value) < 6:
                    ui.notification('New password must be at least 6 characters.', color='red')
                    return
                
                with sqlite3.connect(DATABASE_PATH) as con:
                    cur = con.cursor()
                    cur.execute('SELECT password FROM users WHERE user_id=?', (user_id,))
                    result = cur.fetchone()
                    if not result or not bcrypt.checkpw(old_password_input.value.encode('utf-8'), result[0].encode('utf-8')):
                        ui.notification('Old password is incorrect.', color='red')
                        return
                    
                    hashed_new_password = bcrypt.hashpw(new_password_input.value.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                    cur.execute('UPDATE users SET password=? WHERE user_id=?', (hashed_new_password, user_id))
                    con.commit()
                    ui.notification('Password updated successfully!', color='green')
            with ui.row():
                ui.button("Reset", on_click=load_security_fields, color='indigo').props('flat')
                ui.button("Save Changes", on_click=save_security_fields, color='indigo')
    ui.button('Logout', on_click=lambda: ui.navigate.to('/_delete_session'), color='indigo').classes('w-full')

ui.run(title='Careavan', favicon="🚗", port=8080)
