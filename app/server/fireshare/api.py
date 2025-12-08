import json
import os, re, string
import shutil
import random
import logging
from subprocess import Popen
import subprocess as sp
import signal
from textwrap import indent
from flask import Blueprint, render_template, request, Response, jsonify, current_app, send_file, redirect
from flask_login import current_user, login_required
from flask_cors import CORS
from sqlalchemy.sql import text
from pathlib import Path
import time
from werkzeug.utils import secure_filename


from . import db, logger
from .models import Video, VideoInfo, VideoView
from .constants import SUPPORTED_FILE_TYPES

templates_path = os.environ.get('TEMPLATE_PATH') or 'templates'
api = Blueprint('api', __name__, template_folder=templates_path)

CORS(api, supports_credentials=True)

# --- Simple in-memory rate limiter for /api/stream ---
# Note: This is a best-effort protection primarily for public instances behind a single-process server.
# For multi-process deployments, consider a shared store like Redis.
_rate_limit_store = {}

def _rate_limited(key: str, limit: int, window_s: int) -> bool:
    """Return True if the key has exceeded the allowed request count in the window."""
    now = time.time()
    bucket = _rate_limit_store.get(key)
    if not bucket:
        _rate_limit_store[key] = [now]
        return False
    # prune old
    cutoff = now - window_s
    bucket = [t for t in bucket if t >= cutoff]
    bucket.append(now)
    _rate_limit_store[key] = bucket
    return len(bucket) > limit

def get_video_path(id, subid=None, quality=None):
    video = Video.query.filter_by(video_id=id).first()
    if not video:
        raise Exception(f"No video found for {id}")
    paths = current_app.config['PATHS']

    # Handle quality variants (720p, 1080p)
    if quality and quality in ['720p', '1080p']:
        # Check if the transcoded version exists
        derived_path = paths["processed"] / "derived" / id / f"{id}-{quality}.mp4"
        if derived_path.exists():
            return str(derived_path)
        # Fall back to original if quality doesn't exist
        logger.warning(f"Requested quality {quality} for video {id} not found, falling back to original")

    subid_suffix = f"-{subid}" if subid else ""
    ext = ".mp4" if subid else video.extension
    video_path = paths["processed"] / "video_links" / f"{id}{subid_suffix}{ext}"
    return str(video_path)

@api.route('/w/<video_id>')
def video_metadata(video_id):
    video = Video.query.filter_by(video_id=video_id).first()
    domain = f"https://{current_app.config['DOMAIN']}" if current_app.config['DOMAIN'] else ""
    if video:
        return render_template('metadata.html', video=video.json(), domain=domain)
    else:
        return redirect('{}/#/w/{}'.format(domain, video_id), code=302)

@api.route('/api/config')
def config():
    paths = current_app.config['PATHS']
    config_path = paths['data'] / 'config.json'
    file = open(config_path)
    config = json.load(file)
    file.close()
    if config_path.exists():
        return config["ui_config"]
    else:
        return jsonify({})

@api.route('/api/admin/config', methods=["GET", "PUT"])
@login_required
def get_or_update_config():
    paths = current_app.config['PATHS']
    if request.method == 'GET':
        config_path = paths['data'] / 'config.json'
        file = open(config_path)
        config = json.load(file)
        file.close()
        if config_path.exists():
            return config
        else:
            return jsonify({})
    if request.method == 'PUT':
        config = request.json["config"]
        config_path = paths['data'] / 'config.json'
        if not config:
            return Response(status=400, response='A config must be provided.')
        if not config_path.exists():
            return Response(status=500, response='Could not find a config to update.')
        config_path.write_text(json.dumps(config, indent=2))
        return Response(status=200)

@api.route('/api/admin/warnings', methods=["GET"])
@login_required
def get_warnings():
    warnings = current_app.config['WARNINGS']
    if request.method == 'GET':
        if len(warnings) == 0:
            return jsonify({})
        else:
            return jsonify(warnings)

@api.route('/api/manual/scan')
@login_required
def manual_scan():
    if not current_app.config["ENVIRONMENT"] == 'production':
        return Response(response='You must be running in production for this task to work.', status=400)
    else:
        current_app.logger.info(f"Executed manual scan")
        Popen(["fireshare", "bulk-import"], shell=False)
    return Response(status=200)

