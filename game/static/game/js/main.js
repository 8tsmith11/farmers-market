function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
}

const csrftoken = getCookie('csrftoken');

function plantPlot(plotId) {
    const select = document.getElementById(`crop-select-${plotId}`);
    if (!select) return;
    const cropTypeId = select.value;
    if (!cropTypeId) {
        alert('Choose a crop first');
        return;
    }

    fetch(`/api/plots/${plotId}/plant/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken,
        },
        body: JSON.stringify({ crop_type_id: cropTypeId }),
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

