function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
}

const csrftoken = getCookie('csrftoken');

let selectedSeedId = null;

function setSelectedSeed(cropTypeId) {
    selectedSeedId = cropTypeId || null;
    try {
        if (window.localStorage) {
            window.localStorage.setItem('selectedSeedId', selectedSeedId || '');
        }
    } catch (_) {}
}

function plantPlot(plotId) {
    if (!selectedSeedId) {
        alert('Choose a seed first');
        return;
    }

    fetch(`/api/plots/${plotId}/plant/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken,
        },
        body: JSON.stringify({ crop_type_id: selectedSeedId }),
    }).then(async (resp) => {
        if (resp.ok) {
            const plot = await resp.json();
            updatePlotCellGrowing(plot);
            updateTimers();
            refreshBalance();
        } else {
            let msg = 'Error planting';
            try {
                const data = await resp.json();
                if (data.detail) msg = data.detail;
            } catch {}
            alert(msg);
        }
    });
}

function harvestPlot(plotId) {
    fetch(`/api/plots/${plotId}/harvest/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrftoken,
        },
    }).then(async (resp) => {
        if (resp.ok) {
            const data = await resp.json();
            updatePlotCellEmpty(plotId);
            if (data.inventory_item) {
                refreshInventoryItem(data.inventory_item);
            }
            refreshBalance();
        } else {
            let msg = 'Error harvesting';
            try {
                const data = await resp.json();
                if (data.detail) msg = data.detail;
            } catch {}
            alert(msg);
        }
    });
}

function sellNpc(cropTypeId, quantity) {
    fetch('/api/inventory/sell-npc/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken,
        },
        body: JSON.stringify({ crop_type_id: cropTypeId, quantity: quantity }),
    }).then(async (resp) => {
        const text = await resp.text();
        console.log('sell-npc response:', resp.status, text);

        if (resp.ok) {
            window.location.reload();
        } else {
            let msg = 'Error selling';
            try {
                const data = JSON.parse(text);
                if (data.detail) msg = data.detail;
            } catch {}
            alert(msg);
        }
    });
}

function sellNpcPartial(cropTypeId) {
    const input = document.getElementById(`sell-qty-${cropTypeId}`);
    if (!input) return;

    const qty = parseInt(input.value, 10);
    if (!qty || qty <= 0) {
        alert('Enter a positive quantity');
        return;
    }

    saveSellQty(cropTypeId, qty);
    sellNpc(cropTypeId, qty);
}

function setMaxSellQty(cropTypeId, maxQty) {
    const input = document.getElementById(`sell-qty-${cropTypeId}`);
    if (!input) return;
    input.value = maxQty;
    saveSellQty(cropTypeId, maxQty);
}

function saveSellQty(cropTypeId, qty) {
    try {
        if (window.localStorage) {
            window.localStorage.setItem(`sellQty_${cropTypeId}`, qty.toString());
        }
    } catch (_) {}
}

function getSavedSellQty(cropTypeId) {
    try {
        if (!window.localStorage) return null;
        const raw = window.localStorage.getItem(`sellQty_${cropTypeId}`);
        if (!raw) return null;
        const parsed = parseInt(raw, 10);
        return Number.isFinite(parsed) ? parsed : null;
    } catch (_) {
        return null;
    }
}

function initSellInputs() {
    const inputs = document.querySelectorAll('.sell-qty-input');
    inputs.forEach(input => {
        const cropId = input.getAttribute('data-crop-id');
        const maxVal = parseInt(input.getAttribute('max'), 10);
        const saved = cropId ? getSavedSellQty(cropId) : null;
        if (saved !== null) {
            const applied = Math.min(saved, Number.isFinite(maxVal) ? maxVal : saved);
            input.value = applied;
        }
        input.addEventListener('change', () => {
            const val = parseInt(input.value, 10);
            if (!val || val <= 0) return;
            saveSellQty(cropId, Math.min(val, Number.isFinite(maxVal) ? maxVal : val));
        });
    });
}

function formatRemaining(seconds) {
    if (seconds <= 0) return 'Ready now';
    const minutes = Math.floor(seconds / 60);
    const secs = Math.max(0, seconds % 60);
    return `${minutes}:${secs.toString().padStart(2, '0')}`;
}

function updateTimers() {
    const now = Date.now();
    const elements = document.querySelectorAll('.plot-timer');

    elements.forEach(el => {
        const readyAtStr = el.getAttribute('data-ready-at');
        if (!readyAtStr) return;

        const readyAt = new Date(readyAtStr).getTime();
        const diffSeconds = Math.floor((readyAt - now) / 1000);
        const cell = el.closest('.plot-cell');

        if (diffSeconds <= 0) {
            el.textContent = 'Ready to harvest';

            if (cell) {
                cell.classList.remove('plot-growing');
                cell.classList.add('plot-ready');

                const btn = cell.querySelector('.harvest-btn');
                if (btn) {
                    btn.style.display = 'inline-block';
                }
            }
        } else {
            el.textContent = 'Ready in ' + formatRemaining(diffSeconds);
        }
    });
}