@api.route('/api/videos')
@login_required
def get_videos():
    sort = request.args.get('sort')
    # Check that the sort parameter is one of the allowed values
    allowed_sorts = [
        'updated_at desc',
        'updated_at asc',
        'video_info.title desc',
        'video_info.title asc',
        'views desc',
        'views asc'
    ]
    if sort not in allowed_sorts:
        return jsonify({"error": "Invalid sort parameter"}), 400

    if "views" in sort:
        videos = Video.query.join(VideoInfo).all()
    else:
        videos = Video.query.join(VideoInfo).order_by(text(sort)).all()

    videos_json = []
    for v in videos:
        vjson = v.json()
        vjson["view_count"] = VideoView.count(v.video_id)
        videos_json.append(vjson)

    if sort == "views asc":
        videos_json = sorted(videos_json, key=lambda d: d['view_count'])
    if sort == 'views desc':
        videos_json = sorted(videos_json, key=lambda d: d['view_count'], reverse=True)

    return jsonify({"videos": videos_json})

@api.route('/api/video/random')
@login_required
def get_random_video():
    row_count = Video.query.count()
    random_video = Video.query.offset(int(row_count * random.random())).first()
    current_app.logger.info(f"Fetched random video {random_video.video_id}: {random_video.info.title}")
    return jsonify(random_video.json())

@api.route('/api/video/public/random')
def get_random_public_video():
    row_count =  Video.query.filter(Video.info.has(private=False)).filter_by(available=True).count()
    random_video = Video.query.filter(Video.info.has(private=False)).filter_by(available=True).offset(int(row_count * random.random())).first()
    current_app.logger.info(f"Fetched public random video {random_video.video_id}: {random_video.info.title}")
    return jsonify(random_video.json())

@api.route('/api/videos/public')
def get_public_videos():
    sort = request.args.get('sort')

    # Check that the sort parameter is one of the allowed values
    allowed_sorts = [
        'updated_at desc',
        'updated_at asc',
        'video_info.title desc',
        'video_info.title asc',
        'views desc',
        'views asc'
    ]
    if sort not in allowed_sorts:
        return jsonify({"error": "Invalid sort parameter"}), 400

    if "views" in sort:
        videos = Video.query.join(VideoInfo).filter_by(private=False)
    else:
        videos = Video.query.join(VideoInfo).filter_by(private=False).order_by(text(sort))

    videos_json = []
    for v in videos:
        vjson = v.json()
        if (not vjson["available"]):
            continue
        vjson["view_count"] = VideoView.count(v.video_id)
        videos_json.append(vjson)

    if sort == "views asc":
        videos_json = sorted(videos_json, key=lambda d: d['view_count'])
    if sort == 'views desc':
        videos_json = sorted(videos_json, key=lambda d: d['view_count'], reverse=True)

    return jsonify({"videos": videos_json})

@api.route('/api/video/delete/<id>', methods=["DELETE"])
@login_required
def delete_video(id):
    video = Video.query.filter_by(video_id=id).first()
    if video:
        logging.info(f"Deleting video: {video.video_id}")

        paths = current_app.config['PATHS']
        file_path = paths['video'] / video.path
        link_path = paths['processed'] / 'video_links' / f"{id}{video.extension}"
        derived_path = paths['processed'] / 'derived' / id

        VideoInfo.query.filter_by(video_id=id).delete()
        Video.query.filter_by(video_id=id).delete()
        db.session.commit()

        try:
            if file_path.exists():
                file_path.unlink()
                logging.info(f"Deleted video file: {file_path}")
            if link_path.exists() or link_path.is_symlink():
                link_path.unlink()
                logging.info(f"Deleted link file: {link_path}")
            if derived_path.exists():
                shutil.rmtree(derived_path)
                logging.info(f"Deleted derived directory: {derived_path}")
        except OSError as e:
            logging.error(f"Error deleting files for video {id}: {e}")
            logging.error(f"Attempted to delete: file={file_path}, link={link_path}, derived={derived_path}")
        return Response(status=200)

    else:
        return Response(status=404, response=f"A video with id: {id}, does not exist.")

@api.route('/api/video/details/<id>', methods=["GET", "PUT"])
def handle_video_details(id):
    if request.method == 'GET':
        # db lookup and get the details title/views/etc
        # video_id = request.args['id']
        video = Video.query.filter_by(video_id=id).first()
        if video:
            return jsonify(video.json())
        else:
            return jsonify({
                'message': 'Video not found'
            }), 404
    if request.method == 'PUT':
        if not current_user.is_authenticated:
            return Response(response='You do not have access to this resource.', status=401)
        video_info = VideoInfo.query.filter_by(video_id=id).first()
        if video_info:
            db.session.query(VideoInfo).filter_by(video_id=id).update(request.json)
            db.session.commit()
            return Response(status=201)
        else:
            return jsonify({
                'message': 'Video details not found'
            }), 404

