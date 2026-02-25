// ═══════════════════════════════════════════════
// ENCHANTED GRIMOIRE — Multi-Page Guide System
// ═══════════════════════════════════════════════

(() => {
'use strict';

// ── Constants ──
const STORAGE_KEY = 'hsb-guide-checks';
const NAV_GROUPS = [
  { key: 'start',    label: 'Getting Started',  icon: '⚡',  pages: ['setup','texture-packs','first-day','staying-safe'] },
  { key: 'core',     label: 'Core Systems',      icon: '📖',  pages: ['core-systems','profiles','skills','stats','collections','bestiary','museum'] },
  { key: 'progress', label: 'Early Progression',  icon: '📈',  pages: ['early-game','accessories','equipment','upgrades','fairy-souls','minions','garden'] },
  { key: 'areas',    label: 'Content Areas',      icon: '🗺️',  pages: ['enchanting-potions','sacks','chocolate-factory','slayers','dungeons','mining','galatea','the-end','crimson-isle','the-rift','diana','events'] },
  { key: 'economy',  label: 'Economy & Meta',     icon: '💰',  pages: ['money','mayors','pets'] },
  { key: 'skills',   label: 'Skill Guides',       icon: '📚',  pages: ['skill-guides'] },
  { key: 'ref',      label: 'Reference',           icon: '📌',  pages: ['tips','gear-progression','links'] },
];

// Skill sub-pages inside the skill-guides H2
const SKILL_SUBPAGES = [
  'sg-mining','sg-farming','sg-foraging','sg-combat','sg-fishing',
  'sg-enchanting','sg-alchemy','sg-taming','sg-carpentry',
  'sg-dungeoneering','sg-runecrafting','sg-social'
];

// Nice labels for tab bar
const PAGE_LABELS = {
  'setup': 'Setup & Mods', 'texture-packs': 'Texture Packs', 'first-day': 'First Day',
  'staying-safe': 'Staying Safe', 'core-systems': 'Basics', 'profiles': 'Profiles',
  'skills': 'Skills', 'stats': 'Stats & Damage', 'collections': 'Collections', 'bestiary': 'Bestiary',
  'museum': 'Museum', 'early-game': 'Progression', 'accessories': 'Accessories',
  'equipment': 'Equipment', 'upgrades': 'Item Upgrades', 'fairy-souls': 'Fairy Souls', 'minions': 'Minions',
  'garden': 'Garden', 'enchanting-potions': 'Enchanting', 'sacks': 'Sacks',
  'chocolate-factory': 'Chocolate', 'slayers': 'Slayers', 'dungeons': 'Dungeons',
  'mining': 'Mining & HotM', 'galatea': 'Galatea', 'the-end': 'The End', 'crimson-isle': 'Crimson Isle',
  'the-rift': 'The Rift', 'diana': 'Diana', 'events': 'Events',
  'money': 'Money Making', 'mayors': 'Mayors & Bits', 'pets': 'Pets',
  'skill-guides': 'Overview',
  'sg-mining': 'Mining', 'sg-farming': 'Farming', 'sg-foraging': 'Foraging',
  'sg-combat': 'Combat', 'sg-fishing': 'Fishing', 'sg-enchanting': 'Enchanting',
  'sg-alchemy': 'Alchemy', 'sg-taming': 'Taming', 'sg-carpentry': 'Carpentry',
  'sg-dungeoneering': 'Dungeoneering', 'sg-runecrafting': 'Runecrafting', 'sg-social': 'Social',
  'tips': 'Tips & Tricks', 'gear-progression': 'Gear Progression', 'links': 'Resources',
};

// Short labels for icon rail
const RAIL_LABELS = {
  'start': 'Start', 'core': 'Core', 'progress': 'Progress',
  'areas': 'Areas', 'economy': 'Economy', 'skills': 'Skills', 'ref': 'Reference',
};

// Group descriptions for landing cards
const GROUP_DESCS = {
  'start': 'Mod setup, texture packs, and your critical first-day checklist.',
  'core': 'Skills, stats, Collections, Bestiary, and Museum — the systems behind everything.',
  'progress': 'Phase-by-phase gear progression, accessories, item upgrades, fairy souls, and minions.',
  'areas': 'Enchanting, dungeons, mining, slayers, and every major content area.',
  'economy': 'Money-making methods, mayors & bits, and the pet system.',
  'skills': 'Detailed leveling guides for all 12 skills.',
  'ref': 'Tips & tricks, gear progression tables, and useful resource links.',
};

// ── State ──
let currentGroup = null;
let currentPage = null;
let pages = {};          // id → DOM section
let landingContent = null;

// ── DOM Slicing ──
// Walk <main> and wrap each H2's content into a page section
function slicePages() {
  const main = document.querySelector('main');
  if (!main) return;

  // Extract hero + intro content as landing page
  const landingEl = document.createElement('section');
  landingEl.className = 'page-section landing-page';
  landingEl.id = 'page-landing';

  // Collect all nodes before the first H2
  while (main.firstChild) {
    if (main.firstChild.nodeType === 1 && main.firstChild.tagName === 'H2') break;
    landingEl.appendChild(main.firstChild);
  }
  landingContent = landingEl;

  // Now slice H2 sections
  const allH2 = Array.from(main.querySelectorAll(':scope > h2'));

  allH2.forEach((h2, idx) => {
    const id = h2.id;
    if (!id) return;

    const section = document.createElement('section');
    section.className = 'page-section';
    section.id = 'page-' + id;
    section.style.display = 'none';

    // Collect all nodes from this H2 until the next H2
    const nodes = [h2];
    let next = h2.nextSibling;
    while (next) {
      if (next.nodeType === 1 && next.tagName === 'H2') break;
      nodes.push(next);
      next = next.nextSibling;
    }

    nodes.forEach(n => section.appendChild(n));
    pages[id] = section;
  });

  // Also handle the footer sep/credit line that may remain
  while (main.firstChild) {
    // Remaining content goes into the last page
    const lastPageId = Object.keys(pages).pop();
    if (lastPageId && pages[lastPageId]) {
      pages[lastPageId].appendChild(main.firstChild);
    } else {
      main.removeChild(main.firstChild);
    }
  }

  // Handle skill-guides: split it further by H3
  if (pages['skill-guides']) {
    sliceSkillSubpages(pages['skill-guides']);
  }

  // Create the content container
  const contentArea = document.createElement('div');
  contentArea.id = 'contentArea';
  contentArea.appendChild(landingContent);
  Object.values(pages).forEach(s => contentArea.appendChild(s));
  main.appendChild(contentArea);
}

// Split skill-guides page into sub-pages by H3
function sliceSkillSubpages(skillSection) {
  const h3s = Array.from(skillSection.querySelectorAll(':scope > h3[id^="sg-"]'));
  if (!h3s.length) return;

  // Everything before the first sg- H3 stays in skill-guides as overview
  // Everything after each H3 until the next becomes its own page
  h3s.forEach(h3 => {
    const id = h3.id;
    const subSection = document.createElement('section');
    subSection.className = 'page-section skill-subpage';
    subSection.id = 'page-' + id;
    subSection.style.display = 'none';

    const nodes = [h3];
    let next = h3.nextSibling;
    while (next) {
      if (next.nodeType === 1 && next.tagName === 'H3' && next.id && next.id.startsWith('sg-')) break;
      if (next.nodeType === 1 && next.tagName === 'H2') break;
      nodes.push(next);
      next = next.nextSibling;
    }

    nodes.forEach(n => subSection.appendChild(n));
    pages[id] = subSection;
  });

  // Update the skills group to include sub-pages
  const skillsGroup = NAV_GROUPS.find(g => g.key === 'skills');
  if (skillsGroup) {
    skillsGroup.pages = ['skill-guides', ...SKILL_SUBPAGES];
  }
}

// ── Landing Page Cards ──
function buildLandingCards() {
  if (!landingContent) return;

  // Add CTA button to hero
  const hero = landingContent.querySelector('.hero');
  if (hero) {
    const cta = document.createElement('button');
    cta.className = 'hero-cta';
    cta.innerHTML = 'Begin the Guide <span class="cta-arrow">→</span>';
    cta.addEventListener('click', () => navigateTo('start', 'setup'));
    hero.appendChild(cta);
  }

  // Build group card grid
  const section = document.createElement('div');
  section.className = 'landing-section';
  section.innerHTML = '<h2 class="landing-heading">Choose Your Path</h2>';

  const grid = document.createElement('div');
  grid.className = 'landing-grid';

  NAV_GROUPS.forEach((group, i) => {
    const card = document.createElement('button');
    card.className = 'landing-card';
    card.style.animationDelay = (i * 0.07) + 's';
    card.innerHTML = `
      <span class="landing-card-icon">${group.icon}</span>
      <div class="landing-card-body">
        <span class="landing-card-label">${group.label}</span>
        <span class="landing-card-desc">${GROUP_DESCS[group.key] || ''}</span>
      </div>
      <span class="landing-card-count">${group.pages.length} ${group.pages.length === 1 ? 'page' : 'pages'} →</span>
    `;
    card.addEventListener('click', () => navigateTo(group.key, group.pages[0]));
    grid.appendChild(card);
  });

  section.appendChild(grid);
  landingContent.appendChild(section);
}

// ── Icon Rail ──
function buildIconRail() {
  const oldNav = document.getElementById('sidebar');
  const oldToggle = document.getElementById('navToggle');
  const oldOverlay = document.getElementById('navOverlay');
  if (oldNav) oldNav.remove();
  if (oldToggle) oldToggle.remove();
  if (oldOverlay) oldOverlay.remove();

  const rail = document.createElement('nav');
  rail.id = 'iconRail';
  rail.className = 'icon-rail';

  // Logo / home button
  const logo = document.createElement('button');
  logo.className = 'rail-logo';
  logo.innerHTML = '⛏️';
  logo.title = 'Home';
  logo.addEventListener('click', () => navigateTo(null, null));
  rail.appendChild(logo);

  const divider = document.createElement('div');
  divider.className = 'rail-divider';
  rail.appendChild(divider);

  // Group icons
  NAV_GROUPS.forEach(group => {
    const btn = document.createElement('button');
    btn.className = 'rail-icon';
    btn.dataset.group = group.key;
    btn.title = group.label;
    btn.innerHTML = `<span class="rail-icon-emoji">${group.icon}</span><span class="rail-icon-label">${RAIL_LABELS[group.key] || ''}</span>`;
    btn.addEventListener('click', () => {
      navigateTo(group.key, group.pages[0]);
    });
    rail.appendChild(btn);
  });

  // Progress indicator at bottom
  const progressWrap = document.createElement('div');
  progressWrap.className = 'rail-progress';
  progressWrap.innerHTML = `
    <svg viewBox="0 0 36 36" class="progress-ring">
      <path class="progress-ring-bg" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
      <path class="progress-ring-fill" id="progressRing" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
    </svg>
    <span class="progress-pct" id="progressPct">0%</span>
  `;
  rail.appendChild(progressWrap);

  document.body.insertBefore(rail, document.querySelector('.layout'));
}

// ── Tab Bar ──
function buildTabBar() {
  let tabBar = document.getElementById('tabBar');
  if (!tabBar) {
    tabBar = document.createElement('div');
    tabBar.id = 'tabBar';
    tabBar.className = 'tab-bar';
    const main = document.querySelector('main');
    main.insertBefore(tabBar, main.firstChild);
  }
  return tabBar;
}

function updateTabBar(groupKey) {
  const tabBar = document.getElementById('tabBar');
  if (!tabBar) return;

  const group = NAV_GROUPS.find(g => g.key === groupKey);
  if (!group) {
    tabBar.innerHTML = '';
    tabBar.style.display = 'none';
    return;
  }

  tabBar.style.display = '';
  tabBar.innerHTML = '';

  const tabList = document.createElement('div');
  tabList.className = 'tab-list';

  group.pages.forEach(pageId => {
    const tab = document.createElement('button');
    tab.className = 'tab';
    tab.dataset.page = pageId;
    tab.textContent = PAGE_LABELS[pageId] || pageId;
    if (pageId === currentPage) tab.classList.add('active');
    tab.addEventListener('click', () => navigateTo(groupKey, pageId));
    tabList.appendChild(tab);
  });

  // Animated indicator
  const indicator = document.createElement('div');
  indicator.className = 'tab-indicator';
  indicator.id = 'tabIndicator';

  tabBar.appendChild(tabList);
  tabBar.appendChild(indicator);

  // Position indicator after render
  requestAnimationFrame(() => positionTabIndicator());
}

function positionTabIndicator() {
  const indicator = document.getElementById('tabIndicator');
  const activeTab = document.querySelector('.tab.active');
  if (!indicator || !activeTab) return;

  const tabList = activeTab.parentElement;
  const tabRect = activeTab.getBoundingClientRect();
  const listRect = tabList.getBoundingClientRect();

  indicator.style.width = tabRect.width + 'px';
  indicator.style.left = (tabRect.left - listRect.left + tabList.scrollLeft) + 'px';
}

// ── Router ──
function navigateTo(groupKey, pageId, pushState = true) {
  // Hide all pages
  Object.values(pages).forEach(s => {
    s.classList.remove('page-enter', 'page-visible');
    s.style.display = 'none';
  });
  if (landingContent) {
    landingContent.classList.remove('page-enter', 'page-visible');
    landingContent.style.display = 'none';
  }

  // Update rail active state
  document.querySelectorAll('.rail-icon').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.group === groupKey);
  });

  if (!groupKey || !pageId) {
    // Show landing page
    if (landingContent) {
      landingContent.style.display = '';
      requestAnimationFrame(() => {
        landingContent.classList.add('page-enter');
        requestAnimationFrame(() => landingContent.classList.add('page-visible'));
      });
    }
    const tabBar = document.getElementById('tabBar');
    if (tabBar) tabBar.style.display = 'none';
    currentGroup = null;
    currentPage = null;
    if (pushState) history.pushState(null, '', window.location.pathname);
    return;
  }

  currentGroup = groupKey;
  currentPage = pageId;

  // Show the requested page
  const section = pages[pageId];
  if (section) {
    section.style.display = '';
    requestAnimationFrame(() => {
      section.classList.add('page-enter');
      requestAnimationFrame(() => section.classList.add('page-visible'));
    });
  }

  updateTabBar(groupKey);

  if (pushState) {
    history.pushState({ group: groupKey, page: pageId }, '', '#' + pageId);
  }

  // Scroll content area to top
  const contentArea = document.getElementById('contentArea');
  if (contentArea) contentArea.scrollTop = 0;

  // Re-init checkboxes for newly visible page
  initCheckboxesForPage(pageId);
}

