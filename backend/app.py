from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import json
import time
import subprocess
import threading
import requests
from google import genai

app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 配置
CRAWLER_SCRIPT = os.path.join(os.path.dirname(os.path.dirname(__file__)), "crawler_enhanced.py")
DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "temp_data.json")

# 全局变量存储爬虫状态
crawler_status = {
    "running": False,
    "keyword": "",
    "data": [],
    "error": None
}

# Gemini客户端（延迟初始化）
gemini_client = None

def simple_local_analyze(data):
    """简单的本地分析（当Gemini不可用时的备选方案）"""
    if not data:
        return []
    
    results = []
    for item in data:
        try:
            price = float(item.get("price", "0"))
            title = item.get("title", "")
            
            # 简单的评分逻辑
            score = 7.0  # 基础分
            
            # 根据价格判断（假设价格越低性价比越高，这里需要根据实际情况调整）
            # 可以根据商品类型调整评分逻辑
            
            # 根据标题关键词判断
            title_lower = title.lower()
            if any(kw in title_lower for kw in ["全新", "未拆", "正品", "包邮"]):
                score += 1.0
            if any(kw in title_lower for kw in ["二手", "使用", "旧"]):
                score += 0.5
            
            if score >= 8.0:
                results.append({
                    "title": title,
                    "price": str(price),
                    "reason": "价格合理，商品描述清晰",
                    "score": round(score, 1)
                })
        except:
            continue
    
    # 按价格排序
    results.sort(key=lambda x: float(x.get("price", "999999")))
    return results[:10]  # 返回前10个

