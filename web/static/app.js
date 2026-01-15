// SpottyHue Minimalist App Logic

const basePath = (window.__BASE_PATH__ || '').replace(/\/$/, '');
const API_BASE = `${basePath}/api`;

// State
let state = {
    active: false,
    config: {},
    lights: [],
    groups: [],
    selectedLights: [],
    currentTrack: null,
    currentColors: [],
    viewMode: 'groups' // 'groups' or 'lights'
};

let pollInterval = null;

// Initialization
document.addEventListener('DOMContentLoaded', () => {
    console.log('SpottyHue App Initializing...');
    init();
});

async function init() {
    await Promise.all([
        loadStatus(),
        loadLights(),
        loadGroups()
    ]);
    
    // Smart Default: If no groups exist, switch to lights view automatically
    if (state.groups.length === 0) {
        console.log('No groups found, switching to Lights view');
        switchLightTab('lights');
    }
    
    startPolling();
    render();
}

// API Interactions
async function loadStatus() {
    try {
        const res = await fetch(`${API_BASE}/status`);
        const data = await res.json();
        
        state.active = data.active;
        state.config = data.config;
        state.currentTrack = data.current_track;
        state.currentColors = data.current_colors || [];
        
        // Sync local selection with server config
        if (state.config.light_ids) {
            state.selectedLights = state.config.light_ids;
        }

        render();
    } catch (e) {
        console.error('Status load failed', e);
    }
}

async function loadLights() {
    try {
        const res = await fetch(`${API_BASE}/lights`);
        state.lights = await res.json();
        // Sort: color capable first
        state.lights.sort((a, b) => (b.color_capable - a.color_capable));
        renderLightList();
    } catch (e) {
        console.error('Lights load failed', e);
    }
}

async function loadGroups() {
    try {
        const res = await fetch(`${API_BASE}/groups`);
        state.groups = await res.json();
        renderLightList();
    } catch (e) {
        console.error('Groups load failed', e);
    }
}

async function toggleSync() {
    const endpoint = state.active ? `${API_BASE}/stop` : `${API_BASE}/start`;
    
    // Optimistic UI update
    state.active = !state.active;
    render();

    try {
        const res = await fetch(endpoint, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(state.active ? {
                light_ids: state.selectedLights,
                num_colors: parseInt(document.getElementById('num-colors').value),
                update_interval: parseInt(document.getElementById('update-interval').value),
                brightness: parseInt(document.getElementById('brightness').value)
            } : {})
        });
        
        const data = await res.json();
        if (!res.ok) throw new Error(data.message);
        
    } catch (e) {
        console.error('Toggle failed', e);
        // Revert on error
        state.active = !state.active;
        render();
        alert('Failed to toggle sync: ' + e.message);
    }
}

async function updateConfig() {
    // Read values from DOM
    const brightness = parseInt(document.getElementById('brightness').value);
    const numColors = parseInt(document.getElementById('num-colors').value);
    const interval = parseInt(document.getElementById('update-interval').value);

    // Update UI values immediately
    document.getElementById('brightness-val').textContent = Math.round((brightness/254)*100) + '%';
    document.getElementById('colors-val').textContent = numColors;
    document.getElementById('interval-val').textContent = interval + 's';

    try {
        await fetch(`${API_BASE}/config`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                light_ids: state.selectedLights, // Always send current selection
                brightness,
                num_colors: numColors,
                update_interval: interval
            })
        });
    } catch (e) {
        console.error('Config update failed', e);
    }
}

async function testConnection() {
    const btn = event.target;
    const originalText = btn.textContent;
    btn.textContent = 'Testing...';
    btn.disabled = true;

    try {
        const res = await fetch(`${API_BASE}/test-connection`);
        const data = await res.json();
        const msg = `Spotify: ${data.spotify ? 'OK' : 'Fail'}\nHue: ${data.hue ? 'OK' : 'Fail'}`;
        alert(msg);
    } catch (e) {
        alert('Test failed');
    } finally {
        btn.textContent = originalText;
        btn.disabled = false;
    }
}

