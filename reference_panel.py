"""Translate the original panel's records into the existing local CMS schema.

Reference records retain fields absent from the old CMS. Initial migration reads
the local content only: it never imports production photographs or bookings.
"""
import colorsys
import copy
import json
import re
import secrets
import time
from datetime import date, datetime, timedelta
from flask import abort, current_app, g
from ..config import ROOT
from ..database import db
from ..validation import text, number

REFERENCE = json.loads((ROOT / 'content/reference-defaults.json').read_text(encoding='utf-8'))
TEXT_MAP = dict(zip(
    ['city','name','heroTitleSuffix','tagline','heroButtonPrimary','heroButtonSecondary','heroSubtext','instagramHandle','servicesLabel','servicesTitle','servicesDescription','quoteLabel','quoteTitle','quoteDescription','contactLabel','contactTitle','coverage','testimonialsTitle','footerNote'],
    ['t008','t009','t010','t011','t012','t013','t014','t015','t016','t017','t018','t028','t029','t030','t079','t080','t081','t086','t100']))
CALC_MAP = dict(zip(['sectionLabel','title','description','counterLabel','counterNote','addonsLabel','breakdownLabel','button'],['t064','t065','t066','t067','t068','t072','t077','t078']))
QUIZ_MAP = dict(zip(['sectionLabel','title','description','button','noteIncomplete'],['t019','t020','t021','t026','t027']))
SCHEDULE = dict(active_days=[1,2,3,4,5,6], time_blocks=[dict(start='09:00',end='19:00')], appointment_duration=60, breaks=[], blocked_dates=[], blocked_slots=[])
COLLECTIONS = {'site_content','services','appearance','schedule_config','bookings'}

def hex_hsl(value):
    r,g,b = [int(value[i:i+2],16)/255 for i in (1,3,5)]
    h,l,s = colorsys.rgb_to_hls(r,g,b)
    return f'{h*360:.3f} {s*100:.3f}% {l*100:.3f}%'

def hsl_hex(value):
    match = re.fullmatch(r'(\d+(?:\.\d+)?) (\d+(?:\.\d+)?)% (\d+(?:\.\d+)?)%', value)
    if not match: raise ValueError('Color inválido.')
    h,s,l = map(float,match.groups())
    if h>360 or s>100 or l>100: raise ValueError('Color inválido.')
    rgb = colorsys.hls_to_rgb(h/360,l/100,s/100)
    return '#' + ''.join(f'{round(v*255):02x}' for v in rgb)

def record(c, collection, identity):
    row=c.execute('SELECT * FROM panel_records WHERE collection=? AND id=?',(collection,identity)).fetchone()
    if not row: abort(404,description='Registro no encontrado.')
    return {**json.loads(row['data']), 'id':identity, '_version':row['version']}

def records(c, collection):
    rows=c.execute('SELECT id FROM panel_records WHERE collection=? ORDER BY rowid',(collection,)).fetchall()
    return [record(c,collection,row['id']) for row in rows]

def put(c, collection, identity, data, version=1):
    packed=json.dumps({k:v for k,v in data.items() if k not in ('id','_version')},ensure_ascii=False)
    c.execute('INSERT INTO panel_records VALUES(?,?,?,?) ON CONFLICT(collection,id) DO UPDATE SET data=excluded.data,version=excluded.version',(collection,identity,packed,version))