def check_proxy_status():
    """检查代理是否正常工作"""
    try:
        # 使用代理测试IP地址
        proxies = {
            'http': 'http://127.0.0.1:7890',
            'https': 'http://127.0.0.1:7890'
        }
        resp = requests.get("http://ip-api.com/json/", proxies=proxies, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            country = data.get("country", "Unknown")
            ip = data.get("query", "Unknown")
            print(f"[PROXY] 代理检测: IP={ip}, 国家={country}")
            return True, country, ip
    except Exception as e:
        print(f"[PROXY] 代理检测失败: {e}")
    return False, "Unknown", "Unknown"

def init_gemini_client(api_key):
    """初始化Gemini客户端"""
    global gemini_client
    try:
        # 强制设置代理环境变量
        proxy_url = "http://127.0.0.1:7890"
        os.environ["http_proxy"] = proxy_url
        os.environ["https_proxy"] = proxy_url
        os.environ["HTTP_PROXY"] = proxy_url
        os.environ["HTTPS_PROXY"] = proxy_url
        os.environ["all_proxy"] = proxy_url
        os.environ["ALL_PROXY"] = proxy_url
        
        print(f"[GEMINI] 设置代理: {proxy_url}")
        
        # 检查代理状态
        proxy_ok, country, ip = check_proxy_status()
        if not proxy_ok:
            return False, "代理连接失败，请检查代理是否运行在 127.0.0.1:7890"
        
        if country == "China":
            return False, f"代理未生效，当前IP仍在 {country} ({ip})。请确保代理软件（如Clash）已开启并设置为全局模式\n\n注意：即使代理IP正常，如果API Key在受限地区注册，Gemini API仍可能不可用。"
        
        print(f"[GEMINI] 代理正常，IP位置: {country} ({ip})")
        
        # 使用最简单的初始化方式，代理通过环境变量自动配置
        gemini_client = genai.Client(api_key=api_key)
        print("[GEMINI] 客户端初始化成功")
        return True, "初始化成功"
    except Exception as e:
        error_msg = str(e)
        if "FAILED_PRECONDITION" in error_msg or "location is not supported" in error_msg.lower():
            return False, "地区限制错误：请确保：1) 代理已开启并设置为全局模式 2) 代理IP不在受限地区 3) 重启服务器后重试"
        return False, f"初始化失败: {error_msg}"

@app.route('/')
def index():
    """返回前端页面"""
    return send_from_directory('../frontend', 'index.html')

@app.route('/<path:path>')
def static_files(path):
    """提供静态文件"""
    return send_from_directory('../frontend', path)

@app.route('/api/init', methods=['POST'])
def init_api():
    """初始化Gemini API Key"""
    data = request.json
    api_key = data.get('api_key', '')
    
    if not api_key:
        return jsonify({"success": False, "message": "API Key不能为空"}), 400
    
    success, message = init_gemini_client(api_key)
    if success:
        return jsonify({"success": True, "message": message})
    else:
        return jsonify({"success": False, "message": message}), 500

@app.route('/api/search', methods=['POST'])
def search():
    """搜索商品"""
    global crawler_status
    
    data = request.json
    keyword = data.get('keyword', '')
    api_key = data.get('api_key', '')
    
    if not keyword:
        return jsonify({"success": False, "message": "搜索关键词不能为空"}), 400
    
    if not api_key:
        return jsonify({"success": False, "message": "请先设置Gemini API Key"}), 400
    
    # 初始化Gemini客户端
    if not gemini_client:
        success, message = init_gemini_client(api_key)
        if not success:
            return jsonify({"success": False, "message": f"Gemini初始化失败: {message}"}), 500
    
    # 更新状态
    crawler_status = {
        "running": True,
        "keyword": keyword,
        "data": [],
        "error": None
    }
    
    try:
        # 运行爬虫
        if not os.path.exists(CRAWLER_SCRIPT):
            return jsonify({"success": False, "message": "爬虫脚本不存在"}), 500
        
        # 创建无代理环境
        no_proxy_env = os.environ.copy()
        keys_to_remove = ["http_proxy", "https_proxy", "all_proxy", "HTTP_PROXY", "HTTPS_PROXY"]
        for key in keys_to_remove:
            no_proxy_env.pop(key, None)
        
        # 异步运行爬虫
        def run_crawler():
            try:
                print(f"[CRAWLER] 启动爬虫: {CRAWLER_SCRIPT}")
                print(f"[CRAWLER] 关键词: {keyword}")
                print(f"[CRAWLER] 数据文件: {DATA_FILE}")
                
                # 修复Windows编码问题
                result = subprocess.run(
                    ["python", CRAWLER_SCRIPT, keyword],
                    env=no_proxy_env,
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace',  # 遇到编码错误时替换而不是报错
                    timeout=300,
                    cwd=os.path.dirname(os.path.dirname(__file__))  # 设置工作目录
                )
                
                print(f"[CRAWLER] 返回码: {result.returncode}")
                if result.stdout:
                    print(f"[CRAWLER] 标准输出:\n{result.stdout}")
                if result.stderr:
                    print(f"[CRAWLER] 错误输出:\n{result.stderr}")
                
                # 检查数据文件
                if os.path.exists(DATA_FILE):
                    print(f"[CRAWLER] 找到数据文件: {DATA_FILE}")
                    try:
                        with open(DATA_FILE, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            crawler_status["data"] = data
                            print(f"[CRAWLER] 成功加载 {len(data)} 条数据")
                    except Exception as e:
                        print(f"[CRAWLER] 读取数据文件失败: {e}")
                        crawler_status["error"] = f"读取数据文件失败: {str(e)}"
                else:
                    print(f"[CRAWLER] 数据文件不存在: {DATA_FILE}")
                    crawler_status["error"] = "爬虫未生成数据文件，可能未成功抓取数据"
                
                if result.returncode != 0:
                    crawler_status["error"] = f"爬虫执行失败 (返回码: {result.returncode})\n{result.stderr}"
                
                crawler_status["running"] = False
            except subprocess.TimeoutExpired:
                print("[CRAWLER] 爬虫执行超时")
                crawler_status["error"] = "爬虫执行超时（超过5分钟）"
                crawler_status["running"] = False
            except Exception as e:
                print(f"[CRAWLER] 异常: {e}")
                import traceback
                traceback.print_exc()
                crawler_status["error"] = str(e)
                crawler_status["running"] = False
        
        thread = threading.Thread(target=run_crawler)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            "success": True,
            "message": "爬虫已启动，请在弹出的浏览器窗口中登录闲鱼",
            "status": "running"
        })
        
    except Exception as e:
        crawler_status["running"] = False
        crawler_status["error"] = str(e)
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/status', methods=['GET'])
def get_status():
    """获取爬虫状态"""
    status = {
        "running": crawler_status["running"],
        "keyword": crawler_status["keyword"],
        "data_count": len(crawler_status["data"]),
        "error": crawler_status["error"]
    }
    # 添加调试信息
    if crawler_status["running"]:
        print(f"[STATUS] 爬虫运行中，关键词: {crawler_status['keyword']}, 已抓取: {len(crawler_status['data'])} 条")
    elif crawler_status["error"]:
        print(f"[STATUS] 爬虫已停止，错误: {crawler_status['error']}")
    elif len(crawler_status["data"]) > 0:
        print(f"[STATUS] 爬虫已完成，成功抓取 {len(crawler_status['data'])} 条数据")
    else:
        print(f"[STATUS] 爬虫状态: 未运行，数据: {len(crawler_status['data'])} 条")
    return jsonify(status)

