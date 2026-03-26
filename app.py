import os
import random
import json
import zipfile
import io
import uuid
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file, abort
from werkzeug.utils import secure_filename
from apscheduler.schedulers.background import BackgroundScheduler
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'footykits-2024')
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024

SUPABASE_URL = os.environ.get('SUPABASE_URL', '')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY', '')
BUCKET = 'footykits'

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}

DESCRIPTIONS = [
    "🔥 Nouveau maillot disponible ! Pour commander, lien en bio 🔗",
    "💥 On a ce qu'il vous faut ! Pour commander, lien en bio 🔗",
    "⚽ Qualité premium au meilleur prix ! Pour commander, lien en bio 🔗",
    "🏆 Collection complète disponible ! Pour commander, lien en bio 🔗",
    "👕 Maillot top qualité ! Pour commander, lien en bio 🔗",
    "🎯 Le maillot que tu cherchais ! Pour commander, lien en bio 🔗",
    "✨ Nouvelle arrivée en stock ! Pour commander, lien en bio 🔗",
    "⚡ Qualité premium, prix imbattable ! Pour commander, lien en bio 🔗",
    "🛒 Disponible maintenant ! Pour commander, lien en bio 🔗",
    "💪 Représente ton équipe ! Pour commander, lien en bio 🔗",
    "🔝 Les meilleurs maillots du marché ! Pour commander, lien en bio 🔗",
    "🌟 Édition limitée disponible ! Pour commander, lien en bio 🔗",
    "🎽 Ton maillot préféré est là ! Pour commander, lien en bio 🔗",
    "🏅 Qualité garantie ! Pour commander, lien en bio 🔗",
    "🔗 Livraison rapide ! Pour commander, lien en bio 🔗",
]

HASHTAGS = "#maillotdefoot #football #jersey"


# ─── Supabase ─────────────────────────────────────────────────────────────────

def get_supabase() -> Client:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise Exception("Supabase non configuré. Vérifie SUPABASE_URL et SUPABASE_KEY.")
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def list_images(category):
    try:
        sb = get_supabase()
        files = sb.storage.from_(BUCKET).list(category)
        return [
            f['name'] for f in files
            if f.get('name') and f['name'] != '.emptyFolderPlaceholder'
            and allowed_file(f['name'])
        ]
    except Exception as e:
        print(f"Erreur liste images {category}: {e}")
        return []


def public_url(path):
    return f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET}/{path}"


# ─── Génération carrousel ──────────────────────────────────────────────────────

def generate_carousel(video_type='sans_flocage'):
    try:
        sb = get_supabase()
        stock_category = 'category3' if video_type == 'flocage' else 'category2'
        cat_stock = list_images(stock_category)
        cat4 = list_images('category4')

        if len(cat_stock) < 7:
            label = "Flocage" if video_type == 'flocage' else "Stock"
            print(f"Catégorie {label} insuffisante ({len(cat_stock)}/7), génération annulée.")
            return None
        if not cat4:
            print("Catégorie 4 (Image Finale) vide, génération annulée.")
            return None

        stock = random.sample(cat_stock, 7)
        finale = random.choice(cat4)
        description = random.choice(DESCRIPTIONS)

        carousel_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now()
        carousel_name = f"carousel_{timestamp.strftime('%Y%m%d_%H%M%S')}_{carousel_id}"

        stock_paths = [f"{stock_category}/{img}" for img in stock]
        finale_path = f"category4/{finale}"

        if video_type == 'flocage':
            cover_path = None
            all_paths = stock_paths + [finale_path]
            total_images = 8
        else:
            cat1 = list_images('category1')
            if not cat1:
                print("Catégorie 1 vide, génération annulée.")
                return None
            cover = random.choice(cat1)
            cover_path = f"category1/{cover}"
            all_paths = [cover_path] + stock_paths + [finale_path]
            total_images = 9

        carousel_data = {
            'id': carousel_id,
            'name': carousel_name,
            'timestamp': timestamp.isoformat(),
            'cover': cover_path,
            'stock_images': stock_paths,
            'total_images': total_images,
            'description': description,
            'hashtags': HASHTAGS,
            'all_paths': all_paths,
        }

        sb.table('carousels').insert(carousel_data).execute()
        print(f"Carrousel généré ({video_type}) : {carousel_name}")
        return carousel_data

    except Exception as e:
        print(f"Erreur génération : {e}")
        raise


