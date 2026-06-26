#!/usr/bin/env python3
"""
本地文件分享工具 — 在局域网内快速分享文件
============================================
在任意目录启动 HTTP 服务器，生成二维码，手机扫码即可下载/上传文件。
免去微信传文件的压缩和大小限制。

用法:
  python share.py                    # 分享当前目录
  python share.py /path/to/dir       # 分享指定目录
  python share.py -p 9090            # 指定端口
  python share.py -u                 # 允许上传
  python share.py -p 8080 -u         # 组合使用
"""

import http.server
import socket
import os
import sys
import argparse
import json
import mimetypes
import urllib.parse
import html
import time
import tempfile
from pathlib import Path

# ── 可选依赖 ──────────────────────────────────────────────
try:
    import qrcode

    HAS_QRCODE = True
except ImportError:
    HAS_QRCODE = False

# ── 常量 ──────────────────────────────────────────────────
VERSION = "1.0.0"
MAX_UPLOAD_SIZE = 500 * 1024 * 1024  # 500MB

# ── HTML 模板 ─────────────────────────────────────────────
STYLE = """
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f5f5f7; color: #1d1d1f; min-height: 100vh; }
.header { background: #fff; border-bottom: 1px solid #e5e5e7; padding: 16px 20px; position: sticky; top: 0; z-index: 10; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
.header-top { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px; }
.header h1 { font-size: 18px; font-weight: 600; display: flex; align-items: center; gap: 8px; }
.header h1 .icon { font-size: 22px; }
.header .path { font-size: 12px; color: #86868b; margin-top: 4px; word-break: break-all; }
.header .meta { font-size: 13px; color: #86868b; }
.upload-bar { background: #007aff; color: #fff; border: none; padding: 8px 18px; border-radius: 20px; font-size: 14px; font-weight: 500; cursor: pointer; transition: background .2s; }
.upload-bar:hover { background: #0056cc; }
.upload-bar:disabled { background: #999; cursor: not-allowed; }
.container { max-width: 800px; margin: 0 auto; padding: 16px 20px 40px; }
.file-list { background: #fff; border-radius: 12px; overflow: hidden; box-shadow: 0 1px 4px rgba(0,0,0,0.04); }
.file-row { display: flex; align-items: center; padding: 12px 16px; border-bottom: 1px solid #f0f0f2; gap: 12px; transition: background .15s; }
.file-row:last-child { border-bottom: none; }
.file-row:hover { background: #fafafc; }
.file-row.dir { cursor: pointer; }
.file-icon { font-size: 22px; flex-shrink: 0; width: 28px; text-align: center; }
.file-info { flex: 1; min-width: 0; }
.file-name { font-size: 15px; font-weight: 500; word-break: break-all; }
.file-name a { color: #1d1d1f; text-decoration: none; }
.file-name a:hover { color: #007aff; }
.file-meta { font-size: 12px; color: #86868b; margin-top: 2px; }
.file-actions { display: flex; gap: 8px; flex-shrink: 0; }
.btn { padding: 6px 14px; border-radius: 16px; font-size: 13px; font-weight: 500; cursor: pointer; border: none; transition: all .15s; text-decoration: none; display: inline-flex; align-items: center; gap: 4px; }
.btn-dl { background: #007aff; color: #fff; }
.btn-dl:hover { background: #0056cc; }
.btn-copy { background: #e5e5ea; color: #1d1d1f; }
.btn-copy:hover { background: #d1d1d6; }
.empty { text-align: center; padding: 60px 20px; color: #86868b; }
.empty .icon { font-size: 48px; margin-bottom: 12px; }
.footer { text-align: center; padding: 20px; font-size: 12px; color: #c7c7cc; }
/* 上传区域 */
.drop-zone { border: 2px dashed #d1d1d6; border-radius: 12px; padding: 40px; text-align: center; margin: 16px 0; transition: all .2s; cursor: pointer; }
.drop-zone.drag-over { border-color: #007aff; background: #f0f7ff; }
.drop-zone .dz-icon { font-size: 36px; margin-bottom: 8px; }
.drop-zone .dz-text { font-size: 14px; color: #86868b; }
#upload-input { display: none; }
/* 进度条 */
.progress-wrap { display: none; margin: 12px 0; }
.progress-wrap.active { display: block; }
.progress-bar { height: 6px; background: #e5e5ea; border-radius: 3px; overflow: hidden; }
.progress-fill { height: 100%; background: #007aff; border-radius: 3px; width: 0%; transition: width .3s; }
.progress-text { font-size: 12px; color: #86868b; margin-top: 4px; }
/* 响应式 */
@media (max-width: 600px) {
  .file-actions { flex-direction: column; }
  .file-row { flex-wrap: wrap; }
  .header { padding: 12px 14px; }
  .container { padding: 10px 14px 30px; }
}
"""