@app.route('/api/analyze', methods=['POST'])
def analyze():
    """使用Gemini分析商品数据"""
    global gemini_client
    
    data = request.json
    api_key = data.get('api_key', '')
    
    if not gemini_client and api_key:
        success, message = init_gemini_client(api_key)
        if not success:
            return jsonify({"success": False, "message": f"Gemini初始化失败: {message}"}), 500
    
    if not gemini_client:
        return jsonify({"success": False, "message": "请先设置Gemini API Key"}), 400
    
    if not crawler_status["data"]:
        return jsonify({"success": False, "message": "没有可分析的数据，请先搜索商品"}), 400
    
    try:
        prompt = f"""
        任务：从以下闲鱼商品数据中，识别出高性价比的商品（评分 > 8分）。
        排除：商家/经销商发布的商品。
        输出格式：JSON数组，每个商品包含 title（标题）、price（价格）、reason（推荐理由）、score（评分1-10）。
        
        商品数据：
        {json.dumps(crawler_status["data"], ensure_ascii=False)}
        
        请只返回JSON数组，不要其他文字说明。
        """
        
        print(f"[ANALYZE] 开始分析 {len(crawler_status['data'])} 条商品数据")
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = gemini_client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                    config={"response_mime_type": "application/json"}
                )
                
                result = json.loads(response.text)
                print(f"[ANALYZE] 分析成功，找到 {len(result)} 个推荐商品")
                return jsonify({
                    "success": True,
                    "data": result
                })
                
            except Exception as e:
                error_str = str(e)
                print(f"[ANALYZE] 尝试 {attempt + 1}/{max_retries} 失败: {error_str}")
                
                # 如果是地区限制错误，可能是API Key注册地区的问题
                if "FAILED_PRECONDITION" in error_str or "location is not supported" in error_str.lower():
                    # 重新初始化客户端（可能代理配置有问题）
                    if attempt == 0:
                        print("[ANALYZE] 检测到地区限制，尝试重新初始化客户端...")
                        success, msg = init_gemini_client(api_key)
                        if not success:
                            # 提供本地分析作为备选
                            local_results = simple_local_analyze(crawler_status["data"])
                            return jsonify({
                                "success": False, 
                                "message": f"Gemini API 地区限制错误。\n\n根据 Google 官方文档，Gemini API 在部分地区不可用（包括中国大陆）。\n\n可能原因：\n1. API Key 在受限地区注册\n2. 即使使用代理，Gemini 可能通过 API Key 注册地区判断\n\n解决方案：\n1. 使用在支持地区（如美国、日本、新加坡等）注册的 API Key\n2. 使用 Vertex AI Gemini API（需要 GCP 账号）\n3. 使用本地简单分析（已自动应用，见下方结果）\n\n参考：https://ai.google.dev/gemini-api/docs/available-regions\n\n详细错误: {msg}",
                                "fallback_available": True,
                                "data": local_results
                            }), 500
                        # 重试一次
                        continue
                    else:
                        # 提供本地分析作为备选
                        local_results = simple_local_analyze(crawler_status["data"])
                        return jsonify({
                            "success": False,
                            "message": f"Gemini API 地区限制错误。\n\n根据 Google 官方文档，Gemini API 在部分地区不可用（包括中国大陆）。\n\n即使代理IP正常，Gemini可能通过API Key注册地区判断位置。\n\n建议：\n1. 使用在支持地区（如美国、日本、新加坡等）注册的API Key\n2. 或使用本地简单分析（已自动应用，见下方结果）\n\n参考：https://ai.google.dev/gemini-api/docs/available-regions",
                            "fallback_available": True,
                            "data": local_results
                        }), 500
                
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                else:
                    raise e
                    
    except Exception as e:
        error_str = str(e)
        print(f"[ANALYZE] 分析失败: {error_str}")
        return jsonify({"success": False, "message": f"分析失败: {error_str}"}), 500

if __name__ == '__main__':
    # 设置代理环境变量
    os.environ["http_proxy"] = "http://127.0.0.1:7890"
    os.environ["https_proxy"] = "http://127.0.0.1:7890"
    os.environ["all_proxy"] = "http://127.0.0.1:7890"
    
    print("🚀 后端服务器启动中...")
    print("📡 API地址: http://localhost:5000")
    print("🌐 前端地址: http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)