def auto_generate():
    print(f"[{datetime.now().strftime('%H:%M')}] Génération automatique...")
    generate_carousel()


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/config')
def get_config():
    return jsonify({'supabase_url': SUPABASE_URL, 'bucket': BUCKET})


@app.route('/api/upload', methods=['POST'])
def upload():
    if 'files' not in request.files:
        return jsonify({'error': 'Aucun fichier'}), 400

    category = request.form.get('category', 'category1')
    if category not in ['category1', 'category2', 'category3', 'category4']:
        return jsonify({'error': 'Catégorie invalide'}), 400

    files = request.files.getlist('files')
    uploaded = []
    errors = []

    sb = get_supabase()

    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            name, ext = os.path.splitext(filename)
            unique_name = f"{name}_{uuid.uuid4().hex[:6]}{ext}"
            path = f"{category}/{unique_name}"

            try:
                file_bytes = file.read()
                content_type = file.content_type or 'image/jpeg'
                sb.storage.from_(BUCKET).upload(
                    path,
                    file_bytes,
                    {'content-type': content_type, 'upsert': 'false'}
                )
                uploaded.append({'name': unique_name, 'url': public_url(path)})
            except Exception as e:
                errors.append(str(e))

    return jsonify({'uploaded': uploaded, 'count': len(uploaded), 'errors': errors})


@app.route('/api/images/<category>')
def get_images(category):
    if category not in ['category1', 'category2', 'category3', 'category4']:
        return jsonify({'error': 'Catégorie invalide'}), 400

    names = list_images(category)
    images = [{'name': n, 'url': public_url(f'{category}/{n}')} for n in names]
    return jsonify({'images': images, 'count': len(images)})


@app.route('/api/delete-image', methods=['DELETE'])
def delete_image():
    data = request.get_json()
    category = data.get('category')
    filename = data.get('filename')

    if category not in ['category1', 'category2', 'category3', 'category4']:
        return jsonify({'error': 'Catégorie invalide'}), 400

    try:
        sb = get_supabase()
        sb.storage.from_(BUCKET).remove([f'{category}/{filename}'])
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/generate', methods=['POST'])
def generate_one():
    data = request.get_json() or {}
    video_type = data.get('video_type', 'sans_flocage')
    if video_type not in ['flocage', 'sans_flocage']:
        video_type = 'sans_flocage'

    try:
        carousel = generate_carousel(video_type)
        if carousel:
            preview = carousel['cover'] or (carousel['all_paths'][0] if carousel['all_paths'] else None)
            carousel['preview_url'] = public_url(preview) if preview else None
            return jsonify({'success': True, 'carousel': carousel})
        # Only reaches here if images insufficient
        cat4 = len(list_images('category4'))
        stock_category = 'category3' if video_type == 'flocage' else 'category2'
        cat_stock = len(list_images(stock_category))
        label = "Flocage" if video_type == 'flocage' else "Stock"
        if cat4 == 0:
            return jsonify({'error': 'Ajoutez au moins 1 image en Image Finale (catégorie 4)'}), 400
        if video_type == 'sans_flocage' and len(list_images('category1')) == 0:
            return jsonify({'error': 'Ajoutez au moins 1 image en Catégorie 1'}), 400
        return jsonify({'error': f'Catégorie {label} : {cat_stock}/7 images minimum requises'}), 400
    except Exception as e:
        return jsonify({'error': f'Erreur : {str(e)}'}), 500


@app.route('/api/generate-five', methods=['POST'])
def generate_five():
    data = request.get_json() or {}
    video_type = data.get('video_type', 'sans_flocage')
    if video_type not in ['flocage', 'sans_flocage']:
        video_type = 'sans_flocage'

    try:
        generated = []
        for _ in range(5):
            c = generate_carousel(video_type)
            if c:
                preview = c['cover'] or (c['all_paths'][0] if c['all_paths'] else None)
                c['preview_url'] = public_url(preview) if preview else None
                generated.append(c)
            else:
                break

        if generated:
            return jsonify({'success': True, 'count': len(generated), 'carousels': generated})

        cat4 = len(list_images('category4'))
        stock_category = 'category3' if video_type == 'flocage' else 'category2'
        cat_stock = len(list_images(stock_category))
        label = "Flocage" if video_type == 'flocage' else "Stock"
        if cat4 == 0:
            return jsonify({'error': 'Image Finale (catégorie 4) vide'}), 400
        if video_type == 'sans_flocage' and len(list_images('category1')) == 0:
            return jsonify({'error': 'Catégorie 1 vide'}), 400
        return jsonify({'error': f'Catégorie {label} : {cat_stock}/7 images minimum'}), 400
    except Exception as e:
        return jsonify({'error': f'Erreur : {str(e)}'}), 500


