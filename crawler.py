import sys
import json
import time
import re
from playwright.sync_api import sync_playwright

def run_crawler(keyword):
    results = []
    print(f"--- [START] Crawler: {keyword} ---")
    
    keep_browser_open = False

    with sync_playwright() as p:
        # ======================================================================
        # [3] 浏览器强制直连逻辑
        # ======================================================================
        # args=['--no-proxy-server'] 告诉 Chrome 忽略一切系统代理/TUN 设置
        browser = p.chromium.launch(
            headless=False,
            args=['--no-proxy-server'] 
        )
        
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1400, "height": 900}
        )
        page = context.new_page()
        
        try:
            target_url = f"https://www.goofish.com/search?q={keyword}"
            print(f"Visiting: {target_url}")
            page.goto(target_url, timeout=60000)
            
            print(">>> Waiting for page load...")
            
            try:
                # 使用 r"" 原始字符串避免正则警告
                page.wait_for_selector(r"text=/¥\s*\d+/", timeout=15000)
                print("[OK] Page loaded.")
            except:
                print("[WARN] Wait timeout. Manual check needed.")
                keep_browser_open = True
            
            # 滚动
            for i in range(3):
                page.evaluate("window.scrollBy(0, document.body.scrollHeight/2)")
                time.sleep(1)
            
            print("Extracting data...")
            price_elements = page.locator(r"text=/¥\s*\d+/").all()
            seen_titles = set()
            
            for price_el in price_elements[:30]:
                try:
                    card_text = price_el.locator("..").locator("..").inner_text()
                    price_match = re.search(r'[¥￥]\s*([\d\.]+)', card_text)
                    if not price_match: continue
                    price = price_match.group(1)
                    
                    lines = [l.strip() for l in card_text.split('\n') if len(l.strip()) > 4]
                    title = max(lines, key=len) if lines else "Unknown"
                    
                    if "¥" in title or "人付款" in title: continue

                    if title not in seen_titles:
                        seen_titles.add(title)
                        results.append({"title": title, "price": price, "desc": "Visual"})
                except:
                    continue

        except Exception as e:
            print(f"[ERROR] Crawler Error: {e}")
            keep_browser_open = True
        
        finally:
            print(f"[INFO] Scraped: {len(results)}")
            
            if len(results) == 0 or keep_browser_open:
                print("\n[PAUSED] Window open for debugging.")
                try:
                    while True:
                        time.sleep(1)
                        if page.is_closed(): break
                except:
                    pass
            else:
                print("[SUCCESS] Closing in 3s...")
                time.sleep(3)
                browser.close()

    with open("temp_data.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False)

if __name__ == "__main__":
    kw = sys.argv[1] if len(sys.argv) > 1 else "Bicycle"
    run_crawler(kw)
