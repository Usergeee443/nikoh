// Telegram Web App initialization
const tg = window.Telegram.WebApp;
tg.ready();
tg.expand();
tg.setHeaderColor('#0a0a0b');
tg.setBackgroundColor('#0a0a0b');

// Global state
let currentPage = 'feed';
let userData = null;
let hasActiveTariff = false;

// Page navigation - INSTANT (0.1s)
function showPage(pageName) {
    if (currentPage === pageName) return;
    
    // Hide all pages
    document.querySelectorAll('.page-container').forEach(page => {
        page.classList.remove('active');
    });
    
    // Show target page
    const targetPage = document.getElementById(`page-${pageName}`);
    if (targetPage) {
        targetPage.classList.add('active');
        currentPage = pageName;
        
        // Update nav
        updateNav(pageName);
        
        // Load page data
        loadPageData(pageName);
        
        // Scroll to top
        window.scrollTo({ top: 0, behavior: 'instant' });
    }
}

function updateNav(activePage) {
    document.querySelectorAll('.nav-link').forEach(link => {
        const page = link.getAttribute('data-page');
        const icon = link.querySelector('.material-symbols-outlined');
        
        if (page === activePage) {
            link.classList.remove('text-white/30', 'hover:text-white');
            link.classList.add('text-primary');
            if (icon) icon.style.fontVariationSettings = "'FILL' 1";
        } else {
            link.classList.remove('text-primary');
            link.classList.add('text-white/30', 'hover:text-white');
            if (icon) icon.style.fontVariationSettings = "'FILL' 0";
        }
    });
}

// Navigation event listeners
document.querySelectorAll('.nav-link').forEach(link => {
    link.addEventListener('click', (e) => {
        e.preventDefault();
        const page = link.getAttribute('data-page');
        if (page) showPage(page);
    });
});

// Load page data
async function loadPageData(pageName) {
    switch(pageName) {
        case 'feed':
            await loadFeedData();
            break;
        case 'requests':
            await loadRequestsData();
            break;
        case 'chats':
            await loadChatsData();
            break;
        case 'profile':
            await loadProfileData();
            break;
    }
}

// Initialize user data
async function initUserData() {
    try {
        const response = await fetch('/api/user-data');
        userData = await response.json();
        hasActiveTariff = userData.has_active_tariff || false;
        
        // Update profile page immediately
        if (currentPage === 'profile') {
            updateProfileUI();
        }
        
        // Update feed tariff info
        if (currentPage === 'feed') {
            updateFeedTariffInfo();
        }
    } catch (error) {
        console.error('Error loading user data:', error);
    }
}

// FEED PAGE
let feedCurrentPage = 1;
let feedIsLoading = false;
let feedHasMore = true;

async function loadFeedData() {
    updateFeedTariffInfo();
    if (document.getElementById('feed-listings').children.length === 0 || 
        document.getElementById('feed-skeleton')) {
        await loadFeedListings(1);
    }
}

function updateFeedTariffInfo() {
    const container = document.getElementById('feed-tariff-info');
    const badge = document.getElementById('feed-tariff-badge');
    
    if (hasActiveTariff && userData?.active_tariff) {
        container.innerHTML = `
            <div class="glass-card rounded-2xl p-4 flex items-center justify-between">
                <div>
                    <p class="text-sm font-bold text-white/80">Aktiv tarif</p>
                    <p class="text-xs text-primary mt-1">
                        <span class="font-semibold">${userData.active_tariff.requests_count}</span> ta so'rov qoldi •
                        ${userData.active_tariff.days_remaining} kun qoldi
                    </p>
                </div>
                <a href="/tariff/purchase" class="text-primary text-sm font-semibold hover:underline">Yangilash →</a>
            </div>
        `;
        badge.innerHTML = `<p class="text-[10px] font-black text-primary uppercase tracking-wider">${userData.active_tariff.requests_count} SO'ROV</p>`;
    } else {
        container.innerHTML = `
            <div class="glass-card rounded-2xl p-4 mb-4 border border-yellow-500/30 bg-yellow-500/10">
                <div class="flex items-center gap-3">
                    <div class="size-10 rounded-xl bg-yellow-500/20 flex items-center justify-center">
                        <span class="material-symbols-outlined text-yellow-400 text-[22px]">info</span>
                    </div>
                    <div class="flex-1">
                        <p class="text-sm font-bold text-yellow-400">E'lonlarni ko'rishingiz mumkin</p>
                        <p class="text-[11px] text-yellow-400/80 mt-0.5">So'rov yuborish uchun tarif kerak</p>
                    </div>
                    <a href="/tariff/purchase" class="bg-primary text-black px-4 py-2 rounded-xl text-xs font-bold uppercase tracking-wider active:scale-95 transition-all">
                        Tarif
                    </a>
                </div>
            </div>
        `;
        badge.innerHTML = `<a href="/tariff/purchase" class="glass-card px-3 py-1.5 rounded-full text-[10px] font-black text-yellow-400 uppercase tracking-wider">Tarif</a>`;
    }
}