function handleHashRoute() {
  const hash = window.location.hash.slice(1);
  if (!hash) {
    navigateTo(null, null, false);
    return;
  }

  // Find which group this page belongs to
  for (const group of NAV_GROUPS) {
    if (group.pages.includes(hash)) {
      navigateTo(group.key, hash, false);
      return;
    }
  }

  // Not found — show landing
  navigateTo(null, null, false);
}

// ── Internal Link Routing ──
function initInternalLinks() {
  const contentArea = document.getElementById('contentArea');
  if (!contentArea) return;

  contentArea.addEventListener('click', (e) => {
    const link = e.target.closest('a[href^="#"]');
    if (!link) return;

    const targetId = link.getAttribute('href').slice(1);
    if (!targetId) return;

    // Check if this target is a known page
    for (const group of NAV_GROUPS) {
      if (group.pages.includes(targetId)) {
        e.preventDefault();
        navigateTo(group.key, targetId);
        return;
      }
    }
  });
}

// ── Checkbox Persistence ──
function loadChecks() {
  try { return JSON.parse(localStorage.getItem(STORAGE_KEY)) || {}; }
  catch { return {}; }
}

function saveChecks(data) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
}

function initCheckboxesForPage(pageId) {
  const section = pages[pageId];
  if (!section) return;

  const saved = loadChecks();
  section.querySelectorAll('.checklist input[type=checkbox]').forEach(cb => {
    if (cb.dataset.initialized) return;
    cb.dataset.initialized = 'true';

    const id = cb.dataset.id;
    if (id && saved[id]) {
      cb.checked = true;
      cb.closest('li').classList.add('done');
    }

    cb.addEventListener('change', function() {
      const li = this.closest('li');
      const data = loadChecks();
      if (this.checked) {
        li.classList.add('done');
        data[this.dataset.id] = true;
      } else {
        li.classList.remove('done');
        delete data[this.dataset.id];
      }
      saveChecks(data);
      updateProgress();
    });

    cb.closest('li').addEventListener('click', function(e) {
      if (e.target.tagName === 'A' || e.target.tagName === 'INPUT') return;
      const checkbox = this.querySelector('input[type=checkbox]');
      checkbox.checked = !checkbox.checked;
      checkbox.dispatchEvent(new Event('change'));
    });
  });
}

