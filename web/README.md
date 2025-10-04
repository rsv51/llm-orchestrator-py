# Web 管理界面

LLM Orchestrator 的 Web 管理控制台,提供可视化的系统管理功能。

## 功能特性

### 🎯 仪表盘
- 实时系统统计 (总请求数、成功率、平均延迟、Token 使用)
- 系统健康状态监控 (数据库、缓存、提供商)
- 提供商健康状态列表

### 🔧 提供商管理
- 查看所有提供商列表
- 添加新提供商 (OpenAI、Anthropic、Gemini)
- 启用/禁用提供商
- 删除提供商
- 实时状态更新

### 📊 模型配置
- 查看可用模型列表
- 模型详细信息展示

### 📝 请求日志
- 分页显示请求日志
- 筛选和搜索功能
- 详细的请求信息 (模型、提供商、Token、延迟、状态)

### ⚙️ 系统设置
- API 密钥配置
- 管理员密钥配置
- 本地存储设置

## 访问方式

### 本地开发

1. **启动 API 服务**
```bash
cd llm-orchestrator-py
python -m uvicorn app.main:app --reload
```

2. **访问管理界面**
```
http://localhost:8000/admin-ui/
```

### Docker 部署

使用 Docker Compose 启动后,访问:
```
http://localhost:8000/admin-ui/
```

## 使用指南

### 首次配置

1. 打开管理界面
2. 进入 "系统设置" 标签页
3. 配置管理员密钥 (默认: `admin-key`)
4. 保存设置

### 添加提供商

1. 进入 "提供商管理" 标签页
2. 点击 "➕ 添加提供商" 按钮
3. 填写提供商信息:
   - **名称**: 提供商的唯一标识名称
   - **类型**: 选择 OpenAI、Anthropic 或 Gemini
   - **API 密钥**: 提供商的 API 密钥
   - **基础 URL**: (可选) 自定义 API 端点
   - **优先级**: 数值越大优先级越高
   - **启用**: 是否立即启用
4. 点击 "添加" 按钮

### 查看系统状态

1. 进入 "仪表盘" 标签页
2. 查看实时统计数据
3. 监控提供商健康状态
4. 点击 "检查健康" 强制刷新状态

### 查看请求日志

1. 进入 "请求日志" 标签页
2. 查看最近的请求记录
3. 点击 "🔄 刷新" 更新日志

## 技术架构

### 前端技术
- **纯 JavaScript**: 无框架依赖
- **原生 CSS**: 现代化响应式设计
- **Fetch API**: RESTful API 调用
- **LocalStorage**: 配置持久化

### 设计特点
- 🎨 现代化 UI 设计
- 📱 响应式布局
- 🌙 深色模式友好
- ⚡ 快速加载
- 🔒 安全的 API 调用

### 文件结构
```
web/
├── index.html      # 主页面 (763 行)
├── app.js          # JavaScript 逻辑 (395 行)
└── README.md       # 本文档
```

## API 端点

管理界面使用以下 API 端点:

### 公共端点
- `GET /health` - 健康检查
- `GET /v1/models` - 获取模型列表

### 管理端点 (需要管理员密钥)
- `GET /admin/providers` - 获取提供商列表
- `POST /admin/providers` - 添加提供商
- `PATCH /admin/providers/{id}` - 更新提供商
- `DELETE /admin/providers/{id}` - 删除提供商
- `GET /admin/health` - 系统健康状态
- `GET /admin/stats` - 系统统计
- `GET /admin/logs` - 请求日志

## 安全配置

### API 密钥管理

管理界面使用两种密钥:

1. **API 密钥** (`apiKey`)
   - 用于访问普通 API 端点
   - 存储在 LocalStorage
   - 可在系统设置中配置

2. **管理员密钥** (`adminKey`)
   - 用于访问管理员 API 端点
   - 默认值: `admin-key`
   - 存储在 LocalStorage
   - 可在系统设置中配置

### 配置管理员密钥

在 `.env` 文件中设置:
```env
ADMIN_KEY=your-secure-admin-key
```

在管理界面中配置:
1. 进入 "系统设置"
2. 输入管理员密钥
3. 点击 "保存设置"

### 安全建议

- ✅ 在生产环境中更改默认管理员密钥
- ✅ 使用 HTTPS 访问管理界面
- ✅ 限制管理界面的网络访问
- ✅ 定期更换 API 密钥
- ✅ 不要在公共环境中暴露管理界面

## 浏览器兼容性

支持所有现代浏览器:
- ✅ Chrome/Edge 90+
- ✅ Firefox 88+
- ✅ Safari 14+
- ✅ Opera 76+

## 常见问题

### Q: 无法连接到 API

**解决方法:**
1. 确认 API 服务正在运行
2. 检查 `config.apiBaseUrl` 配置
3. 查看浏览器控制台的错误信息

### Q: 提示认证失败

**解决方法:**
1. 检查管理员密钥是否正确
2. 在系统设置中重新配置密钥
3. 清除浏览器 LocalStorage 后重新配置

### Q: 看不到提供商健康状态

**解决方法:**
1. 确认已添加提供商
2. 点击 "检查健康" 按钮
3. 等待健康检查服务启动 (启动时自动运行)

### Q: 请求日志为空

**解决方法:**
1. 确认已有 API 请求记录
2. 检查数据库连接
3. 查看 API 日志了解详情

## 开发指南

### 修改配置

编辑 `app.js` 中的 `config` 对象:

```javascript
const config = {
    apiBaseUrl: 'http://localhost:8000',  // API 基础 URL
    apiKey: localStorage.getItem('apiKey') || '',
    adminKey: localStorage.getItem('adminKey') || 'admin-key'
};
```

### 添加新功能

1. 在 `index.html` 中添加 UI 元素
2. 在 `app.js` 中添加对应的 JavaScript 逻辑
3. 使用 `utils.request()` 调用 API
4. 使用 `utils.showAlert()` 显示提示

### 自定义样式

在 `index.html` 的 `<style>` 标签中修改 CSS 变量:

```css
:root {
    --primary-color: #2563eb;      /* 主色调 */
    --success-color: #10b981;      /* 成功色 */
    --danger-color: #ef4444;       /* 危险色 */
    --bg-color: #f9fafb;           /* 背景色 */
    /* ... 更多变量 */
}
```

## 更新日志

### v1.0.0 (2025-10-04)
- ✅ 初始版本发布
- ✅ 仪表盘功能
- ✅ 提供商管理
- ✅ 模型配置查看
- ✅ 请求日志查看
- ✅ 系统设置

## 反馈与支持

如有问题或建议,请查看项目主文档或提交 Issue。

---

**管理界面版本**: 1.0.0  
**最后更新**: 2025-10-04  
**维护状态**: ✅ 活跃维护中