@api.route('/api/video/poster', methods=['GET'])
def get_video_poster():
    video_id = request.args['id']
    webm_poster_path = Path(current_app.config["PROCESSED_DIRECTORY"], "derived", video_id, "boomerang-preview.webm")
    jpg_poster_path = Path(current_app.config["PROCESSED_DIRECTORY"], "derived", video_id, "poster.jpg")
    if request.args.get('animated'):
        return send_file(webm_poster_path, mimetype='video/webm')
    else:
        return send_file(jpg_poster_path, mimetype='image/jpg')

@api.route('/api/video/view', methods=['POST'])
def add_video_view():
    video_id = request.json['video_id']
    if request.headers.getlist("X-Forwarded-For"):
        ip_address = request.headers.getlist("X-Forwarded-For")[0].split(",")[0]
    else:
        ip_address = request.remote_addr
    VideoView.add_view(video_id, ip_address)
    return Response(status=200)

@api.route('/api/video/<video_id>/views', methods=['GET'])
def get_video_views(video_id):
    views = VideoView.count(video_id)
    return str(views)

@api.route('/api/upload/public', methods=['POST'])
def public_upload_video():
    paths = current_app.config['PATHS']
    with open(paths['data'] / 'config.json', 'r') as configfile:
        try:
            config = json.load(configfile)
        except:
            logging.error("Invalid or corrupt config file")
            return Response(status=400)
        configfile.close()

    if not config['app_config']['allow_public_upload']:
        logging.warn("A public upload attempt was made but public uploading is disabled")
        return Response(status=401)

    upload_folder = config['app_config']['public_upload_folder_name']

    if 'file' not in request.files:
        return Response(status=400)
    file = request.files['file']
    if file.filename == '':
        return Response(status=400)
    filename = secure_filename(file.filename)
    if not filename:
        return Response(status=400)
    filetype = filename.split('.')[-1]
    if not filetype in SUPPORTED_FILE_TYPES:
        return Response(status=400)
    upload_directory = paths['video'] / upload_folder
    if not os.path.exists(upload_directory):
        os.makedirs(upload_directory)
    save_path = os.path.join(upload_directory, filename)
    if (os.path.exists(save_path)):
        name_no_type = ".".join(filename.split('.')[0:-1])
        uid = ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(6))
        save_path = os.path.join(paths['video'], upload_folder, f"{name_no_type}-{uid}.{filetype}")
    file.save(save_path)
    Popen(["fireshare", "scan-video", f"--path={save_path}"], shell=False)
    return Response(status=201)

@api.route('/api/uploadChunked/public', methods=['POST'])
def public_upload_videoChunked():
    paths = current_app.config['PATHS']
    with open(paths['data'] / 'config.json', 'r') as configfile:
        try:
            config = json.load(configfile)
        except:
            logging.error("Invalid or corrupt config file")
            return Response(status=400)
        configfile.close()

    if not config['app_config']['allow_public_upload']:
        logging.warn("A public upload attempt was made but public uploading is disabled")
        return Response(status=401)

    upload_folder = config['app_config']['public_upload_folder_name']

    required_files = ['blob']
    required_form_fields = ['chunkPart', 'totalChunks', 'checkSum']
    if not all(key in request.files for key in required_files) or not all(key in request.form for key in required_form_fields):
        return Response(status=400)
    blob = request.files.get('blob')
    chunkPart = int(request.form.get('chunkPart'))
    totalChunks = int(request.form.get('totalChunks'))
    checkSum = request.form.get('checkSum')
    if not blob.filename or blob.filename.strip() == '' or blob.filename == 'blob':
        return Response(status=400)
    filename = secure_filename(blob.filename)
    if not filename:
        return Response(status=400)
    filetype = filename.split('.')[-1] # TODO, probe filetype with fmpeg instead and remux to supporrted
    if not filetype in SUPPORTED_FILE_TYPES:
        return Response(status=400)

    upload_directory = paths['video'] / upload_folder
    if not os.path.exists(upload_directory):
        os.makedirs(upload_directory)
    tempPath = os.path.join(upload_directory, f"{checkSum}.{filetype}")
    with open(tempPath, 'ab') as f:
        f.write(blob.read())
    if chunkPart < totalChunks:
        return Response(status=202)

    save_path = os.path.join(upload_directory, filename)

    if (os.path.exists(save_path)):
        name_no_type = ".".join(filename.split('.')[0:-1])
        uid = ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(6))
        save_path = os.path.join(paths['video'], upload_folder, f"{name_no_type}-{uid}.{filetype}")

    os.rename(tempPath, save_path)
    Popen(["fireshare", "scan-video", f"--path={save_path}"], shell=False)
    return Response(status=201)