function initAllCheckboxes() {
  const saved = loadChecks();
  document.querySelectorAll('.checklist input[type=checkbox]').forEach(cb => {
    if (cb.dataset.initialized) return;
    cb.dataset.initialized = 'true';

    const id = cb.dataset.id;
    if (id && saved[id]) {
      cb.checked = true;
      const li = cb.closest('li');
      if (li) li.classList.add('done');
    }

    cb.addEventListener('change', function() {
      const li = this.closest('li');
      const data = loadChecks();
      if (this.checked) {
        li.classList.add('done');
        data[this.dataset.id] = true;
      } else {
        li.classList.remove('done');
        delete data[this.dataset.id];
      }
      saveChecks(data);
      updateProgress();
    });

    const li = cb.closest('li');
    if (li) {
      li.addEventListener('click', function(e) {
        if (e.target.tagName === 'A' || e.target.tagName === 'INPUT') return;
        const checkbox = this.querySelector('input[type=checkbox]');
        checkbox.checked = !checkbox.checked;
        checkbox.dispatchEvent(new Event('change'));
      });
    }
  });
}

function updateProgress() {
  const all = document.querySelectorAll('.checklist input[type=checkbox]');
  const done = document.querySelectorAll('.checklist input[type=checkbox]:checked');
  const pct = all.length ? Math.round((done.length / all.length) * 100) : 0;

  const ring = document.getElementById('progressRing');
  if (ring) {
    const circumference = 100;
    ring.style.strokeDasharray = `${pct}, ${circumference}`;
  }

  const pctLabel = document.getElementById('progressPct');
  if (pctLabel) pctLabel.textContent = pct + '%';
}

