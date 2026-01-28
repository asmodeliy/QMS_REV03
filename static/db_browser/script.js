let currentDatabase = "spec_center";
let currentTable = null;
let currentPage = 1;
let currentLimit = 50;
let totalPages = 1;
let currentTableColumns = [];
let allTables = [];
let editingRowId = null;
let allCommonData = [];
let allIPData = [];

document.addEventListener('DOMContentLoaded', function() {
    loadDatabases();
    loadCommonDataInfo();
    loadIPInfo();
});

async function loadDatabases() {
    try {
        const res = await fetch('/db-browser/api/databases');
        const result = await res.json();
        
        const dbSelect = document.getElementById('dbSelect');
        result.databases.forEach(db => {
            const option = document.createElement('option');
            option.value = db.name;
            option.textContent = `${db.display_name} - ${db.description}`;
            dbSelect.appendChild(option);
        });
        
        await loadTables();
    } catch (err) {
        console.error('Error loading databases:', err);
    }
}

async function loadTables() {
    currentDatabase = document.getElementById('dbSelect').value || "spec_center";
    if (!currentDatabase) return;
    
    try {
        const res = await fetch(`/db-browser/api/tables?db_name=${currentDatabase}`);
        const result = await res.json();
        
        allTables = result.tables;
        const tablesList = document.getElementById('tablesList');
        tablesList.innerHTML = '';
        
        result.tables.forEach(table => {
            const item = document.createElement('div');
            item.className = 'db-table-item';
            item.onclick = () => selectTable(table.name);
            item.innerHTML = `
                <span>${table.name}</span>
                <span class="db-table-count">${table.row_count}</span>
            `;
            tablesList.appendChild(item);
        });
    } catch (err) {
        console.error('Error loading tables:', err);
    }
}

async function selectTable(tableName) {
    currentTable = tableName;
    currentPage = 1;

    document.querySelectorAll('.db-table-item').forEach(item => {
        item.classList.remove('active');
        if (item.textContent.includes(tableName)) {
            item.classList.add('active');
        }
    });

    await loadTableData();
    document.getElementById('searchInput').value = '';
}

async function loadTableData() {
    if (!currentTable) return;
    
    try {
        const res = await fetch(`/db-browser/api/table/${currentTable}?db_name=${currentDatabase}&page=${currentPage}&limit=${currentLimit}`);
        const result = await res.json();
        
        currentTableColumns = result.columns;
        totalPages = result.pages;

        document.getElementById('tableInfo').textContent = 
            `📊 [${currentDatabase}] ${currentTable} (총 ${result.total}개 레코드)`;

        renderTable(result);

        updatePagination(result.total);
    } catch (err) {
        console.error('Error loading table data:', err);
        alert('테이블 데이터를 불러올 수 없습니다.');
    }
}

function renderTable(data) {
    const table = document.getElementById('dataTable');
    const thead = table.querySelector('thead');
    const tbody = table.querySelector('tbody');

    thead.innerHTML = '<tr>';
    data.columns.forEach(col => {
        const th = document.createElement('th');
        th.textContent = col;
        thead.querySelector('tr').appendChild(th);
    });
    const th = document.createElement('th');
    th.textContent = '작업';
    th.style.width = '100px';
    thead.querySelector('tr').appendChild(th);
    thead.innerHTML += '</tr>';
    
    tbody.innerHTML = '';
    data.data.forEach(row => {
        const tr = document.createElement('tr');

        const pkValue = row[data.columns[0]];
        
        data.columns.forEach(col => {
            const td = document.createElement('td');
            const value = row[col];
            
            if (value === null || value === undefined) {
                td.textContent = 'NULL';
                td.className = 'db-null';
            } else if (typeof value === 'object') {
                td.textContent = JSON.stringify(value);
            } else {
                td.textContent = String(value).substring(0, 100);
            }
            td.title = String(value);
            tr.appendChild(td);
        });
        
        const tdAction = document.createElement('td');
        tdAction.className = 'db-cell-actions';
        tdAction.innerHTML = `
            <button class="db-action-btn" onclick="editRow(${pkValue})">✏️ 편집</button>
            <button class="db-action-btn delete" onclick="deleteRow(${pkValue})">🗑️ 삭제</button>
        `;
        tr.appendChild(tdAction);
        
        tbody.appendChild(tr);
    });
}

