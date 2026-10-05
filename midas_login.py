import os
import re
from urllib.parse import urlparse
from flask import Flask, Response, request, render_template, abort, stream_with_context
import requests

app = Flask(__name__)

# ═══════════════════════════════════════════════════════════
#  إعدادات الدروس
# ═══════════════════════════════════════════════════════════
LESSONS_CONFIG = {
    'beshbeshy-haia': {
        'base_url': 'https://vz-b7206aa8-78f.b-cdn.net/4d434aa0-e4c2-40ad-bc0d-5730944b3980/',
        'referer': 'https://ahmedelbeshbeshy.com/'
    },
    'sha3t-dars2': {
        'base_url': 'https://vz-112ff3dc-c1b.b-cdn.net/e08412be-#ede5-4db4-98bc-caa60bd41a28/',
        'referer': 'https://sha3t.ta3allm.com/'
    },
    'misshanaa-foundation': {
        'base_url': 'https://vz-aeccdd43-b74.b-cdn.net/e1ac7cf3-bab1-40e3-8901-6a42af802560/',
        'referer': 'https://www.misshanaa.com/'
    },
    'hodeab-faragya': {
        'base_url': 'https://vz-f2d7c6c4-725.b-cdn.net/201f2233-93a7-41ac-876b-66607920b87f/',
        'referer': 'https://ahmedhodeab.com/'
    }
}


# ═══════════════════════════════════════════════════════════
#  الصفحة الرئيسية
# ═══════════════════════════════════════════════════════════
@app.route('/')
def index():
    return render_template('index.html')


# ═══════════════════════════════════════════════════════════
#  Proxy: /proxy/<lesson_id>/<path:file_path>
# ═══════════════════════════════════════════════════════════
@app.route('/proxy/<lesson_id>/<path:file_path>')
def proxy(lesson_id, file_path):
    config = LESSONS_CONFIG.get(lesson_id)
    if not config:
        abort(404, description='Lesson not found')

    target_url = config['base_url'] + file_path
    print(f'→ Proxying: {target_url}')

    # تجهيز الترويسات
    referer_parsed = urlparse(config['referer'])
    headers = {
        'Referer': config['referer'],
        'Origin': f"{referer_parsed.scheme}://{referer_parsed.netloc}",
        'User-Agent': request.headers.get('User-Agent', 'Mozilla/5.0'),
        'Accept': '*/*',
        'Accept-Language': 'ar,en;q=0.9',
    }

    # تمرير Range لو موجود (مهم للـ seek)
    if 'Range' in request.headers:
        headers['Range'] = request.headers['Range']

    try:
        upstream = requests.get(
            target_url,
            headers=headers,
            stream=True,
            allow_redirects=True,
            timeout=30
        )
    except requests.RequestException as e:
        print(f'✗ Request error: {e}')
        abort(502, description=f'Upstream error: {e}')

    if upstream.status_code >= 400:
        print(f'✗ Bunny error {upstream.status_code} → {target_url}')
        abort(upstream.status_code, description=f'Upstream returned {upstream.status_code}')

    content_type = upstream.headers.get('Content-Type', 'application/octet-stream')
    is_m3u8 = file_path.endswith('.m3u8') or 'mpegurl' in content_type.lower()

    # ═════════════════════════════════════════════════════
    #  إعادة كتابة ملفات m3u8
    #  مع الحفاظ على المسار الفرعي (480p/، 720p/...)
    # ═════════════════════════════════════════════════════
    if is_m3u8:
        text = upstream.text

        # استخراج المجلد الحالي من مسار الملف
        # مثال: file_path = "480p/video.m3u8" → base_dir = "480p/"
        # مثال: file_path = "playlist.m3u8"   → base_dir = ""
        if '/' in file_path:
            base_dir = file_path.rsplit('/', 1)[0] + '/'
        else:
            base_dir = ''

        print(f'  📁 base_dir = "{base_dir}"')

        rewritten_lines = []

        for line in text.splitlines():
            stripped = line.strip()

            if not stripped:
                rewritten_lines.append(line)
                continue

            # سطر تعليق أو خاصية
            if stripped.startswith('#'):
                # معالجة URI داخل الوسوم
                if 'URI="' in stripped:
                    def replace_uri(match):
                        uri = match.group(1)
                        if uri.startswith('http'):
                            return match.group(0)
                        return f'URI="/proxy/{lesson_id}/{base_dir}{uri}"'
                    stripped = re.sub(r'URI="([^"]+)"', replace_uri, stripped)
                rewritten_lines.append(stripped)
                continue

            # رابط كامل (http/https)
            if stripped.startswith('http://') or stripped.startswith('https://'):
                if stripped.startswith(config['base_url']):
                    rel = stripped[len(config['base_url']):]
                    rewritten_lines.append(f'/proxy/{lesson_id}/{rel}')
                else:
                    rewritten_lines.append(stripped)
                continue

            # رابط يبدأ بـ / (absolute path على السيرفر)
            if stripped.startswith('/'):
                rewritten_lines.append(f'/proxy/{lesson_id}{stripped}')
                continue

            # رابط نسبي (زي video0.ts أو 480p/segment.ts)
            # نضيف الـ base_dir عشان نعرف المجلد الحالي
            rewritten_lines.append(f'/proxy/{lesson_id}/{base_dir}{stripped}')

        new_content = '\n'.join(rewritten_lines)

        return Response(
            new_content,
            status=200,
            content_type='application/vnd.apple.mpegurl',
            headers={
                'Access-Control-Allow-Origin': '*',
                'Cache-Control': 'no-cache',
            }
        )

    # ═════════════════════════════════════════════════════
    #  تمرير الملفات العادية (ts, mp4, key)
    # ═════════════════════════════════════════════════════
    response_headers = {
        'Content-Type': content_type,
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Range, Content-Type',
        'Access-Control-Expose-Headers': 'Content-Length, Content-Range, Accept-Ranges',
    }

    if 'Content-Length' in upstream.headers:
        response_headers['Content-Length'] = upstream.headers['Content-Length']

    if 'Content-Range' in upstream.headers:
        response_headers['Content-Range'] = upstream.headers['Content-Range']

    if 'Accept-Ranges' in upstream.headers:
        response_headers['Accept-Ranges'] = upstream.headers['Accept-Ranges']

    status = upstream.status_code  # 200 أو 206

    def generate():
        try:
            for chunk in upstream.iter_content(chunk_size=64 * 1024):
                if chunk:
                    yield chunk
        except Exception as e:
            print(f'✗ Stream error: {e}')

    return Response(
        stream_with_context(generate()),
        status=status,
        headers=response_headers
    )


# ═══════════════════════════════════════════════════════════
#  التشغيل
# ═══════════════════════════════════════════════════════════
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 3000))
    print()
    print('  ╔══════════════════════════════════════════╗')
    print('  ║   🎓 منصة دهمان التعليمية                ║')
    print('  ║   ✅ Flask Proxy is running              ║')
    print(f'  ║   🌐 http://0.0.0.0:{port}                  ║')
    print('  ╚══════════════════════════════════════════╝')
    print()
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
