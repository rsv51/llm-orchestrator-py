# 管理员密钥设置指南

## 问题症状

- ✗ 登录时显示"管理员密钥错误"
- ✗ 使用环境变量设置的密码登录失败
- ✗ 默认密码也无法登录

## 根本原因

之前的配置中 `ADMIN_KEY` 的默认值是 `None`,导致无论设置什么密钥都无法通过验证。

## 已修复的问题

1. **config.py** - `admin_key` 现在有默认值: `admin-secret-key-change-this`
2. **dependencies.py** - 改进了验证逻辑和错误日志
3. **.env.example** - 添加了 `ADMIN_KEY` 配置项

## 如何设置管理员密钥

### 方法 1: Docker 环境变量 (推荐)

编辑 `docker-compose.yml`:

```yaml
services:
  app:
    environment:
      - ADMIN_KEY=your-secure-password-here  # 改成你的密码
```

### 方法 2: .env 文件

创建或编辑 `.env` 文件:

```bash
# 复制示例配置
cp .env.example .env

# 编辑 .env 文件
nano .env
```

添加或修改:

```bash
ADMIN_KEY=your-secure-password-here
```

### 方法 3: 使用默认密钥 (仅测试)

如果未设置环境变量,默认密钥为:

```
admin-secret-key-change-this
```

⚠️ **警告**: 生产环境必须修改默认密钥!

## 重启服务

修改配置后需要重启:

```bash
# Docker 部署
docker-compose restart

# 或重新构建
docker-compose down
docker-compose up -d --build
```

## 验证设置

1. 检查容器日志:
```bash
docker-compose logs app | grep -i admin
```

2. 访问登录页面:
```
https://your-domain/admin-ui/login.html
```

3. 输入你设置的 ADMIN_KEY

4. 如果登录成功,会自动跳转到管理界面

## 调试技巧

### 查看当前配置的密钥 (前8位)

```bash
docker-compose exec app python -c "from app.core.config import settings; print(f'Admin key starts with: {settings.admin_key[:8]}...')"
```

### 查看容器环境变量

```bash
docker-compose exec app env | grep ADMIN
```

### 查看详细日志

```bash
docker-compose logs -f app
```

在日志中搜索:
- `Invalid admin key attempted` - 密钥错误
- `Expected admin key starts with` - 服务器期望的密钥前缀

## 安全建议

1. **使用强密钥**
   - 至少 20 个字符
   - 包含大小写字母、数字和特殊字符
   - 使用密码生成器

2. **定期更换**
   - 建议每 90 天更换一次

3. **不要共享**
   - 每个管理员使用独立的密钥(未来版本支持)

4. **使用 HTTPS**
   - 生产环境必须使用 HTTPS
   - 避免密钥在网络传输中被窃取

## 生成强密钥示例

使用 Python 生成:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

使用 OpenSSL 生成:
```bash
openssl rand -base64 32
```

## 常见问题

### Q: 我忘记了管理员密钥怎么办?

A: 修改 `docker-compose.yml` 或 `.env` 文件,设置新密钥,然后重启服务。

### Q: 可以设置多个管理员密钥吗?

A: 当前版本只支持单一管理员密钥。多用户支持将在未来版本中添加。

### Q: 密钥可以包含特殊字符吗?

A: 可以,但建议使用 URL 安全的字符 (字母、数字、`-`、`_`)。

### Q: 如何验证密钥是否生效?

A: 查看容器日志,在登录失败时会显示"Expected admin key starts with: xxx"。

## 技术说明

### 验证流程

1. 用户在登录页面输入密钥
2. 前端通过 `Authorization: Bearer {key}` 发送到后端
3. 后端 `verify_admin_key()` 验证密钥
4. 验证通过则返回 200,失败返回 403

### 相关文件

- `app/core/config.py` - 配置定义
- `app/api/dependencies.py` - 验证逻辑
- `web/login.html` - 登录界面
- `web/app.js` - 前端验证逻辑

## 支持

如有问题,请检查:
1. Docker 容器日志
2. 浏览器控制台 (F12)
3. 网络请求 (F12 -> Network)

确认密钥已正确设置并重启服务。