UPLOAD_SCRIPT = """
<script>
const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('upload-input');
const progressWrap = document.getElementById('progress-wrap');
const progressFill = document.getElementById('progress-fill');
const progressText = document.getElementById('progress-text');
const uploadBtn = document.getElementById('upload-btn');

uploadBtn.addEventListener('click', () => fileInput.click());
dropZone.addEventListener('click', () => fileInput.click());

dropZone.addEventListener('dragover', (e) => {
  e.preventDefault();
  dropZone.classList.add('drag-over');
});
dropZone.addEventListener('dragleave', () => {
  dropZone.classList.remove('drag-over');
});
dropZone.addEventListener('drop', (e) => {
  e.preventDefault();
  dropZone.classList.remove('drag-over');
  const files = e.dataTransfer.files;
  if (files.length > 0) uploadFiles(files);
});
fileInput.addEventListener('change', () => {
  if (fileInput.files.length > 0) uploadFiles(fileInput.files);
});

function uploadFiles(files) {
  let uploaded = 0;
  progressWrap.classList.add('active');

  function uploadNext() {
    if (uploaded >= files.length) {
      progressText.textContent = '全部上传完成，刷新页面...';
      setTimeout(() => location.reload(), 800);
      return;
    }
    const file = files[uploaded];
    progressText.textContent = '上传中: ' + file.name + ' (' + formatSize(file.size) + ')';
    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/?upload=' + encodeURIComponent(file.name));
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) {
        const pct = Math.round((e.loaded / e.total) * 100);
        progressFill.style.width = pct + '%';
      }
    };
    xhr.onload = () => {
      if (xhr.status === 200) {
        uploaded++;
        uploadNext();
      } else {
        progressText.textContent = '上传失败: ' + file.name;
      }
    };
    xhr.onerror = () => {
      progressText.textContent = '上传失败: ' + file.name;
    };
    xhr.send(file);
  }
  uploadNext();
}

function formatSize(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
  if (bytes < 1073741824) return (bytes / 1048576).toFixed(1) + ' MB';
  return (bytes / 1073741824).toFixed(2) + ' GB';
}
</script>
"""

PAGE_TOP = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>文件分享 — {dir_name}</title>
<style>{style}</style>
</head>
<body>
<div class="header">
  <div class="header-top">
    <h1><span class="icon">📁</span>文件分享</h1>
    <div class="meta">共 {file_count} 项</div>
  </div>
  <div class="path">{root_path}</div>
</div>
<div class="container">
"""

UPLOAD_HTML = """
<div class="drop-zone" id="drop-zone">
  <div class="dz-icon">📤</div>
  <div class="dz-text">点击或拖拽文件到此处上传</div>
  <div style="font-size:12px;color:#aeaeb2;margin-top:4px;">单文件最大 {max_size}</div>
</div>
<input type="file" id="upload-input" multiple>
<div class="progress-wrap" id="progress-wrap">
  <div class="progress-bar"><div class="progress-fill" id="progress-fill"></div></div>
  <div class="progress-text" id="progress-text"></div>