@api.route('/api/upload', methods=['POST'])
@login_required
def upload_video():
    paths = current_app.config['PATHS']
    with open(paths['data'] / 'config.json', 'r') as configfile:
        try:
            config = json.load(configfile)
        except:
            return Response(status=500, response="Invalid or corrupt config file")
        configfile.close()

    upload_folder = config['app_config']['admin_upload_folder_name']

    if 'file' not in request.files:
        return Response(status=400)
    file = request.files['file']
    if file.filename == '':
        return Response(status=400)
    filename = secure_filename(file.filename)
    if not filename:
        return Response(status=400)
    filetype = filename.split('.')[-1]
    if not filetype in SUPPORTED_FILE_TYPES:
        return Response(status=400)
    upload_directory = paths['video'] / upload_folder
    if not os.path.exists(upload_directory):
        os.makedirs(upload_directory)
    save_path = os.path.join(upload_directory, filename)
    if (os.path.exists(save_path)):
        name_no_type = ".".join(filename.split('.')[0:-1])
        uid = ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(6))
        save_path = os.path.join(paths['video'], upload_folder, f"{name_no_type}-{uid}.{filetype}")
    file.save(save_path)
    Popen(["fireshare", "scan-video", f"--path={save_path}"], shell=False)
    return Response(status=201)

@api.route('/api/uploadChunked', methods=['POST'])
@login_required
def upload_videoChunked():
    paths = current_app.config['PATHS']
    with open(paths['data'] / 'config.json', 'r') as configfile:
        try:
            config = json.load(configfile)
        except:
            return Response(status=500, response="Invalid or corrupt config file")
        configfile.close()

    upload_folder = config['app_config']['admin_upload_folder_name']

    required_files = ['blob']
    required_form_fields = ['chunkPart', 'totalChunks', 'checkSum', 'fileName', 'fileSize']

    if not all(key in request.files for key in required_files) or not all(key in request.form for key in required_form_fields):
        return Response(status=400)

    blob = request.files.get('blob')
    chunkPart = int(request.form.get('chunkPart'))
    totalChunks = int(request.form.get('totalChunks'))
    checkSum = request.form.get('checkSum')
    fileName = secure_filename(request.form.get('fileName'))
    fileSize = int(request.form.get('fileSize'))

    if not fileName:
        return Response(status=400)

    filetype = fileName.split('.')[-1]
    if not filetype in SUPPORTED_FILE_TYPES:
        return Response(status=400)

    upload_directory = paths['video'] / upload_folder
    if not os.path.exists(upload_directory):
        os.makedirs(upload_directory)

    # Store chunks with part number to ensure proper ordering
    tempPath = os.path.join(upload_directory, f"{checkSum}.part{chunkPart:04d}")

    # Write this specific chunk
    with open(tempPath, 'wb') as f:
        f.write(blob.read())

    # Check if we have all chunks
    chunk_files = []
    for i in range(1, totalChunks + 1):
        chunk_path = os.path.join(upload_directory, f"{checkSum}.part{i:04d}")
        if os.path.exists(chunk_path):
            chunk_files.append(chunk_path)

    # If we don't have all chunks yet, return 202
    if len(chunk_files) != totalChunks:
        return Response(status=202)

    # All chunks received, reassemble the file
    save_path = os.path.join(upload_directory, fileName)

    if os.path.exists(save_path):
        name_no_type = ".".join(fileName.split('.')[0:-1])
        uid = ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(6))
        save_path = os.path.join(upload_directory, f"{name_no_type}-{uid}.{filetype}")

    # Reassemble chunks in correct order
    try:
        with open(save_path, 'wb') as output_file:
            for i in range(1, totalChunks + 1):
                chunk_path = os.path.join(upload_directory, f"{checkSum}.part{i:04d}")
                with open(chunk_path, 'rb') as chunk_file:
                    output_file.write(chunk_file.read())
                # Clean up chunk file
                os.remove(chunk_path)

        # Verify file size
        if os.path.getsize(save_path) != fileSize:
            os.remove(save_path)
            return Response(status=500, response="File size mismatch after reassembly")

    except Exception as e:
        # Clean up on error
        for chunk_path in chunk_files:
            if os.path.exists(chunk_path):
                os.remove(chunk_path)
        if os.path.exists(save_path):
            os.remove(save_path)
        return Response(status=500, response="Error reassembling file")

    Popen(["fireshare", "scan-video", f"--path={save_path}"], shell=False)
    return Response(status=201)