// Rendering
function render() {
    // 1. Play/Pause Button & Status
    const btn = document.getElementById('toggle-btn');
    const icon = document.getElementById('toggle-icon');
    const badge = document.getElementById('status-badge');

    if (state.active) {
        icon.className = 'fas fa-stop text-xl';
        btn.className = 'absolute -bottom-6 right-6 w-16 h-16 rounded-full bg-red-500 text-white flex items-center justify-center shadow-lg hover:scale-110 transition-transform duration-200 z-20 focus:outline-none play-active';
        badge.textContent = 'Sync Active';
        badge.className = 'mb-8 px-4 py-1.5 rounded-full bg-green-500/20 backdrop-blur-md text-xs font-bold uppercase tracking-wider text-green-200 border border-green-500/30';
    } else {
        icon.className = 'fas fa-play text-xl ml-1';
        btn.className = 'absolute -bottom-6 right-6 w-16 h-16 rounded-full bg-white text-black flex items-center justify-center shadow-lg hover:scale-110 transition-transform duration-200 z-20 focus:outline-none';
        badge.textContent = 'Sync Stopped';
        badge.className = 'mb-8 px-4 py-1.5 rounded-full bg-white/10 backdrop-blur-md text-xs font-medium uppercase tracking-wider text-white/60 border border-white/5';
    }

    // 2. Track Info & Album Art
    const trackName = document.getElementById('track-name');
    const artistName = document.getElementById('artist-name');
    const artImg = document.getElementById('album-art');
    const artPlaceholder = document.getElementById('album-art-placeholder');

    if (state.currentTrack) {
        trackName.textContent = state.currentTrack.name;
        artistName.textContent = state.currentTrack.artist;
        
        if (state.currentTrack.album_art_url) {
            artImg.src = state.currentTrack.album_art_url;
            artImg.classList.remove('hidden');
            artPlaceholder.classList.add('hidden');
        }
    } else {
        trackName.textContent = 'SpottyHue';
        artistName.textContent = 'Sync your lights to Spotify';
        artImg.classList.add('hidden');
        artPlaceholder.classList.remove('hidden');
    }

    // 3. Background Color
    if (state.currentColors && state.currentColors.length > 0) {
        const c1 = state.currentColors[0];
        const c2 = state.currentColors[1] || c1;
        document.body.style.background = `linear-gradient(135deg, rgb(${c1[0]},${c1[1]},${c1[2]}) 0%, rgb(${c2[0]},${c2[1]},${c2[2]}) 100%)`;
    }

    // 4. Update Inputs (if not user interacting)
    if (state.config && !document.getElementById('settings-modal').classList.contains('active')) {
        if(state.config.brightness) {
            document.getElementById('brightness').value = state.config.brightness;
            document.getElementById('brightness-val').textContent = Math.round((state.config.brightness/254)*100) + '%';
        }
        if(state.config.num_colors) {
            document.getElementById('num-colors').value = state.config.num_colors;
            document.getElementById('colors-val').textContent = state.config.num_colors;
        }
        if(state.config.update_interval) {
            document.getElementById('update-interval').value = state.config.update_interval;
            document.getElementById('interval-val').textContent = state.config.update_interval + 's';
        }
    }

    // 5. Render Palette
    renderPalette();
}

function renderPalette() {
    const container = document.getElementById('palette-container');
    if (!container) return;

    if (state.currentColors && state.currentColors.length > 0) {
        container.innerHTML = state.currentColors.map(c => 
            `<div class="w-8 h-8 rounded-full shadow-lg border border-white/10" style="background: rgb(${c[0]},${c[1]},${c[2]})"></div>`
        ).join('');
    } else {
        container.innerHTML = ''; // Hide if no colors
    }
}