// ── Table Wrapping ──
function initTableWrap() {
  document.querySelectorAll('main table').forEach(table => {
    if (table.parentElement.classList.contains('table-wrap')) return;
    const wrapper = document.createElement('div');
    wrapper.className = 'table-wrap';
    table.parentNode.insertBefore(wrapper, table);
    wrapper.appendChild(table);
  });
}

// ── Particle System ──
function initParticles() {
  const canvas = document.getElementById('particles');
  if (!canvas) return;

  const ctx = canvas.getContext('2d');
  let particles = [];
  const PARTICLE_COUNT = 50;
  let animId;

  function resize() {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
  }

  function createParticle() {
    return {
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height,
      size: Math.random() * 2 + 0.5,
      speedY: -(Math.random() * 0.3 + 0.1),
      speedX: (Math.random() - 0.5) * 0.15,
      opacity: Math.random() * 0.5 + 0.1,
      fadeSpeed: Math.random() * 0.003 + 0.001,
      fadingIn: Math.random() > 0.5,
      hue: Math.random() > 0.6 ? 255 : (Math.random() > 0.5 ? 200 : 260),
    };
  }

  function init() {
    resize();
    particles = [];
    for (let i = 0; i < PARTICLE_COUNT; i++) {
      particles.push(createParticle());
    }
  }

  function draw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    particles.forEach(p => {
      // Drift
      p.x += p.speedX;
      p.y += p.speedY;

      // Fade
      if (p.fadingIn) {
        p.opacity += p.fadeSpeed;
        if (p.opacity >= 0.6) p.fadingIn = false;
      } else {
        p.opacity -= p.fadeSpeed;
        if (p.opacity <= 0.05) {
          // Reset particle
          Object.assign(p, createParticle());
          p.y = canvas.height + 10;
          p.fadingIn = true;
          p.opacity = 0;
        }
      }

      // Wrap horizontally
      if (p.x < -10) p.x = canvas.width + 10;
      if (p.x > canvas.width + 10) p.x = -10;

      // Draw glow
      ctx.beginPath();
      const gradient = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, p.size * 3);
      gradient.addColorStop(0, `hsla(${p.hue}, 80%, 70%, ${p.opacity})`);
      gradient.addColorStop(1, `hsla(${p.hue}, 80%, 70%, 0)`);
      ctx.fillStyle = gradient;
      ctx.arc(p.x, p.y, p.size * 3, 0, Math.PI * 2);
      ctx.fill();

      // Draw core
      ctx.beginPath();
      ctx.fillStyle = `hsla(${p.hue}, 90%, 85%, ${p.opacity * 1.5})`;
      ctx.arc(p.x, p.y, p.size * 0.7, 0, Math.PI * 2);
      ctx.fill();
    });

    animId = requestAnimationFrame(draw);
  }

  window.addEventListener('resize', resize, { passive: true });
  init();
  draw();
}

