# 闲鱼商品智能分析系统

基于 Flask 后端 + HTML 前端的闲鱼商品爬取与 AI 分析系统，使用 Gemini AI 进行高性价比商品推荐。

## 功能特点

- 🎨 现代化 Web 界面
- 🔐 支持闲鱼登录（浏览器窗口）
- 🕷️ 自动爬取闲鱼商品数据
- 🤖 使用 Gemini AI 分析商品性价比
- 💾 自动保存登录状态

## 安装步骤

### 1. 安装 Python 依赖

```bash
pip install -r requirements.txt
```

### 2. 安装 Playwright 浏览器

```bash
playwright install chromium
```

### 3. 配置代理（可选）

如果需要在代理环境下使用 Gemini API，请确保代理运行在 `http://127.0.0.1:7890`

## 使用方法

### 启动后端服务器

```bash
cd backend
python app.py
```

服务器将在 `http://localhost:5000` 启动

### 访问前端界面

在浏览器中打开：`http://localhost:5000`

### 使用流程

1. **输入 Gemini API Key**
   - 在界面中输入您的 Google Gemini API Key

2. **输入搜索关键词**
   - 例如：iPhone 15 Pro、笔记本电脑等

3. **点击"开始搜索与分析"**
   - 系统会弹出浏览器窗口
   - **首次使用需要登录闲鱼账号**
   - 登录后，爬虫会自动抓取商品数据
   - 登录状态会自动保存，下次使用无需重复登录

4. **等待分析完成**
   - 系统会自动使用 Gemini AI 分析商品
   - 显示高性价比商品推荐结果

## 项目结构

```
.
├── backend/
│   └── app.py              # Flask 后端服务器
├── frontend/
│   └── index.html          # 前端界面
├── crawler_enhanced.py     # 增强版爬虫（支持登录）
├── requirements.txt        # Python 依赖
└── README.md              # 说明文档
```

## 注意事项

1. **首次登录**：首次使用时需要在弹出的浏览器窗口中手动登录闲鱼账号
2. **登录状态**：登录状态会保存在 `browser_state.json` 文件中
3. **代理设置**：Gemini API 需要代理访问，默认使用 `http://127.0.0.1:7890`
4. **浏览器窗口**：爬虫会显示浏览器窗口，方便查看登录状态和调试

## 技术栈

- **后端**：Flask + Flask-CORS
- **前端**：HTML + CSS + JavaScript
- **爬虫**：Playwright
- **AI 分析**：Google Gemini 2.5 Flash

## 许可证

MIT License


