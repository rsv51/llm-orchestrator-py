// LLM Orchestrator Web 管理界面 JavaScript

// 配置 - 使用相对路径避免跨域问题
const config = {
    apiBaseUrl: '',  // 使用相对路径,与当前域名相同
    apiKey: localStorage.getItem('apiKey') || sessionStorage.getItem('apiKey') || '',
    adminKey: localStorage.getItem('adminKey') || sessionStorage.getItem('adminKey') || ''
};

// 检查登录状态
function checkAuth() {
    if (!config.adminKey) {
        window.location.href = '/admin-ui/login.html';
        return false;
    }
    return true;
}

// 工具函数
const utils = {
    async request(url, options = {}) {
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers
        };

        if (options.useAdmin) {
            headers['Authorization'] = `Bearer ${config.adminKey}`;
        } else if (config.apiKey) {
            headers['Authorization'] = `Bearer ${config.apiKey}`;
        }

        try {
            const response = await fetch(`${config.apiBaseUrl}${url}`, {
                ...options,
                headers
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            return await response.json();
        } catch (error) {
            console.error('Request failed:', error);
            this.showAlert('请求失败: ' + error.message, 'danger');
            throw error;
        }
    },

    showAlert(message, type = 'success') {
        const alert = document.createElement('div');
        alert.className = `alert alert-${type}`;
        alert.textContent = message;
        
        const container = document.querySelector('.container');
        container.insertBefore(alert, container.firstChild);
        
        setTimeout(() => alert.remove(), 5000);
    },

    formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleString('zh-CN');
    },

    formatNumber(num) {
        return new Intl.NumberFormat('zh-CN').format(num);
    }
};

// 标签页切换
function switchTab(tabName) {
    // 隐藏所有标签页内容
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // 移除所有标签页激活状态
    document.querySelectorAll('.nav-tab').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // 显示选中的标签页
    document.getElementById(tabName).classList.add('active');
    event.target.classList.add('active');
    
    // 加载对应数据
    loadTabData(tabName);
}

async function loadTabData(tabName) {
    switch (tabName) {
        case 'dashboard':
            await loadDashboard();
            break;
        case 'providers':
            await loadProviders();
            break;
        case 'models':
            await loadModels();
            break;
        case 'logs':
            await loadLogs();
            break;
    }
}

// 仪表盘
async function loadDashboard() {
    try {
        // 加载系统健康状态
        await checkHealth();
        
        // 加载统计数据
        const stats = await utils.request('/admin/stats?hours=24', { useAdmin: true });
        
        // 更新统计卡片
        document.getElementById('total-requests').textContent = utils.formatNumber(stats.total_requests || 0);
        document.getElementById('success-rate').textContent = ((stats.success_rate || 0) * 100).toFixed(1) + '%';
        document.getElementById('avg-latency').textContent = (stats.avg_latency || 0).toFixed(0) + 'ms';
        document.getElementById('total-tokens').textContent = utils.formatNumber(stats.total_tokens || 0);
        
    } catch (error) {
        console.error('Failed to load dashboard:', error);
    }
}

async function checkHealth() {
    try {
        const health = await utils.request('/admin/health', { useAdmin: true });
        
        const statusHtml = `
            <div style="margin-bottom: 20px;">
                <p><strong>系统状态:</strong> <span class="badge badge-${health.status === 'healthy' ? 'success' : 'danger'}">${health.status}</span></p>
                <p><strong>数据库:</strong> <span class="badge badge-${health.database_status === 'connected' ? 'success' : 'danger'}">${health.database_status}</span></p>
                <p><strong>缓存:</strong> <span class="badge badge-${health.cache_status === 'connected' ? 'success' : 'warning'}">${health.cache_status}</span></p>
            </div>
        `;
        
        document.getElementById('health-status').innerHTML = statusHtml;
        
        // 显示提供商健康状态
        const providersHtml = health.providers.map(p => `
            <div style="padding: 12px; border-bottom: 1px solid var(--border-color); display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <span class="health-indicator ${p.is_healthy ? 'healthy' : 'unhealthy'}"></span>
                    <strong>${p.provider_name}</strong>
                </div>
                <div>
                    <span class="badge badge-${p.is_healthy ? 'success' : 'danger'}">
                        ${p.is_healthy ? '健康' : '不健康'}
                    </span>
                    <span style="margin-left: 10px; color: var(--text-secondary);">
                        ${p.response_time_ms ? p.response_time_ms + 'ms' : 'N/A'}
                    </span>
                </div>
            </div>
        `).join('');
        
        document.getElementById('provider-health-list').innerHTML = providersHtml || '<p class="empty-state-text">暂无提供商</p>';
        
    } catch (error) {
        console.error('Failed to check health:', error);
    }
}

