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
            window.location.reload();
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
            window.location.reload();
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

function initTimers() {
    function tick() {
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

    tick();
    setInterval(tick, 1000);
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
});