@api.route('/api/video')
def get_video():
    video_id = request.args.get('id')
    subid = request.args.get('subid')
    quality = request.args.get('quality')  # Support quality parameter (720p, 1080p)
    video_path = get_video_path(video_id, subid, quality)
    file_size = os.stat(video_path).st_size
    start = 0
    length = 10240

    range_header = request.headers.get('Range', None)
    if range_header:
        m = re.search('([0-9]+)-([0-9]*)', range_header)
        g = m.groups()
        byte1, byte2 = 0, None
        if g[0]:
            byte1 = int(g[0])
        if g[1]:
            byte2 = int(g[1])
        if byte1 < file_size:
            start = byte1
        if byte2:
            length = byte2 + 1 - byte1
        else:
            length = file_size - start

    with open(video_path, 'rb') as f:
        f.seek(start)
        chunk = f.read(length)

    rv = Response(chunk, 206, mimetype='video/mp4', content_type='video/mp4', direct_passthrough=True)
    rv.headers.add('Content-Range', 'bytes {0}-{1}/{2}'.format(start, start + length - 1, file_size))
    return rv

def _select_encoder_from_preferences(preferences, whitelist, use_gpu):
    """
    Select the first codec present in both preferences and whitelist and map it to ffmpeg encoder name.
    Returns tuple (encoder_name, logical_codec) or (None, None) if none matched.
    """
    # Map logical codec -> (cpu_encoder, gpu_encoder)
    codec_map = {
        'H264': ('libx264', 'h264_nvenc'),
        'HEVC': ('libx265', 'hevc_nvenc'),
        'MPEG2': ('mpeg2video', 'mpeg2_nvenc'),
        'MPEG4': ('mpeg4', None),
        'VC1': (None, None),  # No common encoder in ffmpeg
        'VP8': ('libvpx', None),
        'VP9': ('libvpx-vp9', None),
        'AV1': ('libaom-av1', 'av1_nvenc'),
    }
    for c in preferences:
        uc = c.upper()
        if uc in whitelist and uc in codec_map:
            cpu, gpu = codec_map[uc]
            enc = (gpu if use_gpu and gpu else cpu)
            if enc:
                return enc, uc
    return None, None