// 提供商管理
async function loadProviders() {
    try {
        const providers = await utils.request('/admin/providers', { useAdmin: true });
        
        const tbody = document.getElementById('providers-tbody');
        
        if (providers.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" class="empty-state-text">暂无提供商</td></tr>';
            return;
        }
        
        tbody.innerHTML = providers.map(p => `
            <tr>
                <td>${p.id}</td>
                <td>${p.name}</td>
                <td>${p.type}</td>
                <td>${p.base_url || 'N/A'}</td>
                <td>${p.priority}</td>
                <td>
                    <span class="badge badge-${p.enabled ? 'success' : 'danger'}">
                        ${p.enabled ? '启用' : '禁用'}
                    </span>
                </td>
                <td>${utils.formatDate(p.created_at)}</td>
                <td>
                    <button class="btn btn-sm btn-primary" onclick="toggleProvider(${p.id}, ${!p.enabled})">
                        ${p.enabled ? '禁用' : '启用'}
                    </button>
                    <button class="btn btn-sm btn-danger" onclick="deleteProvider(${p.id})">删除</button>
                </td>
            </tr>
        `).join('');
        
    } catch (error) {
        console.error('Failed to load providers:', error);
    }
}

async function toggleProvider(id, enabled) {
    try {
        await utils.request(`/admin/providers/${id}`, {
            method: 'PUT',
            useAdmin: true,
            body: JSON.stringify({ enabled })
        });
        
        utils.showAlert(`提供商已${enabled ? '启用' : '禁用'}`, 'success');
        await loadProviders();
    } catch (error) {
        console.error('Failed to toggle provider:', error);
    }
}

async function deleteProvider(id) {
    if (!confirm('确定要删除此提供商吗?')) return;
    
    try {
        await utils.request(`/admin/providers/${id}`, {
            method: 'DELETE',
            useAdmin: true
        });
        
        utils.showAlert('提供商已删除', 'success');
        await loadProviders();
    } catch (error) {
        console.error('Failed to delete provider:', error);
    }
}

function showAddProviderModal() {
    document.getElementById('add-provider-modal').classList.add('active');
}

function closeModal(modalId) {
    document.getElementById(modalId).classList.remove('active');
}

// 处理添加提供商表单
document.getElementById('add-provider-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const formData = new FormData(e.target);
    const data = {
        name: formData.get('name'),
        type: formData.get('type'),
        api_key: formData.get('api_key'),
        base_url: formData.get('base_url') || null,
        priority: parseInt(formData.get('priority')) || 100,
        enabled: formData.get('enabled') === 'on'
    };
    
    try {
        await utils.request('/admin/providers', {
            method: 'POST',
            useAdmin: true,
            body: JSON.stringify(data)
        });
        
        utils.showAlert('提供商添加成功', 'success');
        closeModal('add-provider-modal');
        e.target.reset();
        await loadProviders();
    } catch (error) {
        console.error('Failed to add provider:', error);
    }
});

// 处理添加模型表单
document.getElementById('add-model-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const formData = new FormData(e.target);
    const data = {
        name: formData.get('name'),
        display_name: formData.get('display_name') || null,
        description: formData.get('description') || null,
        context_length: parseInt(formData.get('context_length')),
        max_output_tokens: parseInt(formData.get('max_output_tokens')) || null,
        input_price_per_million: parseFloat(formData.get('input_price_per_million')),
        output_price_per_million: parseFloat(formData.get('output_price_per_million')),
        supports_streaming: formData.get('supports_streaming') === 'on',
        supports_functions: formData.get('supports_functions') === 'on',
        supports_vision: formData.get('supports_vision') === 'on'
    };
    
    try {
        await utils.request('/admin/models', {
            method: 'POST',
            useAdmin: true,
            body: JSON.stringify(data)
        });
        
        utils.showAlert('模型配置添加成功', 'success');
        closeModal('add-model-modal');
        e.target.reset();
        await loadModels();
    } catch (error) {
        console.error('Failed to add model:', error);
    }
});

