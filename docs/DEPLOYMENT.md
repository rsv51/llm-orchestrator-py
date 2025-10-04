# LLM Orchestrator 部署指南

本文档详细说明如何部署 LLM Orchestrator 项目。

## 目录

- [环境要求](#环境要求)
- [Docker部署(推荐)](#docker部署推荐)
- [手动部署](#手动部署)
- [生产环境配置](#生产环境配置)
- [监控和维护](#监控和维护)

## 环境要求

### Docker部署
- Docker 20.10+
- Docker Compose 2.0+
- 2GB+ 内存
- 10GB+ 磁盘空间

### 手动部署
- Python 3.11+
- Redis 7.0+
- MySQL 8.0+ (可选,默认使用SQLite)
- 2GB+ 内存

## Docker部署(推荐)

### 1. 快速启动

```bash
# 克隆项目
git clone <repository-url>
cd llm-orchestrator-py

# 复制环境配置文件
cp .env.example .env

# 编辑配置(根据需要修改)
nano .env

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f app
```

### 2. 验证部署

```bash
# 检查服务状态
docker-compose ps

# 测试健康检查
curl http://localhost:8000/health

# 查看API文档(开发环境)
# 访问 http://localhost:8000/docs
```

### 3. 常用命令

```bash
# 停止服务
docker-compose stop

# 重启服务
docker-compose restart

# 查看日志
docker-compose logs -f app

# 进入容器
docker-compose exec app bash

# 更新镜像
docker-compose pull
docker-compose up -d --build

# 清理数据
docker-compose down -v
```

## 手动部署

### 1. 安装依赖

```bash
# 安装Python依赖
pip install -r requirements.txt

# 安装Redis(Ubuntu/Debian)
sudo apt-get install redis-server
sudo systemctl start redis-server
sudo systemctl enable redis-server

# 安装MySQL(可选)
sudo apt-get install mysql-server
```

### 2. 配置环境变量

```bash
# 创建.env文件
cp .env.example .env

# 编辑配置
nano .env
```

关键配置项:
```env
APP_ENV=production
APP_DEBUG=false
DATABASE_TYPE=sqlite  # 或 mysql
DATABASE_URL=sqlite+aiosqlite:///./data/llm_orchestrator.db
REDIS_ENABLED=true
REDIS_URL=redis://localhost:6379/0
LOG_LEVEL=INFO
```

### 3. 初始化数据库

```bash
# 创建数据目录
mkdir -p data logs

# 运行数据库迁移(首次启动会自动创建表)
python -m app.main
```

### 4. 启动服务

```bash
# 开发环境
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 生产环境(使用Gunicorn)
gunicorn app.main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --timeout 300 \
    --access-logfile logs/access.log \
    --error-logfile logs/error.log
```

### 5. 配置Systemd服务(生产环境)

创建 `/etc/systemd/system/llm-orchestrator.service`:

```ini
[Unit]
Description=LLM Orchestrator API Service
After=network.target redis.service

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/opt/llm-orchestrator
Environment="PATH=/opt/llm-orchestrator/venv/bin"
ExecStart=/opt/llm-orchestrator/venv/bin/gunicorn app.main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --timeout 300
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启用服务:
```bash
sudo systemctl daemon-reload
sudo systemctl enable llm-orchestrator
sudo systemctl start llm-orchestrator
sudo systemctl status llm-orchestrator
```

## 生产环境配置

### 1. 反向代理(Nginx)

创建 `/etc/nginx/sites-available/llm-orchestrator`:

```nginx
upstream llm_orchestrator {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name your-domain.com;

    # 请求体大小限制
    client_max_body_size 10M;

    # 超时设置
    proxy_connect_timeout 300s;
    proxy_send_timeout 300s;
    proxy_read_timeout 300s;

    location / {
        proxy_pass http://llm_orchestrator;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket支持
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # 健康检查端点(不记录日志)
    location /health {
        proxy_pass http://llm_orchestrator;
        access_log off;
    }
}
```

启用配置:
```bash
sudo ln -s /etc/nginx/sites-available/llm-orchestrator /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 2. SSL证书(Let's Encrypt)

```bash
# 安装Certbot
sudo apt-get install certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d your-domain.com

# 自动续期(已自动配置)
sudo certbot renew --dry-run
```

### 3. 防火墙配置

```bash
# 允许HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# 如果需要直接访问应用端口
sudo ufw allow 8000/tcp

# 启用防火墙
sudo ufw enable
```

### 4. 数据库优化(MySQL)

```sql
-- 创建数据库
CREATE DATABASE llm_orchestrator CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 创建用户
CREATE USER 'llm_orchestrator'@'localhost' IDENTIFIED BY 'your-secure-password';
GRANT ALL PRIVILEGES ON llm_orchestrator.* TO 'llm_orchestrator'@'localhost';
FLUSH PRIVILEGES;

-- 优化配置
SET GLOBAL max_connections = 200;
SET GLOBAL wait_timeout = 28800;
SET GLOBAL interactive_timeout = 28800;
```

更新.env配置:
```env
DATABASE_TYPE=mysql
DATABASE_URL=mysql+aiomysql://llm_orchestrator:your-secure-password@localhost/llm_orchestrator
```

### 5. Redis优化

编辑 `/etc/redis/redis.conf`:

```conf
# 最大内存
maxmemory 512mb
maxmemory-policy allkeys-lru

# 持久化
save 900 1
save 300 10
save 60 10000

# 密码保护
requirepass your-redis-password
```

更新.env配置:
```env
REDIS_URL=redis://:your-redis-password@localhost:6379/0
```

## 监控和维护

### 1. 日志管理

```bash
# 查看应用日志
tail -f logs/app.log

# 查看访问日志
tail -f logs/access.log

# 日志轮转配置(/etc/logrotate.d/llm-orchestrator)
/opt/llm-orchestrator/logs/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0644 www-data www-data
    sharedscripts
    postrotate
        systemctl reload llm-orchestrator
    endscript
}
```

### 2. 健康检查

```bash
# 手动健康检查
curl http://localhost:8000/health

# 查看系统状态(需要管理员密钥)
curl -H "Authorization: Bearer YOUR_ADMIN_KEY" \
    http://localhost:8000/admin/health

# 查看统计信息
curl -H "Authorization: Bearer YOUR_ADMIN_KEY" \
    http://localhost:8000/admin/stats
```

### 3. 备份策略

```bash
# 数据库备份脚本
#!/bin/bash
BACKUP_DIR="/backup/llm-orchestrator"
DATE=$(date +%Y%m%d_%H%M%S)

# 备份SQLite
cp data/llm_orchestrator.db "$BACKUP_DIR/db_$DATE.db"

# 备份MySQL
mysqldump -u llm_orchestrator -p llm_orchestrator > "$BACKUP_DIR/db_$DATE.sql"

# 清理30天前的备份
find "$BACKUP_DIR" -name "*.db" -mtime +30 -delete
find "$BACKUP_DIR" -name "*.sql" -mtime +30 -delete
```

定时任务(crontab):
```bash
# 每天凌晨2点备份
0 2 * * * /opt/llm-orchestrator/scripts/backup.sh
```

### 4. 性能监控

使用Prometheus + Grafana:

```yaml
# docker-compose.monitoring.yml
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    volumes:
      - grafana_data:/var/lib/grafana
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin

volumes:
  prometheus_data:
  grafana_data:
```

### 5. 更新部署

```bash
# Docker部署更新
cd llm-orchestrator-py
git pull
docker-compose down
docker-compose build
docker-compose up -d

# 手动部署更新
cd llm-orchestrator-py
git pull
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart llm-orchestrator
```

## 故障排查

### 常见问题

1. **服务无法启动**
   - 检查端口占用: `sudo lsof -i :8000`
   - 查看日志: `docker-compose logs app` 或 `journalctl -u llm-orchestrator`
   - 验证配置: 确保.env文件正确

2. **数据库连接失败**
   - 检查数据库服务: `systemctl status mysql` 或 `systemctl status redis`
   - 验证连接字符串: 确保DATABASE_URL和REDIS_URL正确
   - 检查权限: 确保数据库用户有足够权限

3. **Redis连接失败**
   - 检查Redis状态: `redis-cli ping`
   - 验证密码: `redis-cli -a your-password ping`
   - 检查防火墙: 确保Redis端口可访问

4. **性能问题**
   - 增加Worker数量: 修改gunicorn的--workers参数
   - 优化数据库: 添加索引,调整连接池大小
   - 检查Redis缓存: 确保缓存正常工作
   - 监控资源使用: `htop`, `docker stats`

5. **请求超时**
   - 增加超时时间: 修改nginx和应用的timeout配置
   - 检查提供商响应: 查看日志中的延迟信息
   - 优化请求: 减少重试次数,调整超时设置

## 安全建议

1. **定期更新**: 保持系统和依赖项最新
2. **强密码**: 使用强密码保护数据库和Redis
3. **防火墙**: 只开放必要的端口
4. **SSL/TLS**: 生产环境必须使用HTTPS
5. **日志审计**: 定期检查访问日志
6. **备份**: 定期备份数据库和配置
7. **监控**: 设置告警监控异常情况
8. **权限**: 使用非root用户运行服务

## 支持

如有问题,请查看:
- [项目文档](../README.md)
- [架构文档](ARCHITECTURE.md)
- [API文档](http://localhost:8000/docs)
- [问题追踪](issues)