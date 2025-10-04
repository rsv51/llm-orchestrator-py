/**
 * Model-Provider Association Management
 * Similar to llmio-master's architecture
 */

const API_BASE = '';
let adminKey = localStorage.getItem('adminKey') || '';
let editingId = null;
let models = [];
let providers = [];
let associations = [];

// API Headers
function getHeaders() {
    return {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${adminKey}`
    };
}

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
    const key = localStorage.getItem('adminKey');
    if (!key) {
        window.location.href = 'login.html';
        return;
    }
    
    adminKey = key;
    await loadData();
    setupEventListeners();
});

// Setup Event Listeners
function setupEventListeners() {
    document.getElementById('association-form').addEventListener('submit', handleSubmit);
    document.getElementById('model-filter').addEventListener('change', filterAssociations);
    document.getElementById('provider-type-filter').addEventListener('change', filterAssociations);
}

// Load Data
async function loadData() {
    try {
        await Promise.all([
            loadModels(),
            loadProviders(),
            loadAssociations()
        ]);
        
        populateFilters();
        populateSelects();
        renderTable();
    } catch (error) {
        console.error('Failed to load data:', error);
        if (error.message.includes('401') || error.message.includes('403')) {
            localStorage.removeItem('adminKey');
            window.location.href = 'login.html';
        }
    }
}

// Load Models
async function loadModels() {
    const response = await fetch(`${API_BASE}/api/admin/models`, {
        headers: getHeaders()
    });
    
    if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
    }
    
    models = await response.json();
}

// Load Providers
async function loadProviders() {
    const response = await fetch(`${API_BASE}/api/admin/providers`, {
        headers: getHeaders()
    });
    
    if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
    }
    
    providers = await response.json();
}

// Load Associations
async function loadAssociations() {
    const response = await fetch(`${API_BASE}/api/admin/model-providers`, {
        headers: getHeaders()
    });
    
    if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
    }
    
    associations = await response.json();
    
    // Load status for each association
    await loadStatuses();
}

// Load Status History
async function loadStatuses() {
    const statusPromises = associations.map(async (assoc) => {
        try {
            const response = await fetch(
                `${API_BASE}/api/admin/model-providers/${assoc.id}/status?limit=10`,
                { headers: getHeaders() }
            );
            
            if (response.ok) {
                const data = await response.json();
                assoc.status_history = data.status_history || [];
            } else {
                assoc.status_history = [];
            }
        } catch (error) {
            console.error(`Failed to load status for association ${assoc.id}:`, error);
            assoc.status_history = [];
        }
    });
    
    await Promise.all(statusPromises);
}

// Populate Filters
function populateFilters() {
    // Provider Type Filter
    const typeFilter = document.getElementById('provider-type-filter');
    const types = [...new Set(providers.map(p => p.type))].filter(Boolean);
    
    typeFilter.innerHTML = '<option value="">全部提供商类型</option>';
    types.forEach(type => {
        const option = document.createElement('option');
        option.value = type;
        option.textContent = type;
        typeFilter.appendChild(option);
    });
    
    // Model Filter
    const modelFilter = document.getElementById('model-filter');
    modelFilter.innerHTML = '<option value="">全部模型</option>';
    models.forEach(model => {
        const option = document.createElement('option');
        option.value = model.id;
        option.textContent = model.name;
        modelFilter.appendChild(option);
    });
}

// Populate Selects
function populateSelects() {
    // Model Select
    const modelSelect = document.getElementById('model-select');
    modelSelect.innerHTML = '<option value="">选择模型</option>';
    models.forEach(model => {
        const option = document.createElement('option');
        option.value = model.id;
        option.textContent = model.name;
        modelSelect.appendChild(option);
    });
    
    // Provider Select
    const providerSelect = document.getElementById('provider-select');
    providerSelect.innerHTML = '<option value="">选择提供商</option>';
    providers.forEach(provider => {
        const option = document.createElement('option');
        option.value = provider.id;
        option.textContent = `${provider.name} (${provider.type})`;
        providerSelect.appendChild(option);
    });
}

// Filter Associations
function filterAssociations() {
    const modelId = document.getElementById('model-filter').value;
    const providerType = document.getElementById('provider-type-filter').value;
    
    let filtered = associations;
    
    if (modelId) {
        filtered = filtered.filter(a => a.model_id == modelId);
    }
    
    if (providerType) {
        filtered = filtered.filter(a => a.provider_type === providerType);
    }
    
    renderTable(filtered);
}

// Render Table
function renderTable(data = associations) {
    const tbody = document.getElementById('associations-tbody');
    
    if (data.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="11" style="text-align: center; padding: 40px;">
                    <div class="empty-state">
                        <div class="empty-state-icon">📋</div>
                        <div class="empty-state-text">暂无模型-提供商关联</div>
                    </div>
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = data.map(assoc => `
        <tr>
            <td>${assoc.id}</td>
            <td>${assoc.model_name}</td>
            <td>${assoc.provider_name}</td>
            <td>${assoc.provider_type}</td>
            <td>${assoc.provider_model}</td>
            <td>${assoc.weight}</td>
            <td>
                <span class="badge ${assoc.tool_call ? 'badge-success' : 'badge-danger'}">
                    ${assoc.tool_call ? '✓' : '✗'}
                </span>
            </td>
            <td>
                <span class="badge ${assoc.structured_output ? 'badge-success' : 'badge-danger'}">
                    ${assoc.structured_output ? '✓' : '✗'}
                </span>
            </td>
            <td>
                <span class="badge ${assoc.image ? 'badge-success' : 'badge-danger'}">
                    ${assoc.image ? '✓' : '✗'}
                </span>
            </td>
            <td>
                <div class="status-bars">
                    ${renderStatusBars(assoc.status_history || [])}
                </div>
            </td>
            <td>
                <button class="btn btn-primary btn-sm" onclick="editAssociation(${assoc.id})">编辑</button>
                <button class="btn btn-danger btn-sm" onclick="deleteAssociation(${assoc.id})">删除</button>
            </td>
        </tr>
    `).join('');
}

// Render Status Bars (like llmio-master)
function renderStatusBars(statusHistory) {
    if (!statusHistory || statusHistory.length === 0) {
        return '<span style="color: var(--text-secondary); font-size: 12px;">无数据</span>';
    }
    
    return statusHistory.map(isSuccess => 
        `<div class="status-bar ${isSuccess ? 'success' : 'failure'}" 
              title="${isSuccess ? '成功' : '失败'}"></div>`
    ).join('');
}

// Show Add Modal
function showAddModal() {
    editingId = null;
    document.getElementById('modal-title').textContent = '添加模型-提供商关联';
    document.getElementById('submit-text').textContent = '创建';
    
    // Reset form
    document.getElementById('association-form').reset();
    document.getElementById('weight').value = 1;
    document.getElementById('tool-call').checked = true;
    document.getElementById('structured-output').checked = true;
    document.getElementById('image').checked = false;
    document.getElementById('enabled').checked = true;
    
    document.getElementById('association-modal').classList.add('active');
}

// Edit Association
async function editAssociation(id) {
    const assoc = associations.find(a => a.id === id);
    if (!assoc) return;
    
    editingId = id;
    document.getElementById('modal-title').textContent = '编辑模型-提供商关联';
    document.getElementById('submit-text').textContent = '更新';
    
    // Fill form
    document.getElementById('model-select').value = assoc.model_id;
    document.getElementById('provider-select').value = assoc.provider_id;
    document.getElementById('provider-model').value = assoc.provider_model;
    document.getElementById('weight').value = assoc.weight;
    document.getElementById('tool-call').checked = assoc.tool_call;
    document.getElementById('structured-output').checked = assoc.structured_output;
    document.getElementById('image').checked = assoc.image;
    document.getElementById('enabled').checked = assoc.enabled;
    
    document.getElementById('association-modal').classList.add('active');
}

// Delete Association
async function deleteAssociation(id) {
    if (!confirm('确定要删除这个关联吗?')) return;
    
    try {
        const response = await fetch(`${API_BASE}/api/admin/model-providers/${id}`, {
            method: 'DELETE',
            headers: getHeaders()
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        await loadAssociations();
        renderTable();
        
        alert('删除成功');
    } catch (error) {
        console.error('Failed to delete association:', error);
        alert('删除失败: ' + error.message);
    }
}

// Handle Form Submit
async function handleSubmit(e) {
    e.preventDefault();
    
    const formData = {
        model_id: parseInt(document.getElementById('model-select').value),
        provider_id: parseInt(document.getElementById('provider-select').value),
        provider_model: document.getElementById('provider-model').value,
        weight: parseInt(document.getElementById('weight').value),
        tool_call: document.getElementById('tool-call').checked,
        structured_output: document.getElementById('structured-output').checked,
        image: document.getElementById('image').checked,
        enabled: document.getElementById('enabled').checked
    };
    
    try {
        const url = editingId
            ? `${API_BASE}/api/admin/model-providers/${editingId}`
            : `${API_BASE}/api/admin/model-providers`;
        
        const method = editingId ? 'PATCH' : 'POST';
        
        const response = await fetch(url, {
            method,
            headers: getHeaders(),
            body: JSON.stringify(formData)
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || `HTTP ${response.status}`);
        }
        
        closeModal();
        await loadAssociations();
        renderTable();
        
        alert(editingId ? '更新成功' : '创建成功');
    } catch (error) {
        console.error('Failed to save association:', error);
        alert('保存失败: ' + error.message);
    }
}

// Close Modal
function closeModal() {
    document.getElementById('association-modal').classList.remove('active');
    editingId = null;
}

// Logout
function logout() {
    localStorage.removeItem('adminKey');
    window.location.href = 'login.html';
}