// 模型管理
async function loadModels() {
    try {
        const models = await utils.request('/admin/models', { useAdmin: true });
        
        const tbody = document.getElementById('models-tbody');
        
        if (!models || models.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="empty-state-text">暂无模型配置</td></tr>';
            return;
        }
        
        tbody.innerHTML = models.map(m => `
            <tr>
                <td>${m.name}</td>
                <td>${m.display_name || m.name}</td>
                <td>${utils.formatNumber(m.context_length)}</td>
                <td>${m.max_output_tokens ? utils.formatNumber(m.max_output_tokens) : 'N/A'}</td>
                <td>
                    ${m.supports_streaming ? '<span class="badge badge-success">流式</span>' : ''}
                    ${m.supports_functions ? '<span class="badge badge-success">函数</span>' : ''}
                    ${m.supports_vision ? '<span class="badge badge-success">视觉</span>' : ''}
                </td>
                <td>
                    <button class="btn btn-sm btn-primary" onclick="editModel(${m.id})">编辑</button>
                    <button class="btn btn-sm btn-danger" onclick="deleteModel(${m.id})">删除</button>
                </td>
            </tr>
        `).join('');
        
    } catch (error) {
        console.error('Failed to load models:', error);
    }
}

function showAddModelModal() {
    document.getElementById('add-model-modal').classList.add('active');
}

async function editModel(id) {
    utils.showAlert('编辑功能暂未实现', 'warning');
}

async function deleteModel(id) {
    if (!confirm('确定要删除此模型配置吗?')) return;
    
    try {
        await utils.request(`/admin/models/${id}`, {
            method: 'DELETE',
            useAdmin: true
        });
        
        utils.showAlert('模型配置已删除', 'success');
        await loadModels();
    } catch (error) {
        console.error('Failed to delete model:', error);
    }
}

// 请求日志
async function loadLogs() {
    try {
        const response = await utils.request('/admin/logs?page=1&page_size=50', { useAdmin: true });
        
        const tbody = document.getElementById('logs-tbody');
        
        if (!response.logs || response.logs.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="empty-state-text">暂无日志</td></tr>';
            return;
        }
        
        tbody.innerHTML = response.logs.map(log => `
            <tr>
                <td>${utils.formatDate(log.created_at)}</td>
                <td>${log.id}</td>
                <td>${log.model}</td>
                <td>${log.provider_name}</td>
                <td>${log.total_tokens || 0}</td>
                <td>${log.latency_ms}ms</td>
                <td>
                    <span class="badge badge-${log.status_code === 200 ? 'success' : 'danger'}">
                        ${log.status_code === 200 ? '成功' : '失败'}
                    </span>
                </td>
            </tr>
        `).join('');
        
    } catch (error) {
        console.error('Failed to load logs:', error);
    }
}

// Excel 导入导出功能
let currentImportType = 'providers';

function exportProviders() {
    // 使用相对路径自动适配域名
    const url = '/admin/excel/export/providers';
    window.open(url, '_blank');
    utils.showAlert('正在下载提供商列表...', 'success');
}

function exportModels() {
    // 使用相对路径自动适配域名
    const url = '/admin/excel/export/models';
    window.open(url, '_blank');
    utils.showAlert('正在下载模型列表...', 'success');
}

function showImportModal(type) {
    currentImportType = type;
    const modal = document.getElementById('import-modal');
    const title = document.getElementById('import-modal-title');
    
    if (type === 'providers') {
        title.textContent = '导入提供商';
    } else if (type === 'models') {
        title.textContent = '导入模型配置';
    }
    
    // 重置表单
    document.getElementById('import-form').reset();
    document.getElementById('import-result').style.display = 'none';
    
    modal.classList.add('active');
}

async function downloadTemplate() {
    // 使用相对路径自动适配域名
    const url = currentImportType === 'providers'
        ? '/admin/excel/template/providers'
        : '/admin/excel/template/models';
    
    window.open(url, '_blank');
    utils.showAlert('正在下载模板...', 'success');
}