</div>
<script>{upload_script}</script>
"""

BACK_LINK = '<div style="margin-bottom:12px;"><a href="/" style="color:#007aff;text-decoration:none;font-size:14px;">← 返回根目录</a></div>'
FILE_LIST_START = '<div class="file-list">'
FILE_LIST_END = '</div>'
PAGE_BOTTOM = '</div><div class="footer">FileShare v{version}</div></body></html>'


# ── 工具函数 ──────────────────────────────────────────────

def format_size(size_bytes):
    """人类可读的文件大小"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1048576:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1073741824:
        return f"{size_bytes / 1048576:.1f} MB"
    else:
        return f"{size_bytes / 1073741824:.2f} GB"


def format_max_size():
    """人类可读的最大上传大小"""
    if MAX_UPLOAD_SIZE < 1048576:
        return f"{MAX_UPLOAD_SIZE / 1024:.0f}KB"
    elif MAX_UPLOAD_SIZE < 1073741824:
        return f"{MAX_UPLOAD_SIZE / 1048576:.0f}MB"
    else:
        return f"{MAX_UPLOAD_SIZE / 1073741824:.1f}GB"


def get_file_icon(name, is_dir):
    """根据文件名/类型返回图标"""
    if is_dir:
        return "📁"
    ext = Path(name).suffix.lower()
    icons = {
        # 图片
        ".jpg": "🖼️", ".jpeg": "🖼️", ".png": "🖼️", ".gif": "🖼️",
        ".webp": "🖼️", ".svg": "🖼️", ".bmp": "🖼️", ".ico": "🖼️",
        # 视频
        ".mp4": "🎬", ".mov": "🎬", ".avi": "🎬", ".mkv": "🎬",
        ".webm": "🎬", ".flv": "🎬",
        # 音频
        ".mp3": "🎵", ".wav": "🎵", ".flac": "🎵", ".aac": "🎵",
        ".ogg": "🎵", ".m4a": "🎵",
        # 文档
        ".pdf": "📄", ".doc": "📝", ".docx": "📝", ".xls": "📊",
        ".xlsx": "📊", ".ppt": "📽️", ".pptx": "📽️",
        ".txt": "📃", ".md": "📃", ".csv": "📊", ".json": "📃",
        ".xml": "📃", ".yaml": "📃", ".yml": "📃",
        # 压缩包
        ".zip": "📦", ".rar": "📦", ".7z": "📦", ".tar": "📦",
        ".gz": "📦", ".bz2": "📦",
        # 代码
        ".py": "💻", ".js": "💻", ".ts": "💻", ".html": "💻",
        ".css": "💻", ".java": "💻", ".go": "💻", ".rs": "💻",
        ".c": "💻", ".cpp": "💻", ".sh": "💻",
        # 安装包
        ".dmg": "💿", ".pkg": "💿", ".apk": "💿", ".ipa": "💿",
        ".exe": "💿", ".msi": "💿",
    }
    return icons.get(ext, "📎")


def get_local_ip():
    """获取本机局域网 IPv4 地址"""
    # 方法 1：连接一个外部地址来获取本机 IP
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        if ip and not ip.startswith("127."):
            return ip
    except Exception:
        pass

    # 方法 2：遍历网络接口
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            ip = info[4][0]
            if not ip.startswith("127."):
                return ip
    except Exception:
        pass

    return "127.0.0.1"


def get_all_ips():
    """获取所有可能的局域网 IP"""
    ips = []
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            ip = info[4][0]
            if not ip.startswith("127."):
                ips.append(ip)
    except Exception:
        pass
    return ips


def generate_qr_terminal(url):
    """在终端生成 ASCII 二维码"""
    if not HAS_QRCODE:
        return None

    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=1,
            border=2,
        )
        qr.add_data(url)
        qr.make(fit=True)
        qr.print_ascii(tty=True)
        return True
    except Exception:
        return None


def generate_qr_png(url, filepath):
    """生成二维码 PNG 图片"""
    if not HAS_QRCODE:
        return None
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=4,
        )
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        img.save(filepath)
        return True
    except Exception:
        return None


# ── HTTP 请求处理器 ───────────────────────────────────────

