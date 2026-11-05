import {test} from 'node:test'
import assert from 'node:assert/strict'
import {loadTs} from './tsload.mjs'
const {rotateHouse,directionName,dayPath,northSunSpan,sideFacing,CITIES}=await loadTs('orientation')

const base={north_rotation_deg:0,roof_azimuth_deg:180,roof_tilt_deg:0,roof_faces:[{id:'a',azimuth_deg:180},{id:'b',azimuth_deg:0}],rack_azimuth_deg:180,geometry_confirmed:true}

test('turning the house turns every roof face with it, racks keep their compass direction',()=>{
 const east=rotateHouse(base,90)
 assert.equal(east.north_rotation_deg,90)
 assert.deepEqual(east.roof_faces.map(f=>f.azimuth_deg),[270,90])
 assert.equal(east.roof_azimuth_deg,270)
 assert.equal(east.rack_azimuth_deg,180)
 assert.equal(east.geometry_confirmed,false)
 const back=rotateHouse(rotateHouse(east,315),0)
 assert.deepEqual(back.roof_faces.map(f=>f.azimuth_deg),[180,0])
 assert.equal(rotateHouse(base,-45).north_rotation_deg,315)
 assert.equal(rotateHouse(base,0),base)
})

test('compass names and the side of the drawing facing each way',()=>{
 assert.equal(directionName(0),'Bắc');assert.equal(directionName(135),'Đông Nam');assert.equal(directionName(359.6),'Bắc')
 assert.equal(directionName(100),'Đông (100°)')
 assert.deepEqual(sideFacing(90),{top:90,right:180,bottom:270,left:0})
})

test('the sun path depends on latitude: north of the house at noon in summer only inside the tropics',()=>{
 const [,hlat,hlon]=CITIES.find(c=>c[0]==='TP. Hồ Chí Minh'),[,nlat,nlon]=CITIES.find(c=>c[0]==='Hà Nội')
 const juneHcm=dayPath(hlat,hlon,'2026-06-21'),decHcm=dayPath(hlat,hlon,'2026-12-21')
 assert(juneHcm.north&&!decHcm.north,'June noon sun is north of Hồ Chí Minh City, December south')
 assert(Math.abs(juneHcm.noon.alt-(90-(23.44-hlat)))<.6)
 assert(decHcm.noon.az>90&&decHcm.noon.az<270&&Math.abs(decHcm.noon.alt-(90-hlat-23.44))<.6)
 // Sunrise far north of east in June, south of east in December.
 assert(juneHcm.rise<70&&decHcm.rise>110)
 const hcm=northSunSpan(hlat,hlon,2026),hn=northSunSpan(nlat,nlon,2026)
 // The sun is overhead when its declination equals the latitude: about 18 April and 24 August at 10,8° N.
 assert(hcm.first>='2026-04-16'&&hcm.first<='2026-04-20'&&hcm.last>='2026-08-22'&&hcm.last<='2026-08-26',JSON.stringify(hcm))
 assert(hn.first>'2026-05-20'&&hn.last<'2026-07-25','Hà Nội: a shorter span around the June solstice')
 assert.equal(northSunSpan(30,105,2026),null)
 assert(dayPath(nlat,nlon,'2026-12-21').noon.alt<dayPath(hlat,hlon,'2026-12-21').noon.alt-9)
})
