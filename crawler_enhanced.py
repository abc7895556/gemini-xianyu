import sys
import os
import json
import time
import re
from playwright.sync_api import sync_playwright

# 设置输出编码为UTF-8，避免Windows GBK编码问题
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def run_crawler(keyword):
    """
    增强版爬虫：支持登录状态保持
    """
    results = []
    print(f"--- [START] 增强爬虫启动: {keyword} ---")
    
    keep_browser_open = False
    login_required = False

    with sync_playwright() as p:
        # 浏览器配置：强制直连，不使用代理
        browser = p.chromium.launch(
            headless=False,  # 显示浏览器窗口，方便登录
            args=['--no-proxy-server']
        )
        
        # 尝试加载已保存的登录状态
        context = None
        try:
            if os.path.exists("browser_state.json"):
                context = browser.new_context(
                    storage_state="browser_state.json",
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    viewport={"width": 1400, "height": 900}
                )
                print("[INFO] 已加载保存的登录状态")
        except:
            pass
        
        # 如果没有登录状态，创建新context
        if context is None:
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1400, "height": 900}
            )
        
        page = context.new_page()
        
        try:
            # 访问闲鱼搜索页面
            target_url = f"https://www.goofish.com/search?q={keyword}"
            print(f"[访问] {target_url}")
            page.goto(target_url, timeout=60000, wait_until="domcontentloaded")
            
            print("[等待] 等待页面加载（10秒）...")
            time.sleep(10)  # 给页面更多时间加载
            
            # 检查是否需要登录 - 使用多种方式检测
            print("[检查] 检查登录状态...")
            login_detected = False
            
            # 方法1: 检查登录按钮
            try:
                login_selectors = [
                    "text=登录",
                    "text=立即登录",
                    "a:has-text('登录')",
                    ".login-btn",
                    "[class*='login']"
                ]
                
                for selector in login_selectors:
                    try:
                        login_btn = page.locator(selector).first
                        if login_btn.is_visible(timeout=2000):
                            print(f"[登录] 检测到登录按钮: {selector}")
                            login_detected = True
                            login_required = True
                            keep_browser_open = True
                            break
                    except:
                        continue
            except Exception as e:
                print(f"[DEBUG] 登录按钮检测异常: {e}")
            
            # 方法2: 检查页面内容是否显示需要登录
            try:
                page_content = page.content()
                if "登录" in page_content and ("立即登录" in page_content or "请登录" in page_content):
                    # 再检查是否真的需要登录（可能只是页面上的文字）
                    if not login_detected:
                        print("[登录] 页面内容显示可能需要登录")
                        # 给用户一些时间手动检查
                        login_required = True
                        keep_browser_open = True
            except:
                pass
            
            # 如果检测到需要登录，等待用户登录
            if login_required:
                print("\n" + "="*50)
                print("[登录] 检测到需要登录！")
                print("="*50)
                print("[步骤] 操作步骤：")
                print("  1. 在浏览器窗口中点击登录按钮")
                print("  2. 完成登录（扫码或输入账号密码）")
                print("  3. 登录成功后，关闭浏览器窗口或等待自动继续")
                print("="*50)
                print("[等待] 等待登录中...（最多等待5分钟，您可以随时关闭窗口）")
                print()
                
                # 等待用户登录（最多等待5分钟）
                login_success = False
                for i in range(300):  # 5分钟 = 300秒
                    time.sleep(1)
                    try:
                        # 检查页面是否已登录（登录按钮消失）
                        page_content = page.content()
                        # 检查是否有用户信息或登录按钮消失
                        if "登录" not in page_content or page.locator("text=登录").count() == 0:
                            # 再次确认：尝试查找用户相关元素
                            try:
                                # 如果找不到登录按钮，可能已登录
                                if page.locator("text=登录").count() == 0:
                                    print("[成功] 登录按钮已消失，可能已登录成功！")
                                    login_success = True
                                    login_required = False
                                    # 保存登录状态
                                    try:
                                        context.storage_state(path="browser_state.json")
                                        print("[成功] 登录状态已保存")
                                    except:
                                        pass
                                    break
                            except:
                                pass
                        
                        # 检查浏览器窗口是否被关闭
                        if page.is_closed():
                            print("[成功] 浏览器窗口已关闭，假设登录完成")
                            login_success = True
                            login_required = False
                            break
                    except Exception as e:
                        # 如果页面出错，继续等待
                        pass
                    
                    # 每30秒提示一次
                    if i > 0 and i % 30 == 0:
                        remaining = (300 - i) // 60
                        print(f"[等待] 仍在等待登录...（剩余约{remaining}分钟）")
                
                if not login_success and login_required:
                    print("[警告] 登录等待超时，继续尝试爬取...")
            else:
                print("[INFO] 未检测到登录需求，可能已登录或无需登录")
            
            # 等待商品列表加载
            print("[检查] 等待商品列表加载...")
            goods_loaded = False
            try:
                page.wait_for_selector(r"text=/¥\s*\d+/", timeout=15000)
                print("[成功] 商品列表已加载")
                goods_loaded = True
            except:
                print("[警告] 未检测到商品列表，可能原因：")
                print("  - 需要登录")
                print("  - 页面结构变化")
                print("  - 网络问题")
                keep_browser_open = True
                
                # 如果没加载到商品，给用户更多时间
                if not goods_loaded:
                    print("[等待] 等待30秒，请检查是否需要登录...")
                    time.sleep(30)
            
            # 滚动页面加载更多商品
            print("[滚动] 滚动页面加载商品...")
            for i in range(5):
                page.evaluate("window.scrollBy(0, document.body.scrollHeight/2)")
                time.sleep(1.5)
            
            # 提取商品数据
            print("[提取] 开始提取商品数据...")
            
            # 尝试多种选择器来查找商品
            price_elements = []
            try:
                # 方法1: 使用价格文本
                price_elements = page.locator(r"text=/¥\s*\d+/").all()
                print(f"[调试] 方法1找到 {len(price_elements)} 个价格元素")
            except Exception as e:
                print(f"[调试] 方法1失败: {e}")
            
            # 如果方法1没找到，尝试其他方法
            if len(price_elements) == 0:
                try:
                    # 方法2: 查找包含价格的元素
                    price_elements = page.locator("[class*='price'], [class*='Price']").all()
                    print(f"[调试] 方法2找到 {len(price_elements)} 个价格元素")
                except:
                    pass
            
            if len(price_elements) == 0:
                # 方法3: 尝试查找商品卡片
                try:
                    cards = page.locator("[class*='item'], [class*='card'], [class*='goods']").all()
                    print(f"[调试] 方法3找到 {len(cards)} 个商品卡片")
                    if len(cards) > 0:
                        price_elements = cards
                except:
                    pass
            
            # 如果还是没找到，尝试获取页面所有文本内容进行分析
            if len(price_elements) == 0:
                print("[调试] 尝试从页面内容中提取...")
                try:
                    page_text = page.inner_text("body")
                    # 查找所有价格模式
                    prices = re.findall(r'[¥￥]\s*([\d\.]+)', page_text)
                    print(f"[调试] 从页面文本中找到 {len(prices)} 个价格")
                    if len(prices) > 0:
                        # 尝试提取商品信息
                        # 这里可以进一步优化
                        pass
                except Exception as e:
                    print(f"[调试] 页面文本提取失败: {e}")
            
            seen_titles = set()
            extracted_count = 0
            
            for idx, price_el in enumerate(price_elements[:50]):  # 最多提取50个商品
                try:
                    # 尝试多种方式获取商品信息
                    card_text = None
                    
                    # 方法1: 向上查找父元素
                    try:
                        card_text = price_el.locator("..").locator("..").inner_text()
                    except:
                        try:
                            card_text = price_el.locator("..").inner_text()
                        except:
                            card_text = price_el.inner_text()
                    
                    if not card_text or len(card_text.strip()) < 5:
                        continue
                    
                    # 提取价格
                    price_match = re.search(r'[¥￥]\s*([\d\.]+)', card_text)
                    if not price_match:
                        continue
                    price = price_match.group(1)
                    
                    # 提取标题（最长的文本行，排除价格行）
                    lines = [l.strip() for l in card_text.split('\n') if len(l.strip()) > 4]
                    # 过滤掉包含价格、付款、已售等关键词的行
                    lines = [l for l in lines if not any(kw in l for kw in ["¥", "￥", "人付款", "已售", "浏览", "想要"])] 
                    
                    if not lines:
                        continue
                    
                    title = max(lines, key=len)
                    
                    # 进一步过滤无效标题
                    if len(title) < 5 or any(kw in title for kw in ["¥", "￥", "人付款", "已售", "浏览", "想要", "立即"]):
                        continue
                    
                    # 去重
                    if title not in seen_titles:
                        seen_titles.add(title)
                        results.append({
                            "title": title,
                            "price": price,
                            "desc": "闲鱼商品"
                        })
                        extracted_count += 1
                        if extracted_count <= 5:  # 只打印前5个
                            print(f"[调试] 提取商品 {extracted_count}: {title[:30]}... - ¥{price}")
                except Exception as e:
                    if idx < 3:  # 只打印前3个错误
                        print(f"[调试] 提取第 {idx+1} 个商品时出错: {e}")
                    continue
            
            print(f"[成功] 成功提取 {len(results)} 个商品")
            
            # 如果没提取到数据，保存页面截图和HTML用于调试
            if len(results) == 0:
                print("[警告] 未提取到任何商品数据")
                try:
                    screenshot_path = os.path.join(os.path.dirname(__file__), "debug_screenshot.png")
                    page.screenshot(path=screenshot_path)
                    print(f"[调试] 已保存页面截图到: {screenshot_path}")
                except:
                    pass

        except Exception as e:
            print(f"[错误] 爬虫错误: {e}")
            keep_browser_open = True
        
        finally:
            # 保存数据（无论是否有结果都要保存）
            data_file = os.path.join(os.path.dirname(__file__), "temp_data.json")
            print(f"[保存] 保存数据到: {data_file}")
            print(f"[统计] 提取到 {len(results)} 个商品")
            with open(data_file, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False)
            print(f"[成功] 数据已保存到 {data_file}")
            
            # 如果结果为空，给用户提示
            if len(results) == 0:
                print("\n[警告] 未提取到商品数据")
                print("可能原因：")
                print("  1. 需要登录闲鱼账号（请重新运行并完成登录）")
                print("  2. 页面结构发生变化")
                print("  3. 网络连接问题")
                print("  4. 搜索关键词无结果")
            
            # 如果还需要登录，再等待一下
            if login_required and keep_browser_open:
                print("\n[暂停] 浏览器窗口保持打开，等待登录...")
                print("[提示] 登录后可以关闭浏览器窗口，程序会自动保存登录状态并继续")
                print("[提示] 或者等待5分钟后程序会自动继续")
                
                # 再等待一段时间让用户完成登录
                for i in range(60):  # 额外等待1分钟
                    time.sleep(1)
                    try:
                        if page.is_closed():
                            print("[成功] 浏览器窗口已关闭")
                            break
                    except:
                        break
            
            # 关闭浏览器前，再尝试保存登录状态
            if not login_required:
                try:
                    context.storage_state(path="browser_state.json")
                    print("[保存] 已保存登录状态")
                except:
                    pass
            
            # 关闭浏览器
            print("\n[关闭] 准备关闭浏览器...")
            time.sleep(2)  # 给一点时间让用户看到消息
            try:
                if browser.is_connected():
                    browser.close()
                    print("[成功] 浏览器已关闭")
            except Exception as e:
                print(f"[警告] 关闭浏览器时出错: {e}")

if __name__ == "__main__":
    import os
    keyword = sys.argv[1] if len(sys.argv) > 1 else "iPhone"
    run_crawler(keyword)