def initialize(app):
    with app.app_context(), db() as c:
        c.executescript('''CREATE TABLE IF NOT EXISTS panel_records(collection TEXT NOT NULL,id TEXT NOT NULL,data TEXT NOT NULL,version INTEGER NOT NULL,PRIMARY KEY(collection,id));
        CREATE TABLE IF NOT EXISTS panel_history(id INTEGER PRIMARY KEY,created REAL NOT NULL,user TEXT NOT NULL,collection TEXT NOT NULL,record_id TEXT NOT NULL,previous TEXT NOT NULL);''')
        if c.execute('SELECT 1 FROM panel_records LIMIT 1').fetchone(): return
        data=json.loads(c.execute('SELECT published FROM state WHERE id=1').fetchone()[0])
        site=copy.deepcopy(REFERENCE['rr'])
        site.update({k:data['texts'][v] for k,v in TEXT_MAP.items()})
        site['whatsapp']=data['settings']['whatsapp']
        site['socials']={k:data['settings'][k] for k in ('instagram','facebook','tiktok')}
        site['socials']['whatsapp']='https://wa.me/'+data['settings']['contactWhatsapp']
        site['calculator']=copy.deepcopy(REFERENCE['Nt'])
        site['calculator'].update(basePrice=data['settings']['base'],perPerson=data['settings']['companion'])
        site['calculator']['addons'][0]['price']=data['settings']['hair']
        site['calculator']['addons'][1]['price']=data['settings']['trial']
        site['calculator']['texts'].update({k:data['texts'][v] for k,v in CALC_MAP.items()})
        site['quiz']=dict(questions=copy.deepcopy(REFERENCE['zd']),extrasNote=copy.deepcopy(REFERENCE['$d']),texts=copy.deepcopy(REFERENCE['Vd']))
        site['quiz']['texts'].update({k:data['texts'][v] for k,v in QUIZ_MAP.items()})
        for i,t in enumerate(site['testimonials']):
            t['name']=data['texts'][f't{88+i*3:03}'];t['event']=data['texts'][f't{89+i*3:03}']
            key=['assets/testimonio-mariana.svg','assets/testimonio-fernanda.svg','assets/testimonio-alejandra.svg'][i]
            t['photo']='/'+data['images'][key]['src'].lstrip('/')
        put(c,'site_content','site',{'data':site})
        appearance=copy.deepcopy(REFERENCE['yr'])
        appearance.update(titleFont=data['theme']['heading'],bodyFont='Modern' if data['theme']['font']=='Outfit' else data['theme']['font'])
        appearance['colors']={k:hex_hsl(data['theme'].get(k,data['theme']['primary'])) for k in appearance['colors']}
        put(c,'appearance','appearance',dict(data=appearance,logo='/'+data['images']['assets/logo-placeholder.svg']['src'].lstrip('/'),hero_image='/'+data['images']['assets/portada-retrato.svg']['src'].lstrip('/'),logo_alt=data['images']['assets/logo-placeholder.svg']['alt'],hero_image_alt=data['images']['assets/portada-retrato.svg']['alt']))
        put(c,'schedule_config','schedule',SCHEDULE)
        for i,s in enumerate(data['services']):
            value=copy.deepcopy(s)
            value['images']=['/'+data['images'][key]['src'].lstrip('/') for key in s['images']]
            value.update(active=s['status']=='visible',sort_order=i)
            value.pop('status',None)
            put(c,'services',s['slug'],value)

def plain_tree(value, depth=0):
    if depth>12: raise ValueError('Configuración demasiado anidada.')
    if isinstance(value,str): return text(value,12000)
    if value is None or isinstance(value,bool): return value
    if isinstance(value,(int,float)): return number(value,10000000)
    if isinstance(value,list) and len(value)<=1000: return [plain_tree(v,depth+1) for v in value]
    if isinstance(value,dict) and len(value)<=200:
        return {text(k,100):plain_tree(v,depth+1) for k,v in value.items() if k not in ('__proto__','constructor','prototype')}
    raise ValueError('Datos de configuración inválidos.')

def validate_schedule(value):
    if set(value)-set(SCHEDULE): raise ValueError('Campo de agenda desconocido.')
    value={**copy.deepcopy(SCHEDULE),**value}
    if not isinstance(value['active_days'],list) or any(type(v) is not int or not 0<=v<=6 for v in value['active_days']): raise ValueError('Días inválidos.')
    duration=value['appointment_duration']
    if type(duration) is not int or not 5<=duration<=720: raise ValueError('La duración debe estar entre 5 y 720 minutos.')
    for key in ('time_blocks','breaks'):
        spans=[]
        for item in value[key]:
            start=minutes(item['start']); end=minutes(item['end'])
            if end<=start: raise ValueError('La hora final debe ser posterior a la inicial.')
            if key=='time_blocks' and any(start<b and end>a for a,b in spans): raise ValueError('Los bloques de horario no deben superponerse.')
            spans.append((start,end))
    for day in value['blocked_dates']: date.fromisoformat(day)
    for slot in value['blocked_slots']: date.fromisoformat(slot['date']); minutes(slot['time'])
    return value

def minutes(value):
    if not isinstance(value,str) or not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d',value): raise ValueError('Hora inválida.')
    h,m=map(int,value.split(':'));return h*60+m