function initTimers() {
    updateTimers();
    setInterval(updateTimers, 1000);
}

function initContractBoard() {
    const items = Array.from(document.querySelectorAll('.contract-item'));
    const timerEl = document.getElementById('contracts-timer');
    const expiresAt = timerEl ? new Date(timerEl.getAttribute('data-expires-at')).getTime() : null;
    if (!items.length || !timerEl || !expiresAt) return;

    let refreshed = false;

    function formatCountdown(seconds) {
        if (seconds <= 0) return 'Expired';
        const minutes = Math.floor(seconds / 60);
        const secs = Math.max(0, seconds % 60);
        return `${minutes}:${secs.toString().padStart(2, '0')}`;
    }

    function updateContractTimers() {
        const now = Date.now();
        const diffSeconds = Math.floor((expiresAt - now) / 1000);
        if (diffSeconds <= 0) {
            timerEl.textContent = 'New Contracts In: 0:00';
            items.forEach(item => {
                item.classList.add('contract-expired');
                item.classList.remove('contract-active');
            });
            if (!refreshed) {
                refreshed = true;
                setTimeout(() => window.location.reload(), 500);
            }
        } else {
            timerEl.textContent = 'New Contracts In: ' + formatCountdown(diffSeconds);
        }
    }

    function tryComplete(item) {
        if (
            item.classList.contains('contract-expired') ||
            item.classList.contains('contract-completed') ||
            item.classList.contains('contract-busy')
        ) return;
        const id = item.getAttribute('data-contract-id');
        if (!id) return;

        item.classList.add('contract-busy');
        fetch(`/api/contracts/${id}/complete/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrftoken,
            },
        }).then(async (resp) => {
            if (resp.ok) {
                window.location.reload();
            }
        }).catch(() => {
            // silent failure per requirements
        }).finally(() => {
            item.classList.remove('contract-busy');
        });
    }

    items.forEach(item => {
        item.addEventListener('click', () => tryComplete(item));
    });

    updateContractTimers();
    setInterval(updateContractTimers, 1000);
}

document.addEventListener('DOMContentLoaded', () => {
    const globalSeedSelect = document.getElementById('global-crop-select');
    if (globalSeedSelect) {
        let savedSeed = null;
        try {
            savedSeed = window.localStorage ? window.localStorage.getItem('selectedSeedId') : null;
        } catch (_) {}

        if (savedSeed) {
            globalSeedSelect.value = savedSeed;
            setSelectedSeed(savedSeed);
        } else {
            setSelectedSeed(globalSeedSelect.value);
        }

        globalSeedSelect.addEventListener('change', (e) => setSelectedSeed(e.target.value));
    }
    initSellInputs();
    initTimers();
    initContractBoard();
    initBalancePolling();
    const cropSelect = document.getElementById('market-crop-select');
    const qtyInput = document.getElementById('market-qty');
    if (cropSelect && qtyInput) {
        function capQuantity() {
            const available = parseInt(cropSelect.selectedOptions[0]?.getAttribute('data-available') || '0', 10);
            const maxVal = isNaN(available) ? 0 : Math.max(0, available);
            qtyInput.max = maxVal || '';

            let current = parseInt(qtyInput.value, 10);
            if (isNaN(current) || current <= 0) return;
            if (maxVal && current > maxVal) {
                qtyInput.value = maxVal;
            }
        }
        cropSelect.addEventListener('change', capQuantity);
        qtyInput.addEventListener('input', capQuantity);
        capQuantity();
    }
});

function submitMarketListing() {
    const cropSelect = document.getElementById('market-crop-select');
    const qtyInput = document.getElementById('market-qty');
    const priceInput = document.getElementById('market-price');
    if (!cropSelect || !qtyInput || !priceInput) return;

    const cropId = cropSelect.value;
    const qty = parseInt(qtyInput.value, 10);
    const price = parseInt(priceInput.value, 10);

    if (!cropId || !qty || qty <= 0 || !price || price <= 0) {
        alert('Enter crop, quantity, and price.');
        return;
    }

    const available = parseInt(cropSelect.selectedOptions[0]?.getAttribute('data-available') || '0', 10);
    const safeQty = Math.min(qty, isNaN(available) ? qty : available);
    qtyInput.value = safeQty > 0 ? safeQty : '';

    fetch('/api/market/listings/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken,
        },
        body: JSON.stringify({
            crop_type_id: cropId,
            quantity: safeQty,
            unit_price: price,
        }),
    }).then(async (resp) => {
        if (resp.ok) {
            window.location.reload();
        } else {
            let msg = 'Error creating listing';
            try {
                const data = await resp.json();
                if (data.detail) msg = data.detail;
            } catch {}
            alert(msg);
        }
    });
}

function buyListing(listingId) {
    fetch(`/api/market/listings/${listingId}/buy/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken,
        },
        body: JSON.stringify({}),
    }).then(async (resp) => {
        if (resp.ok) {
            window.location.reload();
        } else {
            let msg = 'Error buying listing';
            try {
                const data = await resp.json();
                if (data.detail) msg = data.detail;
            } catch {}
            alert(msg);
        }
    });
}