@api.route('/api/stream', methods=['GET', 'HEAD'])
def stream_video():
    """
    Stream a browser-compatible MP4 (H.264/AAC) version of the requested video.

    This endpoint will:
      - Determine the source video path (original or quality variant)
      - If a cached, compatible MP4 exists, stream it with range support
      - Otherwise, start an ffmpeg transcode to a derived MP4 using fragmented MP4 flags
        and stream the file progressively as it is written (suitable for Firefox)
    """
    from pathlib import Path as _Path
    from .util import build_streamable_mp4_command, get_video_duration, _probe_codecs

    video_id = request.args.get('id')
    if not video_id:
        return Response(status=400, response='Missing required parameter: id')
    quality = request.args.get('quality')
    subid = request.args.get('subid')

    # Rate limiting (IP + video id key)
    rl_enabled = bool(current_app.config.get('STREAM_RATE_LIMIT_ENABLED', True))
    if rl_enabled and request.method == 'GET':
        # defaults: 20 requests per 60s per IP+video (tunable)
        rl_limit = int(current_app.config.get('STREAM_RATE_LIMIT_REQUESTS', 20))
        rl_window = int(current_app.config.get('STREAM_RATE_LIMIT_WINDOW', 60))
        ip = request.headers.get('X-Forwarded-For', request.remote_addr) or 'unknown'
        key = f"{ip}:{request.args.get('id','')}:stream"
        if _rate_limited(key, rl_limit, rl_window):
            return Response(status=429, response='Too Many Requests')

    # Resolve source path
    try:
        src_path = _Path(get_video_path(video_id, subid, quality if quality != 'original' else None))
    except Exception as ex:
        return Response(status=404, response=str(ex))

    # Compute duration once for header usage (best-effort)
    duration = None
    try:
        duration = get_video_duration(src_path)
    except Exception:
        duration = None

    # If this is a HEAD request, short-circuit without doing any I/O/transcoding
    if request.method == 'HEAD':
        headers = {
            'Content-Type': 'video/mp4',
        }
        if duration is not None:
            # Include duration header for client probes
            headers['Content-Duration'] = str(duration)
        return Response(status=200, headers=headers)

    # Prepare output directory
    paths = current_app.config['PATHS']
    derived_dir = _Path(paths['processed']) / 'derived' / video_id
    derived_dir.mkdir(parents=True, exist_ok=True)

    def _stream_file_with_range(file_path: _Path):
        """Serve an existing file with range support."""
        file_size = file_path.stat().st_size
        start = 0
        end = file_size - 1
        range_header = request.headers.get('Range', None)
        if range_header:
            m = re.search('bytes=(\\d+)-(\\d*)', range_header)
            if m:
                g = m.groups()
                if g[0]:
                    start = int(g[0])
                if g[1]:
                    end = int(g[1])
        length = max(0, end - start + 1)
        with open(file_path, 'rb') as f:
            f.seek(start)
            data = f.read(length)
        resp = Response(data, 206, mimetype='video/mp4', content_type='video/mp4', direct_passthrough=True)
        resp.headers.add('Content-Range', f'bytes {start}-{start + length - 1}/{file_size}')
        resp.headers.add('Accept-Ranges', 'bytes')
        # Caching headers for already-derived static files
        max_age = int(current_app.config.get('STREAM_CACHE_MAX_AGE', 3600))
        resp.headers.add('Cache-Control', f'public, max-age={max_age}')
        # Weak ETag based on size and mtime
        try:
            st = file_path.stat()
            etag = f"W/\"{st.st_size}-{int(st.st_mtime)}\""
            resp.headers.add('ETag', etag)
        except Exception:
            pass
        # Best-effort codec indicator for cached file:
        # 1) Infer from filename suffix patterns like "-stream-CODEC.mp4" or "-720p-CODEC.mp4"
        # 2) Fallback to probing the file with ffprobe to detect the actual video codec
        # 3) Default to H264 if all else fails
        codec_used = 'H264'
        # Try to extract from filename patterns
        mname = re.search(r"-(?:stream|\d{3,4}p)-([A-Za-z0-9_]+)\.mp4$", file_path.name)
        if mname:
            codec_used = mname.group(1).upper()
        else:
            # Probe file to detect codec name
            vcodec, _ = _probe_codecs(file_path)
            if vcodec:
                v = vcodec.lower()
                mapping = {
                    'h264': 'H264',
                    'avc': 'H264',
                    'hevc': 'HEVC',
                    'h265': 'HEVC',
                    'av1': 'AV1',
                    'mpeg4': 'MPEG4',
                    'mp4v': 'MPEG4',
                    'vp9': 'VP9',
                    'vp8': 'VP8',
                }
                codec_used = mapping.get(v, v.upper())
        resp.headers.add('X-Codec-Used', codec_used)
        if duration is not None:
            resp.headers.add('Content-Duration', str(duration))
        return resp

    # Parse client codec preferences and apply server rules
    codecs_csv = request.args.get('codecs', '') or ''
    try_index = request.args.get('codec_try', '0') or '0'
    try:
        try_index = int(try_index)
    except Exception:
        try_index = 0

    prefs = [c.strip().upper() for c in codecs_csv.split(',') if c.strip()]
    # MP4-friendly set we support minimally
    mp4_friendly = ['H264', 'HEVC', 'AV1']
    whitelist = [c for c in current_app.config.get('VIDEO_CODEC_WHITELIST', ['H264'])]
    enable_transcoding = bool(current_app.config.get('ENABLE_TRANSCODING', False))
    use_gpu = bool(current_app.config.get('TRANSCODE_GPU', False))

    # If transcoding disabled, we only allow default H264 compatibility path (practical approach)
    if not enable_transcoding:
        allowed = ['H264'] if 'H264' in whitelist else []
    else:
        # Filter by whitelist and MP4-friendly
        if not prefs:
            prefs = ['H264']
        allowed = [c for c in prefs if c in whitelist and c in mp4_friendly]
        # Apply retry offset
        if allowed and try_index > 0:
            try_index = min(try_index, len(allowed) - 1)
            allowed = allowed[try_index:] + allowed[:try_index]

    # Choose target codec with fallback
    target_codec = None
    if allowed:
        target_codec = allowed[0]
    else:
        # Fallbacks: if H264 whitelisted use it, otherwise pick first common option
        if 'H264' in whitelist:
            target_codec = 'H264'
        else:
            # pick any whitelist value that we support in MP4
            common = [c for c in whitelist if c in mp4_friendly]
            target_codec = common[0] if common else 'H264'

    # Now that we know the target codec, compute the codec-specific stream cache path
    # Use suffix -stream-CODEC.mp4 to avoid cross-codec collisions
    out_path = derived_dir / f"{video_id}-stream-{target_codec}.mp4"

    # If there is already a derived quality-specific mp4, prefer it; otherwise prefer the codec-specific stream cache
    preferred_mp4 = None
    if quality in ('720p', '1080p'):
        candidate = derived_dir / f"{video_id}-{quality}.mp4"
        if candidate.exists():
            preferred_mp4 = candidate
    if preferred_mp4 is None:
        # Prefer new codec-specific cache, else fall back to legacy cache name for backward compatibility
        if out_path.exists():
            preferred_mp4 = out_path
        else:
            legacy = derived_dir / f"{video_id}-stream.mp4"
            if legacy.exists():
                preferred_mp4 = legacy

    # If we already have a playable mp4, serve it with range support
    if preferred_mp4 and preferred_mp4.exists():
        return _stream_file_with_range(preferred_mp4)

    # Otherwise, begin (re)mux/transcode to out_path and stream progressively
    try:
        # Ensure any previous partial is removed to avoid stale tails
        # Only remove if not currently being written by a concurrent process (lock present)
        lock_path = _Path(str(out_path) + '.lock')
        if out_path.exists() and not lock_path.exists() and out_path.stat().st_size < 1024:
            out_path.unlink(missing_ok=True)
    except Exception:
        pass

    # Opportunistic cleanup of stale partials and locks in the same derived directory
    try:
        cleanup_age = int(current_app.config.get('STREAM_CLEANUP_AGE_SECONDS', 3600))
        min_partial_size = int(current_app.config.get('STREAM_CLEANUP_MIN_SIZE_BYTES', 1024 * 1024))
        now_ts = time.time()
        for p in derived_dir.glob(f"{video_id}-stream*.mp4"):
            try:
                st = p.stat()
                if st.st_size < min_partial_size and (now_ts - st.st_mtime) > cleanup_age:
                    current_app.logger.info(f"Cleaning stale partial stream file {p}")
                    p.unlink(missing_ok=True)
            except Exception:
                pass
        for p in derived_dir.glob(f"{video_id}-*.lock"):
            try:
                st = p.stat()
                if (now_ts - st.st_mtime) > cleanup_age:
                    current_app.logger.info(f"Cleaning stale lock file {p}")
                    p.unlink(missing_ok=True)
            except Exception:
                pass
    except Exception:
        pass

    # Simple per-output lock to avoid concurrent ffmpeg processes writing the same file
    lock_path = _Path(str(out_path) + '.lock')

    def _acquire_lock(timeout_s: float = 60.0):
        start_time = time.time()
        last_growth_check = time.time()
        last_size = out_path.stat().st_size if out_path.exists() else 0
        while True:
            try:
                # Atomic create lock file
                fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                with os.fdopen(fd, 'w') as f:
                    payload = {
                        'pid': os.getpid(),
                        'ts': time.time(),
                        'out': str(out_path)
                    }
                    f.write(json.dumps(payload))
                current_app.logger.info(f"Acquired stream lock {lock_path}")
                return True
            except FileExistsError:
                # Someone else is working on it; stream existing/growing file or wait briefly
                if out_path.exists():
                    return False  # We can stream the growing file below
                # No file yet; wait but break stale locks if needed
                time.sleep(0.25)
                now = time.time()
                # If we've waited beyond timeout, consider lock stale and remove if file absent or not growing
                if now - start_time > timeout_s:
                    try:
                        # If file exists and is growing, keep waiting; otherwise remove stale lock
                        if out_path.exists():
                            size_now = out_path.stat().st_size
                            if size_now > last_size:
                                last_size = size_now
                                last_growth_check = now
                                continue
                        current_app.logger.warning(f"Stale lock detected at {lock_path}, removing")
                        lock_path.unlink(missing_ok=True)
                    except Exception:
                        pass
                    # Try one more time to acquire after removing
            except Exception as e:
                current_app.logger.warning(f"Unexpected error acquiring lock {lock_path}: {e}")
                time.sleep(0.25)

    def _release_lock():
        try:
            lock_path.unlink(missing_ok=True)
            current_app.logger.info(f"Released stream lock {lock_path}")
        except Exception:
            pass

    acquired = _acquire_lock()

    proc = None
    if acquired:
        # Build an ffmpeg command: remux if already target-compatible; else transcode
        cmd = build_streamable_mp4_command(src_path, out_path, target_codec=target_codec, use_gpu=use_gpu)
        current_app.logger.info(f"Starting on-the-fly transcode for {video_id}: {' '.join(cmd)}")
        proc = Popen(cmd)

        # Spawn a lightweight cleanup that releases the lock when ffmpeg exits
        def _wait_and_cleanup(p):
            try:
                p.wait()
            finally:
                _release_lock()

        import threading as _threading
        _threading.Thread(target=_wait_and_cleanup, args=(proc,), daemon=True).start()

        # Watchdog to enforce total timeout and inactivity timeout
        def _watchdog(p, watched_path: _Path):
            base_timeout = int(current_app.config.get('TRANSCODE_TIMEOUT', 7200))
            inactivity_timeout = int(current_app.config.get('TRANSCODE_INACTIVITY_TIMEOUT', 120))
            last_size = watched_path.stat().st_size if watched_path.exists() else 0
            start_ts = time.time()
            last_change = start_ts
            while True:
                if p.poll() is not None:
                    return
                now = time.time()
                # total runtime limit
                if now - start_ts > base_timeout:
                    try:
                        current_app.logger.warning(f"Killing ffmpeg for {video_id} due to timeout ({base_timeout}s)")
                        p.kill()
                    except Exception:
                        pass
                    return
                # inactivity limit (no file growth)
                try:
                    if watched_path.exists():
                        size_now = watched_path.stat().st_size
                        if size_now > last_size:
                            last_size = size_now
                            last_change = now
                        elif now - last_change > inactivity_timeout:
                            current_app.logger.warning(f"Killing ffmpeg for {video_id} due to inactivity > {inactivity_timeout}s")
                            try:
                                p.kill()
                            except Exception:
                                pass
                            return
                except Exception:
                    # Ignore probing errors
                    pass
                time.sleep(1.0)

        _threading.Thread(target=_watchdog, args=(proc, out_path), daemon=True).start()
    else:
        current_app.logger.info(f"Another process is already transcoding {out_path}. Streaming the growing file.")

    def generate():
        chunk_size = 1024 * 256  # 256KB
        # Wait for file to appear
        while not out_path.exists():
            time.sleep(0.1)
        with open(out_path, 'rb') as f:
            while True:
                data = f.read(chunk_size)
                if data:
                    yield data
                else:
                    # If ffmpeg still running OR another process holds the lock, wait for more data
                    if (proc is not None and proc.poll() is None) or lock_path.exists():
                        time.sleep(0.2)
                        continue
                    # ffmpeg finished and no more data
                    break

    # For progressive streaming we cannot provide Content-Length up-front; return 200 with chunked transfer
    headers = {
        'Content-Type': 'video/mp4',
        'Cache-Control': 'no-cache',
        'X-Codec-Used': (target_codec or 'H264')
    }
    if duration is not None:
        headers['Content-Duration'] = str(duration)
    return Response(generate(), headers=headers)