@app.route('/api/trigger', methods=['GET', 'POST'])
def trigger_generation():
    """Endpoint for cron-job.org to trigger daily carousel generation."""
    secret = request.args.get('secret', '')
    expected = os.environ.get('CRON_SECRET', '')
    if expected and secret != expected:
        return jsonify({'error': 'Unauthorized'}), 401

    generated = []
    for _ in range(5):
        c = generate_carousel()
        if c:
            generated.append(c['name'])
        else:
            break

    return jsonify({'generated': len(generated), 'names': generated})


@app.route('/api/carousels')
def get_carousels():
    try:
        sb = get_supabase()
        result = sb.table('carousels').select('*').order('timestamp', desc=True).limit(30).execute()
        carousels = []
        for c in result.data:
            preview = c.get('cover') or ((c.get('all_paths') or [None])[0])
            c['preview_url'] = public_url(preview) if preview else None
            c['image_urls'] = [public_url(p) for p in (c.get('all_paths') or [])]
            carousels.append(c)
        return jsonify({'carousels': carousels})
    except Exception as e:
        return jsonify({'error': str(e), 'carousels': []}), 500


@app.route('/api/download/<carousel_name>')
def download_carousel(carousel_name):
    try:
        sb = get_supabase()
        result = sb.table('carousels').select('*').eq('name', carousel_name).execute()
        if not result.data:
            abort(404)

        c = result.data[0]
        paths = c.get('all_paths', [])

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            for i, path in enumerate(paths, 1):
                try:
                    data = sb.storage.from_(BUCKET).download(path)
                    ext = os.path.splitext(path)[1] or '.jpg'
                    zf.writestr(f'{i:02d}_image{ext}', data)
                except Exception as e:
                    print(f"Skip {path}: {e}")

        zip_buffer.seek(0)
        return send_file(
            zip_buffer,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f'{carousel_name}.zip'
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/delete-carousel', methods=['DELETE'])
def delete_carousel():
    data = request.get_json()
    name = data.get('name')
    try:
        sb = get_supabase()
        sb.table('carousels').delete().eq('name', name).execute()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/stats')
def get_stats():
    try:
        cat1 = len(list_images('category1'))
        cat2 = len(list_images('category2'))
        cat3 = len(list_images('category3'))
        cat4 = len(list_images('category4'))

        sb = get_supabase()
        total_res = sb.table('carousels').select('id', count='exact').execute()
        total = total_res.count or 0

        today_str = datetime.now().strftime('%Y%m%d')
        today_res = sb.table('carousels').select('id', count='exact').like('name', f'carousel_{today_str}%').execute()
        today = today_res.count or 0

        return jsonify({
            'category1': cat1,
            'category2': cat2,
            'category3': cat3,
            'category4': cat4,
            'total_generated': total,
            'today_generated': today,
            'ready_sans_flocage': cat1 >= 1 and cat2 >= 7 and cat4 >= 1,
            'ready_flocage': cat3 >= 7 and cat4 >= 1,
        })
    except Exception as e:
        return jsonify({
            'category1': 0, 'category2': 0, 'category3': 0, 'category4': 0,
            'total_generated': 0, 'today_generated': 0,
            'ready_sans_flocage': False, 'ready_flocage': False, 'error': str(e)
        })


if __name__ == '__main__':
    scheduler = BackgroundScheduler()
    for hour in [8, 10, 12, 14, 16]:
        scheduler.add_job(auto_generate, 'cron', hour=hour, minute=0)
    scheduler.start()

    port = int(os.environ.get('PORT', 8080))
    print(f"🚀 Footykits démarré sur http://localhost:{port}")

    try:
        app.run(debug=False, host='0.0.0.0', port=port, use_reloader=False)
    finally:
        scheduler.shutdown()