async function loadFeedListings(page = 1, topOnly = false) {
    if (feedIsLoading) return;
    feedIsLoading = true;

    const container = document.getElementById('feed-listings');
    const skeleton = document.getElementById('feed-skeleton');

    try {
        if (skeleton) {
            setTimeout(() => skeleton.style.display = 'none', 200);
        }

        const response = await fetch(`/feed/api/listings?page=${page}&top_only=${topOnly}`);
        const data = await response.json();

        if (skeleton) skeleton.remove();
        if (page === 1) container.innerHTML = '';

        if (data.listings.length === 0 && page === 1) {
            container.innerHTML = '<div class="text-center py-8 text-white/60">E\'lonlar topilmadi</div>';
            feedHasMore = false;
            return;
        }

        data.listings.forEach(listing => {
            container.appendChild(createFeedListingCard(listing));
        });

        feedHasMore = data.has_next;
        document.getElementById('feed-load-more').classList.toggle('hidden', !feedHasMore);
        feedCurrentPage = page;

    } catch (error) {
        console.error('Error loading listings:', error);
        if (skeleton) skeleton.remove();
        container.innerHTML = '<div class="text-center py-8 text-red-400">Xatolik yuz berdi</div>';
    } finally {
        feedIsLoading = false;
    }
}

function createFeedListingCard(listing) {
    const div = document.createElement('article');
    div.className = 'profile-card glass-card rounded-[22px] overflow-hidden relative flex flex-col group';
    div.style.height = 'calc((100vh - 220px) / 2.8)';
    div.style.minHeight = '245px';
    div.onclick = () => showFeedProfile(listing.user_id);

    const bgImage = listing.photo_url || 'https://via.placeholder.com/400x600?text=' + listing.name;
    
    div.innerHTML = `
        <div class="relative flex-1 bg-cover bg-center" style="background-image: url('${bgImage}')">
            <div class="absolute inset-0 profile-gradient"></div>
            <div class="absolute top-3 left-3 right-3 flex justify-between items-start z-10">
                <div class="flex flex-wrap gap-1.5 items-center">
                    <span class="bg-primary px-2.5 py-1 rounded text-[9px] font-black tracking-widest text-black neon-glow uppercase">#${listing.user_id || '0000'}</span>
                    ${listing.is_top ? '<div class="tag-premium px-2.5 py-1.5 rounded-xl flex items-center gap-1.5 text-[8px] font-extrabold text-white uppercase tracking-wider shadow-lg"><span class="material-symbols-outlined text-[12px] text-primary">star</span> TOP</div>' : ''}
                    <div class="tag-premium px-2.5 py-1.5 rounded-xl flex items-center gap-1.5 text-[8px] font-extrabold text-white uppercase tracking-wider shadow-lg">
                        <span class="material-symbols-outlined text-[12px] text-primary">public</span>
                        ${listing.nationality || 'O\'zbek'}
                    </div>
                    <div class="tag-premium px-2.5 py-1.5 rounded-xl flex items-center gap-1.5 text-[8px] font-extrabold text-white uppercase tracking-wider shadow-lg">
                        <span class="material-symbols-outlined text-[12px] text-primary">location_on</span>
                        ${listing.region || 'Toshkent'}
                    </div>
                </div>
                <button class="size-8 rounded-full glass-card flex items-center justify-center text-white/80 border-white/20">
                    <span class="material-symbols-outlined text-[18px]">favorite</span>
                </button>
            </div>
            <div class="absolute bottom-2 left-4 right-4 z-10">
                <div class="flex items-baseline gap-2 mb-1">
                    <h2 class="text-xl font-extrabold tracking-tight">${listing.name}</h2>
                    <span class="text-[12px] font-bold text-white/60">${listing.age} yosh</span>
                </div>
                <div class="grid grid-cols-2 gap-x-3 gap-y-0.5 text-[10px] font-bold text-white">
                    <span class="flex items-center gap-1.5 truncate">
                        <span class="material-symbols-outlined text-[13px] text-primary">straighten</span>
                        ${listing.height || '-'} sm • ${listing.weight || '-'} kg
                    </span>
                    <span class="flex items-center gap-1.5 truncate">
                        <span class="material-symbols-outlined text-[13px] text-primary">family_restroom</span>
                        ${listing.marital_status || 'Bo\'ydoq'}
                    </span>
                    <span class="flex items-center gap-1.5 truncate">
                        <span class="material-symbols-outlined text-[13px] text-primary">verified_user</span>
                        ${listing.religious_level || 'O\'rtacha'}
                    </span>
                    <span class="flex items-center gap-1.5 truncate">
                        <span class="material-symbols-outlined text-[13px] text-primary">school</span>
                        ${listing.education || 'Oliy'}
                    </span>
                </div>
            </div>
        </div>
        <div class="glass-strip px-4 py-2 flex justify-between items-center text-[8px] uppercase tracking-[0.12em] font-black">
            <div class="flex items-center gap-3 text-white/50">
                <span class="flex items-center gap-1"><span class="material-symbols-outlined text-[14px]">visibility</span> ${listing.views || 0}</span>
                <span class="flex items-center gap-1"><span class="material-symbols-outlined text-[14px]">favorite</span> ${listing.likes || 0}</span>
            </div>
        </div>
    `;

    return div;
}