// 设置
function saveSettings() {
    const apiKey = document.getElementById('api-key').value;
    const adminKey = document.getElementById('admin-key').value;
    
    if (apiKey) {
        localStorage.setItem('apiKey', apiKey);
        config.apiKey = apiKey;
    }
    
    if (adminKey) {
        localStorage.setItem('adminKey', adminKey);
        config.adminKey = adminKey;
    }
    
    utils.showAlert('设置已保存', 'success');
}

// 刷新所有数据
async function refreshAll() {
    const currentTab = document.querySelector('.tab-content.active').id;
    await loadTabData(currentTab);
    utils.showAlert('数据已刷新', 'success');
}

// 初始化
document.addEventListener('DOMContentLoaded', async () => {
    // 检查登录状态
    if (!checkAuth()) {
        return;
    }
    
    // 加载保存的设置
    const savedApiKey = localStorage.getItem('apiKey') || sessionStorage.getItem('apiKey');
    const savedAdminKey = localStorage.getItem('adminKey') || sessionStorage.getItem('adminKey');
    
    if (savedApiKey) {
        document.getElementById('api-key').value = savedApiKey;
    }
    if (savedAdminKey) {
        document.getElementById('admin-key').value = savedAdminKey;
    }
    
    // 检查 API 连接
    try {
        await utils.request('/health');
        document.getElementById('api-status').textContent = 'API 正常';
        document.getElementById('api-status').className = 'badge badge-success';
    } catch (error) {
        document.getElementById('api-status').textContent = 'API 离线';
        document.getElementById('api-status').className = 'badge badge-danger';
        utils.showAlert('无法连接到 API 服务,请检查服务状态', 'danger');
    }
    
    // 加载仪表盘数据
    try {
        await loadDashboard();
    } catch (error) {
        // 如果是认证错误,跳转到登录页
        if (error.message.includes('401') || error.message.includes('403')) {
            localStorage.removeItem('adminKey');
            sessionStorage.removeItem('adminKey');
            window.location.href = '/admin-ui/login.html';
        }
    }
});

// 添加登出功能
function logout() {
    if (confirm('确定要退出登录吗?')) {
        localStorage.removeItem('adminKey');
        sessionStorage.removeItem('adminKey');
        localStorage.removeItem('apiKey');
        sessionStorage.removeItem('apiKey');
        window.location.href = '/admin-ui/login.html';
    }
}

// 处理导入表单
document.getElementById('import-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const fileInput = document.getElementById('import-file');
    const skipDuplicates = document.getElementById('skip-duplicates').checked;
    const resultDiv = document.getElementById('import-result');
    
    if (!fileInput.files.length) {
        utils.showAlert('请选择文件', 'danger');
        return;
    }
    
    const file = fileInput.files[0];
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const endpoint = currentImportType === 'providers'
            ? `/admin/excel/import/providers?skip_duplicates=${skipDuplicates}`
            : `/admin/excel/import/models?skip_duplicates=${skipDuplicates}`;
        
        // 使用相对路径,不需要 config.apiBaseUrl
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${config.adminKey}`
            },
            body: formData
        });
        
        const result = await response.json();
        
        if (response.ok) {
            // 显示结果
            resultDiv.style.display = 'block';
            resultDiv.innerHTML = `
                <div class="alert alert-success">
                    <strong>导入成功!</strong><br>
                    创建: ${result.details.created} 个<br>
                    跳过: ${result.details.skipped} 个<br>
                    总计: ${result.details.total} 个
                    ${result.details.errors.length > 0 ? '<br><br><strong>错误:</strong><br>' + result.details.errors.join('<br>') : ''}
                </div>
            `;
            
            // 刷新列表
            if (currentImportType === 'providers') {
                await loadProviders();
            } else {
                await loadModels();
            }
        } else {
            resultDiv.style.display = 'block';
            resultDiv.innerHTML = `
                <div class="alert alert-danger">
                    <strong>导入失败!</strong><br>
                    ${result.detail || '未知错误'}
                </div>
            `;
        }
    } catch (error) {
        console.error('Import failed:', error);
        resultDiv.style.display = 'block';
        resultDiv.innerHTML = `
            <div class="alert alert-danger">
                <strong>导入失败!</strong><br>
                ${error.message}
            </div>
        `;
    }
});

// 点击模态框外部关闭
document.querySelectorAll('.modal').forEach(modal => {
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.classList.remove('active');
        }
    });
});