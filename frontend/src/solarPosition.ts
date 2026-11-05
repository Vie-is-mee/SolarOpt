const D=Math.PI/180
/** NOAA solar position (good to a fraction of a degree): altitude and compass azimuth for a local
 * date/hour in a fixed UTC offset. Used only to draw the day's sun path; the live sun comes from pvlib. */
export function solarPosition(lat:number,lon:number,date:string,hour:number,tz=7){
 const [Y,M,Dd]=date.split('-').map(Number)
 const jd=Date.UTC(Y,M-1,Dd)/86400000+2440587.5+(hour-tz)/24,T=(jd-2451545)/36525
 const L0=(280.46646+T*(36000.76983+T*.0003032))%360,Mm=357.52911+T*(35999.05029-.0001537*T),e=.016708634-T*(.000042037+.0000001267*T)
 const C=Math.sin(Mm*D)*(1.914602-T*(.004817+.000014*T))+Math.sin(2*Mm*D)*(.019993-.000101*T)+Math.sin(3*Mm*D)*.000289
 const omega=125.04-1934.136*T,lambda=L0+C-.00569-.00478*Math.sin(omega*D)
 const eps=23+(26+(21.448-T*(46.815+T*(.00059-T*.001813)))/60)/60+.00256*Math.cos(omega*D)
 const decl=Math.asin(Math.sin(eps*D)*Math.sin(lambda*D)),y=Math.tan(eps*D/2)**2
 const eqt=4/D*(y*Math.sin(2*L0*D)-2*e*Math.sin(Mm*D)+4*e*y*Math.sin(Mm*D)*Math.cos(2*L0*D)-.5*y*y*Math.sin(4*L0*D)-1.25*e*e*Math.sin(2*Mm*D))
 const ha=(hour*60+eqt+4*lon-60*tz)/4-180
 const zen=Math.acos(Math.max(-1,Math.min(1,Math.sin(lat*D)*Math.sin(decl)+Math.cos(lat*D)*Math.cos(decl)*Math.cos(ha*D))))
 const az=(Math.atan2(Math.sin(ha*D),Math.cos(ha*D)*Math.sin(lat*D)-Math.tan(decl)*Math.cos(lat*D))/D+180+360)%360
 return {alt:90-zen/D,az,decl:decl/D}
}