// ── Keyboard Navigation ──
function initKeyboardNav() {
  document.addEventListener('keydown', (e) => {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
    if (!currentGroup) return;

    const group = NAV_GROUPS.find(g => g.key === currentGroup);
    if (!group) return;

    const idx = group.pages.indexOf(currentPage);
    if (idx === -1) return;

    if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
      e.preventDefault();
      if (idx < group.pages.length - 1) {
        navigateTo(currentGroup, group.pages[idx + 1]);
      } else {
        // Jump to next group
        const groupIdx = NAV_GROUPS.indexOf(group);
        if (groupIdx < NAV_GROUPS.length - 1) {
          const nextGroup = NAV_GROUPS[groupIdx + 1];
          navigateTo(nextGroup.key, nextGroup.pages[0]);
        }
      }
    } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
      e.preventDefault();
      if (idx > 0) {
        navigateTo(currentGroup, group.pages[idx - 1]);
      } else {
        // Jump to previous group
        const groupIdx = NAV_GROUPS.indexOf(group);
        if (groupIdx > 0) {
          const prevGroup = NAV_GROUPS[groupIdx - 1];
          navigateTo(prevGroup.key, prevGroup.pages[prevGroup.pages.length - 1]);
        }
      }
    } else if (e.key === 'Escape') {
      navigateTo(null, null);
    }
  });
}

