
document.addEventListener('DOMContentLoaded', function() {

  // Mobile menu toggle
  const menuBtn = document.getElementById('mobile-menu-btn');
  const mobileMenu = document.getElementById('mobile-menu');
  if (menuBtn && mobileMenu) {
    menuBtn.addEventListener('click', function() {
      mobileMenu.classList.toggle('hidden');
      const icon = menuBtn.querySelector('i');
      if (icon) {
        icon.classList.toggle('fa-bars');
        icon.classList.toggle('fa-times');
      }
    });
  }

  // Sticky header shadow
  const header = document.getElementById('main-header');
  if (header) {
    window.addEventListener('scroll', function() {
      if (window.scrollY > 20) {
        header.classList.add('shadow-lg');
        header.classList.remove('shadow-sm');
      } else {
        header.classList.remove('shadow-lg');
        header.classList.add('shadow-sm');
      }
    });
  }

  // Scroll animations
  const observer = new IntersectionObserver(function(entries) {
    entries.forEach(function(entry) {
      if (entry.isIntersecting) {
        entry.target.classList.add('animate-in');
      }
    });
  }, { threshold: 0.1 });

  document.querySelectorAll('.animate-on-scroll').forEach(function(el) {
    observer.observe(el);
  });

  // Back to top
  const backTop = document.getElementById('back-to-top');
  if (backTop) {
    window.addEventListener('scroll', function() {
      if (window.scrollY > 300) {
        backTop.classList.remove('hidden');
      } else {
        backTop.classList.add('hidden');
      }
    });
    backTop.addEventListener('click', function() {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  }

  // Stats counter animation
  document.querySelectorAll('[data-count]').forEach(function(el) {
    const target = parseInt(el.getAttribute('data-count'));
    const suffix = el.getAttribute('data-suffix') || '';
    let count = 0;
    const step = Math.ceil(target / 60);
    const timer = setInterval(function() {
      count = Math.min(count + step, target);
      el.textContent = count + suffix;
      if (count >= target) clearInterval(timer);
    }, 25);
  });

  // Contact form
  const form = document.getElementById('contact-form');
  if (form) {
    form.addEventListener('submit', async function(e) {
      e.preventDefault();
      const btn = form.querySelector('[type="submit"]');
      if (btn) { btn.disabled = true; btn.textContent = 'Envoi...'; }
      const data = Object.fromEntries(new FormData(form));
      try {
        await fetch('http://194.163.187.192:8084/api/contacts/new', {
          method: 'POST',
          mode: 'no-cors',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            firstname: (data.name || '').split(' ')[0],
            lastname: (data.name || '').split(' ').slice(1).join(' '),
            email: data.email || '',
            phone: data.phone || '',
            company: data.company || ''
          })
        });
      } catch(err) { console.log('Form submit:', err); }
      const ok = document.getElementById('form-success');
      if (ok) { ok.classList.remove('hidden'); form.classList.add('hidden'); }
      if (btn) { btn.disabled = false; }
    });
  }

});
