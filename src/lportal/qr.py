"""二维码生成和浏览器唤起"""

import socket
import webbrowser
from io import BytesIO

import qrcode


def get_local_ip() -> str:
    """获取本机局域网 IP 地址"""
    try:
        # 通过连接外部地址来获取本机 IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def generate_qr_png(url: str) -> bytes:
    """生成二维码 PNG 图片字节"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    return buffer.getvalue()


def generate_qr_html(url: str) -> str:
    """生成二维码展示页面 HTML"""
    return f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Local Portal - 扫码访问</title>
    <style>
        body {{
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            margin: 0;
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            background: #1a1a2e;
            color: #eee;
        }}
        .container {{
            text-align: center;
            padding: 40px;
        }}
        h1 {{ margin-bottom: 10px; }}
        .subtitle {{ color: #888; margin-bottom: 30px; }}
        img {{ 
            max-width: 300px; 
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
        }}
        .url {{ 
            margin-top: 20px;
            padding: 10px 20px;
            background: #0f3460;
            border-radius: 8px;
            font-family: monospace;
            word-break: break-all;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Local Portal</h1>
        <div class="subtitle">手机扫码访问语音输入页面</div>
        <img src="/qr.png" alt="QR Code">
        <div class="url">{url}</div>
    </div>
</body>
</html>
'''


def open_browser(url: str) -> None:
    """唤起系统默认浏览器"""
    webbrowser.open(url)
