// assets/partials.js - GitHub Pages compatible component loader

document.addEventListener('DOMContentLoaded', function() {
  // Detect GitHub Pages repository path
  var base = '';
  if (window.location.hostname.indexOf('github.io') !== -1) {
    // Extract repo name from pathname
    var pathParts = window.location.pathname.split('/').filter(Boolean);
    if (pathParts.length > 0) {
      base = '/' + pathParts[0];
    }
  }
  
  // Load header and footer
  loadPartial('header-container', base + '/includes/header.html');
  loadPartial('footer-container', base + '/includes/footer.html');
});

function loadPartial(id, url) {
  var el = document.getElementById(id);
  if (!el) return;
  
  fetch(url)
    .then(function(r) { 
      if (!r.ok) throw new Error(r.status); 
      return r.text(); 
    })
    .then(function(html) { 
      el.innerHTML = html;
      // Fix relative links in header for GitHub Pages
      fixHeaderLinks();
    })
    .catch(function(err) { 
      console.error('Partial load failed:', url, err); 
    });
}

function fixHeaderLinks() {
  var base = '';
  if (window.location.hostname.indexOf('github.io') !== -1) {
    var pathParts = window.location.pathname.split('/').filter(Boolean);
    if (pathParts.length > 0) {
      base = '/' + pathParts[0];
    }
  }
  
  // Get current language from URL
  var isEnglish = window.location.pathname.indexOf('/en/') !== -1;
  var langDir = isEnglish ? '/en/' : '/fr/';
  
  // Fix navigation links
  var navLinks = document.querySelectorAll('.main-nav a, .mobile-menu a');
  navLinks.forEach(function(link) {
    var href = link.getAttribute('href');
    if (href && !href.startsWith('http') && !href.startsWith('#') && !href.startsWith(base)) {
      // Prepend base + lang directory for relative links
      if (href.indexOf('.html') !== -1) {
        link.setAttribute('href', base + langDir + href);
      }
    }
  });
  
  // Fix logo link
  var logoLink = document.querySelector('.logo-link');
  if (logoLink) {
    logoLink.setAttribute('href', base + langDir + 'index.html');
  }
  
  // Fix language selector links
  var langOptions = document.querySelectorAll('.lang-option');
  langOptions.forEach(function(option) {
    var lang = option.getAttribute('data-lang');
    if (lang) {
      // Get current filename
      var path = window.location.pathname;
      var filename = path.split('/').pop() || 'index.html';
      if (filename === '' || filename === pathParts[0]) {
        filename = 'index.html';
      }
      option.setAttribute('href', base + '/' + lang + '/' + filename);
    }
  });
}
