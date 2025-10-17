from flask import Blueprint, jsonify, request
from sqlalchemy import func
from src.models.note import Note, db

note_bp = Blueprint('note', __name__)

@note_bp.route('/notes', methods=['GET'])
def get_notes():
    """Get all notes, ordered by most recently updated"""
    notes = Note.query.order_by(Note.position.asc(), Note.updated_at.desc()).all()
    return jsonify([note.to_dict() for note in notes])

@note_bp.route('/notes', methods=['POST'])
def create_note():
    """Create a new note"""
    try:
        data = request.json
        if not data or 'title' not in data or 'content' not in data:
            return jsonify({'error': 'Title and content are required'}), 400
        
        max_position = db.session.query(func.max(Note.position)).scalar()
        next_position = (max_position + 1) if max_position is not None else 0

        note = Note(title=data['title'], content=data['content'], position=next_position)
        db.session.add(note)
        db.session.commit()
        return jsonify(note.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@note_bp.route('/notes/<int:note_id>', methods=['GET'])
def get_note(note_id):
    """Get a specific note by ID"""
    note = Note.query.get_or_404(note_id)
    return jsonify(note.to_dict())

@note_bp.route('/notes/<int:note_id>', methods=['PUT'])
def update_note(note_id):
    """Update a specific note"""
    try:
        note = Note.query.get_or_404(note_id)
        data = request.json
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        note.title = data.get('title', note.title)
        note.content = data.get('content', note.content)
        if 'position' in data and isinstance(data['position'], int):
            note.position = data['position']
        db.session.commit()
        return jsonify(note.to_dict())
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@note_bp.route('/notes/<int:note_id>', methods=['DELETE'])
def delete_note(note_id):
    """Delete a specific note"""
    try:
        note = Note.query.get_or_404(note_id)
        db.session.delete(note)
        db.session.commit()
        return '', 204
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@note_bp.route('/notes/search', methods=['GET'])
def search_notes():
    """Search notes by title or content"""
    query = request.args.get('q', '')
    if not query:
        return jsonify([])
    
    notes = Note.query.filter(
        (Note.title.contains(query)) | (Note.content.contains(query))
    ).order_by(Note.position.asc(), Note.updated_at.desc()).all()
    
    return jsonify([note.to_dict() for note in notes])

@note_bp.route('/notes/reorder', methods=['PATCH'])
def reorder_notes():
    """Reorder notes based on provided ID sequence"""
    data = request.json
    if not data or 'order' not in data or not isinstance(data['order'], list):
        return jsonify({'error': 'Request body must include an \"order\" list'}), 400

    order = data['order']
    if len(order) == 0:
        return jsonify({'error': 'Order list cannot be empty'}), 400

    notes = Note.query.filter(Note.id.in_(order)).all()
    if len(notes) != len(order):
        return jsonify({'error': 'One or more note IDs are invalid'}), 400

    position_map = {note_id: idx for idx, note_id in enumerate(order)}
    try:
        for note in notes:
            note.position = position_map[note.id]
        db.session.commit()
        return jsonify({'status': 'success'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