@api.route('/api/transcoding/enabled')
def transcoding_enabled():
    """Lightweight capability endpoint for clients to know if server-side transcoding is enabled."""
    enabled = current_app.config.get('ENABLE_TRANSCODING', False)
    return jsonify({"enabled": bool(enabled)})

def get_folder_size(folder_path: str) -> int:
    """Safely compute the total size of regular files under folder_path.

    - Skips symlinks and special files.
    - Ignores files that disappear during traversal (TOCTOU) or that are not
      readable due to permissions, avoiding raising errors for best‑effort size.
    """
    total_size = 0
    # Ignore errors during traversal (e.g., permission denied directories)
    for dirpath, dirnames, filenames in os.walk(folder_path, onerror=lambda e: None):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            try:
                # Skip symlinks (can point to /proc, sockets, etc.)
                if os.path.islink(fp):
                    continue
                # Only count regular files
                if not os.path.isfile(fp):
                    continue
                try:
                    total_size += os.path.getsize(fp)
                except (FileNotFoundError, PermissionError, OSError):
                    # File might have been removed between isfile and getsize,
                    # or be unreadable; skip it.
                    continue
            except OSError:
                # Any unexpected OS error on this entry; skip it and continue.
                continue
    return total_size

@api.route('/api/folder-size', methods=['GET'])
def folder_size():
    path = request.args.get('path', default='.', type=str)
    # Validate the requested path
    if not os.path.exists(path):
        return jsonify({"error": "Path does not exist", "folder": path}), 400
    if not os.path.isdir(path):
        return jsonify({"error": "Path is not a directory", "folder": path}), 400
    size_bytes = get_folder_size(path)
    size_mb = size_bytes / (1024 * 1024)

    if size_mb < 1024:
        rounded_mb = round(size_mb / 100) * 100
        size_pretty = f"{rounded_mb} MB"
    elif size_mb < 1024 * 1024:
        size_gb = size_mb / 1024
        size_pretty = f"{round(size_gb, 1)} GB"
    else:
        size_tb = size_mb / (1024 * 1024)
        size_pretty = f"{round(size_tb, 1)} TB"

    return jsonify({
        "folder": path,
        "size_bytes": size_bytes,
        "size_pretty": size_pretty
    })

@api.after_request
def after_request(response):
    response.headers.add('Accept-Ranges', 'bytes')
    return response
