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

            // 对于 204 No Content,不尝试解析 JSON
            if (response.status === 204) {
                return null;
            }

            // 检查响应是否有内容
            const text = await response.text();
            return text ? JSON.parse(text) : null;
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
        const stats = await utils.request('/api/admin/stats?hours=24', { useAdmin: true });
        
        // 更新统计卡片
        document.getElementById('total-requests').textContent = utils.formatNumber(stats.total_requests || 0);
        document.getElementById('success-rate').textContent = (stats.success_rate || 0).toFixed(1) + '%';
        document.getElementById('avg-latency').textContent = (stats.avg_response_time_ms || 0).toFixed(0) + 'ms';
        
        // 计算总 Token 数(从各个 Provider 统计中汇总)
        const totalTokens = stats.providers?.reduce((sum, p) => sum + (p.total_tokens || 0), 0) || 0;
        document.getElementById('total-tokens').textContent = utils.formatNumber(totalTokens);
        
    } catch (error) {
        console.error('Failed to load dashboard:', error);
    }
}

async function checkHealth() {
    try {
        const health = await utils.request('/api/admin/health', { useAdmin: true });
        
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
        const providers = await utils.request('/api/admin/providers', { useAdmin: true });
        
        const tbody = document.getElementById('providers-tbody');
        
        if (providers.length === 0) {
            tbody.innerHTML = '<tr><td colspan="9" class="empty-state-text">暂无提供商</td></tr>';
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
                    <button class="btn btn-sm btn-success" onclick="getProviderModels(${p.id}, '${p.name}')">
                        📋 获取模型
                    </button>
                    <button class="btn btn-sm btn-primary" onclick="editProvider(${p.id})">编辑</button>
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

// 编辑提供商
async function editProvider(id) {
    try {
        const provider = await utils.request(`/api/admin/providers/${id}`, { useAdmin: true });
        
        const modalHtml = `
            <div id="edit-provider-modal" class="modal active">
                <div class="modal-content">
                    <div class="modal-header">
                        <h3 class="modal-title">编辑提供商 - ${provider.name}</h3>
                        <button class="close-btn" onclick="closeModal('edit-provider-modal')">×</button>
                    </div>
                    <form id="edit-provider-form">
                        <input type="hidden" id="edit-provider-id" value="${provider.id}">
                        <div class="form-group">
                            <label class="form-label">名称</label>
                            <input type="text" class="form-control" value="${provider.name}" disabled>
                            <small style="color: var(--text-secondary);">提供商名称不可修改</small>
                        </div>
                        <div class="form-group">
                            <label class="form-label">类型</label>
                            <input type="text" class="form-control" value="${provider.type}" disabled>
                            <small style="color: var(--text-secondary);">提供商类型不可修改</small>
                        </div>
                        <div class="form-group">
                            <label class="form-label">API 密钥 *</label>
                            <input type="password" class="form-control" id="edit-api-key" value="${provider.api_key}" required>
                        </div>
                        <div class="form-group">
                            <label class="form-label">基础 URL</label>
                            <input type="text" class="form-control" id="edit-base-url" value="${provider.base_url || ''}" placeholder="留空使用默认值">
                        </div>
                        <div style="display: flex; gap: 10px; margin-top: 20px;">
                            <button type="button" class="btn" onclick="closeModal('edit-provider-modal')">取消</button>
                            <button type="submit" class="btn btn-primary">保存</button>
                        </div>
                    </form>
                </div>
            </div>
        `;
        
        const oldModal = document.getElementById('edit-provider-modal');
        if (oldModal) oldModal.remove();
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        
        document.getElementById('edit-provider-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const data = {
                api_key: document.getElementById('edit-api-key').value,
                base_url: document.getElementById('edit-base-url').value || null
            };
            
            try {
                await utils.request(`/api/admin/providers/${id}`, {
                    method: 'PATCH',
                    useAdmin: true,
                    body: JSON.stringify(data)
                });
                
                utils.showAlert('提供商已更新', 'success');
                closeModal('edit-provider-modal');
                await loadProviders();
            } catch (error) {
                console.error('Failed to update provider:', error);
            }
        });
    } catch (error) {
        console.error('Failed to load provider:', error);
    }
}

async function toggleProvider(id, enabled) {
    try {
        await utils.request(`/api/admin/providers/${id}`, {
            method: 'PATCH',
            useAdmin: true,
            body: JSON.stringify({ enabled })
        });
        
        utils.showAlert(`提供商已${enabled ? '启用' : '禁用'}`, 'success');
        await loadProviders();
    } catch (error) {
        console.error('Failed to toggle provider:', error);
    }
}

// 获取提供商模型列表
async function getProviderModels(providerId, providerName) {
    try {
        const data = await utils.request(`/api/admin/providers/${providerId}/models`, { useAdmin: true });
        
        // 显示模型列表模态框
        showProviderModelsModal(data.models, providerId, providerName);
    } catch (error) {
        console.error('Failed to get provider models:', error);
        utils.showAlert('获取模型列表失败: ' + error.message, 'danger');
    }
}

// 显示提供商模型列表模态框
function showProviderModelsModal(models, providerId, providerName) {
    const modalHtml = `
        <div id="provider-models-modal" class="modal active">
            <div class="modal-content">
                <div class="modal-header">
                    <h3 class="modal-title">${providerName} - 可用模型</h3>
                    <button class="close-btn" onclick="closeModal('provider-models-modal')">×</button>
                </div>
                <div style="margin-bottom: 20px; display: flex; gap: 10px; align-items: center;">
                    <button class="btn btn-primary" onclick="importAllModels(${providerId}, ${JSON.stringify(models).replace(/"/g, '&quot;')})">
                        📥 一键导入全部模型
                    </button>
                    <button class="btn btn-success" onclick="copyAllModels(${JSON.stringify(models).replace(/"/g, '&quot;')})">
                        📋 一键复制全部模型
                    </button>
                    <p style="margin: 0; color: var(--text-secondary);">共 ${models.length} 个模型</p>
                </div>
                <div style="max-height: 400px; overflow-y: auto;">
                    ${models.map(model => `
                        <div style="padding: 12px; border-bottom: 1px solid var(--border-color); display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <strong>${model}</strong>
                            </div>
                            <div>
                                <button class="btn btn-sm btn-primary" onclick="copyModelName('${model}')">
                                    📋 复制
                                </button>
                                <button class="btn btn-sm btn-success" onclick="importSingleModel(${providerId}, '${model}')">
                                    ➕ 导入
                                </button>
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
        </div>
    `;
    
    // 移除旧模态框
    const oldModal = document.getElementById('provider-models-modal');
    if (oldModal) oldModal.remove();
    
    // 添加新模态框
    document.body.insertAdjacentHTML('beforeend', modalHtml);
}

// 复制模型名称
function copyModelName(modelName) {
    navigator.clipboard.writeText(modelName).then(() => {
        utils.showAlert(`已复制: ${modelName}`, 'success');
    }).catch(err => {
        console.error('Failed to copy:', err);
        utils.showAlert('复制失败', 'danger');
    });
}

// 一键复制全部模型名称
function copyAllModels(models) {
    if (!models || models.length === 0) {
        utils.showAlert('没有可复制的模型', 'warning');
        return;
    }
    
    // 将所有模型名称用换行符连接
    const allModelsText = models.join('\n');
    
    navigator.clipboard.writeText(allModelsText).then(() => {
        utils.showAlert(`已复制 ${models.length} 个模型名称`, 'success');
    }).catch(err => {
        console.error('Failed to copy all models:', err);
        utils.showAlert('复制失败', 'danger');
    });
}

// 导入单个模型
async function importSingleModel(providerId, modelName) {
    try {
        const result = await utils.request(`/api/admin/providers/${providerId}/models/import`, {
            method: 'POST',
            useAdmin: true,
            body: JSON.stringify({ model_names: [modelName] })
        });
        
        utils.showAlert(result.message, 'success');
        await loadModels();  // 刷新模型列表
    } catch (error) {
        console.error('Failed to import model:', error);
        utils.showAlert('导入失败: ' + error.message, 'danger');
    }
}

// 一键导入全部模型
async function importAllModels(providerId, models) {
    if (!confirm(`确定要导入全部 ${models.length} 个模型吗?`)) return;
    
    try {
        const result = await utils.request(`/api/admin/providers/${providerId}/models/import`, {
            method: 'POST',
            useAdmin: true,
            body: JSON.stringify({ model_names: null })  // null = 导入全部
        });
        
        utils.showAlert(result.message, 'success');
        closeModal('provider-models-modal');
        await loadModels();  // 刷新模型列表
    } catch (error) {
        console.error('Failed to import all models:', error);
        utils.showAlert('批量导入失败: ' + error.message, 'danger');
    }
}

async function deleteProvider(id) {
    if (!confirm('确定要删除此提供商吗?')) return;
    
    try {
        await utils.request(`/api/admin/providers/${id}`, {
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

// 处理添加提供商表单 - 移到 DOMContentLoaded 内部
// 处理添加模型表单 - 移到 DOMContentLoaded 内部

// 模型管理
async function loadModels() {
    try {
        const models = await utils.request('/api/admin/models', { useAdmin: true });
        
        const tbody = document.getElementById('models-tbody');
        
        if (!models || models.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="empty-state-text">暂无模型配置</td></tr>';
            return;
        }
        
        tbody.innerHTML = models.map(m => `
            <tr>
                <td>${m.name}</td>
                <td>${m.remark || '-'}</td>
                <td>${m.max_retry}</td>
                <td>${m.timeout}</td>
                <td>
                    <span class="badge badge-${m.enabled ? 'success' : 'danger'}">
                        ${m.enabled ? '启用' : '禁用'}
                    </span>
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

// 编辑模型
async function editModel(id) {
    try {
        const model = await utils.request(`/api/admin/models/${id}`, { useAdmin: true });
        
        const modalHtml = `
            <div id="edit-model-modal" class="modal active">
                <div class="modal-content">
                    <div class="modal-header">
                        <h3 class="modal-title">编辑模型</h3>
                        <button class="close-btn" onclick="closeModal('edit-model-modal')">×</button>
                    </div>
                    <form id="edit-model-form">
                        <input type="hidden" id="edit-model-id" value="${model.id}">
                        <div class="form-group">
                            <label class="form-label">模型名称 *</label>
                            <input type="text" class="form-control" id="edit-model-name" value="${model.name}" required>
                            <small style="color: var(--text-secondary);">用户请求时使用的模型名称</small>
                        </div>
                        <div class="form-group">
                            <label class="form-label">备注</label>
                            <textarea class="form-control" id="edit-model-remark" rows="2">${model.remark || ''}</textarea>
                        </div>
                        <div class="form-group">
                            <label class="form-label">最大重试次数</label>
                            <input type="number" class="form-control" value="${model.max_retry}" disabled>
                            <small style="color: var(--text-secondary);">暂不支持修改</small>
                        </div>
                        <div class="form-group">
                            <label class="form-label">超时时间 (秒)</label>
                            <input type="number" class="form-control" value="${model.timeout}" disabled>
                            <small style="color: var(--text-secondary);">暂不支持修改</small>
                        </div>
                        <div style="display: flex; gap: 10px; margin-top: 20px;">
                            <button type="button" class="btn" onclick="closeModal('edit-model-modal')">取消</button>
                            <button type="submit" class="btn btn-primary">保存</button>
                        </div>
                    </form>
                </div>
            </div>
        `;
        
        const oldModal = document.getElementById('edit-model-modal');
        if (oldModal) oldModal.remove();
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        
        document.getElementById('edit-model-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const data = {
                name: document.getElementById('edit-model-name').value,
                remark: document.getElementById('edit-model-remark').value || null
            };
            
            try {
                await utils.request(`/api/admin/models/${id}`, {
                    method: 'PATCH',
                    useAdmin: true,
                    body: JSON.stringify(data)
                });
                
                utils.showAlert('模型已更新', 'success');
                closeModal('edit-model-modal');
                await loadModels();
            } catch (error) {
                console.error('Failed to update model:', error);
            }
        });
    } catch (error) {
        console.error('Failed to load model:', error);
    }
}