class ShareHandler(http.server.SimpleHTTPRequestHandler):
    """自定义请求处理器：文件浏览 + 下载 + 可选上传"""

    root_dir = os.getcwd()
    allow_upload = False

    def log_message(self, format, *args):
        """自定义日志格式"""
        timestamp = time.strftime("%H:%M:%S")
        sys.stderr.write(f"[{timestamp}] {self.client_address[0]} — {format % args}\n")

    def translate_path(self, path):
        """将 URL 路径转换为文件系统路径，防止目录遍历"""
        path = urllib.parse.unquote(path.split("?", 1)[0])
        # 清理路径
        path = os.path.normpath(path.lstrip("/"))
        # 防止访问根目录之外的路径
        full = os.path.normpath(os.path.join(self.root_dir, path))
        root = os.path.normpath(self.root_dir)
        if not full.startswith(root):
            full = root
        return full

    def do_GET(self):
        """处理 GET 请求"""
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        # 普通文件请求
        filepath = self.translate_path(path)

        if os.path.isdir(filepath):
            self.serve_directory(filepath, path)
        elif os.path.isfile(filepath):
            self.serve_file(filepath)
        else:
            self.send_error(404, "File not found")
            self.send_response(404)

    def do_POST(self):
        """处理 POST 请求（文件上传）"""
        if not self.allow_upload:
            self.send_error(403, "Upload not allowed")
            return

        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)
        filename = qs.get("upload", [None])[0]

        if not filename:
            self.send_error(400, "Missing filename")
            return

        # 安全检查文件名
        filename = os.path.basename(filename)
        if not filename or filename.startswith("."):
            # 默认隐藏文件
            pass

        content_length = int(self.headers.get("Content-Length", 0))
        if content_length > MAX_UPLOAD_SIZE:
            self.send_error(413, "File too large")
            return

        # 保存到目标目录
        save_path = os.path.join(self.root_dir, filename)
        # 如果文件已存在，加上时间戳
        if os.path.exists(save_path):
            name, ext = os.path.splitext(filename)
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            save_path = os.path.join(self.root_dir, f"{name}_{timestamp}{ext}")

        try:
            with open(save_path, "wb") as f:
                remaining = content_length
                while remaining > 0:
                    chunk = self.rfile.read(min(remaining, 65536))
                    if not chunk:
                        break
                    f.write(chunk)
                    remaining -= len(chunk)

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "ok": True,
                "name": os.path.basename(save_path),
                "size": os.path.getsize(save_path),
            }).encode())
        except Exception as e:
            self.send_error(500, str(e))

    def serve_directory(self, dirpath, urlpath):
        """渲染目录列表页面"""
        try:
            entries = sorted(os.listdir(dirpath), key=lambda x: (
                not os.path.isdir(os.path.join(dirpath, x)),  # 目录优先
                x.lower()
            ))
        except PermissionError:
            self.send_error(403, "Permission denied")
            return

        dir_name = os.path.basename(dirpath) or os.path.basename(self.root_dir)

        # 判断是否是子目录
        root_norm = os.path.normpath(self.root_dir)
        dir_norm = os.path.normpath(dirpath)
        in_subdir = dir_norm != root_norm

        # 根目录路径字符串
        root_path_str = os.path.abspath(self.root_dir)

        # 构建 HTML
        body_parts = []

        # 页面头部
        body_parts.append(PAGE_TOP.format(
            dir_name=html.escape(dir_name),
            file_count=len(entries),
            root_path=root_path_str,
            style=STYLE,
        ))

        # 上传区
        if self.allow_upload and not in_subdir:
            body_parts.append(UPLOAD_HTML.format(
                max_size=format_max_size(),
                upload_script=UPLOAD_SCRIPT,
            ))

        # 返回链接
        if in_subdir:
            body_parts.append(BACK_LINK)

        # 文件列表
        body_parts.append(FILE_LIST_START)
        if entries:
            for name in entries:
                full_path = os.path.join(dirpath, name)
                is_dir = os.path.isdir(full_path)
                try:
                    size = os.path.getsize(full_path) if not is_dir else 0
                except OSError:
                    size = 0

                icon = get_file_icon(name, is_dir)
                escaped_name = html.escape(name)
                # URL 编码路径
                if in_subdir:
                    relative = urllib.parse.quote(name)
                else:
                    relative = urllib.parse.quote(name)

                # 构建文件行
                if is_dir:
                    download_url = relative + "/"
                    row = f"""
                    <div class="file-row dir" onclick="location.href='{download_url}'">
                      <div class="file-icon">{icon}</div>
                      <div class="file-info">
                        <div class="file-name"><a href="{download_url}">{escaped_name}/</a></div>
                        <div class="file-meta">文件夹</div>
                      </div>
                      <div class="file-actions">
                        <span class="btn btn-copy" onclick="event.stopPropagation();copyLink('{download_url}')">📋 复制链接</span>
                      </div>
                    </div>"""
                else:
                    download_url = relative
                    row = f"""
                    <div class="file-row">
                      <div class="file-icon">{icon}</div>
                      <div class="file-info">
                        <div class="file-name"><a href="{download_url}" download="{escaped_name}">{escaped_name}</a></div>
                        <div class="file-meta">{format_size(size)}</div>
                      </div>
                      <div class="file-actions">
                        <a href="{download_url}" download="{escaped_name}" class="btn btn-dl">⬇ 下载</a>
                        <span class="btn btn-copy" onclick="copyLink('{download_url}')">📋 复制链接</span>
                      </div>
                    </div>"""
                body_parts.append(row)
        else:
            body_parts.append(
                '<div class="empty"><div class="icon">📭</div><div>目录为空</div></div>'
            )

        body_parts.append(FILE_LIST_END)

        # JS: 复制链接
        body_parts.append("""
<script>
function copyLink(path) {
  var url = location.protocol + '//' + location.host + '/' + path;
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(url).then(function() {
      alert('链接已复制！\\n' + url);
    }).catch(function() {
      prompt('复制以下链接：', url);
    });
  } else {
    prompt('复制以下链接：', url);
  }
}
</script>
""")

        # 页面底部
        body_parts.append(PAGE_BOTTOM.format(version=VERSION))

        html_content = "".join(body_parts)

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(html_content.encode("utf-8"))))
        self.end_headers()
        self.wfile.write(html_content.encode("utf-8"))

    def serve_file(self, filepath):
        """提供文件下载"""
        try:
            f = open(filepath, "rb")
        except OSError:
            self.send_error(404, "File not found")
            return

        try:
            fs = os.fstat(f.fileno())
            file_size = fs[6]
            content_type, _ = mimetypes.guess_type(filepath)
            if content_type is None:
                content_type = "application/octet-stream"

            # 支持 Range 请求（大文件断点续传/视频跳转）
            range_header = self.headers.get("Range")
            if range_header:
                self.send_response(206)
                try:
                    range_str = range_header.split("=")[1]
                    start_str, _, end_str = range_str.partition("-")
                    start = int(start_str) if start_str else 0
                    end = int(end_str) if end_str else file_size - 1
                except (ValueError, IndexError):
                    start, end = 0, file_size - 1

                if start >= file_size:
                    self.send_error(416, "Range not satisfiable")
                    f.close()
                    return

                end = min(end, file_size - 1)
                content_length = end - start + 1

                self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
                self.send_header("Content-Length", str(content_length))
                self.send_header("Accept-Ranges", "bytes")
                self.send_header("Content-Type", content_type)

                # 设置下载文件名（处理中文）
                self.set_content_disposition(filepath)

                self.end_headers()

                f.seek(start)
                remaining = content_length
                while remaining > 0:
                    chunk = f.read(min(remaining, 65536))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    remaining -= len(chunk)
            else:
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(file_size))
                self.send_header("Accept-Ranges", "bytes")
                self.set_content_disposition(filepath)
                self.end_headers()

                while True:
                    chunk = f.read(65536)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
        except (ConnectionResetError, BrokenPipeError):
            pass  # 客户端断开连接
        finally:
            f.close()

    def set_content_disposition(self, filepath):
        """设置 Content-Disposition 头，支持中文文件名"""
        filename = os.path.basename(filepath)
        try:
            filename.encode("ascii")
            # 纯 ASCII 文件名
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        except UnicodeEncodeError:
            # 中文文件名，使用 RFC 5987 编码
            from urllib.parse import quote
            encoded = quote(filename, safe="")
            self.send_header(
                "Content-Disposition",
                f"attachment; filename*=UTF-8''{encoded}",
            )


