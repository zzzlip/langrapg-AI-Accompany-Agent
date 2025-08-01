// script.js (FINAL, COMPLETE, AND FIXED VERSION)
document.addEventListener('DOMContentLoaded', () => {
    // --- State Management ---
    const state = {
        token: localStorage.getItem('token'),
        characters: [],
        currentCharacter: null,
        // START OF MODIFICATION: Update user avatar path
        userAvatar: 'assets/user_hand_portrait.jpg'
        // END OF MODIFICATION
    };
    // --- START OF MODIFICATION: Diary state management ---
    let diaryState = {
        entries: [],
        currentIndex: 0
    };
    // --- END OF MODIFICATION ---

    // --- DOM Elements ---
    const views = {
        auth: document.getElementById('auth-view'),
        character: document.getElementById('character-view'),
        app: document.getElementById('app-view')
    };
    const modals = {
        createCharacter: document.getElementById('create-character-modal'),
        moments: document.getElementById('moments-modal'),
        diary: document.getElementById('diary-modal')
    };
    const authForms = {
        login: document.getElementById('login-form'),
        register: document.getElementById('register-form'),
        loginContainer: document.getElementById('login-form-container'),
        registerContainer: document.getElementById('register-form-container'),
        showRegisterLink: document.getElementById('show-register'),
        showLoginLink: document.getElementById('show-login'),
        authError: document.getElementById('auth-error')
    };
    const charElements = {
        list: document.getElementById('character-list'),
        showCreateBtn: document.getElementById('show-create-character-form-btn'),
        logoutBtn: document.getElementById('logout-btn'),
        createForm: document.getElementById('create-character-form'),
        avatarPreview: document.getElementById('avatar-preview'),
        avatarInput: document.getElementById('avatar-input'),
        createError: document.getElementById('create-char-error')
    };
    const appElements = {
        backBtn: document.getElementById('back-to-characters-btn'),
        chatAvatar: document.getElementById('chat-avatar'),
        chatName: document.getElementById('chat-character-name'),
        openMomentsBtn: document.getElementById('open-moments-btn'),
        openDiaryBtn: document.getElementById('open-diary-btn'),
        chatWindow: document.getElementById('chat-window'),
        messageInput: document.getElementById('message-input'),
        sendBtn: document.getElementById('send-btn')
    };
    const momentsElements = {
        avatar: document.getElementById('moments-avatar'),
        name: document.getElementById('moments-char-name'),
        feed: document.getElementById('moments-feed')
    };
    const diaryElements = {
        name: document.getElementById('diary-char-name'),
        entries: document.getElementById('diary-entries'),
        // --- START OF MODIFICATION: Add navigation elements ---
        navigation: document.getElementById('diary-navigation'),
        prevBtn: document.getElementById('diary-prev-btn'),
        nextBtn: document.getElementById('diary-next-btn'),
        pageIndicator: document.getElementById('diary-page-indicator')
        // --- END OF MODIFICATION ---
    };

    // --- HELPER for Authenticated Image URLs ---
    function getAuthenticatedUrl(baseUrl) {
        if (!baseUrl || !baseUrl.startsWith('/')) {
            return baseUrl || 'assets/default_avatar.png';
        }
        if (baseUrl.includes('?token=') || baseUrl.includes('&token=')) {
            return baseUrl;
        }
        if (state.token) {
            return `${baseUrl}?token=${state.token}`;
        }
        return 'assets/default_avatar.png';
    }

    // --- API Helper ---
    const api = {
        async request(endpoint, options = {}) {
            const headers = { ...options.headers };
            if (state.token) {
                headers['Authorization'] = `Bearer ${state.token}`;
            }
            if (!(options.body instanceof FormData)) {
                headers['Content-Type'] = 'application/json';
            }

            const response = await fetch(`/api${endpoint}`, { ...options, headers });

            if (response.status === 401) {
                handleLogout();
                throw new Error('会话已过期，请重新登录。');
            }
            if (!response.ok) {
                try {
                    const errorData = await response.json();
                    throw new Error(errorData.message || '发生未知错误');
                } catch (e) {
                     throw new Error(`HTTP 错误: ${response.status}`);
                }
            }
            if (response.headers.get('Content-Type')?.includes('text/event-stream')) {
                return response;
            }

            const responseText = await response.text();
            if (responseText) {
                try {
                    return JSON.parse(responseText);
                } catch (e) {
                    console.error("Failed to parse API response as JSON:", responseText);
                    throw new Error("服务器返回了无效的数据格式。");
                }
            }
            return;
        }
    };

    // --- View & Modal Management ---
    const showView = (viewName) => {
        Object.values(views).forEach(v => v.classList.remove('active-view'));
        views[viewName].classList.add('active-view');
    };

    const showModal = (modalName) => modals[modalName].style.display = 'flex';
    const hideModal = (modalName) => modals[modalName].style.display = 'none';

    // --- Rendering Functions ---
    const renderCharacterList = () => {
        charElements.list.innerHTML = '';
        if (state.characters.length === 0) {
            charElements.list.innerHTML = '<p class="no-characters">你还没有创建任何角色，快来创建一个吧！</p>';
        } else {
            state.characters.forEach(char => {
                const card = document.createElement('div');
                card.className = 'character-card';
                card.dataset.id = char.id;
                const avatarSrc = getAuthenticatedUrl(char.avatar_url);
                card.innerHTML = `
                    <img src="${avatarSrc}" alt="${char.name}" onerror="this.onerror=null;this.src='assets/default_avatar.png';">
                    <h3>${char.name}</h3>
                `;
                card.addEventListener('click', () => selectCharacter(card.dataset.id));
                charElements.list.appendChild(card);
            });
        }
    };

    const addChatMessage = (type, { text, imageUrl }) => {
        const messageDiv = document.createElement('div');
        const isUserMessage = type === 'user' || type === 'human';
        const displayType = isUserMessage ? 'user' : 'ai';
        messageDiv.className = `chat-message ${displayType}-message`;

        const avatarSrc = isUserMessage ? state.userAvatar : getAuthenticatedUrl(state.currentCharacter.avatar_url);
        let imageHtml = '';
        if (imageUrl && typeof imageUrl === 'string' && imageUrl.trim() !== '') {
            const authenticatedImageUrl = getAuthenticatedUrl(imageUrl);
            imageHtml = `<img src="${authenticatedImageUrl}" alt="Generated image" class="message-image" onerror="this.onerror=null;this.style.display='none';">`;
        }

        messageDiv.innerHTML = `
            <img src="${avatarSrc}" alt="avatar" class="avatar" onerror="this.onerror=null;this.src='assets/default_avatar.png';">
            <div class="message-bubble">
                <p>${text || ''}</p>
                ${imageHtml}
            </div>
        `;
        appElements.chatWindow.appendChild(messageDiv);
        appElements.chatWindow.scrollTop = appElements.chatWindow.scrollHeight;
        return messageDiv;
    };

    // --- Event Handlers & Logic ---
    const handleLogin = async (e) => {
        e.preventDefault();
        authForms.authError.textContent = '';
        const username = document.getElementById('login-username').value;
        const password = document.getElementById('login-password').value;
        try {
            const data = await api.request('/login', {
                method: 'POST',
                body: JSON.stringify({ username, password })
            });
            state.token = data.token;
            localStorage.setItem('token', data.token);
            await fetchCharacters();
            showView('character');
        } catch (error) {
            authForms.authError.textContent = error.message;
        }
    };

    const handleRegister = async (e) => {
        e.preventDefault();
        authForms.authError.textContent = '';
        const username = document.getElementById('register-username').value;
        const email = document.getElementById('register-email').value;
        const password = document.getElementById('register-password').value;
        try {
            await api.request('/register', {
                method: 'POST',
                body: JSON.stringify({ username, email, password })
            });
            const loginData = await api.request('/login', {
                method: 'POST',
                body: JSON.stringify({ username, password })
            });
            state.token = loginData.token;
            localStorage.setItem('token', loginData.token);
            await fetchCharacters();
            showView('character');
        } catch (error) {
            authForms.authError.textContent = error.message;
        }
    };

    const handleLogout = () => {
        state.token = null;
        state.characters = [];
        state.currentCharacter = null;
        localStorage.removeItem('token');
        showView('auth');
    };

    const fetchCharacters = async () => {
        try {
            state.characters = await api.request('/characters');
            renderCharacterList();
        } catch (error) {
            console.error('Failed to fetch characters:', error);
        }
    };

    const selectCharacter = async (charId) => {
        try {
            const numericCharId = parseInt(charId, 10);
            state.currentCharacter = state.characters.find(c => c.id === numericCharId);

            if (!state.currentCharacter) {
                console.error(`严重错误: 在 state 中未找到 ID 为 ${charId} 的角色。`);
                alert("出现错误：无法找到所选角色。");
                return;
            }

            appElements.chatName.textContent = state.currentCharacter.name;
            appElements.chatAvatar.src = getAuthenticatedUrl(state.currentCharacter.avatar_url);
            appElements.chatAvatar.onerror = () => { appElements.chatAvatar.src = 'assets/default_avatar.png'; };

            appElements.chatWindow.innerHTML = '<p style="text-align:center;">正在加载聊天记录...</p>';
            appElements.openMomentsBtn.classList.remove('has-notification');
            appElements.openDiaryBtn.classList.remove('has-notification');
            showView('app');

            const history = await api.request(`/characters/${state.currentCharacter.id}/history`);
            appElements.chatWindow.innerHTML = '';

            if (history && history.length > 0) {
                history.forEach(msg => {
                    addChatMessage(msg.message_type, { text: msg.content, imageUrl: msg.image_url });
                });
            }

        } catch (error) {
            console.error("selectCharacter 出错:", error);
            alert(`加载聊天失败: ${error.message}`);
            appElements.chatWindow.innerHTML = `<p class="error-message">加载聊天失败: ${error.message}</p>`;
        }
    };

    const handleCreateCharacter = async (e) => {
        e.preventDefault();
        charElements.createError.textContent = '';
        const formData = new FormData();
        formData.append('name', document.getElementById('char-name').value);
        formData.append('description', document.getElementById('char-desc').value);
        formData.append('first_talk', document.getElementById('char-first-talk').value);
        if (charElements.avatarInput.files[0]) {
            formData.append('avatar', charElements.avatarInput.files[0]);
        }

        try {
            const data = await api.request('/characters', {
                method: 'POST',
                body: formData
            });
            state.characters.push(data.character);
            renderCharacterList();
            hideModal('createCharacter');
            charElements.createForm.reset();
            charElements.avatarPreview.src = 'assets/default_avatar.png';
        } catch (error) {
            charElements.createError.textContent = error.message;
        }
    };

    const handleSendMessage = async () => {
        const text = appElements.messageInput.value.trim();
        if (!text) return;

        addChatMessage('user', { text });
        appElements.messageInput.value = '';
        appElements.sendBtn.disabled = true;

        try {
            const response = await api.request('/start_talk', {
                method: 'POST',
                body: JSON.stringify({ text, character_id: state.currentCharacter.id })
            });

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            let currentAiMessageBubble = null;

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const events = buffer.split('\n\n');
                buffer = events.pop();

                for (const event of events) {
                    if (!event.startsWith('data:')) continue;
                    const jsonData = event.substring(5);
                    try {
                        const data = JSON.parse(jsonData);

                        if (data.type === 'text') {
                            if (!currentAiMessageBubble) {
                                currentAiMessageBubble = addChatMessage('ai', { text: data.content });
                            } else {
                                currentAiMessageBubble.querySelector('p').textContent = data.content;
                            }
                        } else if (data.type === 'image') {
                            if (data.url) {
                                currentAiMessageBubble = addChatMessage('ai', { text: '', imageUrl: data.url });
                            }
                        } else if (data.type === 'event') {
                            console.log('Received event:', data.event_name);
                            if (data.event_name === 'new_moment_available') {
                                appElements.openMomentsBtn.classList.add('has-notification');
                            } else if (data.event_name === 'new_diary_available') {
                                appElements.openDiaryBtn.classList.add('has-notification');
                            }
                        } else if (data.type === 'done') {
                            console.log('Stream finished.');
                        }
                    } catch (e) {
                        console.error('解析 SSE 数据出错:', e, '数据:', jsonData);
                    }
                }
                 appElements.chatWindow.scrollTop = appElements.chatWindow.scrollHeight;
            }
        } catch (error) {
            console.error('流式传输错误:', error);
            addChatMessage('ai', { text: `抱歉，我好像出错了: ${error.message}` });
        } finally {
            appElements.sendBtn.disabled = false;
        }
    };

    const handleOpenMoments = async () => {
        appElements.openMomentsBtn.classList.remove('has-notification');
        momentsElements.name.textContent = state.currentCharacter.name;
        momentsElements.avatar.src = getAuthenticatedUrl(state.currentCharacter.avatar_url);
        momentsElements.avatar.onerror = () => { momentsElements.avatar.src = 'assets/default_avatar.png'; };
        momentsElements.feed.innerHTML = '<p>加载中...</p>';
        showModal('moments');

        try {
            const moments = await api.request(`/get_dynamic_text?character_id=${state.currentCharacter.id}`);
            momentsElements.feed.innerHTML = '';
            if (moments.length === 0) {
                momentsElements.feed.innerHTML = '<p>还没有任何动态哦。</p>';
                return;
            }
            moments.forEach(moment => {
                const momentCard = document.createElement('div');
                momentCard.className = 'moment-card';
                const tagsHtml = (moment.tags || []).map(tag => `<span class="tag">#${tag}</span>`).join(' ');

                const avatarSrc = getAuthenticatedUrl(state.currentCharacter.avatar_url);
                const imageSrc = moment.image_url ? getAuthenticatedUrl(moment.image_url) : '';
                const imageHtml = imageSrc ? `<div class="image-container"><img src="${imageSrc}" alt="Moment Image" onerror="this.onerror=null;this.parentElement.style.display='none';"></div>` : '';

                momentCard.innerHTML = `
                    <div class="moment-avatar">
                        <img src="${avatarSrc}" alt="avatar" onerror="this.onerror=null;this.src='assets/default_avatar.png';">
                    </div>
                    <div class="moment-body">
                        <div class="name">${state.currentCharacter.name}</div>
                        <div class="content">${moment.content || ''}</div>
                        ${imageHtml}
                        <div class="moment-footer">
                            <span class="time">${moment.post_time || ''}</span>
                            <div class="moment-tags">${tagsHtml}</div>
                        </div>
                    </div>
                `;
                momentsElements.feed.appendChild(momentCard);
            });
        } catch (error) {
            momentsElements.feed.innerHTML = `<p class="error-message">加载失败: ${error.message}</p>`;
        }
    };

    // --- START OF MODIFICATION: New diary rendering logic ---
    const renderDiaryPage = () => {
        const { entries, currentIndex } = diaryState;
        const entry = entries[currentIndex];

        // Format date to be precise to the minute
        const dateOptions = { year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' };
        const formattedDate = new Date(entry.date || Date.now()).toLocaleString(undefined, dateOptions);

        diaryElements.entries.innerHTML = `
            <div class="diary-entry">
                <div class="diary-date">${formattedDate}</div>
                <p class="diary-text">${entry.content}</p>
            </div>
        `;

        // Update navigation controls
        diaryElements.pageIndicator.textContent = `第 ${currentIndex + 1} / ${entries.length} 页`;
        diaryElements.prevBtn.disabled = currentIndex === 0;
        diaryElements.nextBtn.disabled = currentIndex === entries.length - 1;
    };

    const handleOpenDiary = async () => {
        appElements.openDiaryBtn.classList.remove('has-notification');
        diaryElements.name.textContent = state.currentCharacter.name;
        diaryElements.entries.innerHTML = '<p>加载中...</p>';
        diaryElements.navigation.classList.add('hidden'); // Hide nav while loading
        showModal('diary');

        try {
            const diaries = await api.request(`/get_diary?character_id=${state.currentCharacter.id}`);

            if (diaries.length === 0) {
                diaryElements.entries.innerHTML = '<p>日记本还是空的呢。</p>';
                return;
            }

            // Store entries and reset index
            diaryState.entries = diaries;
            diaryState.currentIndex = 0;

            // Show navigation and render the first page
            diaryElements.navigation.classList.remove('hidden');
            renderDiaryPage();

        } catch (error) {
            diaryElements.entries.innerHTML = `<p class="error-message">加载失败: ${error.message}</p>`;
        }
    };
    // --- END OF MODIFICATION ---

    const init = async () => {
        authForms.showRegisterLink.addEventListener('click', (e) => { e.preventDefault(); authForms.loginContainer.style.display = 'none'; authForms.registerContainer.style.display = 'block'; });
        authForms.showLoginLink.addEventListener('click', (e) => { e.preventDefault(); authForms.registerContainer.style.display = 'none'; authForms.loginContainer.style.display = 'block'; });
        authForms.login.addEventListener('submit', handleLogin);
        authForms.register.addEventListener('submit', handleRegister);
        charElements.createForm.addEventListener('submit', handleCreateCharacter);
        charElements.logoutBtn.addEventListener('click', handleLogout);
        charElements.showCreateBtn.addEventListener('click', () => showModal('createCharacter'));
        appElements.backBtn.addEventListener('click', () => showView('character'));
        appElements.sendBtn.addEventListener('click', handleSendMessage);
        appElements.openMomentsBtn.addEventListener('click', handleOpenMoments);
        appElements.openDiaryBtn.addEventListener('click', handleOpenDiary);
        appElements.messageInput.addEventListener('keydown', (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSendMessage(); } });
        document.querySelectorAll('.close-modal').forEach(btn => { btn.addEventListener('click', (e) => { e.target.closest('.modal-overlay').style.display = 'none'; }); });
        charElements.avatarInput.addEventListener('change', (e) => { if (e.target.files && e.target.files[0]) { const reader = new FileReader(); reader.onload = (event) => { charElements.avatarPreview.src = event.target.result; }; reader.readAsDataURL(e.target.files[0]); } });

        // --- START OF MODIFICATION: Add event listeners for diary navigation ---
        diaryElements.prevBtn.addEventListener('click', () => {
            if (diaryState.currentIndex > 0) {
                diaryState.currentIndex--;
                renderDiaryPage();
            }
        });

        diaryElements.nextBtn.addEventListener('click', () => {
            if (diaryState.currentIndex < diaryState.entries.length - 1) {
                diaryState.currentIndex++;
                renderDiaryPage();
            }
        });
        // --- END OF MODIFICATION ---

        if (state.token) {
            try {
                await fetchCharacters();
                showView('character');
            } catch (error) {
                console.log("Token 无效或初始化出错，正在登出。", error);
                handleLogout();
            }
        } else {
            showView('auth');
        }
    };

    init();
});