def validate_record(collection, value, c, identity):
    value=plain_tree(value)
    if collection=='schedule_config': return validate_schedule(value)
    if collection=='services':
        if not value.get('name','').strip() or not re.fullmatch('[a-z0-9-]{1,60}',value.get('slug','')): raise ValueError('Escribe un nombre y un identificador único en minúsculas, sin espacios.')
        if any(s['id']!=identity and s['slug']==value['slug'] for s in records(c,'services')): raise ValueError('El identificador ya existe.')
        number(value.get('price_amount',0))
        if type(value.get('active')) is not bool: raise ValueError('Estado inválido.')
        for path in value.get('images',[]): local_image(path,c)
        if not isinstance(value.get('includes',[]),list): raise ValueError('Incluye debe ser una lista.')
        if not 0<=value.get('cover_index',0)<max(1,len(value.get('images',[]))): raise ValueError('Portada inválida.')
    if collection=='appearance':
        data=value.get('data',{})
        for color in data.get('colors',{}).values(): hsl_hex(color)
        for key in ('titleFont','bodyFont'):
            if data.get(key) not in FONT_NAMES: raise ValueError('Fuente inválida.')
        for key in ('logo','hero_image'):
            if value.get(key):local_image(value[key],c)
    if collection=='site_content':
        site=value.get('data')
        if not isinstance(site,dict): raise ValueError('Contenido inválido.')
        for url in site.get('socials',{}).values():
            if url and not re.fullmatch(r'https://[^\s<>]+',url): raise ValueError('Usa enlaces HTTPS.')
        if site.get('whatsapp') and not re.fullmatch(r'\d{8,15}',site['whatsapp']):raise ValueError('WhatsApp necesita entre 8 y 15 dígitos.')
        for item in site.get('testimonials',[]):
            if item.get('photo'):local_image(item['photo'],c)
            if type(item.get('rating')) is not int or not 1<=item['rating']<=5:raise ValueError('La valoración debe estar entre 1 y 5.')
        calc=site.get('calculator',{})
        for key in ('basePrice','perPerson'):
            amount=calc.get(key,0)
            if isinstance(amount,str):amount=float(amount)
            calc[key]=number(amount)
        for a in calc.get('addons',[]):number(a.get('price',0))
        for q in site.get('quiz',{}).get('questions',[]):
            if not q.get('question','').strip():raise ValueError('Todas las preguntas necesitan texto.')
            if not q.get('options'):raise ValueError('Cada pregunta necesita opciones.')
        loc=site.get('locationConfig',{})
        if loc and (not loc.get('studio',{}).get('address','').strip() or not any(f.get('required') for f in loc.get('external',{}).get('fields',[]))):raise ValueError('Escribe la dirección del estudio y al menos un campo obligatorio.')
    return value

FONT_NAMES={'Outfit','Georgia','Arial','system-ui','Cormorant Garamond','Jost','Playfair Display','Bodoni Moda','Prata','Marcellus','DM Serif Display','Lora','Modern','Pinyon Script','Montserrat','Raleway','Work Sans','Nunito Sans','Inter','Open Sans','Poppins','Roboto','Lato'}

def local_image(path,c):
    path='/'+path.lstrip('/')
    if path.startswith('/assets/'):
        target=(ROOT/'static'/path.lstrip('/')).resolve()
        if target.is_relative_to((ROOT/'static/assets').resolve()) and target.is_file():return path
    if re.fullmatch(r'/media/[a-f0-9]{32}\.webp',path) and c.execute('SELECT 1 FROM media WHERE id=?',(path.split('/')[-1],)).fetchone():return path
    raise ValueError('Usa una imagen de la biblioteca local. No se descargan fotografías externas.')

