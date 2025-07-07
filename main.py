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

def _update_status_label(label: ui.label, text: str, is_success: bool):
    label.set_text(text)
    if is_success:
        label.classes(remove='text-red-500', add='text-green-600')
    else:
        label.classes(remove='text-green-600', add='text-red-500')

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
        ui.button('Go to trips', on_click=lambda: ui.navigate.to('/trips')).classes('w-full bg-primary text-white py-2 rounded-lg')
        return
    
    ui.label('Register').classes('text-2xl font-bold mb-6 text-center text-indigo')

    email_input = ui.input('Email').props('type=email outlined clearable').classes('w-full mb-3')
    password_input = ui.input('Password', password=True, password_toggle_button=True).props('outlined clearable').classes('w-full mb-3')
    first_name_input = ui.input('First Name').props('outlined clearable').classes('w-full mb-3')
    last_name_input = ui.input('Last Name').props('outlined clearable').classes('w-full mb-3')
    role_input = ui.select(['Parent', 'Child'], label='Role').props('outlined').classes('w-full mb-6')

    status_label = ui.label().classes('text-center w-full min-h-[20px] mb-3')

    async def on_register_click():
        if not all([f.value for f in [email_input, password_input, first_name_input, last_name_input, role_input]]):
            _update_status_label(status_label, 'All fields are required.', is_success=False)
            return
        
        if len(password_input.value) < 6:
            _update_status_label(status_label, 'Password must be at least 6 characters.', is_success=False)
            return
        
        with sqlite3.connect(DATABASE_PATH) as con:
            cur = con.cursor()
            _update_status_label(status_label, 'Working on it...', is_success=True)

            cur.execute('SELECT 1 FROM users WHERE email=?', (email_input.value,))
            if cur.fetchone():
                _update_status_label(status_label, 'Email already exists.', is_success=False)
                return
            user_id = str(uuid4())
            now_iso = datetime.now(timezone.utc).isoformat()
            
            cur.execute('''INSERT INTO users (user_id, family_id, email, password, first_name, last_name, role, points, established_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                        (user_id, '', email_input.value, bcrypt.hashpw(password_input.value.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'), first_name_input.value, last_name_input.value, role_input.value.lower(), 0, now_iso))
            
            _update_status_label(status_label, 'Registration successful! Creating session...', is_success=True)

            ui.navigate.to('/_create_session?user_id=' + user_id)
    
    ui.button('Register', on_click=on_register_click, color='indigo').classes('w-full bg-primary text-white py-2 rounded-lg')
    ui.button('Already have an account? Login', on_click=lambda: ui.navigate.to('/login'), color='indigo').props('flat dense').classes('w-full mt-3 text-primary')

@ui.page('/login')
async def login_page(request: Request):
    session_id = request.cookies.get(SESSION_COOKIE)

    if await verify_session(session_id) != False:
        ui.label('There\'s no need to login. You are already logged in.').classes('text-2xl font-bold mb-6 text-center text-primary')
        ui.button('Go to trips', on_click=lambda: ui.navigate.to('/trips')).classes('w-full bg-primary text-white py-2 rounded-lg')
        return
    
    ui.label('Login').classes('text-2xl font-bold mb-6 text-center text-indigo')

    email_input = ui.input('Email').props('type=email outlined clearable').classes('w-full mb-3')
    password_input = ui.input('Password', password=True, password_toggle_button=True).props('outlined clearable').classes('w-full mb-3')
    status_label = ui.label().classes('text-center w-full min-h-[20px] mb-3')

    async def on_login_click():
        if not all([f.value for f in [email_input, password_input]]):
            _update_status_label(status_label, 'All fields are required.', is_success=False)
            return
        
        with sqlite3.connect(DATABASE_PATH) as con:
            cur = con.cursor()

            _update_status_label(status_label, 'Working on it...', is_success=True)

            cur.execute('SELECT user_id, password FROM users WHERE email=?', (email_input.value,))
            user = cur.fetchone()

            if user and bcrypt.checkpw(password_input.value.encode('utf-8'), user[1].encode('utf-8')):
                user_id = user[0]
                ui.navigate.to('/_create_session?user_id=' + user_id)

                _update_status_label(status_label, 'Logged In Successfully!', is_success=True)
            else:
                _update_status_label(status_label, 'Invalid email or password.', is_success=False)
    
    ui.button('Login', on_click=on_login_click, color='indigo').classes('w-full bg-indigo text-white py-2 rounded-lg')
    ui.button('Don\'t have an account? Register', on_click=lambda: ui.navigate.to('/register')).props('flat dense').classes('w-full mt-3 text-indigo')

@ui.page('/family')
async def family_page(request: Request):
    _app_footer()

    session_id = request.cookies.get(SESSION_COOKIE)

    if not await verify_session(session_id):
        ui.label('You need to login first.').classes('text-2xl font-bold mb-6 text-center text-indigo')
        ui.button('Login', on_click=lambda: ui.navigate.to('/login')).classes('w-full bg-indigo text-white py-2 rounded-lg')
        return

    user_id = await retrieve_user_id_from_session_id(session_id)

    async def create_family():
        with sqlite3.connect(DATABASE_PATH) as con:
            cur = con.cursor()
            cur.execute('SELECT family_id, role FROM users WHERE user_id=?', (user_id,))
            family_id, role = cur.fetchone() or (None, None)

            if family_id and family_id[0]:
                _update_status_label(status_label, 'You are already part of a family.', is_success=False)
                return
            if role != 'parent':
                _update_status_label(status_label, 'Only parents can create a family.', is_success=False)
                return
            
            family_id = str(uuid4())
            

    with sqlite3.connect(DATABASE_PATH) as con:
        cur = con.cursor()
        cur.execute('SELECT family_id FROM users WHERE user_id=?', (user_id,))
        family_id = cur.fetchone()
        if not family_id or not family_id[0]:
            ui.label('You are not part of a family.').classes('text-2xl font-bold mb-6 text-center text-indigo')
            ui.button('Create Family', on_click=create_family).classes('w-full bg-indigo text-white py-2 rounded-lg')
            with ui.row():
                ui.input('Family Code', placeholder='Enter family code to join').props('outlined clearable').classes('w-half mb-3')
                ui.button('Join Family', on_click=lambda: ui.navigate.to('/join_family')).classes('w-half bg-indigo text-white py-2 rounded-lg')
            status_label = ui.label().classes('text-center w-full min-h-[20px] mb-3')
            return
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

            status_label = ui.label().classes('text-center w-full min-h-[20px] mb-3')

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

            await load_general_fields()

            async def save_general_fields():
                if not all([f.value for f in [first_name_input, last_name_input, role_input]]):
                    _update_status_label(status_label, 'All fields are required.', is_success=False)
                    return

                with sqlite3.connect(DATABASE_PATH) as con: # Make sure user isn't already in a family.
                    cur = con.cursor() # Make sure user isn't already in a family.
                    cur.execute(' SELECT family_id FROM users WHERE user_id=?', (user_id,))
                    family_id = cur.fetchone()
                    if family_id and family_id[0] != '':
                        _update_status_label(status_label, 'You are in a family. Please leave the family before changing your general settings.', is_success=False)
                        return

                with sqlite3.connect(DATABASE_PATH) as con:
                    _update_status_label(status_label, 'Working on it...', is_success=True)
                    cur = con.cursor()
                    cur.execute('UPDATE users SET first_name=?, last_name=?, role=? WHERE user_id=?',
                                (first_name_input.value, last_name_input.value, role_input.value.lower(), user_id))
                    con.commit()
                    _update_status_label(status_label, 'Updated Successfully!', is_success=True)
            
            with ui.row():
                ui.button("Reset", on_click=load_general_fields, color='indigo').props('flat')
                ui.button("Save Changes", on_click=save_general_fields, color='indigo')
        with ui.tab_panel(security_tab):
            old_password_input = ui.input('Old Password', password=True, password_toggle_button=True).props('outlined clearable').classes('w-full mb-3')
            new_password_input = ui.input('New Password', password=True, password_toggle_button=True).props('outlined clearable').classes('w-full mb-3')
            confirm_new_password_input = ui.input('Confirm New Password', password=True, password_toggle_button=True).props('outlined clearable').classes('w-full mb-6')

            status_label = ui.label().classes('text-center w-full min-h-[20px] mb-3')

            async def load_security_fields():
                old_password_input.value = ''
                new_password_input.value = ''
                confirm_new_password_input.value = ''
                _update_status_label(status_label, 'Fields reset.', is_success=True)
            async def save_security_fields():
                if not all([f.value for f in [old_password_input, new_password_input, confirm_new_password_input]]): # Check if all fields are filled in.
                    _update_status_label(status_label, 'All fields are required.', is_success=False)
                    return
                if new_password_input.value != confirm_new_password_input.value: # Check if new password and confirm new password match.
                    _update_status_label(status_label, 'New passwords do not match.', is_success=False)
                    return
                if len(new_password_input.value) < 6: # Check if new password is at least 6 characters long. Not the standard, which would be 8, but this is a family app.
                    _update_status_label(status_label, 'New password must be at least 6 characters.', is_success=False)
                    return
                with sqlite3.connect(DATABASE_PATH) as con:
                    cur = con.cursor()
                    cur.execute('SELECT password FROM users WHERE user_id=?', (user_id,))
                    result = cur.fetchone()
                    if not result or not bcrypt.checkpw(old_password_input.value.encode('utf-8'), result[0].encode('utf-8')):
                        _update_status_label(status_label, 'Old password is incorrect.', is_success=False)
                        return
                    
                    hashed_new_password = bcrypt.hashpw(new_password_input.value.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                    cur.execute('UPDATE users SET password=? WHERE user_id=?', (hashed_new_password, user_id))
                    con.commit()
                    _update_status_label(status_label, 'Password updated successfully!', is_success=True)
            with ui.row():
                ui.button("Reset", on_click=load_general_fields, color='indigo').props('flat')
                ui.button("Save Changes", on_click=save_general_fields, color='indigo')
    ui.button('Logout', on_click=lambda: ui.navigate.to('/_delete_session')).classes('w-full bg-indigo text-white py-2 rounded-lg')
ui.run(title='Careavan', favicon="🚗", port=8080)
