
# Save the following as app.py (separate file next to a `static/` folder containing index.html)

from __future__ import annotations
from flask import Flask, request, jsonify, send_from_directory
import secrets
import string
import threading
from collections import Counter

app = Flask(__name__, static_folder='static', static_url_path='')

rooms = {}
lock = threading.Lock()

DECKS = {
    'fibonacci': ["0","1","2","3","5","8","13","20","40","100","?","☕"],
    'powers2':  ["0","1","2","4","8","16","32","64","?","☕"],
    'tshirt':   ["XS","S","M","L","XL","?","☕"],
}

def _id(n=5):
    alphabet = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(n))

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.post('/api/rooms')
def create_room():
    rid = _id()
    with lock:
        rooms[rid] = {
            'deck': 'fibonacci',
            'story': '',
            'revealed': False,
            'users': {},           # user_id -> name
            'votes': {},           # user_id -> str(value)
        }
    return jsonify({'room_id': rid})

@app.post('/api/rooms/<rid>/join')
def join_room(rid):
    name = (request.json or {}).get('name') or 'Guest'
    with lock:
        room = rooms.get(rid)
        if not room:
            return jsonify({'error': 'Room not found'}), 404
        uid = _id(8)
        room['users'][uid] = name
        room['votes'].pop(uid, None)
    return jsonify({'user_id': uid, 'room_id': rid, 'name': name})

@app.get('/api/rooms/<rid>/state')
def room_state(rid):
    with lock:
        room = rooms.get(rid)
        if not room:
            return jsonify({'error': 'Room not found'}), 404
        revealed = room['revealed']
        users = []
        for uid, name in room['users'].items():
            vote = room['votes'].get(uid)
            users.append({
                'user_id': uid,
                'name': name,
                'voted': vote is not None,
                'vote': vote if revealed else None,
            })
        summary = None
        if revealed:
            counts = Counter(v for v in room['votes'].values())
            summary = {k: counts[k] for k in sorted(counts.keys(), key=str)}
        return jsonify({
            'room_id': rid,
            'deck': room['deck'],
            'story': room['story'],
            'revealed': revealed,
            'users': users,
            'votes_summary': summary,
        })

@app.post('/api/rooms/<rid>/vote')
def cast_vote(rid):
    data = request.get_json(force=True, silent=True) or {}
    uid = data.get('user_id')
    value = str(data.get('value'))
    with lock:
        room = rooms.get(rid)
        if not room:
            return jsonify({'error': 'Room not found'}), 404
        if uid not in room['users']:
            return jsonify({'error': 'User not in room'}), 400
        # Free-form values allowed, but if you want to restrict to deck, uncomment below
        # if value not in DECKS.get(room['deck'], []):
        #     return jsonify({'error': 'Invalid card value for current deck'}), 400
        room['votes'][uid] = value
    return jsonify({'ok': True})

@app.post('/api/rooms/<rid>/reveal')
def reveal(rid):
    with lock:
        room = rooms.get(rid)
        if not room:
            return jsonify({'error': 'Room not found'}), 404
        room['revealed'] = True
    return jsonify({'ok': True})

@app.post('/api/rooms/<rid>/reset')
def reset(rid):
    with lock:
        room = rooms.get(rid)
        if not room:
            return jsonify({'error': 'Room not found'}), 404
        room['revealed'] = False
        room['votes'] = {}
    return jsonify({'ok': True})

@app.post('/api/rooms/<rid>/deck')
def set_deck(rid):
    data = request.get_json(force=True, silent=True) or {}
    deck = data.get('deck')
    if deck not in DECKS:
        return jsonify({'error': 'Unknown deck'}), 400
    with lock:
        room = rooms.get(rid)
        if not room:
            return jsonify({'error': 'Room not found'}), 404
        room['deck'] = deck
    return jsonify({'ok': True, 'deck': deck})

@app.post('/api/rooms/<rid>/story')
def set_story(rid):
    data = request.get_json(force=True, silent=True) or {}
    story = (data.get('story') or '').strip()
    with lock:
        room = rooms.get(rid)
        if not room:
            return jsonify({'error': 'Room not found'}), 404
        room['story'] = story
    return jsonify({'ok': True})

if __name__ == '__main__':
    #url = 'http://127.0.0.1:3000'
    #webbrowser.open_new(url)
    #app.run()
    app.run(host='127.0.0.1', port=3000, debug=False)


