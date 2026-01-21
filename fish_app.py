import os
import sys
import streamlit as st
import json
import time
import subprocess
import requests 
from google import genai

# --- 1. 环境变量配置 (双重保险) ---
os.environ["http_proxy"] = "http://127.0.0.1:7890"
os.environ["https_proxy"] = "http://127.0.0.1:7890"
os.environ["all_proxy"]   = "http://127.0.0.1:7890"

st.set_page_config(page_title="闲鱼神搜 Pro", layout="wide")
st.title("🔍 闲鱼高性价比商品 AI 筛选器")
st.caption("引擎：Gemini 2.5 Flash | 修复：Client 显式代理注入")

api_key = st.sidebar.text_input("Gemini API Key", type="password")

# --- 🔍 网络自检 ---
def check_proxy_status():
    try:
        resp = requests.get("http://ip-api.com/json/", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            return True, data.get("country"), data.get("query")
    except Exception as e:
        return False, str(e), "Unknown"
    return False, "Unknown", "Unknown"

def run_external_crawler(keyword):
    if not os.path.exists("crawler.py"):
        st.error("❌ 找不到 crawler.py！")
        return []
    
    cmd = ["python", "crawler.py", keyword]
    
    # 爬虫分流：剥离代理，强制直连
    no_proxy_env = os.environ.copy()
    keys_to_remove = ["http_proxy", "https_proxy", "all_proxy", "HTTP_PROXY", "HTTPS_PROXY"]
    for key in keys_to_remove:
        no_proxy_env.pop(key, None)
            
    try:
        result = subprocess.run(
            cmd, check=True, shell=True, env=no_proxy_env, capture_output=True, text=True
        )
        print(result.stdout)
        
        if os.path.exists("temp_data.json"):
            try:
                with open("temp_data.json", "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                return []
        else:
            return []
    except subprocess.CalledProcessError as e:
        st.error("❌ 爬虫运行失败")
        st.code(e.stderr)
        return []

if api_key:
    try:
        # ======================================================================
        # 🚨🚨🚨 绝杀修改：显式注入代理配置 🚨🚨🚨
        # 我们不再只依赖 os.environ，而是直接告诉 Client 用哪个代理
        # ======================================================================
        client = genai.Client(
            api_key=api_key,
            http_options={
                'proxy': 'http://127.0.0.1:7890',  # 强制指定代理地址
                'timeout': 30.0                    # 增加超时时间防止断连
            }
        )
    except Exception as e:
        st.error(f"API Key 格式错误: {e}")

    keyword = st.text_input("搜索关键词", "iPhone 15 Pro")
    
    if st.button("启动分析"):
        
        # 1. 自检
        with st.spinner("🔍 正在检测网络环境..."):
            status, country, ip_addr = check_proxy_status()
            
            if not status:
                st.error("❌ 无法连接代理！请检查 FlClash 是否开启。")
                st.stop()
            
            # 如果是 Rule 模式，这里可能会误判，所以必须强制 Global
            if country == "China":
                st.error(f"❌ 你的 IP 依然是 中国 ({ip_addr})！")
                st.warning("👉 请务必去 FlClash 把【规则】改为【全局 (Global)】！")
                st.stop()
                
            st.success(f"✅ 网络环境合格！IP 归属地：{country} ({ip_addr})")

        # 2. 爬虫
        with st.spinner("🚀 正在启动视觉爬虫 (直连模式)..."):
            raw_data = run_external_crawler(keyword)
        
        # 3. AI 分析
        if raw_data:
            st.success(f"提取到 {len(raw_data)} 条数据")
            
            with st.spinner("🤖 Gemini 2.5 正在分析 (已强制代理注入)..."):
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        prompt = f"""
                        Task: Identify undervalued items (score > 8).
                        Exclude: Dealers.
                        Output JSON: [{{ "title": "xx", "price": "xx", "reason": "xx", "score": 9 }}]
                        Data: {json.dumps(raw_data, ensure_ascii=False)}
                        """
                        
                        response = client.models.generate_content(
                            model="gemini-2.5-flash", 
                            contents=prompt,
                            config={"response_mime_type": "application/json"}
                        )
                        
                        st.subheader("🎯 推荐结果")
                        st.json(json.loads(response.text))
                        break 
                        
                    except Exception as e:
                        err_str = str(e)
                        if "FAILED_PRECONDITION" in err_str:
                             st.error("❌ 还是提示地区不支持？")
                             st.warning("这就只剩一种可能：你的 FlClash 依然是【规则模式】。")
                             st.markdown("### ⚡️ 请立即去 FlClash 切换为【全局 / Global】模式")
                             st.stop()
                        elif "429" in err_str:
                            st.warning("配额耗尽，等待重试...")
                            time.sleep(5)
                        elif attempt < max_retries - 1:
                            st.warning("连接波动，重试中...")
                            time.sleep(2)
                        else:
                            st.error("分析失败")
                            st.exception(e)
        else:
            st.warning("未抓取到数据，请检查浏览器窗口。")
else:
    st.info("💡 请输入 API Key")