async function deleteModel(id) {
    if (!confirm('确定要删除此模型配置吗?')) return;
    
    try {
        await utils.request(`/api/admin/models/${id}`, {
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
        const response = await utils.request('/api/admin/logs?page=1&page_size=50', { useAdmin: true });
        
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

// ==================== Excel 统一导入导出功能 ====================

/**
 * 导出所有配置(三工作表)
 */
async function exportAllConfig() {
    try {
        const response = await fetch('/api/admin/export/config', {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${config.adminKey}`
            }
        });
        
        if (!response.ok) {
            throw new Error(`导出失败: ${response.status}`);
        }
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `llm_orchestrator_config_${new Date().toISOString().split('T')[0]}.xlsx`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        
        utils.showAlert('配置导出成功,包含3个工作表', 'success');
    } catch (error) {
        console.error('Export config failed:', error);
        utils.showAlert('导出失败: ' + error.message, 'danger');
    }
}

/**
 * 下载配置模板
 * @param {boolean} withSample - 是否包含示例数据
 */
async function downloadConfigTemplate(withSample = false) {
    try {
        const url = `/api/admin/export/template?with_sample=${withSample}`;
        const response = await fetch(url, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${config.adminKey}`
            }
        });
        
        if (!response.ok) {
            throw new Error(`下载模板失败: ${response.status}`);
        }
        
        const blob = await response.blob();
        const downloadUrl = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = downloadUrl;
        a.download = withSample
            ? `llm_orchestrator_template_with_sample.xlsx`
            : `llm_orchestrator_template.xlsx`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(downloadUrl);
        
        utils.showAlert(
            withSample ? '模板下载成功(含示例数据)' : '空白模板下载成功',
            'success'
        );
    } catch (error) {
        console.error('Download template failed:', error);
        utils.showAlert('下载模板失败: ' + error.message, 'danger');
    }
}

/**
 * 显示统一导入模态框
 */
function showUnifiedImportModal() {
    const modal = document.getElementById('unified-import-modal');
    document.getElementById('unified-import-form').reset();
    document.getElementById('unified-import-result').style.display = 'none';
    modal.classList.add('active');
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

// 初始化 - 合并所有 DOMContentLoaded 事件
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
        await utils.request('/api/admin/health', { useAdmin: true });
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
    
    // 绑定添加提供商表单
    const providerForm = document.getElementById('add-provider-form');
    if (providerForm) {
        providerForm.addEventListener('submit', async (e) => {
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
                await utils.request('/api/admin/providers', {
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
    }
    
    // 绑定添加模型表单
    const modelForm = document.getElementById('add-model-form');
    if (modelForm) {
        modelForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const formData = new FormData(e.target);
            const data = {
                name: formData.get('name'),
                remark: formData.get('remark') || null,
                max_retry: parseInt(formData.get('max_retry')) || 3,
                timeout: parseInt(formData.get('timeout')) || 30,
                enabled: formData.get('enabled') === 'on'
            };
            
            try {
                await utils.request('/api/admin/models', {
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
    }
    
    // 绑定统一导入表单
    const unifiedImportForm = document.getElementById('unified-import-form');
    if (unifiedImportForm) {
        unifiedImportForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const fileInput = document.getElementById('unified-import-file');
            const resultDiv = document.getElementById('unified-import-result');
            
            if (!fileInput.files.length) {
                utils.showAlert('请选择文件', 'danger');
                return;
            }
            
            const file = fileInput.files[0];
            
            // 验证文件类型
            if (!file.name.endsWith('.xlsx')) {
                utils.showAlert('请选择 .xlsx 格式的文件', 'danger');
                return;
            }
            
            const formData = new FormData();
            formData.append('file', file);
            
            // 显示加载状态
            resultDiv.style.display = 'block';
            resultDiv.innerHTML = `
                <div class="alert alert-warning">
                    <div class="loading" style="margin-right: 10px;"></div>
                    正在导入配置,请稍候...
                </div>
            `;
            
            try {
                const response = await fetch('/api/admin/import/config/upload', {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${config.adminKey}`
                    },
                    body: formData
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    // 构建详细结果显示
                    const providersResult = result.result.providers;
                    const modelsResult = result.result.models;
                    const associationsResult = result.result.associations;
                    
                    let html = `<div class="alert alert-success">
                        <strong>✅ 配置导入成功!</strong><br><br>`;
                    
                    // Providers统计
                    html += `<strong>📦 提供商:</strong><br>`;
                    html += `• 创建: ${providersResult.created} 个<br>`;
                    html += `• 跳过: ${providersResult.skipped} 个<br>`;
                    html += `• 总计: ${providersResult.total} 个<br>`;
                    if (providersResult.errors.length > 0) {
                        html += `<div style="color: var(--danger-color); margin-top: 8px;">`;
                        html += `⚠️ 错误 (${providersResult.errors.length}):<br>`;
                        providersResult.errors.slice(0, 5).forEach(err => {
                            html += `• 第${err.row}行 ${err.field}: ${err.error}<br>`;
                        });
                        if (providersResult.errors.length > 5) {
                            html += `• ... 还有 ${providersResult.errors.length - 5} 个错误<br>`;
                        }
                        html += `</div>`;
                    }
                    html += `<br>`;
                    
                    // Models统计
                    html += `<strong>🤖 模型:</strong><br>`;
                    html += `• 创建: ${modelsResult.created} 个<br>`;
                    html += `• 跳过: ${modelsResult.skipped} 个<br>`;
                    html += `• 总计: ${modelsResult.total} 个<br>`;
                    if (modelsResult.errors.length > 0) {
                        html += `<div style="color: var(--danger-color); margin-top: 8px;">`;
                        html += `⚠️ 错误 (${modelsResult.errors.length}):<br>`;
                        modelsResult.errors.slice(0, 5).forEach(err => {
                            html += `• 第${err.row}行 ${err.field}: ${err.error}<br>`;
                        });
                        if (modelsResult.errors.length > 5) {
                            html += `• ... 还有 ${modelsResult.errors.length - 5} 个错误<br>`;
                        }
                        html += `</div>`;
                    }
                    html += `<br>`;
                    
                    // Associations统计
                    html += `<strong>🔗 关联:</strong><br>`;
                    html += `• 创建: ${associationsResult.created} 个<br>`;
                    html += `• 跳过: ${associationsResult.skipped} 个<br>`;
                    html += `• 总计: ${associationsResult.total} 个<br>`;
                    if (associationsResult.errors.length > 0) {
                        html += `<div style="color: var(--danger-color); margin-top: 8px;">`;
                        html += `⚠️ 错误 (${associationsResult.errors.length}):<br>`;
                        associationsResult.errors.slice(0, 5).forEach(err => {
                            html += `• 第${err.row}行 ${err.field}: ${err.error}<br>`;
                        });
                        if (associationsResult.errors.length > 5) {
                            html += `• ... 还有 ${associationsResult.errors.length - 5} 个错误<br>`;
                        }
                        html += `</div>`;
                    }
                    
                    html += `</div>`;
                    resultDiv.innerHTML = html;
                    
                    // 刷新列表
                    utils.showAlert('配置导入成功,正在刷新列表...', 'success');
                    await Promise.all([
                        loadProviders(),
                        loadModels()
                    ]);
                    
                } else {
                    resultDiv.innerHTML = `
                        <div class="alert alert-danger">
                            <strong>❌ 导入失败!</strong><br>
                            ${result.detail || result.message || '未知错误'}
                        </div>
                    `;
                }
            } catch (error) {
                console.error('Unified import failed:', error);
                resultDiv.innerHTML = `
                    <div class="alert alert-danger">
                        <strong>❌ 导入失败!</strong><br>
                        ${error.message}
                    </div>
                `;
            }
        });
    }
    
    // 绑定模态框点击外部关闭
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.classList.remove('active');
            }
        });
    });
});

// 点击模态框外部关闭
document.querySelectorAll('.modal').forEach(modal => {
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.classList.remove('active');
        }
    });
});