async function performSearch() {
    if (!currentTable) return;
    
    const searchQuery = document.getElementById('searchInput').value.trim();
    currentPage = 1;
    
    if (!searchQuery) {
        await loadTableData();
        return;
    }
    
    try {
        const res = await fetch(
            `/db-browser/api/table/${currentTable}/search?db_name=${currentDatabase}&q=${encodeURIComponent(searchQuery)}&page=${currentPage}&limit=${currentLimit}`
        );
        const result = await res.json();
        
        currentTableColumns = result.columns;
        totalPages = result.pages;
        
        document.getElementById('tableInfo').textContent = 
            `📊 [${currentDatabase}] ${currentTable} - 검색: "${searchQuery}" (${result.total}개 결과)`;
        
        renderTable(result);
        updatePagination(result.total);
    } catch (err) {
        console.error('Error searching:', err);
    }
}

async function editRow(rowId) {
    editingRowId = rowId;
    
    const row = allTables.find(t => t.name === currentTable);
    if (!row) return;
    
    const tableData = document.getElementById('dataTable').querySelector('tbody');
    const rowElement = Array.from(tableData.querySelectorAll('tr')).find(tr => {
        const firstCell = tr.querySelector('td');
        return firstCell && firstCell.textContent == rowId;
    });
    
    if (!rowElement) return;
    
    const formBody = document.getElementById('editModalBody');
    formBody.innerHTML = '';
    
    const cells = rowElement.querySelectorAll('td');
    currentTableColumns.forEach((col, idx) => {
        const value = cells[idx].textContent;
        
        const group = document.createElement('div');
        group.className = 'db-form-group';
        
        const label = document.createElement('label');
        label.textContent = col;
        group.appendChild(label);
        
        const input = document.createElement('input');
        input.id = `field_${col}`;
        input.type = 'text';
        input.value = value === 'NULL' ? '' : value;
        group.appendChild(input);
        
        formBody.appendChild(group);
    });
    
    document.getElementById('editModal').classList.add('active');
    document.getElementById('editModalTitle').textContent = `레코드 편집 (ID: ${rowId})`;
}

