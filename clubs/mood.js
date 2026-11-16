/* ciel selon l heure à La Réunion (repris de l accueil) ; ?ambiance=lagon|jour|couchant|soir */
(function(){try{var q=(location.search.match(/[?&]ambiance=(\w+)/)||[])[1],m;
if(q)m=q;else if(matchMedia("(prefers-color-scheme: dark)").matches&&document.documentElement.dataset.theme!=="light")m="soir";else{
var now=new Date(),t=new Date(now.getTime()+144e5),d=Math.floor((Date.UTC(t.getUTCFullYear(),t.getUTCMonth(),t.getUTCDate())-Date.UTC(t.getUTCFullYear(),0,0))/864e5),
g=2*Math.PI/365*(d-1),eq=229.18*(7.5e-5+.001868*Math.cos(g)-.032077*Math.sin(g)-.014615*Math.cos(2*g)-.040849*Math.sin(2*g)),
de=.006918-.399912*Math.cos(g)+.070257*Math.sin(g)-.006758*Math.cos(2*g)+9.07e-4*Math.sin(2*g)-.002697*Math.cos(3*g)+.00148*Math.sin(3*g),
la=-20.9*Math.PI/180,ha=Math.acos(Math.cos(90.833*Math.PI/180)/(Math.cos(la)*Math.cos(de))-Math.tan(la)*Math.tan(de))*180/Math.PI,
noon=720-4*55.45-eq+240,rise=noon-4*ha,set=noon+4*ha,h=t.getUTCHours()*60+t.getUTCMinutes();
m=h<rise||h>=set+30?"soir":h<540?"lagon":h>=set-60?"couchant":"jour";}
document.documentElement.dataset.mood=m;}catch(e){}})();