// ── Mobile Bottom Bar ──
function initMobileNav() {
  // The icon rail transforms into a bottom bar via CSS on small screens
  // But we need a mobile menu overlay for the tab bar
  const rail = document.getElementById('iconRail');
  if (!rail) return;

  // Add a current-page indicator for mobile
  const mobileLabel = document.createElement('div');
  mobileLabel.id = 'mobilePageLabel';
  mobileLabel.className = 'mobile-page-label';
  document.querySelector('main').prepend(mobileLabel);
}

// ── Back to Top ──
function initBackToTop() {
  const btn = document.getElementById('backToTop');
  if (!btn) return;

  const contentArea = document.getElementById('contentArea');
  const scrollTarget = contentArea || window;
  const getScroll = () => contentArea ? contentArea.scrollTop : window.scrollY;

  (contentArea || window).addEventListener('scroll', () => {
    btn.classList.toggle('visible', getScroll() > 600);
  }, { passive: true });

  btn.addEventListener('click', () => {
    if (contentArea) {
      contentArea.scrollTo({ top: 0, behavior: 'smooth' });
    } else {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  });
}

// ── Scroll Reveal ──
function initScrollReveal() {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.06, rootMargin: '0px 0px -30px 0px' });

  // Observe elements inside all pages
  const selectors = 'h2, h3, .callout, .mod-grid, table, .link-grid, .table-wrap, .checklist, h4';
  document.querySelectorAll('#contentArea ' + selectors).forEach(el => {
    el.classList.add('reveal');
    observer.observe(el);
  });
}

// ── Init ──
document.addEventListener('DOMContentLoaded', () => {
  // Remove old layout class — we're restructuring
  const layout = document.querySelector('.layout');
  if (layout) layout.className = 'grimoire-layout';

  // 1. Wrap tables first (before slicing moves them)
  initTableWrap();

  // 2. Slice content into pages
  slicePages();

  // 2b. Build landing page cards
  buildLandingCards();

  // 3. Build new navigation
  buildIconRail();
  buildTabBar();

  // 4. Init all checkboxes across all pages
  initAllCheckboxes();

  // 5. Route to current hash or show landing
  handleHashRoute();

  // 6. Listen for hash changes
  window.addEventListener('popstate', () => handleHashRoute());

  // 7. Particles
  initParticles();

  // 8. Keyboard nav
  initKeyboardNav();

  // 9. Mobile
  initMobileNav();

  // 10. Back to top
  initBackToTop();

  // 10b. Internal link routing
  initInternalLinks();

  // 11. Progress
  updateProgress();

  // 12. Scroll reveal
  requestAnimationFrame(() => initScrollReveal());
});

})();
