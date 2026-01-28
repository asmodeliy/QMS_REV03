function renderStatusView(status){
    if(!status) return `<span class="pi-dot empty" title="Not Set"></span>`;
    if(status === 'mass') return `<span class="pi-dot mass" title="Mass Production"></span>`;
    if(status === 'proven') return `<span class="pi-dot proven" title="Silicon Proven"></span>`;
    if(status === 'dev') return `<span class="pi-dot dev" title="Under Development"></span>`;
    if(status === 'plan') return `<span class="pi-dot plan" title="Planning"></span>`;
    return `<span class="pi-dot" title="${status}"></span>`;
}

function updateStatus(ipName, node, status) {
    if (!confirm('Are you sure you want to update the status?')) {
        return;
    }

    fetch(`/product-info/api/status/${encodeURIComponent(ipName)}/${node}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ status: status })
    })
    .then(response => response.json())
    .then(data => {
        if (data.ok) {
            const select = event.target;
            const cell = select.closest('.pi-matrix-cell');
            const view = cell.querySelector('.pi-dot');

            if (view) {
                if (status) {
                    view.outerHTML = renderStatusView(status);
                } else {
                    view.outerHTML = renderStatusView('');
                }
            } else if (status) {
                const temp = document.createElement('div');
                temp.innerHTML = renderStatusView(status);
                cell.appendChild(temp.firstChild);
            }

            showNotification('Status updated successfully', 'success');
        } else {
            showNotification('Failed to update status', 'error');
            location.reload();
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('Failed to update status', 'error');
        location.reload();
    });
}

function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;

    document.body.appendChild(notification);

    setTimeout(() => {
        notification.remove();
    }, 3000);
}

const style = document.createElement('style');
style.textContent = `
    .notification {
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 12px 20px;
        border-radius: 8px;
        color: white;
        font-weight: 500;
        z-index: 1000;
        animation: slideIn 0.3s ease-out;
    }

    .notification-success {
        background: #10b981;
    }

    .notification-error {
        background: #ef4444;
    }

    .notification-info {
        background: #3b82f6;
    }

    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
`;
document.head.appendChild(style);