# ── 主函数 ────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="本地文件分享工具 — 在局域网内快速分享文件",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python share.py                  # 分享当前目录，端口 8080
  python share.py ~/Downloads      # 分享下载目录
  python share.py -p 9090          # 使用 9090 端口
  python share.py -u               # 允许手机上传文件
  python share.py ~/Photos -p 3000 -u  # 组合使用
        """,
    )
    parser.add_argument(
        "directory",
        nargs="?",
        default=".",
        help="要分享的目录（默认当前目录）",
    )
    parser.add_argument(
        "-p", "--port",
        type=int,
        default=8080,
        help="HTTP 服务端口（默认 8080）",
    )
    parser.add_argument(
        "-u", "--upload",
        action="store_true",
        help="允许上传文件",
    )
    parser.add_argument(
        "-q", "--qr",
        action="store_true",
        default=True,
        help="在终端显示二维码（默认开启）",
    )
    parser.add_argument(
        "--qr-png",
        type=str,
        default=None,
        help="保存二维码为 PNG 图片",
    )
    parser.add_argument(
        "--no-qr",
        action="store_true",
        help="不显示二维码",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="不自动打开浏览器",
    )

    args = parser.parse_args()

    # 解析目录
    root = os.path.abspath(os.path.expanduser(args.directory))
    if not os.path.isdir(root):
        print(f"❌ 目录不存在: {root}")
        sys.exit(1)

    # 配置处理器
    ShareHandler.root_dir = root
    ShareHandler.allow_upload = args.upload
    ShareHandler.directory = root

    # 获取局域网 IP
    main_ip = get_local_ip()
    all_ips = get_all_ips()

    # 启动信息
    url = f"http://{main_ip}:{args.port}"

    print("=" * 55)
    print("  📁  FileShare — 本地文件分享")
    print("=" * 55)
    print(f"  分享目录: {root}")
    print(f"  访问地址: {url}")
    print(f"  本机访问: http://localhost:{args.port}")
    if args.upload:
        print(f"  上传功能: ✅ 已开启（最大 {format_max_size()}）")
    else:
        print(f"  上传功能: ❌ 已关闭（使用 -u 开启）")
    print("=" * 55)

    # 多个 IP 提示
    if len(all_ips) > 1:
        print("\n  ⚠️  本机有多个局域网 IP，如果默认地址无法访问，请尝试：")
        for ip in all_ips:
            alt_url = f"http://{ip}:{args.port}"
            print(f"     {alt_url}")
        print()

    # 生成二维码
    if not args.no_qr:
        if HAS_QRCODE:
            print("\n  📱 手机扫描下方二维码访问：\n")
            generate_qr_terminal(url)
        else:
            print("\n  💡 安装 qrcode 库可显示二维码：")
            print("     pip install qrcode")
            print()

    # 保存二维码图片
    if args.qr_png:
        if generate_qr_png(url, args.qr_png):
            print(f"\n  🖼️  二维码已保存: {args.qr_png}")
        else:
            print(f"\n  ❌ 二维码生成失败（需要 qrcode 库）")

    print(f"\n  🟢 服务器已启动，按 Ctrl+C 停止\n")

    # 自动打开浏览器
    if not args.no_browser:
        import threading
        def open_browser():
            import time
            time.sleep(0.5)
            try:
                import webbrowser
                webbrowser.open(f"http://localhost:{args.port}")
            except Exception:
                pass
        threading.Thread(target=open_browser, daemon=True).start()

    # 启动 HTTP 服务器
    server = http.server.ThreadingHTTPServer(("0.0.0.0", args.port), ShareHandler)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\n  👋 服务器已停止\n")
        server.shutdown()


if __name__ == "__main__":
    main()
