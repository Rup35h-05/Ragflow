/* ═══════════════════════════════════════════════════════
   RAGFlow — Frontend Application
   ═══════════════════════════════════════════════════════ */

(function () {
  'use strict';

  // ── State ──
  const state = {
    apiKey: '',
    messages: [],
    documents: [],
    isLoading: false,
  };

  // ── DOM References ──
  const $ = (sel) => document.querySelector(sel);

  const els = {
    apiKeyInput: null,
    saveApiKeyBtn: null,
    uploadZone: null,
    fileInput: null,
    uploadProgress: null,
    progressFill: null,
    progressText: null,
    documentList: null,
    docCountBadge: null,
    emptyDocs: null,
    chatContainer: null,
    welcomeScreen: null,
    chatInput: null,
    sendBtn: null,
    toastContainer: null,
    hamburgerToggle: null,
    sidebar: null,
    sidebarOverlay: null,
  };

  // ── Toast Icons ──
  const TOAST_ICONS = {
    success: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>',
    error: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>',
    warning: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
  };

  // ═══════════════════════════════════════════════════════
  //  INITIALIZATION
  // ═══════════════════════════════════════════════════════

  function initApp() {
    // Resolve DOM references
    els.apiKeyInput = $('#apiKeyInput');
    els.saveApiKeyBtn = $('#saveApiKeyBtn');
    els.uploadZone = $('#uploadZone');
    els.fileInput = $('#fileInput');
    els.uploadProgress = $('#uploadProgress');
    els.progressFill = $('#progressFill');
    els.progressText = $('#progressText');
    els.documentList = $('#documentList');
    els.docCountBadge = $('#docCountBadge');
    els.emptyDocs = $('#emptyDocs');
    els.chatContainer = $('#chatContainer');
    els.welcomeScreen = $('#welcomeScreen');
    els.chatInput = $('#chatInput');
    els.sendBtn = $('#sendBtn');
    els.toastContainer = $('#toastContainer');
    els.hamburgerToggle = $('#hamburgerToggle');
    els.sidebar = $('#sidebar');
    els.sidebarOverlay = $('#sidebarOverlay');

    // Load API key
    const savedKey = localStorage.getItem('ragflow_api_key');
    if (savedKey) {
      state.apiKey = savedKey;
      els.apiKeyInput.value = savedKey;
    }

    // Load documents
    loadDocuments();

    // Setup event listeners
    setupEventListeners();
  }

  function setupEventListeners() {
    // API Key
    els.saveApiKeyBtn.addEventListener('click', function () {
      setApiKey(els.apiKeyInput.value.trim());
    });

    els.apiKeyInput.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') {
        e.preventDefault();
        setApiKey(els.apiKeyInput.value.trim());
      }
    });

    // Upload
    els.uploadZone.addEventListener('click', function () {
      els.fileInput.click();
    });

    els.fileInput.addEventListener('change', function (e) {
      if (e.target.files.length > 0) {
        uploadDocument(e.target.files[0]);
        e.target.value = '';
      }
    });

    // Drag & Drop
    els.uploadZone.addEventListener('dragenter', handleDragEnter);
    els.uploadZone.addEventListener('dragover', handleDragOver);
    els.uploadZone.addEventListener('dragleave', handleDragLeave);
    els.uploadZone.addEventListener('drop', handleDrop);

    // Chat input
    els.chatInput.addEventListener('input', handleInputResize);
    els.chatInput.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage(els.chatInput.value.trim());
      }
    });

    // Send button
    els.sendBtn.addEventListener('click', function () {
      sendMessage(els.chatInput.value.trim());
    });

    // Document list — event delegation
    els.documentList.addEventListener('click', function (e) {
      var deleteBtn = e.target.closest('.doc-item-delete');
      if (deleteBtn) {
        var docName = deleteBtn.dataset.docName;
        deleteDocument(docName);
      }
    });

    // Sources toggle — event delegation
    els.chatContainer.addEventListener('click', function (e) {
      var toggle = e.target.closest('.sources-toggle');
      if (toggle) {
        toggleSources(toggle);
      }
    });

    // Mobile hamburger
    els.hamburgerToggle.addEventListener('click', toggleMobileSidebar);
    els.sidebarOverlay.addEventListener('click', closeMobileSidebar);
  }

  // ═══════════════════════════════════════════════════════
  //  API KEY
  // ═══════════════════════════════════════════════════════

  function setApiKey(key) {
    if (!key) {
      showToast('Please enter an API key', 'warning');
      return;
    }
    state.apiKey = key;
    localStorage.setItem('ragflow_api_key', key);
    showToast('API key saved successfully', 'success');
  }

  // ═══════════════════════════════════════════════════════
  //  DOCUMENT UPLOAD
  // ═══════════════════════════════════════════════════════

  function handleDragEnter(e) {
    e.preventDefault();
    els.uploadZone.classList.add('dragover');
  }

  function handleDragOver(e) {
    e.preventDefault();
    els.uploadZone.classList.add('dragover');
  }

  function handleDragLeave(e) {
    e.preventDefault();
    if (!els.uploadZone.contains(e.relatedTarget)) {
      els.uploadZone.classList.remove('dragover');
    }
  }

  function handleDrop(e) {
    e.preventDefault();
    els.uploadZone.classList.remove('dragover');
    var files = e.dataTransfer.files;
    if (files.length > 0) {
      uploadDocument(files[0]);
    }
  }

  async function uploadDocument(file) {
    // Validate
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      showToast('Only PDF files are supported', 'error');
      return;
    }

    if (!state.apiKey) {
      showToast('Please set your API key first', 'warning');
      return;
    }

    // Show progress
    els.uploadProgress.classList.add('active');
    els.progressFill.style.width = '0%';
    els.progressText.textContent = 'Uploading...';

    // Simulate progress increments
    var progress = 0;
    var progressInterval = setInterval(function () {
      progress = Math.min(progress + Math.random() * 15, 90);
      els.progressFill.style.width = progress + '%';
    }, 300);

    try {
      var formData = new FormData();
      formData.append('file', file);
      formData.append('api_key', state.apiKey);

      var response = await fetch('/api/upload', {
        method: 'POST',
        body: formData,
      });

      var data = await response.json();

      clearInterval(progressInterval);

      if (!response.ok || !data.success) {
        throw new Error(data.message || 'Upload failed');
      }

      // Complete progress
      els.progressFill.style.width = '100%';
      els.progressText.textContent = 'Uploaded! ' + data.chunks_count + ' chunks created.';

      showToast('"' + data.document_name + '" uploaded — ' + data.chunks_count + ' chunks', 'success');

      // Reload documents
      await loadDocuments();

      // Hide progress after a brief delay
      setTimeout(function () {
        els.uploadProgress.classList.remove('active');
        els.progressFill.style.width = '0%';
      }, 2000);
    } catch (err) {
      clearInterval(progressInterval);
      els.uploadProgress.classList.remove('active');
      showToast(err.message || 'Upload failed', 'error');
    }
  }

  // ═══════════════════════════════════════════════════════
  //  DOCUMENTS
  // ═══════════════════════════════════════════════════════

  async function loadDocuments() {
    try {
      var response = await fetch('/api/documents');
      var data = await response.json();
      state.documents = data.documents || [];
      renderDocumentList();
    } catch (err) {
      state.documents = [];
      renderDocumentList();
    }
  }

  function renderDocumentList() {
    var list = els.documentList;
    // Clear existing doc items
    var items = list.querySelectorAll('.doc-item');
    items.forEach(function (item) { item.remove(); });

    els.docCountBadge.textContent = state.documents.length;

    if (state.documents.length === 0) {
      els.emptyDocs.style.display = 'flex';
      return;
    }

    els.emptyDocs.style.display = 'none';

    state.documents.forEach(function (doc) {
      var el = document.createElement('div');
      el.className = 'doc-item';
      el.innerHTML =
        '<div class="doc-item-icon">' +
          '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
            '<path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/>' +
            '<polyline points="14 2 14 8 20 8"/>' +
          '</svg>' +
        '</div>' +
        '<div class="doc-item-info">' +
          '<div class="doc-item-name" title="' + escapeHTML(doc.name) + '">' + escapeHTML(doc.name) + '</div>' +
          '<div class="doc-item-chunks">' + doc.chunks_count + ' chunk' + (doc.chunks_count !== 1 ? 's' : '') + '</div>' +
        '</div>' +
        '<button class="doc-item-delete" data-doc-name="' + escapeAttr(doc.name) + '" title="Delete document">' +
          '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
            '<polyline points="3 6 5 6 21 6"/>' +
            '<path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>' +
          '</svg>' +
        '</button>';
      list.appendChild(el);
    });
  }

  async function deleteDocument(name) {
    if (!confirm('Delete "' + name + '"? This cannot be undone.')) return;

    try {
      var response = await fetch('/api/documents/' + encodeURIComponent(name), {
        method: 'DELETE',
      });
      var data = await response.json();

      if (!response.ok || !data.success) {
        throw new Error(data.message || 'Delete failed');
      }

      showToast('"' + name + '" deleted', 'success');
      await loadDocuments();
    } catch (err) {
      showToast(err.message || 'Delete failed', 'error');
    }
  }

  // ═══════════════════════════════════════════════════════
  //  CHAT
  // ═══════════════════════════════════════════════════════

  async function sendMessage(query) {
    if (!query || state.isLoading) return;

    if (!state.apiKey) {
      showToast('Please set your API key first', 'warning');
      return;
    }

    // Hide welcome screen
    els.welcomeScreen.classList.add('hidden');

    // Add user message
    var userMsg = { role: 'user', content: query };
    state.messages.push(userMsg);
    appendMessageToDOM(userMsg);

    // Clear input
    els.chatInput.value = '';
    handleInputResize();

    // Show typing indicator
    state.isLoading = true;
    updateSendButton();
    var typingEl = showTypingIndicator();

    try {
      var response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: query, api_key: state.apiKey }),
      });

      var data = await response.json();

      if (!response.ok) {
        throw new Error(data.message || data.error || 'Chat request failed');
      }

      // Remove typing indicator
      typingEl.remove();

      // Add assistant message
      var assistantMsg = {
        role: 'assistant',
        content: data.answer,
        sources: data.sources || [],
      };
      state.messages.push(assistantMsg);
      appendMessageToDOM(assistantMsg);
    } catch (err) {
      typingEl.remove();
      showToast(err.message || 'Failed to get response', 'error');

      // Add error as assistant message
      var errorMsg = {
        role: 'assistant',
        content: '\u26a0\ufe0f Error: ' + (err.message || 'Something went wrong. Please try again.'),
        sources: [],
      };
      state.messages.push(errorMsg);
      appendMessageToDOM(errorMsg);
    } finally {
      state.isLoading = false;
      updateSendButton();
    }
  }

  function appendMessageToDOM(message) {
    var row = document.createElement('div');
    row.className = 'message-row ' + message.role;

    var content = message.role === 'assistant'
      ? renderMarkdown(message.content)
      : escapeHTML(message.content);

    var sourcesHTML = '';
    if (message.role === 'assistant' && message.sources && message.sources.length > 0) {
      sourcesHTML = buildSourcesHTML(message.sources);
    }

    row.innerHTML =
      '<div class="message-content-wrap">' +
        '<div class="message-bubble">' + content + '</div>' +
        sourcesHTML +
      '</div>';

    els.chatContainer.appendChild(row);
    scrollToBottom();
  }

  function buildSourcesHTML(sources) {
    var cards = sources
      .map(function (s) {
        var truncated = truncateText(s.text, 150);
        var pageLabel = s.page != null ? '<span class="source-page-badge">Page ' + s.page + '</span>' : '';
        var scoreLabel = s.score != null ? '<span class="source-score">' + (s.score * 100).toFixed(0) + '% match</span>' : '';
        return (
          '<div class="source-card">' +
            '<div class="source-card-text">' + escapeHTML(truncated) + '</div>' +
            '<div class="source-card-meta">' +
              pageLabel +
              '<span class="source-doc-name" title="' + escapeAttr(s.doc_name || '') + '">' + escapeHTML(s.doc_name || 'Unknown') + '</span>' +
              scoreLabel +
            '</div>' +
          '</div>'
        );
      })
      .join('');

    return (
      '<div class="sources-section">' +
        '<div class="sources-toggle">' +
          '\ud83d\udcc4 ' + sources.length + ' source' + (sources.length !== 1 ? 's' : '') +
          ' <span class="toggle-chevron">\u25bc</span>' +
        '</div>' +
        '<div class="sources-grid">' + cards + '</div>' +
      '</div>'
    );
  }

  function toggleSources(toggleEl) {
    var section = toggleEl.closest('.sources-section');
    var grid = section.querySelector('.sources-grid');
    var isExpanded = toggleEl.classList.contains('expanded');

    if (isExpanded) {
      toggleEl.classList.remove('expanded');
      grid.classList.remove('expanded');
    } else {
      toggleEl.classList.add('expanded');
      grid.classList.add('expanded');
      scrollToBottom();
    }
  }

  function showTypingIndicator() {
    var el = document.createElement('div');
    el.className = 'typing-indicator';
    el.innerHTML =
      '<div class="typing-bubble">' +
        '<div class="typing-dot"></div>' +
        '<div class="typing-dot"></div>' +
        '<div class="typing-dot"></div>' +
      '</div>';
    els.chatContainer.appendChild(el);
    scrollToBottom();
    return el;
  }

  // ═══════════════════════════════════════════════════════
  //  INPUT HANDLING
  // ═══════════════════════════════════════════════════════

  function handleInputResize() {
    var ta = els.chatInput;
    ta.style.height = 'auto';
    ta.style.height = Math.min(ta.scrollHeight, 160) + 'px';
    updateSendButton();
  }

  function updateSendButton() {
    var hasText = els.chatInput.value.trim().length > 0;
    els.sendBtn.disabled = !hasText || state.isLoading;

    if (hasText && !state.isLoading) {
      els.sendBtn.classList.add('has-text');
    } else {
      els.sendBtn.classList.remove('has-text');
    }
  }

  // ═══════════════════════════════════════════════════════
  //  MOBILE SIDEBAR
  // ═══════════════════════════════════════════════════════

  function toggleMobileSidebar() {
    var isOpen = els.sidebar.classList.contains('open');
    if (isOpen) {
      closeMobileSidebar();
    } else {
      els.sidebar.classList.add('open');
      els.sidebarOverlay.classList.add('active');
      els.hamburgerToggle.classList.add('active');
    }
  }

  function closeMobileSidebar() {
    els.sidebar.classList.remove('open');
    els.sidebarOverlay.classList.remove('active');
    els.hamburgerToggle.classList.remove('active');
  }

  // ═══════════════════════════════════════════════════════
  //  TOAST NOTIFICATIONS
  // ═══════════════════════════════════════════════════════

  function showToast(message, type) {
    type = type || 'success';
    var toast = document.createElement('div');
    toast.className = 'toast ' + type;
    toast.innerHTML =
      '<div class="toast-icon">' + (TOAST_ICONS[type] || TOAST_ICONS.success) + '</div>' +
      '<span>' + escapeHTML(message) + '</span>';
    els.toastContainer.appendChild(toast);

    // Auto-dismiss
    setTimeout(function () {
      toast.classList.add('dismissing');
      toast.addEventListener('animationend', function () {
        toast.remove();
      });
    }, 3000);
  }

  // ═══════════════════════════════════════════════════════
  //  UTILITIES
  // ═══════════════════════════════════════════════════════

  function scrollToBottom() {
    requestAnimationFrame(function () {
      els.chatContainer.scrollTop = els.chatContainer.scrollHeight;
    });
  }

  function escapeHTML(str) {
    if (!str) return '';
    var div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  function escapeAttr(str) {
    if (!str) return '';
    return str
      .replace(/&/g, '&amp;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
  }

  function truncateText(text, maxLen) {
    if (!text) return '';
    if (text.length <= maxLen) return text;
    return text.slice(0, maxLen).trim() + '...';
  }

  /**
   * Basic Markdown renderer
   * Converts: **bold**, *italic*, `inline code`, ```code blocks```, newlines
   */
  function renderMarkdown(text) {
    if (!text) return '';

    var html = escapeHTML(text);

    // Code blocks (```)
    html = html.replace(/```(\w*)\n?([\s\S]*?)```/g, function (_, lang, code) {
      return '<pre><code>' + code.trim() + '</code></pre>';
    });

    // Inline code
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

    // Bold (**text**)
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');

    // Italic (*text*)
    html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');

    // Newlines to <br> (but not inside <pre>)
    var parts = html.split(/(<pre>[\s\S]*?<\/pre>)/g);
    html = parts
      .map(function (part) {
        if (part.startsWith('<pre>')) return part;
        return part.replace(/\n/g, '<br>');
      })
      .join('');

    return html;
  }

  // ═══════════════════════════════════════════════════════
  //  BOOT
  // ═══════════════════════════════════════════════════════

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initApp);
  } else {
    initApp();
  }
})();
