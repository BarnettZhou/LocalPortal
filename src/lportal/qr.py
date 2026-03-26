"""二维码生成和浏览器唤起"""

import socket
import webbrowser
from io import BytesIO

import qrcode


def _is_private_ip(ip: str) -> bool:
    """检查 IP 是否是 RFC 1918 私有地址"""
    if not ip or ip.startswith('127.'):
        return False
    if ip.startswith('192.168.'):
        return True
    if ip.startswith('10.'):
        return True
    if ip.startswith('172.'):
        try:
            second_octet = int(ip.split('.')[1])
            return 16 <= second_octet <= 31
        except (ValueError, IndexError):
            return False
    return False


def get_local_ip() -> str:
    """获取本机局域网 IP 地址
    
    优先返回 RFC 1918 规定的私有地址段：
    - 192.168.0.0/16
    - 10.0.0.0/8  
    - 172.16.0.0/12
    """
    # 方法1：通过连接外部地址获取（最快，但可能在 VPN 环境下返回非内网地址）
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(2)
        s.connect(("223.5.5.5", 53))  # 使用阿里 DNS，国内访问更快
        ip = s.getsockname()[0]
        s.close()
        # 如果获取到的是私有地址，直接返回
        if _is_private_ip(ip):
            return ip
    except Exception:
        pass
    
    # 方法2：遍历所有网络接口获取 IP 列表
    try:
        hostname = socket.gethostname()
        ip_list = []
        
        # 获取本机所有 IP 地址
        try:
            # Python 3.3+ 的方式
            addr_info = socket.getaddrinfo(hostname, None, socket.AF_INET)
            for info in addr_info:
                ip = info[4][0]
                if _is_private_ip(ip):
                    ip_list.append(ip)
        except Exception:
            pass
        
        # 尝试通过 socket 连接本地网络广播地址来获取
        if not ip_list:
            # 尝试常见的内网网关地址
            test_targets = []
            for i in range(1, 255):
                test_targets.append(f'192.168.{i}.1')
            for i in range(16, 32):
                test_targets.append(f'172.{i}.1.1')
            for i in range(1, 255):
                test_targets.append(f'10.{i}.1.1')
            
            for target in test_targets[:10]:  # 只尝试前10个，避免太慢
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    s.settimeout(0.1)
                    s.connect((target, 80))
                    ip = s.getsockname()[0]
                    s.close()
                    if _is_private_ip(ip):
                        ip_list.append(ip)
                        break
                except Exception:
                    continue
        
        # 优先返回 192.168.x.x 地址
        for ip in ip_list:
            if ip.startswith('192.168.'):
                return ip
        # 其次返回 10.x.x.x
        for ip in ip_list:
            if ip.startswith('10.'):
                return ip
        # 最后返回 172.16-31.x.x
        if ip_list:
            return ip_list[0]
            
    except Exception:
        pass
    
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


def generate_qr_ascii(url: str) -> str:
    """生成 ASCII 艺术二维码（紧凑版）
    
    使用上下半块字符，两行像素合并为一行字符显示，
    保持可扫描性的同时高度减半。
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=1,
        border=1,
    )
    qr.add_data(url)
    qr.make(fit=True)
    
    # 使用 Unicode 上下半块字符：
    # ▀ 上半块 (upper half) - 上黑下白
    # ▄ 下半块 (lower half) - 上白下黑  
    # █ 全块 (full block) - 全黑
    #   空格 - 全白
    
    lines = []
    modules = list(qr.modules)
    
    # 每两行原始像素合并成一行终端字符
    for i in range(0, len(modules), 2):
        row1 = modules[i]  # 上行
        row2 = modules[i + 1] if i + 1 < len(modules) else [False] * len(row1)  # 下行
        
        line = ''
        for j in range(len(row1)):
            upper = row1[j]  # 上像素
            lower = row2[j]  # 下像素
            
            if upper and lower:
                line += '█'  # 全黑
            elif upper and not lower:
                line += '▀'  # 上半块（上黑下白）
            elif not upper and lower:
                line += '▄'  # 下半块（上白下黑）
            else:
                line += ' '  # 全白
        lines.append(line)
    
    return '\n'.join(lines)
