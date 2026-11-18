(function(){
  var q=document.getElementById('q'); if(!q) return;
  var muns=[].slice.call(document.querySelectorAll('#muns li'));
  var cts=[].slice.call(document.querySelectorAll('#centers li'));
  var empty=document.getElementById('empty');
  function norm(s){return s.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/[^a-z0-9]+/g,' ').trim();}
  q.addEventListener('input',function(){
    var v=norm(q.value), shown=0;
    muns.forEach(function(li){var ok=!v||li.dataset.q.indexOf(v)>-1; li.hidden=!ok; if(ok)shown++;});
    cts.forEach(function(li){var ok=v.length>2&&li.dataset.q.indexOf(v)>-1; li.hidden=!ok; if(ok)shown++;});
    empty.hidden=shown>0;
  });
})();
