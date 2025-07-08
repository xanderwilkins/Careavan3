from nicegui import ui, app, events
from starlette.requests import Request
from starlette.responses import RedirectResponse
from starlette.staticfiles import StaticFiles

from datetime import datetime, timezone, timedelta
from PIL import Image
from uuid import uuid4
import bcrypt
import sqlite3
import base64
import json
import io

SESSION_COOKIE = 'careavan_session'
DATABASE_PATH = 'careavan.db'

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
            role TEXT NOT NULL CHECK (role IN ('parent', 'child')),
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
            child_ids TEXT NOT NULL,
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
            description TEXT NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            image TEXT NOT NULL -- Required image for the trip
        )
    ''')

    con.commit()

def _app_footer():
    with ui.footer(elevated=True).classes('bg-indigo-700 print-hide p-2'):
        with ui.row().classes('mx-auto items-center justify-center gap-x-3'):
            ui.button('', icon='explore', on_click=lambda: ui.navigate.to('/explore')).props('flat text-color="white"')
            ui.button('', icon='list', on_click=lambda: ui.navigate.to('/trips')).props('flat text-color="white"')
            ui.button('', icon='diversity_1', on_click=lambda: ui.navigate.to('/family')).props('flat text-color="white"')
            ui.button('', icon='settings', on_click=lambda: ui.navigate.to('/settings')).props('flat text-color="white"')

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
    role_input = ui.select(['Parent', 'Child'], label='Role').props('outlined').classes('w-full mb-6')

    async def on_register_click():
        if not all([f.value for f in [email_input, password_input, first_name_input, last_name_input, role_input]]):
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
            
            cur.execute('''INSERT INTO users (user_id, family_id, email, password, first_name, last_name, role, points, established_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                        (user_id, '', email_input.value, bcrypt.hashpw(password_input.value.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'), first_name_input.value, last_name_input.value, role_input.value.lower(), 0, now_iso))
            
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

@ui.page('/family')
async def family_page(request: Request):
    _app_footer()

    session_id = request.cookies.get(SESSION_COOKIE)

    if not await verify_session(session_id):
        ui.label('You need to login first.').classes('text-2xl font-bold mb-6 text-center text-indigo')
        ui.button('Login', on_click=lambda: ui.navigate.to('/login')).classes('w-full')
        return

    user_id = await retrieve_user_id_from_session_id(session_id)

    async def is_admin(): # This helper is fine
        with sqlite3.connect(DATABASE_PATH) as con:
            cur = con.cursor()
            cur.execute('SELECT family_id FROM users WHERE user_id=?', (user_id,))
            family_id_tuple = cur.fetchone()
            if not family_id_tuple or not family_id_tuple[0]:
                return False
            cur.execute('SELECT admin_user_id FROM families WHERE family_id=?', (family_id_tuple[0],))
            admin_id_tuple = cur.fetchone()
            return admin_id_tuple and admin_id_tuple[0] == user_id

    async def create_family():
        with sqlite3.connect(DATABASE_PATH) as con:
            cur = con.cursor()
            cur.execute('SELECT family_id, role FROM users WHERE user_id=?', (user_id,))
            family_id, role = cur.fetchone() or (None, None)

            if family_id and family_id[0]:
                ui.notification('You\'re already in a family.', color='green')
                return
            if role != 'parent':
                ui.notification('Only parents can create a family.', color='red')
                return
            
            with sqlite3.connect(DATABASE_PATH) as con:
                cur = con.cursor()
                family_id = str(uuid4())
                cur.execute('INSERT INTO families (family_id, admin_user_id, adult_ids, child_ids, trip_ids, traits) VALUES (?, ?, ?, ?, ?, ?)',
                            (family_id, user_id, json.dumps([user_id]), json.dumps([]), json.dumps([]), json.dumps([])))
                cur.execute('UPDATE users SET family_id=? WHERE user_id=?',
                            (family_id, user_id))
                con.commit()
                ui.notification('Family created successfully!', color='green')
                ui.timer(0.1, ui.navigate.reload, once=True)
    async def delete_family():
        if not await is_admin():
            # Use the main status_label for the card
            ui.notification('You are not the admin of this family.', color='green')
            return
        with sqlite3.connect(DATABASE_PATH) as con:
            cur = con.cursor()
            cur.execute('SELECT family_id FROM users WHERE user_id=?', (user_id,))
            family_id_tuple = cur.fetchone()
            if not family_id_tuple or not family_id_tuple[0]:
                ui.notification('You\'re not in a family.', color='green')
                return
            family_id_to_delete = family_id_tuple[0]
            cur.execute('DELETE FROM families WHERE family_id=?', (family_id_to_delete,))
            # Set family_id to empty for all users in that family
            cur.execute('UPDATE users SET family_id=? WHERE family_id=?', ('', family_id_to_delete))
            # Delete all trips owned by this family
            cur.execute('DELETE FROM trips WHERE admin_family_id=?', (family_id_to_delete,))
            con.commit()
            ui.notification('Family deleted successfully.', color='green')
            ui.timer(0.1, ui.navigate.reload, once=True)
    
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
            cur.execute('SELECT role FROM users WHERE user_id=?', (user_id,))
            role = cur.fetchone()
            if role and role[0] == 'parent':
                adult_ids = json.loads(family_data[2])
                if user_id not in adult_ids:
                    adult_ids.append(user_id)
                cur.execute('UPDATE families SET adult_ids=? WHERE family_id=?',
                            (json.dumps(adult_ids), family_id_to_join))
            else:
                child_ids = json.loads(family_data[3])
                if user_id not in child_ids:
                    child_ids.append(user_id)
                cur.execute('UPDATE families SET child_ids=? WHERE family_id=?',
                            (json.dumps(child_ids), family_id_to_join))
            con.commit()
            ui.notification('You have joined the family successfully!', color='green')
            ui.timer(0.1, ui.navigate.reload, once=True)
    
    async def leave_family():
        with sqlite3.connect(DATABASE_PATH) as con:
            user_id = await retrieve_user_id_from_session_id(session_id)
            cur = con.cursor()
            cur.execute('SELECT family_id FROM users WHERE user_id=?', (user_id,))
            family_id_tuple = cur.fetchone() # Renamed for clarity
            if not family_id_tuple or not family_id_tuple[0]:
                ui.notification('You are not in a family.', color='red')
                return
            current_family_id = family_id_tuple[0] # Extracted for clarity
            cur.execute('SELECT admin_user_id FROM families WHERE family_id=?', (current_family_id,))
            admin_id_tuple = cur.fetchone() # Renamed
            if admin_id_tuple and admin_id_tuple[0] == user_id:
                ui.notification('You are the admin of the family. You cannot leave. Transfer admin rights or delete the family.', color='red')
                return
            cur.execute('UPDATE users SET family_id=? WHERE user_id=?', ('', user_id))
            cur.execute('SELECT adult_ids, child_ids FROM families WHERE family_id=?', (current_family_id,))
            family_data = cur.fetchone()
            if family_data:
                adult_ids = json.loads(family_data[0])
                child_ids = json.loads(family_data[1])
                if user_id in adult_ids:
                    adult_ids.remove(user_id)
                elif user_id in child_ids:
                    child_ids.remove(user_id)
                # No else needed here as user might already be removed by another process, or not in list
                cur.execute('UPDATE families SET adult_ids=?, child_ids=? WHERE family_id=?',
                            (json.dumps(adult_ids), json.dumps(child_ids), current_family_id))
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
            # Prevent admin from removing themselves
            if user_to_delete_id == current_logged_in_user_id: # which is admin_id_tuple[0]
                ui.notification('Admin cannot remove themselves. Transfer admin rights first or delete the family.', color='red')
                return
            cur.execute('SELECT adult_ids, child_ids FROM families WHERE family_id=?', (current_family_id,))
            family_data = cur.fetchone()
            if family_data:
                adult_ids = json.loads(family_data[0])
                child_ids = json.loads(family_data[1])
                found_and_removed = False
                if user_to_delete_id in adult_ids:
                    adult_ids.remove(user_to_delete_id)
                    found_and_removed = True
                elif user_to_delete_id in child_ids:
                    child_ids.remove(user_to_delete_id)
                    found_and_removed = True
                if not found_and_removed:
                    ui.notification('User not found in the family lists.', color='red')
                    return
                cur.execute('UPDATE families SET adult_ids=?, child_ids=? WHERE family_id=?',
                            (json.dumps(adult_ids), json.dumps(child_ids), current_family_id))
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
                # Fetch new admin's name for a friendlier message
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
        family_id = cur.fetchone()
    if not family_id or not family_id[0]:
        ui.label('You are not part of a family.').classes('text-2xl font-bold mb-6 text-center text-indigo')
        ui.button('Create Family', on_click=create_family, color='indigo').classes('w-full')
        with ui.row():
            family_code_input = ui.input('Family Code', placeholder='Enter family code to join').props('outlined clearable').classes('w-half mb-3')
            ui.button('Join Family', on_click=join_family, color='indigo').classes('w-half')
        return
    else:
        #ui.label('Family')
        with sqlite3.connect(DATABASE_PATH) as con:
            cur = con.cursor()
            cur.execute('SELECT family_id, role FROM users WHERE user_id=?', (user_id,))
            family_id, role = cur.fetchone()
        if not family_id:
            ui.notification('No family found.', color='green')
            return
        #ui.label(f'{family_id} {role}')
        if role == 'parent':
            ui.label(f'Family Management').classes('text-2xl font-bold mb-6 text-center text-indigo')
            with ui.tabs().classes('w-full') as tabs:
                family_dashboard = ui.tab('Dashboard', icon='dashboard')
                common_traits = ui.tab('Common Traits', icon='menu')
            with ui.tab_panels(tabs, value=family_dashboard).classes('w-full'):
                with ui.tab_panel(family_dashboard):
                    if await is_admin():
                        ui.label('You are a parent and the admin of this family.')
                    else:
                        ui.label('You are a parent but not the admin of this family.')
                    ui.button('Refresh', on_click=ui.navigate.reload, color='indigo').classes('w-full')
                    with sqlite3.connect(DATABASE_PATH) as con:
                        cur = con.cursor()
                        cur.execute('SELECT admin_user_id, adult_ids, child_ids FROM families WHERE family_id=?', (family_id,))
                    family_info_row = cur.fetchone()
                    if family_info_row:
                        admin_user_id = family_info_row[0]
                        adult_ids = json.loads(family_info_row[1])
                        child_ids = json.loads(family_info_row[2])
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
                            for member in child_ids:
                                with sqlite3.connect(DATABASE_PATH) as con:
                                    cur = con.cursor()
                                    cur.execute('SELECT user_id, first_name, last_name FROM users WHERE user_id=?', (member,))
                                member_user_data = cur.fetchone()
                                if member_user_data:
                                    with ui.item():
                                        with ui.item_section().props('avatar'):
                                            ui.icon('child_care')
                                        with ui.item_section():
                                            ui.item_label(f'{member_user_data[1]} {member_user_data[2]}')
                                            ui.item_label('Child').props('caption')
                                        if await is_admin() and member_user_data[0] != user_id:
                                            with ui.item_section().props('side'):
                                                ui.button('Remove', on_click=lambda mid=member_user_data[0]: remove_member(mid)).props('flat dense color="red" size=sm')
                    if await is_admin() and member_user_data[0] != user_id:
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
                            traits = cur.fetchone()
                            if traits:
                                traits = json.loads(traits[0])
                                ui.label(f'Traits: {traits}')
                            else:
                                ui.label('No traits found.')
                        names = ['Sports', 'Music', 'Art', 'Reading', 'Writing', 'Cooking', 'Gardening', 'Hiking', 'Camping', 'Fishing', 'Swimming', 'Biking', 'Walking', 'Yoga', 'Meditation', 'Reading', 'Writing', 'Cooking', 'Gardening', 'Hiking', 'Camping', 'Fishing', 'Swimming', 'Biking', 'Walking', 'Yoga', 'Meditation']
                        #ui.select(names, multiple=True, value=names[:2], label='comma-separated') \
                        traits_input = ui.select(names, multiple=True, value=traits, label='comma-separated') \
                            .classes('w-full')
                        
                        with ui.row():
                            ui.button("Reset", on_click=ui.navigate.reload, color='indigo').props('flat')
                            ui.button("Save Changes", on_click=save_traits, color='indigo')
                        ui.label('Because of the way NiceGUI works, the easiest way to make a reset button with ui.select is to reload the page.')
        else:
            ui.label(f'Your Family 🌞').classes('text-2xl font-bold mb-6 text-center text-indigo')
            ui.label('Because you are a child, you cannot see many of the features of the family page.')
            ui.button('Leave Family', on_click=leave_family, color='red').classes('w-full')


@ui.page('/settings')
async def settings_page(request: Request):
    _app_footer()

    session_id = request.cookies.get(SESSION_COOKIE)

    if not await verify_session(session_id):
        ui.label('You need to login first.').classes('text-2xl font-bold mb-6 text-center text-indigo')
        ui.button('Login', on_click=lambda: ui.navigate.to('/login')).classes('w-full bg-indigo text-white py-2 rounded-lg')
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
            role_input = ui.select(['Parent', 'Child'], label='Role').props('outlined clearable').classes('w-full mb-3')

            async def load_general_fields():
                with sqlite3.connect(DATABASE_PATH) as con:
                    cur = con.cursor()
                    cur.execute('SELECT first_name, last_name, email, role FROM users WHERE user_id=?', (user_id,))
                    user = cur.fetchone()

                if not user:
                    ui.label('User not found.').classes('text-2xl font-bold mb-6 text-center text-indigo')
                    return

                first_name_input.value = user[0]
                last_name_input.value = user[1]
                email_input.value = user[2]
                role_input.value = user[3].capitalize()  # Ensure role is capitalized for display

                ui.notification('Fields reset.', color='green')

            await load_general_fields()

            async def save_general_fields():
                if not all([f.value for f in [first_name_input, last_name_input, role_input]]):
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
                    cur.execute('UPDATE users SET first_name=?, last_name=?, role=? WHERE user_id=?',
                                (first_name_input.value, last_name_input.value, role_input.value.lower(), user_id))
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
