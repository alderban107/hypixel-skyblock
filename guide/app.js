// ============================================================
// SkyBlock Guide v2 — Nether Slate SPA
// Routing, sidebar, tabs, search, keyboard navigation
// ============================================================

(() => {
  'use strict';

  // --- DOM refs ---
  const sidebar = document.getElementById('sidebar');
  const sidebarNav = document.getElementById('sidebar-nav');
  const main = document.getElementById('main');
  const content = document.getElementById('content');
  const tabBar = document.getElementById('tab-bar');
  const searchOverlay = document.getElementById('search-overlay');
  const searchInput = document.getElementById('search-input');
  const searchResults = document.getElementById('search-results');
  const mobileOverlay = document.querySelector('.mobile-overlay');

  // --- State ---
  let currentPage = 'landing';
  let currentTab = null;
  let sidebarCollapsed = localStorage.getItem('sb-sidebar') === 'collapsed';
  let searchFocusIndex = -1;

  // --- Page registry (built from DOM) ---
  const pages = {};
  const navItems = [];
  document.querySelectorAll('.nav-item[data-page]').forEach(el => {
    const id = el.dataset.page;
    navItems.push({ id, el, text: el.querySelector('.nav-item-text')?.textContent || id });
  });
  document.querySelectorAll('.page[data-page]').forEach(el => {
    const id = el.dataset.page;
    const title = el.querySelector('.page-title')?.textContent || id;
    const tabs = el.dataset.tabs ? el.dataset.tabs.split(',') : null;
    pages[id] = { el, title, tabs };
  });

  // --- Search index ---
  const searchIndex = [];
  document.querySelectorAll('.page[data-page]').forEach(el => {
    const id = el.dataset.page;
    if (id === 'landing') return;
    const title = el.querySelector('.page-title')?.textContent || id;
    // Find which group this belongs to
    const navItem = sidebarNav.querySelector(`.nav-item[data-page="${id}"]`);
    let group = '';
    if (navItem) {
      const groupEl = navItem.closest('.nav-group');
      if (groupEl) {
        group = groupEl.querySelector('.nav-group-label span')?.textContent || '';
      }
    }
    // Index page title + body text for content search
    const bodyText = el.textContent.replace(/\s+/g, ' ').trim().toLowerCase();
    searchIndex.push({ id, title, group, text: title.toLowerCase(), body: bodyText });
  });

  // --- Init ---
  function init() {
    if (sidebarCollapsed) sidebar.classList.add('collapsed');
    wrapTables();
    bindEvents();
    handleHashChange();
    initScrollReveal();
  }

  // --- Auto-wrap tables for mobile scroll ---
  function wrapTables() {
    content.querySelectorAll('table').forEach(table => {
      if (table.parentElement.classList.contains('table-wrap')) return;
      const wrapper = document.createElement('div');
      wrapper.className = 'table-wrap';
      table.parentNode.insertBefore(wrapper, table);
      wrapper.appendChild(table);
    });
  }

  // --- Event binding ---
  function bindEvents() {
    // Sidebar toggle
    sidebar.querySelector('.sidebar-toggle')?.addEventListener('click', toggleSidebar);

    // Logo → landing page
    sidebar.querySelector('.sidebar-logo')?.addEventListener('click', () => navigateTo('landing'));

    // Sidebar search trigger (click + keyboard)
    const searchTrigger = sidebar.querySelector('.sidebar-search');
    searchTrigger?.addEventListener('click', openSearch);
    searchTrigger?.addEventListener('keydown', e => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        openSearch();
      }
    });

    // Nav items — make focusable + keyboard activatable
    sidebarNav.querySelectorAll('.nav-item[data-page]').forEach(item => {
      item.setAttribute('tabindex', '0');
      item.setAttribute('role', 'button');
    });
    sidebarNav.addEventListener('click', e => {
      const item = e.target.closest('.nav-item');
      if (item?.dataset.page) {
        navigateTo(item.dataset.page);
        closeMobileMenu();
      }
    });
    sidebarNav.addEventListener('keydown', e => {
      if (e.key === 'Enter' || e.key === ' ') {
        const item = e.target.closest('.nav-item');
        if (item?.dataset.page) {
          e.preventDefault();
          navigateTo(item.dataset.page);
          closeMobileMenu();
        }
      }
    });

    // Landing cards
    content.addEventListener('click', e => {
      const card = e.target.closest('.landing-card[data-nav]');
      if (card) navigateTo(card.dataset.nav);
    });

    // Tab bar
    tabBar.addEventListener('click', e => {
      const tab = e.target.closest('.tab-item');
      if (tab?.dataset.tab) selectTab(tab.dataset.tab);
    });

    // Hash change
    window.addEventListener('hashchange', handleHashChange);

    // Keyboard
    document.addEventListener('keydown', handleKeydown);

    // Mobile menu
    document.querySelector('.menu-btn')?.addEventListener('click', toggleMobileMenu);
    document.querySelector('.search-btn-mobile')?.addEventListener('click', openSearch);
    mobileOverlay?.addEventListener('click', closeMobileMenu);

    // Search overlay close on background click
    searchOverlay?.addEventListener('click', e => {
      if (e.target === searchOverlay) closeSearch();
    });

    // Search input
    searchInput?.addEventListener('input', handleSearchInput);

    // Copy buttons on code blocks
    content.addEventListener('click', e => {
      const btn = e.target.closest('.copy-btn');
      if (btn) {
        const pre = btn.closest('pre');
        const code = pre?.querySelector('code');
        if (code) {
          navigator.clipboard.writeText(code.textContent).then(() => {
            btn.textContent = 'Copied!';
            setTimeout(() => { btn.textContent = 'Copy'; }, 1500);
          });
        }
      }
    });

    // Back to top button
    const backToTop = document.getElementById('back-to-top');
    if (backToTop) {
      window.addEventListener('scroll', () => {
        backToTop.classList.toggle('visible', window.scrollY > 300);
      });
      backToTop.addEventListener('click', () => {
        window.scrollTo({ top: 0, behavior: 'smooth' });
      });
    }

    // Internal links
    content.addEventListener('click', e => {
      const link = e.target.closest('a[href^="#"]');
      if (link) {
        e.preventDefault();
        const hash = link.getAttribute('href').slice(1);
        // Check if it's an in-page anchor (element ID within current page)
        const target = document.getElementById(hash);
        if (target && pages[currentPage]?.el.contains(target)) {
          target.scrollIntoView({ behavior: 'smooth', block: 'start' });
          history.replaceState(null, '', `#${currentPage}`);
        } else {
          navigateTo(hash);
        }
      }
    });
  }

  // --- Navigation ---
  function navigateTo(pageId, tab) {
    if (!pages[pageId] && pageId !== 'landing') return;

    // Update hash without triggering hashchange
    const hash = pageId === 'landing' ? '' : `#${pageId}${tab ? '/' + tab : ''}`;
    history.pushState(null, '', hash || window.location.pathname);

    showPage(pageId, tab);
  }

  // Redirects for removed/merged pages
  const redirects = {
    'diana-event': 'events-calendar',
    'skill-guides': 'skills',
    'sacks-inventory': 'core-mechanics',
  };

  function handleHashChange() {
    const hash = window.location.hash.slice(1);
    if (!hash) {
      showPage('landing');
      return;
    }
    const parts = hash.split('/');
    let pageId = parts[0];
    const tab = parts[1] || null;

    // Handle redirects for removed pages
    if (redirects[pageId]) {
      pageId = redirects[pageId];
      history.replaceState(null, '', `#${pageId}`);
    }

    if (pages[pageId]) {
      showPage(pageId, tab);
    } else {
      showPage('landing');
    }
  }

  function showPage(pageId, tab) {
    currentPage = pageId;

    // Hide all pages, show target
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    const target = pages[pageId]?.el || document.querySelector('.page[data-page="landing"]');
    target.classList.add('active');

    // Update nav active state
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    const activeNav = sidebarNav.querySelector(`.nav-item[data-page="${pageId}"]`);
    if (activeNav) activeNav.classList.add('active');

    // Scroll nav item into view
    if (activeNav) {
      requestAnimationFrame(() => {
        activeNav.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
      });
    }

    // Tab bar
    const pageData = pages[pageId];
    if (pageData?.tabs) {
      renderTabs(pageData.tabs, tab);
      tabBar.classList.add('visible');
      selectTab(currentTab);
    } else {
      tabBar.classList.remove('visible');
      tabBar.innerHTML = '';
      currentTab = null;
    }

    // Instantly reveal all elements on content pages (keep animation for landing only)
    if (pageId !== 'landing') {
      target.querySelectorAll('.reveal:not(.visible)').forEach(el => el.classList.add('visible'));
    }

    // Scroll to top
    window.scrollTo({ top: 0, behavior: 'instant' });

    // Re-observe for scroll reveal (landing page animations)
    observeReveals();
  }

  // --- Tabs ---
  function renderTabs(tabs, activeTab) {
    const active = activeTab || tabs[0];
    currentTab = active;
    tabBar.innerHTML = tabs.map(t =>
      `<div class="tab-item${t === active ? ' active' : ''}" data-tab="${t}">${t}</div>`
    ).join('');
  }

  function selectTab(tab) {
    currentTab = tab;
    tabBar.querySelectorAll('.tab-item').forEach(t => {
      t.classList.toggle('active', t.dataset.tab === tab);
    });

    // Update hash
    const hash = `#${currentPage}/${tab}`;
    history.replaceState(null, '', hash);

    // Show/hide tab content sections
    const page = pages[currentPage]?.el;
    if (!page) return;
    page.querySelectorAll('[data-tab]').forEach(el => {
      el.style.display = el.dataset.tab === tab ? '' : 'none';
    });
  }

  // --- Sidebar ---
  function toggleSidebar() {
    sidebarCollapsed = !sidebarCollapsed;
    sidebar.classList.toggle('collapsed', sidebarCollapsed);
    localStorage.setItem('sb-sidebar', sidebarCollapsed ? 'collapsed' : 'expanded');
  }

  // --- Mobile menu ---
  function toggleMobileMenu() {
    sidebar.classList.toggle('open');
    mobileOverlay?.classList.toggle('visible');
  }

  function closeMobileMenu() {
    sidebar.classList.remove('open');
    mobileOverlay?.classList.remove('visible');
  }

  // --- Search ---
  function openSearch() {
    searchOverlay.classList.add('open');
    searchInput.value = '';
    searchInput.focus();
    searchFocusIndex = -1;
    renderSearchResults('');
  }

  function closeSearch() {
    searchOverlay.classList.remove('open');
    searchInput.value = '';
    searchResults.innerHTML = '';
  }

  function handleSearchInput() {
    const query = searchInput.value.trim().toLowerCase();
    searchFocusIndex = -1;
    renderSearchResults(query);
  }

  function renderSearchResults(query) {
    if (!query) {
      // Show all pages as suggestions
      searchResults.innerHTML = searchIndex.map((item, i) =>
        `<div class="search-result" data-page="${item.id}" data-index="${i}">
          <svg class="search-result-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/></svg>
          <div>
            <div class="search-result-title">${item.title}</div>
            <div class="search-result-group">${item.group}</div>
          </div>
        </div>`
      ).join('');
      return;
    }

    // Score results: title match > group match > body match
    const results = [];
    for (const item of searchIndex) {
      const titleMatch = item.text.includes(query);
      const groupMatch = item.group.toLowerCase().includes(query);
      const bodyMatch = item.body.includes(query);
      if (titleMatch || groupMatch || bodyMatch) {
        let snippet = '';
        if (!titleMatch && bodyMatch) {
          const idx = item.body.indexOf(query);
          const start = Math.max(0, idx - 40);
          const end = Math.min(item.body.length, idx + query.length + 60);
          snippet = (start > 0 ? '...' : '') + item.body.slice(start, end) + (end < item.body.length ? '...' : '');
        }
        results.push({ ...item, score: titleMatch ? 3 : groupMatch ? 2 : 1, snippet });
      }
    }
    results.sort((a, b) => b.score - a.score);

    if (results.length === 0) {
      searchResults.innerHTML = '<div class="search-empty">No results found</div>';
      return;
    }

    searchResults.innerHTML = results.slice(0, 20).map((item, i) =>
      `<div class="search-result" data-page="${item.id}" data-index="${i}">
        <svg class="search-result-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/></svg>
        <div>
          <div class="search-result-title">${highlightMatch(item.title, query)}</div>
          <div class="search-result-group">${item.group}</div>
          ${item.snippet ? `<div class="search-result-snippet">${highlightMatch(item.snippet, query)}</div>` : ''}
        </div>
      </div>`
    ).join('');
  }

  function highlightMatch(text, query) {
    const idx = text.toLowerCase().indexOf(query);
    if (idx === -1) return text;
    return text.slice(0, idx) +
      `<strong style="color:var(--ember)">${text.slice(idx, idx + query.length)}</strong>` +
      text.slice(idx + query.length);
  }

  // --- Keyboard navigation ---
  function handleKeydown(e) {
    const searchOpen = searchOverlay.classList.contains('open');

    // Ctrl+K → open search
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
      e.preventDefault();
      if (searchOpen) closeSearch();
      else openSearch();
      return;
    }

    // Search modal navigation
    if (searchOpen) {
      const items = searchResults.querySelectorAll('.search-result');
      if (e.key === 'Escape') {
        e.preventDefault();
        closeSearch();
        return;
      }
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        searchFocusIndex = Math.min(searchFocusIndex + 1, items.length - 1);
        updateSearchFocus(items);
        return;
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault();
        searchFocusIndex = Math.max(searchFocusIndex - 1, 0);
        updateSearchFocus(items);
        return;
      }
      if (e.key === 'Enter' && searchFocusIndex >= 0) {
        e.preventDefault();
        const focused = items[searchFocusIndex];
        if (focused?.dataset.page) {
          navigateTo(focused.dataset.page);
          closeSearch();
        }
        return;
      }
      // Click on result
      if (e.type === 'click') return; // handled elsewhere
      return;
    }

    // Arrow key page navigation (not in search, not in input)
    if (document.activeElement?.tagName === 'INPUT' || document.activeElement?.tagName === 'TEXTAREA') return;

    if (e.key === 'ArrowUp' || e.key === 'ArrowDown') {
      e.preventDefault();
      const currentIdx = navItems.findIndex(n => n.id === currentPage);
      if (currentIdx === -1) return;
      const nextIdx = e.key === 'ArrowDown'
        ? Math.min(currentIdx + 1, navItems.length - 1)
        : Math.max(currentIdx - 1, 0);
      navigateTo(navItems[nextIdx].id);
    }
  }

  function updateSearchFocus(items) {
    items.forEach((el, i) => {
      el.classList.toggle('focused', i === searchFocusIndex);
      if (i === searchFocusIndex) el.scrollIntoView({ block: 'nearest' });
    });
  }

  // Search result click
  searchResults?.addEventListener('click', e => {
    const result = e.target.closest('.search-result');
    if (result?.dataset.page) {
      navigateTo(result.dataset.page);
      closeSearch();
    }
  });

  // --- Scroll reveal ---
  let revealObserver;

  function initScrollReveal() {
    if (!('IntersectionObserver' in window)) {
      document.querySelectorAll('.reveal').forEach(el => el.classList.add('visible'));
      return;
    }
    revealObserver = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
          revealObserver.unobserve(entry.target);
        }
      });
    }, { threshold: 0.1, rootMargin: '0px 0px -40px 0px' });

    observeReveals();
  }

  function observeReveals() {
    if (!revealObserver) return;
    document.querySelectorAll('.reveal:not(.visible)').forEach(el => {
      revealObserver.observe(el);
    });
  }

  // --- Forge checklists (localStorage persistence) ---
  function initForgeChecklists() {
    const saved = JSON.parse(localStorage.getItem('forge-checklists') || '{}');
    document.querySelectorAll('.forge-checklist').forEach((checklist, ci) => {
      checklist.querySelectorAll('input[type="checkbox"]').forEach((cb, ii) => {
        const key = `${ci}-${ii}`;
        if (saved[key]) cb.checked = true;
        cb.addEventListener('change', () => {
          const state = JSON.parse(localStorage.getItem('forge-checklists') || '{}');
          if (cb.checked) state[key] = true;
          else delete state[key];
          localStorage.setItem('forge-checklists', JSON.stringify(state));
        });
      });
    });
  }
  initForgeChecklists();

  // --- Start ---
  init();
})();
