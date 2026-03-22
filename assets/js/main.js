
document.addEventListener('DOMContentLoaded',function(){
  // Mobile menu
  const btn=document.getElementById('mobile-menu-btn');
  const menu=document.getElementById('mobile-menu');
  if(btn&&menu) btn.addEventListener('click',()=>menu.classList.toggle('hidden'));

  // Sticky header
  const hdr=document.getElementById('main-header');
  if(hdr) window.addEventListener('scroll',()=>hdr.classList.toggle('shadow-lg',window.scrollY>20));

  // Dropdowns
  document.querySelectorAll('[data-dropdown]').forEach(btn=>{
    btn.addEventListener('click',e=>{
      e.stopPropagation();
      const t=document.getElementById(btn.getAttribute('data-dropdown'));
      if(t) t.classList.toggle('hidden');
    });
  });
  document.addEventListener('click',()=>document.querySelectorAll('[id$="-dropdown"]').forEach(d=>d.classList.add('hidden')));

  // Scroll animations
  const obs=new IntersectionObserver(entries=>entries.forEach(e=>{if(e.isIntersecting)e.target.classList.add('animate-in');}),{threshold:0.1});
  document.querySelectorAll('.animate-on-scroll').forEach(el=>obs.observe(el));

  // Back to top
  const btt=document.getElementById('back-to-top');
  if(btt){
    window.addEventListener('scroll',()=>btt.classList.toggle('hidden',window.scrollY<300));
    btt.addEventListener('click',()=>window.scrollTo({top:0,behavior:'smooth'}));
  }

  // Stats counter
  document.querySelectorAll('[data-count]').forEach(el=>{
    const target=parseInt(el.getAttribute('data-count'));
    const suffix=el.getAttribute('data-suffix')||'';
    let count=0; const step=Math.ceil(target/50);
    const t=setInterval(()=>{count=Math.min(count+step,target);el.textContent=count+suffix;if(count>=target)clearInterval(t);},30);
  });

  // Contact form
  const form=document.getElementById('contact-form');
  if(form){
    form.addEventListener('submit',async function(e){
      e.preventDefault();
      const btn=form.querySelector('[type="submit"]');
      btn.disabled=true; btn.textContent='Envoi...';
      const data=Object.fromEntries(new FormData(form));
      try{
        await fetch('http://194.163.187.192:8084/api/contacts/new',{
          method:'POST',mode:'no-cors',
          headers:{'Content-Type':'application/json'},
          body:JSON.stringify({firstname:data.name,email:data.email,phone:data.phone||'',company:data.company||''})
        });
      }catch(err){}
      const ok=document.getElementById('form-success');
      if(ok){ok.classList.remove('hidden');form.classList.add('hidden');}
      btn.disabled=false;
    });
  }
});
