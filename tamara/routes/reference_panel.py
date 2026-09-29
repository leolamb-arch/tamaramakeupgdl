"""Cookie-authenticated compatibility API for the reference administration UI."""
import json
import secrets
import time
from datetime import date
from flask import Blueprint, abort, current_app, g, jsonify, request
from ..database import db
from ..services import reference_panel as panel
from ..services.images import decode_image
from ..services import storage

bp = Blueprint('reference_panel', __name__)

def upload(file, c):
    raw=file.read(8*1024*1024+1)
    if len(raw)>8*1024*1024:abort(413,description='Máximo 8 MB por imagen.')
    image=decode_image(raw)
    name=secrets.token_hex(16)+'.webp'
    width,height=storage.save_pair(image,name)
    c.execute('INSERT INTO media VALUES(?,?,?,?,?)',(name,time.time(),g.session['user'],width,height))
    return '/media/'+name

def body(c):
    if request.is_json:
        value=request.get_json()
        if not isinstance(value,dict):abort(400,description='Datos inválidos.')
        return value
    if request.mimetype!='multipart/form-data':abort(415,description='Formato no admitido.')
    value=request.form.to_dict()
    for key in ('includes','data'):
        if key in value:value[key]=json.loads(value[key])
    for key in ('price_amount','cover_index','sort_order'):
        if key in value:value[key]=float(value[key]) if key=='price_amount' else int(value[key])
    if 'active' in value:value['active']=value['active']=='true'
    if 'slug' in value or 'images' in request.form or 'images' in request.files:
        value['images']=request.form.getlist('images')+[upload(f,c) for f in request.files.getlist('images')]
    for key in ('logo','hero_image'):
        if key in request.files:value[key]=upload(request.files[key],c)
    return value

@bp.get('/api/admin/reference/<collection>')
def listing(collection):
    if collection not in panel.COLLECTIONS:abort(404)
    with db() as c:rows=panel.records(c,collection)
    if collection=='services':rows.sort(key=lambda r:r.get('sort_order',0))
    if collection=='bookings':rows.sort(key=lambda r:(r.get('event_date',''),r.get('event_time','')),reverse=True)
    return jsonify(rows)

@bp.route('/api/admin/reference/<collection>',methods=['POST'])
@bp.route('/api/admin/reference/<collection>/<identity>',methods=['POST','DELETE'])
def save(collection,identity=None):
    if collection not in panel.COLLECTIONS:abort(404)
    if collection=='bookings' and not identity:abort(405)
    try:
        with db() as c:
            c.execute('BEGIN IMMEDIATE')
            previous=panel.record(c,collection,identity) if identity else {}
            if identity and request.headers.get('X-Record-Version')!=str(previous['_version']):
                abort(409,description='Este registro cambió en otra pestaña. Vuelve a abrir el apartado antes de guardar.')
            identity=identity or secrets.token_hex(8)
            if collection!='services' and not previous and panel.records(c,collection):abort(409,description='La configuración ya existe. Recarga el panel.')
            c.execute('INSERT INTO panel_history(created,user,collection,record_id,previous) VALUES(?,?,?,?,?)',(time.time(),g.session['user'],collection,identity,json.dumps(previous,ensure_ascii=False)))
            if request.method=='DELETE':
                if collection!='services':abort(405)
                c.execute('DELETE FROM panel_records WHERE collection=? AND id=?',(collection,identity))
                panel.apply_public(c,collection,previous,{})
                return jsonify(ok=True)
            incoming=body(c)
            if collection=='bookings' and (set(incoming)-{'exported_google','exported_apple'} or any(type(v) is not bool for v in incoming.values())):
                abort(400,description='Solo se permite actualizar la marca de exportación.')
            clean={k:v for k,v in previous.items() if k not in ('id','_version')}
            clean.update(incoming)
            clean.pop('enabled',None)
            clean=panel.validate_record(collection,clean,c,identity)
            if collection=='schedule_config':clean['enabled']=True
            elif previous.get('enabled'):clean['enabled']=previous['enabled']
            panel.put(c,collection,identity,clean,previous.get('_version',0)+1)
            result=panel.record(c,collection,identity)
            panel.apply_public(c,collection,previous,result)
            return jsonify(result)
    except (ValueError,TypeError,KeyError,AttributeError) as e:
        abort(400,description=str(e) if isinstance(e,ValueError) else 'Revisa los datos del formulario.')

@bp.get('/api/admin/reference-tools/google/status')
def google_status():
    # OAuth is also disabled on the reference deployment. Never claim a connection
    # or accept tokens without an implemented callback and token verification.
    return jsonify(configured=False,connected=False,account='')

@bp.post('/api/admin/reference-tools/google/disconnect')
def google_disconnect():
    return jsonify(error='No hay una conexión de Google Calendar configurada.'),409

@bp.post('/api/admin/reference-tools/schedule/delete-booking')
def delete_booking():
    value=request.get_json()
    if not isinstance(value,dict) or value.get('mode') not in ('free','keep'):abort(400,description='Selecciona si deseas liberar o bloquear el horario.')
    with db() as c:
        c.execute('BEGIN IMMEDIATE')
        booking=panel.record(c,'bookings',value.get('bookingId',''))
        c.execute('INSERT INTO panel_history(created,user,collection,record_id,previous) VALUES(?,?,?,?,?)',(time.time(),g.session['user'],'bookings',booking['id'],json.dumps(booking,ensure_ascii=False)))
        if value['mode']=='keep':
            schedule=panel.record(c,'schedule_config','schedule')
            start=panel.minutes(booking['event_time']);end=start+int(booking.get('duration_minutes',schedule['appointment_duration']))
            blocked=schedule['blocked_slots']
            for minute in range(max(0,start-schedule['appointment_duration']+1),min(1440,end)):
                slot=dict(date=booking['event_date'],time=f'{minute//60:02}:{minute%60:02}')
                if slot not in blocked:blocked.append(slot)
            panel.put(c,'schedule_config','schedule',schedule,schedule['_version']+1)
        c.execute('DELETE FROM panel_records WHERE collection=? AND id=?',('bookings',booking['id']))
    return jsonify(ok=True)

@bp.get('/api/schedule/availability')
def availability():
    try:
        day=request.args.get('date','')
        date.fromisoformat(day)
        with db() as c:return jsonify(slots=panel.slots(c,day),timezone='America/Mexico_City')
    except (ValueError,TypeError):abort(400,description='Fecha inválida.')