def apply_public(c, collection, old, new):
    """Only propagate edited values; never overwrite pre-existing drafts on migration."""
    if collection not in ('site_content','services','appearance'):return
    row=c.execute('SELECT * FROM state WHERE id=1').fetchone()
    data=json.loads(row['published'])
    if collection=='site_content':
        before=old.get('data',{});after=new.get('data',{})
        enabled=set(old.get('enabled',[]))
        for key in ('calculator','quiz','locationConfig','testimonials','socials','email','whatsappDisplay'):
            if before.get(key)!=after.get(key):enabled.add(key)
        new['enabled']=sorted(enabled)
        panel_version=new.get('_version',1)
        put(c,collection,new['id'],new,panel_version)
        for k,v in TEXT_MAP.items():
            if after.get(k)!=before.get(k):data['texts'][v]=after.get(k,'')
        if after.get('whatsapp')!=before.get('whatsapp'):data['settings']['whatsapp']=after.get('whatsapp','')
        for k in ('instagram','facebook','tiktok'):
            if after.get('socials',{}).get(k)!=before.get('socials',{}).get(k):data['settings'][k]=after.get('socials',{}).get(k,'')
        contact=after.get('socials',{}).get('whatsapp','')
        if contact!=before.get('socials',{}).get('whatsapp',''):
            match=re.fullmatch(r'https://wa\.me/(\d{8,15})(?:\?.*)?',contact)
            if contact and not match:raise ValueError('El enlace de WhatsApp debe usar https://wa.me/ seguido del número.')
            data['settings']['contactWhatsapp']=match.group(1) if match else ''
        for section,mapping in [('calculator',CALC_MAP),('quiz',QUIZ_MAP)]:
            a=after.get(section,{}).get('texts',{});b=before.get(section,{}).get('texts',{})
            for k,v in mapping.items():
                if a.get(k)!=b.get(k):data['texts'][v]=a.get(k,'')
        calc=after.get('calculator',{})
        if calc!=before.get('calculator',{}):
            data['settings']['base']=calc.get('basePrice',3500);data['settings']['companion']=calc.get('perPerson',800)
            for addon in calc.get('addons',[]):
                if addon['id'] in ('peinado','prueba'):data['settings']['hair' if addon['id']=='peinado' else 'trial']=addon['price']
    if collection=='services':
        existing={s['slug']:s for s in data['services']}
        result=[]
        for item in sorted(records(c,'services'),key=lambda s:s.get('sort_order',0)):
            service={k:item.get(k,'') for k in ('slug','name','short','description','duration','price')}
            service.update(price_amount=item.get('price_amount',0),includes=item.get('includes',[]),status='visible' if item.get('active') else 'hidden',cover_index=item.get('cover_index',0),images=[])
            for path in item.get('images',[]):
                key=next((k for k,v in data['images'].items() if '/'+v['src'].lstrip('/')==path),path)
                if key not in data['images']:data['images'][key]=dict(src=path,alt=item['name'],x=50,y=50)
                service['images'].append(key)
            previous=existing.get(old.get('slug') if item['id']==new.get('id') else item['slug'],{})
            if previous.get('quiz_slug'):service['quiz_slug']=previous['quiz_slug']
            result.append(service)
        data['services']=result
    if collection=='appearance':
        new['enabled']=True
        put(c,collection,new['id'],new,new.get('_version',1))
        a=new.get('data',{});b=old.get('data',{})
        for k,v in a.get('colors',{}).items():
            if k in data['theme'] and v!=b.get('colors',{}).get(k):data['theme'][k]=hsl_hex(v)
        for k,v in [('titleFont','heading'),('bodyFont','font')]:
            if a.get(k)!=b.get(k):data['theme'][v]='Outfit' if a.get(k)=='Modern' else a.get(k,'Georgia')
        for key,imagekey,alt in [('logo','assets/logo-placeholder.svg','logo_alt'),('hero_image','assets/portada-retrato.svg','hero_image_alt')]:
            if new.get(key)!=old.get(key):data['images'][imagekey]['src']=new.get(key) or imagekey
            if new.get(alt)!=old.get(alt):data['images'][imagekey]['alt']=new.get(alt,'')
    packed=json.dumps(data,ensure_ascii=False)
    # Preserve the old draft in history before saving the reference panel directly.
    c.execute('INSERT INTO history(created,user,action,content) VALUES(?,?,?,?)',(time.time(),g.session['user'],'antes-panel',row['draft']))
    c.execute('UPDATE state SET draft=?,published=?,revision=revision+1 WHERE id=1',(packed,packed))
    c.execute('INSERT INTO history(created,user,action,content) VALUES(?,?,?,?)',(time.time(),g.session['user'],'panel-'+collection,packed))

def public_settings():
    """Expose only display configuration, never bookings or audit history."""
    with db() as c:
        site=record(c,'site_content','site')
        appearance=record(c,'appearance','appearance')
        schedule=record(c,'schedule_config','schedule')
    result={k:site['data'].get(k) for k in site.get('enabled',[])}
    if appearance.get('enabled'):result['appearance']=appearance['data']
    if schedule.get('enabled'):result['schedule']=True
    return result

def slots(c, day):
    chosen=date.fromisoformat(day)
    schedule=record(c,'schedule_config','schedule')
    if (chosen.weekday()+1)%7 not in schedule['active_days'] or day in schedule['blocked_dates']:return []
    occupied=[]
    for b in records(c,'bookings'):
        if b.get('event_date')==day and b.get('status')!='cancelled':
            start=minutes(b['event_time']);occupied.append((start,start+int(b.get('duration_minutes',schedule['appointment_duration']))))
    occupied.extend((minutes(b['start']),minutes(b['end'])) for b in schedule['breaks'])
    blocked={b['time'] for b in schedule['blocked_slots'] if b['date']==day}
    result=set();duration=schedule['appointment_duration']
    for block in schedule['time_blocks']:
        for start in range(minutes(block['start']),minutes(block['end'])-duration+1,duration):
            label=f'{start//60:02}:{start%60:02}'
            if label not in blocked and not any(start<end and start+duration>begin for begin,end in occupied):result.add(label)
    return sorted(result)