async function showFeedProfile(userId) {
    const modal = document.getElementById('feed-profile-modal');
    const content = document.getElementById('feed-profile-content');

    content.innerHTML = '<div class="text-center py-8"><div class="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div></div>';
    modal.classList.remove('hidden');

    try {
        const response = await fetch(`/feed/api/listing/${userId}`);
        const profile = await response.json();

        const bgImage = profile.photo_url || 'https://via.placeholder.com/400x600?text=' + profile.name;

        content.innerHTML = `
            <div class="relative h-[45vh] w-full overflow-hidden rounded-2xl mb-4">
                <div class="absolute inset-0 bg-cover bg-center" style="background-image: url('${bgImage}')"></div>
                <div class="absolute inset-0 profile-gradient"></div>
                <button onclick="closeFeedModal()" class="absolute top-4 right-4 size-10 glass-card rounded-full flex items-center justify-center text-white/80">
                    <span class="material-symbols-outlined">close</span>
                </button>
                <div class="absolute bottom-6 left-6 right-6">
                    <div class="flex items-center gap-2 mb-2">
                        <span class="bg-primary/20 text-primary border border-primary/30 px-2 py-0.5 rounded text-[10px] font-black tracking-widest uppercase">#${profile.user_id || '0000'}</span>
                    </div>
                    <h1 class="text-3xl font-extrabold tracking-tight mb-1">${profile.name}, <span class="text-white/70 font-medium text-2xl">${profile.age}</span></h1>
                    <div class="flex items-center gap-1.5 text-white/60 font-medium">
                        <span class="material-symbols-outlined text-[18px] text-primary">location_on</span>
                        ${profile.region || 'Toshkent'}
                    </div>
                </div>
            </div>
            <div class="space-y-4">
                <div class="glass-card rounded-2xl p-4">
                    <div class="flex items-center gap-2 mb-4 border-b border-white/5 pb-2">
                        <span class="material-symbols-outlined text-primary text-[20px]">straighten</span>
                        <h3 class="text-[12px] font-black uppercase tracking-widest text-white/80">Jismoniy ma'lumotlar</h3>
                    </div>
                    <div class="grid grid-cols-2 gap-4">
                        <div>
                            <p class="text-[10px] text-white/40 font-bold uppercase tracking-wider mb-1">Bo'yi</p>
                            <p class="text-[14px] text-white font-semibold">${profile.height || '-'} sm</p>
                        </div>
                        <div>
                            <p class="text-[10px] text-white/40 font-bold uppercase tracking-wider mb-1">Vazni</p>
                            <p class="text-[14px] text-white font-semibold">${profile.weight || '-'} kg</p>
                        </div>
                    </div>
                </div>
                <div class="glass-card rounded-2xl p-4">
                    <div class="flex items-center gap-2 mb-4 border-b border-white/5 pb-2">
                        <span class="material-symbols-outlined text-primary text-[20px]">auto_awesome</span>
                        <h3 class="text-[12px] font-black uppercase tracking-widest text-white/80">Diniy ma'lumotlar</h3>
                    </div>
                    <div class="grid grid-cols-2 gap-y-4 gap-x-4">
                        <div>
                            <p class="text-[10px] text-white/40 font-bold uppercase tracking-wider mb-1">Namoz</p>
                            <p class="text-[14px] text-white font-semibold">${profile.prays || '-'}</p>
                        </div>
                        <div>
                            <p class="text-[10px] text-white/40 font-bold uppercase tracking-wider mb-1">Ro'za</p>
                            <p class="text-[14px] text-white font-semibold">${profile.fasts || '-'}</p>
                        </div>
                        <div class="col-span-2">
                            <p class="text-[10px] text-white/40 font-bold uppercase tracking-wider mb-1">Diniy daraja</p>
                            <p class="text-[14px] text-white font-semibold">${profile.religious_level || '-'}</p>
                        </div>
                    </div>
                </div>
                ${profile.bio ? `
                <div class="glass-card rounded-2xl p-5">
                    <h3 class="text-[13px] font-black uppercase tracking-widest text-primary mb-3">O'zim haqimda</h3>
                    <p class="text-[14px] leading-relaxed text-white/80 font-medium">${profile.bio}</p>
                </div>
                ` : ''}
            </div>
            ${profile.request_sent ?
                '<div class="mt-6 glass-card p-4 rounded-2xl text-center text-white/60">So\'rov allaqachon yuborilgan</div>' :
                `<button onclick="sendFeedRequest(${userId})" class="mt-6 w-full h-14 bg-gradient-to-r from-primary to-green-500 rounded-2xl flex items-center justify-center gap-2 text-black font-extrabold text-[15px] tracking-widest uppercase neon-glow active:scale-95 transition-all">SO'ROV YUBORISH 💌</button>`
            }
        `;
    } catch (error) {
        content.innerHTML = '<div class="text-center py-8 text-red-400">Xatolik yuz berdi</div>';
    }
}

function closeFeedModal() {
    document.getElementById('feed-profile-modal').classList.add('hidden');
}

async function sendFeedRequest(receiverId) {
    if (!hasActiveTariff) {
        alert('So\'rov yuborish uchun tarif kerak. Iltimos, tarif sotib oling.');
        showPage('profile');
        return;
    }
    
    if (!confirm('Ushbu foydalanuvchiga so\'rov yuborasizmi?')) return;

    try {
        const response = await fetch('/requests/api/send', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({receiver_id: receiverId})
        });

        const data = await response.json();

        if (response.ok) {
            alert('So\'rov muvaffaqiyatli yuborildi!');
            closeFeedModal();
            showPage('requests');
        } else {
            alert(data.error || 'Xatolik yuz berdi');
        }
    } catch (error) {
        alert('Xatolik yuz berdi');
    }
}

// Feed event listeners
document.getElementById('feed-top-only')?.addEventListener('change', (e) => {
    feedCurrentPage = 1;
    loadFeedListings(1, e.target.checked);
});

document.getElementById('feed-load-more-btn')?.addEventListener('click', () => {
    feedCurrentPage++;
    const topOnly = document.getElementById('feed-top-only')?.checked || false;
    loadFeedListings(feedCurrentPage, topOnly);
});

// REQUESTS PAGE
let requestsCurrentTab = 'received';

async function loadRequestsData() {
    updateRequestsTariffInfo();
    await loadReceivedRequests();
}

function updateRequestsTariffInfo() {
    const container = document.getElementById('requests-tariff-info');
    if (!hasActiveTariff) {
        container.innerHTML = `
            <div class="glass-card rounded-2xl p-5 mb-4 border border-yellow-500/30 bg-yellow-500/10">
                <div class="flex items-center gap-3 mb-3">
                    <div class="size-12 rounded-xl bg-yellow-500/20 flex items-center justify-center">
                        <span class="material-symbols-outlined text-yellow-400 text-[28px]">workspace_premium</span>
                    </div>
                    <div>
                        <h3 class="text-base font-bold text-yellow-400">Tarif kerak</h3>
                        <p class="text-[11px] text-yellow-400/80">So'rov yuborish uchun tarif sotib oling</p>
                    </div>
                </div>
                <a href="/tariff/purchase" class="block w-full bg-primary text-black py-3 rounded-xl text-center font-bold text-sm uppercase tracking-wider neon-glow active:scale-95 transition-all">
                    Tarif sotib olish
                </a>
            </div>
        `;
    } else {
        container.innerHTML = '';
    }
}

function switchRequestsTab(tab) {
    requestsCurrentTab = tab;
    
    if (tab === 'received') {
        document.getElementById('requests-received-tab').classList.add('text-primary', 'active-neon-btn');
        document.getElementById('requests-received-tab').classList.remove('text-white/40');
        document.getElementById('requests-sent-tab').classList.remove('text-primary', 'active-neon-btn');
        document.getElementById('requests-sent-tab').classList.add('text-white/40');
        document.getElementById('requests-received-container').classList.remove('hidden');
        document.getElementById('requests-sent-container').classList.add('hidden');
        loadReceivedRequests();
    } else {
        document.getElementById('requests-sent-tab').classList.add('text-primary', 'active-neon-btn');
        document.getElementById('requests-sent-tab').classList.remove('text-white/40');
        document.getElementById('requests-received-tab').classList.remove('text-primary', 'active-neon-btn');
        document.getElementById('requests-received-tab').classList.add('text-white/40');
        document.getElementById('requests-sent-container').classList.remove('hidden');
        document.getElementById('requests-received-container').classList.add('hidden');
        loadSentRequests();
    }
}

async function loadReceivedRequests() {
    const container = document.getElementById('requests-received-container');
    const skeleton = document.getElementById('requests-received-skeleton');
    
    try {
        if (skeleton) setTimeout(() => skeleton.style.display = 'none', 200);
        
        const response = await fetch('/requests/api/received');
        const data = await response.json();

        if (skeleton) skeleton.remove();
        container.innerHTML = '';

        if (data.requests.length === 0) {
            container.innerHTML = '<div class="text-center py-8 text-white/60">Qabul qilingan so\'rovlar yo\'q</div>';
            return;
        }
        
        const badge = document.getElementById('requests-received-badge');
        if (badge && data.count > 0) {
            badge.textContent = data.count;
            badge.classList.remove('hidden');
        }

        data.requests.forEach(request => {
            container.appendChild(createReceivedRequestCard(request));
        });

    } catch (error) {
        console.error('Error loading received requests:', error);
        if (skeleton) skeleton.remove();
        container.innerHTML = '<div class="text-center py-8 text-red-400">Xatolik yuz berdi</div>';
    }
}

async function loadSentRequests() {
    const container = document.getElementById('requests-sent-container');
    const skeleton = document.getElementById('requests-sent-skeleton');
    
    try {
        if (skeleton) setTimeout(() => skeleton.style.display = 'none', 200);
        
        const response = await fetch('/requests/api/sent');
        const data = await response.json();

        if (skeleton) skeleton.remove();
        container.innerHTML = '';

        if (data.requests.length === 0) {
            container.innerHTML = '<div class="text-center py-8 text-white/60">Yuborilgan so\'rovlar yo\'q</div>';
            return;
        }
        
        const badge = document.getElementById('requests-sent-badge');
        if (badge && data.count > 0) {
            badge.textContent = data.count;
            badge.classList.remove('hidden');
        }

        data.requests.forEach(request => {
            container.appendChild(createSentRequestCard(request));
        });

    } catch (error) {
        console.error('Error loading sent requests:', error);
        if (skeleton) skeleton.remove();
        container.innerHTML = '<div class="text-center py-8 text-red-400">Xatolik yuz berdi</div>';
    }
}

function createReceivedRequestCard(request) {
    const div = document.createElement('article');
    div.className = 'profile-card glass-card rounded-[28px] overflow-hidden relative flex flex-col group';
    div.style.height = 'calc((100vh - 220px) / 2.8)';
    div.style.minHeight = '245px';

    const statusBadge = request.status === 'pending' 
        ? '<div class="status-pending px-3 py-1 rounded-full flex items-center gap-1.5"><span class="material-symbols-outlined text-[14px]">pending_actions</span> KUTILMOQDA</div>'
        : request.status === 'accepted'
        ? '<div class="bg-green-500/20 border-green-500/40 text-green-400 px-3 py-1 rounded-full flex items-center gap-1.5 text-[9px] font-black uppercase"><span class="material-symbols-outlined text-[14px]">check_circle</span> QABUL QILINDI</div>'
        : '<div class="status-rejected px-3 py-1 rounded-full flex items-center gap-1.5"><span class="material-symbols-outlined text-[14px]">cancel</span> RAD ETILDI</div>';

    const bgImage = 'https://via.placeholder.com/400x600?text=' + (request.sender_name || 'User');
    
    div.innerHTML = `
        <div class="relative flex-1 bg-cover bg-center" style="background-image: url('${bgImage}')">
            <div class="absolute inset-0 profile-gradient"></div>
            <div class="absolute top-4 left-4 right-4 flex justify-between items-start z-10">
                <div class="flex flex-wrap items-center gap-1.5">
                    <span class="bg-primary px-2.5 py-1 rounded text-[10px] font-black tracking-widest text-black neon-glow uppercase">#${request.sender_id || '0000'}</span>
                </div>
            </div>
            <div class="absolute bottom-3 left-5 right-5 z-10">
                <div class="flex items-baseline gap-2 mb-1.5">
                    <h2 class="text-2xl font-extrabold tracking-tight">${request.sender_name || 'Foydalanuvchi'}</h2>
                </div>
                ${request.message ? `<p class="text-sm text-white/80 mt-2 line-clamp-2">${request.message}</p>` : ''}
            </div>
        </div>
        <div class="glass-strip px-5 py-3 flex justify-between items-center text-[9px] uppercase tracking-[0.15em] font-black">
            <div class="flex items-center gap-3.5 text-white/50">
                <span class="flex items-center gap-1"><span class="material-symbols-outlined text-[15px]">schedule</span> ${formatTimeAgo(new Date(request.created_at))}</span>
            </div>
            ${statusBadge}
        </div>
        ${request.status === 'pending' ? `
            <div class="glass-strip px-5 py-3 flex gap-2">
                <button onclick="acceptRequest(${request.id})" class="flex-1 bg-green-500/20 border-green-500/40 text-green-400 py-2.5 rounded-xl font-black text-[10px] uppercase tracking-wider hover:bg-green-500/30 transition active:scale-95">
                    Qabul qilish
                </button>
                <button onclick="rejectRequest(${request.id})" class="flex-1 bg-red-500/20 border-red-500/40 text-red-400 py-2.5 rounded-xl font-black text-[10px] uppercase tracking-wider hover:bg-red-500/30 transition active:scale-95">
                    Rad etish
                </button>
            </div>
        ` : ''}
        ${request.chat_id ? `
            <div class="glass-strip px-5 py-3">
                <a href="/chat/${request.chat_id}" class="block text-center bg-primary/20 border-primary/40 text-primary py-2.5 rounded-xl font-black text-[10px] uppercase tracking-wider hover:bg-primary/30 transition">
                    Chatga o'tish
                </a>
            </div>
        ` : ''}
    `;

    return div;
}

function createSentRequestCard(request) {
    const div = document.createElement('article');
    div.className = 'profile-card glass-card rounded-[28px] overflow-hidden relative flex flex-col group';
    div.style.height = 'calc((100vh - 220px) / 2.8)';
    div.style.minHeight = '245px';

    const statusBadge = request.status === 'pending' 
        ? '<div class="status-pending px-3 py-1 rounded-full flex items-center gap-1.5"><span class="material-symbols-outlined text-[14px]">pending_actions</span> KUTILMOQDA</div>'
        : request.status === 'accepted'
        ? '<div class="bg-green-500/20 border-green-500/40 text-green-400 px-3 py-1 rounded-full flex items-center gap-1.5 text-[9px] font-black uppercase"><span class="material-symbols-outlined text-[14px]">check_circle</span> QABUL QILINDI</div>'
        : '<div class="status-rejected px-3 py-1 rounded-full flex items-center gap-1.5"><span class="material-symbols-outlined text-[14px]">cancel</span> RAD ETILDI</div>';

    const bgImage = 'https://via.placeholder.com/400x600?text=' + (request.receiver_name || 'User');
    
    div.innerHTML = `
        <div class="relative flex-1 bg-cover bg-center" style="background-image: url('${bgImage}')">
            <div class="absolute inset-0 profile-gradient"></div>
            <div class="absolute top-4 left-4 right-4 flex justify-between items-start z-10">
                <div class="flex flex-wrap items-center gap-1.5">
                    <span class="bg-primary px-2.5 py-1 rounded text-[10px] font-black tracking-widest text-black neon-glow uppercase">#${request.receiver_id || '0000'}</span>
                </div>
            </div>
            <div class="absolute bottom-3 left-5 right-5 z-10">
                <div class="flex items-baseline gap-2 mb-1.5">
                    <h2 class="text-2xl font-extrabold tracking-tight">${request.receiver_name || 'Foydalanuvchi'}</h2>
                </div>
                ${request.message ? `<p class="text-sm text-white/80 mt-2 line-clamp-2">${request.message}</p>` : ''}
            </div>
        </div>
        <div class="glass-strip px-5 py-3 flex justify-between items-center text-[9px] uppercase tracking-[0.15em] font-black">
            <div class="flex items-center gap-3.5 text-white/50">
                <span class="flex items-center gap-1"><span class="material-symbols-outlined text-[15px]">schedule</span> ${formatTimeAgo(new Date(request.created_at))}</span>
            </div>
            ${statusBadge}
        </div>
        ${request.status === 'pending' ? `
            <div class="glass-strip px-5 py-3">
                <button onclick="cancelRequest(${request.id})" class="w-full bg-gray-500/20 border-gray-500/40 text-gray-400 py-2.5 rounded-xl font-black text-[10px] uppercase tracking-wider hover:bg-gray-500/30 transition active:scale-95">
                    Bekor qilish
                </button>
            </div>
        ` : ''}
        ${request.chat_id ? `
            <div class="glass-strip px-5 py-3">
                <a href="/chat/${request.chat_id}" class="block text-center bg-primary/20 border-primary/40 text-primary py-2.5 rounded-xl font-black text-[10px] uppercase tracking-wider hover:bg-primary/30 transition">
                    Chatga o'tish
                </a>
            </div>
        ` : ''}
    `;

    return div;
}

async function acceptRequest(requestId) {
    if (!confirm('Ushbu so\'rovni qabul qilasizmi?')) return;
    try {
        const response = await fetch(`/requests/api/${requestId}/accept`, { method: 'POST' });
        const data = await response.json();
        if (response.ok) {
            alert('So\'rov qabul qilindi!');
            loadReceivedRequests();
        } else {
            alert(data.error || 'Xatolik yuz berdi');
        }
    } catch (error) {
        alert('Xatolik yuz berdi');
    }
}

async function rejectRequest(requestId) {
    if (!confirm('Ushbu so\'rovni rad qilasizmi?')) return;
    try {
        const response = await fetch(`/requests/api/${requestId}/reject`, { method: 'POST' });
        const data = await response.json();
        if (response.ok) {
            alert('So\'rov rad etildi');
            loadReceivedRequests();
        } else {
            alert(data.error || 'Xatolik yuz berdi');
        }
    } catch (error) {
        alert('Xatolik yuz berdi');
    }
}

async function cancelRequest(requestId) {
    if (!confirm('Ushbu so\'rovni bekor qilasizmi?')) return;
    try {
        const response = await fetch(`/requests/api/${requestId}/cancel`, { method: 'POST' });
        const data = await response.json();
        if (response.ok) {
            alert('So\'rov bekor qilindi');
            loadSentRequests();
        } else {
            alert(data.error || 'Xatolik yuz berdi');
        }
    } catch (error) {
        alert('Xatolik yuz berdi');
    }
}

// Requests event listeners
document.getElementById('requests-received-tab')?.addEventListener('click', () => switchRequestsTab('received'));
document.getElementById('requests-sent-tab')?.addEventListener('click', () => switchRequestsTab('sent'));

// CHATS PAGE
async function loadChatsData() {
    const container = document.getElementById('chats-list');
    const skeleton = document.getElementById('chats-skeleton');
    
    try {
        if (skeleton) setTimeout(() => skeleton.style.display = 'none', 200);
        
        const response = await fetch('/chat/api/list');
        const data = await response.json();

        if (skeleton) skeleton.remove();
        container.innerHTML = '';

        if (data.chats.length === 0) {
            container.innerHTML = '<div class="text-center py-8 text-white/60">Chatlar yo\'q</div>';
            return;
        }

        data.chats.forEach(chat => {
            container.appendChild(createChatCard(chat));
        });

    } catch (error) {
        console.error('Error loading chats:', error);
        if (skeleton) skeleton.remove();
        container.innerHTML = '<div class="text-center py-8 text-red-400">Xatolik yuz berdi</div>';
    }
}

function createChatCard(chat) {
    const div = document.createElement('div');
    div.className = 'glass-card rounded-2xl p-4 cursor-pointer hover:bg-white/5 transition active:scale-[0.98]';
    div.onclick = () => window.location.href = `/chat/${chat.id}`;

    const lastMsg = chat.last_message;
    const timeAgo = lastMsg ? formatTimeAgo(new Date(lastMsg.created_at)) : '';
    const unreadBadge = chat.unread_count > 0 ? `
        <span class="absolute -top-1 -right-1 bg-primary text-black text-[10px] font-black px-1.5 rounded-full min-w-[18px] h-[18px] flex items-center justify-center border-2 border-background-dark">
            ${chat.unread_count}
        </span>
    ` : '';

    div.innerHTML = `
        <div class="flex items-center gap-3">
            <div class="relative size-14 rounded-full overflow-hidden border-2 border-white/10">
                <div class="w-full h-full bg-gradient-to-br from-primary/20 to-green-500/20 flex items-center justify-center text-2xl font-bold">
                    ${chat.other_user.name ? chat.other_user.name.charAt(0).toUpperCase() : '?'}
                </div>
                ${chat.is_active && !chat.is_expired ? `
                    <div class="absolute bottom-0 right-0 size-3 bg-primary rounded-full border-2 border-background-dark"></div>
                ` : ''}
            </div>
            <div class="flex-1 min-w-0">
                <div class="flex items-center justify-between mb-1">
                    <h3 class="text-base font-bold text-white truncate">${chat.other_user.name || 'Foydalanuvchi'}</h3>
                    <span class="text-[10px] text-white/40 ml-2">${timeAgo}</span>
                </div>
                ${lastMsg ? `
                    <p class="text-sm text-white/60 truncate">${lastMsg.is_mine ? 'Siz: ' : ''}${lastMsg.content}</p>
                ` : '<p class="text-sm text-white/40">Chat boshlandi</p>'}
                ${chat.is_expired ? `
                    <p class="text-[10px] text-red-400 mt-1">Muddati tugagan</p>
                ` : chat.days_remaining !== null ? `
                    <p class="text-[10px] text-primary mt-1">${chat.days_remaining} kun qoldi</p>
                ` : ''}
            </div>
            ${unreadBadge}
        </div>
    `;

    return div;
}

// PROFILE PAGE
async function loadProfileData() {
    if (!userData) {
        await initUserData();
    }
    updateProfileUI();
}

function updateProfileUI() {
    if (!userData) return;
    
    document.getElementById('profile-avatar').textContent = userData.profile?.name?.[0] || '?';
    document.getElementById('profile-name').textContent = userData.profile?.name || 'Foydalanuvchi';
    document.getElementById('profile-telegram-id').textContent = `#${userData.telegram_id || '0'}`;
    document.getElementById('profile-views').textContent = userData.profile?.views || 0;
    document.getElementById('profile-likes').textContent = userData.profile?.likes || 0;
    document.getElementById('profile-requests').textContent = userData.sent_requests_count || 0;
    
    const isActive = userData.profile?.is_active || false;
    document.getElementById('profile-status-text').textContent = isActive ? 'Aktiv' : 'Passiv';
    document.getElementById('profile-toggle').checked = isActive;
    
    if (hasActiveTariff) {
        document.getElementById('profile-top-btn').classList.remove('hidden');
    } else {
        document.getElementById('profile-top-btn').classList.add('hidden');
    }
}

document.getElementById('profile-toggle')?.addEventListener('change', async function() {
    try {
        const response = await fetch('/profile/toggle-active', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'}
        });
        
        const data = await response.json();
        
        if (response.ok) {
            await initUserData();
            updateProfileUI();
        } else {
            alert(data.error || 'Xatolik yuz berdi');
            this.checked = !this.checked;
        }
    } catch (error) {
        alert('Xatolik yuz berdi');
        this.checked = !this.checked;
    }
});

// Utility functions
function formatTimeAgo(date) {
    const now = new Date();
    const diff = now - date;
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) return 'hozir';
    if (minutes < 60) return `${minutes}min`;
    if (hours < 24) return `${hours}soat`;
    if (days < 7) return `${days}kun`;
    return date.toLocaleDateString('uz-UZ', { day: 'numeric', month: 'short' });
}

// Initialize on load
document.addEventListener('DOMContentLoaded', () => {
    initUserData();
    loadPageData(currentPage);
});
