
const PRICES = {
  CAD: { symbol:'CA$', outbound_trial:15, outbound:[19,18,17,16], ai_trial:6, ai:[7,9,8,7], inbound:[199,339,479], support:[269,409,609], crm:[269,409,679] },
  EUR: { symbol:'\u20ac', outbound_trial:11, outbound:[14,13,12,12], ai_trial:5, ai:[5,7,6,5], inbound:[149,249,349], support:[199,299,449], crm:[199,299,499] },
  USD: { symbol:'$',   outbound_trial:11, outbound:[13,12,12,11], ai_trial:4, ai:[5,6,6,5], inbound:[139,229,319], support:[179,269,399], crm:[179,269,449] },
  CHF: { symbol:'CHF', outbound_trial:10, outbound:[13,12,11,11], ai_trial:4, ai:[5,6,6,5], inbound:[139,229,319], support:[189,279,419], crm:[189,279,469] }
};
const COUNTRY_CURRENCY = {
  CA:'CAD',US:'USD',FR:'EUR',BE:'EUR',LU:'EUR',MC:'EUR',
  MA:'EUR',DZ:'EUR',TN:'EUR',SN:'EUR',CI:'EUR',CH:'CHF'
};
let currentCurrency='EUR';
async function detectAndApplyCurrency(){
  try{
    const r=await fetch('https://ipapi.co/json/');
    const d=await r.json();
    currentCurrency=COUNTRY_CURRENCY[d.country_code]||'EUR';
  }catch(e){currentCurrency='EUR';}
  applyCurrency(currentCurrency);
}
function applyCurrency(code){
  currentCurrency=code;
  const p=PRICES[code];
  document.querySelectorAll('[data-price]').forEach(el=>{
    const key=el.getAttribute('data-price');
    const idx=el.getAttribute('data-idx');
    let val=idx!==null?p[key][parseInt(idx)]:p[key];
    if(val!==undefined) el.textContent=p.symbol+val;
  });
  document.querySelectorAll('[data-symbol]').forEach(el=>el.textContent=p.symbol);
  const sel=document.getElementById('currency-selector');
  if(sel) sel.value=code;
}
document.addEventListener('DOMContentLoaded',()=>{
  detectAndApplyCurrency();
  const sel=document.getElementById('currency-selector');
  if(sel) sel.addEventListener('change',e=>applyCurrency(e.target.value));
});