function renderLightList() {
    const container = document.getElementById('selection-container');
    if (!container) return; // Guard for old HTML version cache
    
    container.innerHTML = '';

    if (state.viewMode === 'groups') {
        if (state.groups.length === 0) {
            container.innerHTML = `
                <div class="text-white/40 text-center py-8">
                    <div class="mb-2"><i class="fas fa-layer-group text-2xl"></i></div>
                    <div class="text-sm">No groups found</div>
                </div>`;
            return;
        }

        state.groups.forEach(group => {
            const allSelected = group.lights.every(id => state.selectedLights.includes(id));
            
            const div = document.createElement('div');
            div.className = `p-4 rounded-xl cursor-pointer flex items-center justify-between transition-colors ${allSelected ? 'bg-white text-black' : 'bg-white/5 hover:bg-white/10 text-white'}`;
            div.onclick = () => toggleGroup(group);

            const iconMap = {'Living room': 'fa-couch', 'Bedroom': 'fa-bed', 'Kitchen': 'fa-utensils', 'Office': 'fa-briefcase', 'Entertainment': 'fa-tv'};
            const iconClass = iconMap[group.class] || 'fa-lightbulb';

            div.innerHTML = `
                <div class="flex items-center space-x-3">
                    <div class="w-8 h-8 rounded-full flex items-center justify-center ${allSelected ? 'bg-black/10' : 'bg-white/10'}">
                        <i class="fas ${iconClass} text-xs"></i>
                    </div>
                    <div>
                        <div class="font-bold text-sm">${group.name}</div>
                        <div class="text-xs opacity-60">${group.lights.length} Lights</div>
                    </div>
                </div>
                <div class="w-5 h-5 rounded-full border flex items-center justify-center ${allSelected ? 'border-black bg-black text-white' : 'border-white/30'}">
                    ${allSelected ? '<i class="fas fa-check text-[10px]"></i>' : ''}
                </div>
            `;
            container.appendChild(div);
        });
    } else {
        if (state.lights.length === 0) {
            container.innerHTML = `
                <div class="text-white/40 text-center py-8">
                    <div class="mb-2"><i class="fas fa-lightbulb text-2xl"></i></div>
                    <div class="text-sm">No lights found</div>
                </div>`;
            return;
        }

        // Individual Lights Grid
        const grid = document.createElement('div');
        grid.className = 'grid grid-cols-2 gap-3';
        
        state.lights.forEach(light => {
            const isSelected = state.selectedLights.includes(light.id);
            const isColor = light.color_capable;

            const div = document.createElement('div');
            div.className = `p-3 rounded-xl cursor-pointer transition-colors border ${isSelected ? 'bg-white text-black border-white' : 'bg-white/5 border-white/5 hover:bg-white/10 text-white'}`;
            div.onclick = () => toggleLight(light.id);

            div.innerHTML = `
                <div class="flex justify-between items-start mb-2">
                    <i class="fas fa-lightbulb text-sm ${isColor ? '' : 'opacity-50'}"></i>
                    <div class="w-4 h-4 rounded-full border flex items-center justify-center ${isSelected ? 'border-black bg-black text-white' : 'border-white/30'}">
                        ${isSelected ? '<i class="fas fa-check text-[8px]"></i>' : ''}
                    </div>
                </div>
                <div class="font-bold text-sm truncate">${light.name}</div>
            `;
            grid.appendChild(div);
        });
        container.appendChild(grid);
    }
}

function switchLightTab(mode) {
    state.viewMode = mode;
    
    // Update Tab Styles
    const groupTab = document.getElementById('tab-groups');
    const lightTab = document.getElementById('tab-lights');
    
    if (mode === 'groups') {
        groupTab.className = 'px-3 py-1 rounded text-xs font-medium transition-colors bg-white/20 text-white';
        lightTab.className = 'px-3 py-1 rounded text-xs font-medium transition-colors text-white/50 hover:text-white';
    } else {
        groupTab.className = 'px-3 py-1 rounded text-xs font-medium transition-colors text-white/50 hover:text-white';
        lightTab.className = 'px-3 py-1 rounded text-xs font-medium transition-colors bg-white/20 text-white';
    }

    renderLightList();
}

function toggleGroup(group) {
    const allSelected = group.lights.every(id => state.selectedLights.includes(id));

    if (allSelected) {
        // Deselect all
        state.selectedLights = state.selectedLights.filter(id => !group.lights.includes(id));
    } else {
        // Select all (avoid duplicates)
        const newIds = group.lights.filter(id => !state.selectedLights.includes(id));
        state.selectedLights.push(...newIds);
    }
    
    renderLightList();
    updateConfig();
}

function toggleLight(id) {
    if (state.selectedLights.includes(id)) {
        state.selectedLights = state.selectedLights.filter(i => i !== id);
    } else {
        state.selectedLights.push(id);
    }
    renderLightList();
    updateConfig();
}


// UI Helpers
function openSettings() {
    document.getElementById('settings-modal').classList.add('active');
}

function closeSettings() {
    document.getElementById('settings-modal').classList.remove('active');
}

function startPolling() {
    if (pollInterval) clearInterval(pollInterval);
    pollInterval = setInterval(loadStatus, 2000);
}