async function saveRow() {
    if (!currentTable || !editingRowId) return;
    
    const data = {};
    currentTableColumns.forEach(col => {
        const input = document.getElementById(`field_${col}`);
        if (input) {
            data[col] = input.value;
        }
    });
    
    try {
        const res = await fetch(`/db-browser/api/table/${currentTable}/${editingRowId}?db_name=${currentDatabase}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        if (res.ok) {
            closeEditModal();
            await loadTableData();
            alert('레코드가 저장되었습니다.');
        } else {
            alert('저장 실패');
        }
    } catch (err) {
        console.error('Error saving row:', err);
        alert('오류가 발생했습니다.');
    }
}

async function deleteRow(rowId) {
    if (!confirm('정말 삭제하시겠습니까?')) return;
    
    if (!currentTable) return;
    
    try {
        const res = await fetch(`/db-browser/api/table/${currentTable}/${rowId}?db_name=${currentDatabase}`, {
            method: 'DELETE'
        });
        
        if (res.ok) {
            await loadTableData();
            alert('레코드가 삭제되었습니다.');
        } else {
            alert('삭제 실패');
        }
    } catch (err) {
        console.error('Error deleting row:', err);
        alert('오류가 발생했습니다.');
    }
}

function addRowModal() {
    if (!currentTable) {
        alert('테이블을 선택하세요.');
        return;
    }
    
    const formBody = document.getElementById('addRowModalBody');
    formBody.innerHTML = '';
    
    currentTableColumns.forEach(col => {
        const group = document.createElement('div');
        group.className = 'db-form-group';
        
        const label = document.createElement('label');
        label.textContent = col;
        group.appendChild(label);
        
        const input = document.createElement('input');
        input.id = `new_field_${col}`;
        input.type = 'text';
        input.placeholder = col;
        group.appendChild(input);
        
        formBody.appendChild(group);
    });
    
    document.getElementById('addRowModal').classList.add('active');
}

async function insertRow() {
    if (!currentTable) return;
    
    const data = {};
    currentTableColumns.forEach(col => {
        const input = document.getElementById(`new_field_${col}`);
        if (input && input.value) {
            data[col] = input.value;
        }
    });
    
    try {
        const res = await fetch(`/db-browser/api/table/${currentTable}?db_name=${currentDatabase}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        if (res.ok) {
            closeAddRowModal();
            await loadTableData();
            alert('새 레코드가 추가되었습니다.');
        } else {
            alert('추가 실패');
        }
    } catch (err) {
        console.error('Error inserting row:', err);
        alert('오류가 발생했습니다.');
    }
}

function previousPage() {
    if (currentPage > 1) {
        currentPage--;
        loadTableData();
    }
}

function nextPage() {
    if (currentPage < totalPages) {
        currentPage++;
        loadTableData();
    }
}

function updatePagination(total) {
    document.getElementById('pageInfo').textContent = 
        `${currentPage} / ${totalPages} (총 ${total}개)`;
}

function refreshData() {
    loadTableData();
}

function closeEditModal() {
    document.getElementById('editModal').classList.remove('active');
    editingRowId = null;
}

async function loadCommonDataInfo() {
    try {
        const res = await fetch('/api/common/summary');
        const data = await res.json();
        const res2 = await fetch('/api/common/products');
        const products = await res2.json();
        
        allCommonData = products.data;
        
        let html = '<div class="db-info-item">';
        html += `<div class="db-info-label">총 제품</div><div class="db-info-value">${data.data.total_products}</div>`;
        html += '</div>';
        html += '<div class="db-info-item">';
        html += `<div class="db-info-label">Variants</div><div class="db-info-value">${data.data.total_variants}</div>`;
        html += '</div>';
        html += '<div class="db-info-item">';
        html += `<div class="db-info-label">Configs</div><div class="db-info-value">${data.data.total_configs}</div>`;
        html += '</div>';
        
        const infoArea = document.getElementById('tableInfo');
        if (infoArea && !currentTable) {
            infoArea.innerHTML = html;
        }
    } catch (e) {
        console.error('Error loading common data:', e);
    }
}

async function loadIPInfo() {
    try {
        const res = await fetch('/api/common/ip-info');
        const data = await res.json();
        allIPData = data.data;
    } catch (e) {
        console.error('Error loading IP info:', e);
    }
}

function displayCommonProducts() {
    let html = '<div class="db-card-grid">';
    
    if (allCommonData.length === 0) {
        html = '<div style="padding: 20px; text-align: center; color: #999;">데이터 없음</div>';
    } else {
        allCommonData.forEach(p => {
            html += `<div class="db-card">
                <div class="db-card-title">Product ${p.db_name}</div>
                <div class="db-card-row">
                    <span>ID</span>
                    <span style="font-weight: 600;">${p.id}</span>
                </div>
                <div class="db-card-row">
                    <span>Code</span>
                    <span style="font-weight: 600;">${p.product_code || '-'}</span>
                </div>
            </div>`;
        });
        html += '</div>';
    }
    
    return html;
}

function displayIPProducts() {
    let html = '<div class="db-card-grid">';
    
    if (allIPData.length === 0) {
        html = '<div style="padding: 20px; text-align: center; color: #999;">IP 정보 없음</div>';
    } else {
        allIPData.forEach(ip => {
            html += `<div class="db-card">
                <div class="db-card-title">${ip.product_name} - <span class="db-badge">${ip.tech}</span></div>
                <div class="db-card-row">
                    <span>IP Name</span>
                    <span style="font-weight: 600;">${ip.ip_name || '-'}</span>
                </div>
                <div class="db-card-row">
                    <span>Lane Config</span>
                    <span style="font-weight: 600; font-size: 0.85rem;">${ip.lane_config}</span>
                </div>
                <div class="db-card-row">
                    <span>Process</span>
                    <span style="font-weight: 600;">${ip.process}</span>
                </div>
                <div class="db-card-row">
                    <span>Metal</span>
                    <span style="font-weight: 600; font-size: 0.85rem;">${ip.metal_option}</span>
                </div>
                <div class="db-card-row">
                    <span>PDK</span>
                    <span style="font-weight: 600; font-size: 0.85rem;">${ip.pdk_version}</span>
                </div>
                <div class="db-card-row">
                    <span>Customer</span>
                    <span style="font-weight: 600;">${ip.customer || 'N/A'}</span>
                </div>
            </div>`;
        });
        html += '</div>';
    }
    
    return html;
}


function closeAddRowModal() {
    document.getElementById('addRowModal').classList.remove('active');
}