function toggleMarketForm() {
    const form = document.getElementById('market-form');
    if (!form) return;
    form.classList.toggle('hidden');
}

function initBalancePolling() {
    const balanceEl = document.getElementById('farm-balance-value');
    if (!balanceEl) return;

    async function fetchBalance() {
        try {
            const resp = await fetch('/api/farm/me/');
            if (!resp.ok) return;
            const data = await resp.json();
            if (typeof data.balance === 'number') {
                balanceEl.textContent = `${data.balance} coins`;
            }
        } catch (e) {
            // ignore polling errors
        }
    }

    fetchBalance();
    setInterval(fetchBalance, 5000);
}

async function refreshBalance() {
    const balanceEl = document.getElementById('farm-balance-value');
    if (!balanceEl) return;
    try {
        const resp = await fetch('/api/farm/me/');
        if (!resp.ok) return;
        const data = await resp.json();
        if (typeof data.balance === 'number') {
            balanceEl.textContent = `${data.balance} coins`;
        }
    } catch {}
}
function updatePlotCellGrowing(plot) {
    const cell = document.querySelector(`.plot-cell[data-plot-id="${plot.id}"]`);
    if (!cell) return;

    const readyAt = plot.harvest_ready_at;
    const cropName = plot.crop_type?.name || 'Crop';

    cell.className = 'plot-cell plot-growing';
    cell.innerHTML = `
        <div class="plot-title">${cropName}</div>
        <div class="plot-meta plot-timer" data-ready-at="${readyAt}">Ready in ...</div>
        <button type="button" class="harvest-btn" style="display: none;" onclick="harvestPlot(${plot.id})">Harvest</button>
    `;
}

function updatePlotCellEmpty(plotId) {
    const cell = document.querySelector(`.plot-cell[data-plot-id="${plotId}"]`);
    if (!cell) return;
    cell.className = 'plot-cell plot-empty';
    cell.setAttribute('data-plot-id', plotId);
    cell.setAttribute('onclick', `plantPlot(${plotId})`);
    cell.innerHTML = `<div class="plot-title">Empty</div>`;
}

function refreshInventoryItem(inventoryItem) {
    const cropId = inventoryItem.crop_type.id;
    const quantity = inventoryItem.quantity;
    const cropName = inventoryItem.crop_type.name;
    const basePrice = inventoryItem.crop_type.base_price;

    // find existing line by data attribute or input id
    let line = document.querySelector(`.inventory-line[data-crop-id="${cropId}"]`);
    if (!line) {
        const input = document.getElementById(`sell-qty-${cropId}`);
        if (input) line = input.closest('.inventory-line');
    }

    if (!line) {
        const ul = document.querySelector('.inventory-card ul');
        if (!ul) return;
        const liWrapper = document.createElement('li');
        liWrapper.innerHTML = `
            <div class="inventory-line" data-crop-id="${cropId}">
                <span class="inventory-name"></span>
                <input type="number" id="sell-qty-${cropId}" data-crop-id="${cropId}" class="sell-qty-input" min="1" value="1">
                <button type="button" class="sell-btn inventory-sell-btn" onclick="setMaxSellQty(${cropId}, ${quantity})">Max</button>
                <button type="button" class="sell-btn inventory-sell-btn" onclick="sellNpcPartial(${cropId})">Sell</button>
            </div>
        `;
        ul.prepend(liWrapper);
        line = liWrapper.querySelector('.inventory-line');
    }

    const nameEl = line.querySelector('.inventory-name');
    const inputEl = line.querySelector('input');

    if (quantity > 0) {
        nameEl.textContent = `${cropName}: ${quantity} (${basePrice}c)`;
        inputEl.max = quantity;
        if (!inputEl.value || parseInt(inputEl.value, 10) > quantity) {
            inputEl.value = quantity;
        }
        line.closest('li').style.display = '';
    } else {
        line.closest('li').style.display = 'none';
    }

    const marketSelect = document.getElementById('market-crop-select');
    if (marketSelect) {
        const opt = marketSelect.querySelector(`option[value="${cropId}"]`);
        if (opt) opt.setAttribute('data-available', quantity);
    }
}
