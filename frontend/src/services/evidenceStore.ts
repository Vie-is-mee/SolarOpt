import type {ProjectEvidence} from '../studioTypes'
type SavedEvidence={fingerprint:string;evidence:ProjectEvidence}
function open():Promise<IDBDatabase>{return new Promise((resolve,reject)=>{
 const req=indexedDB.open('solaropt-evidence-v1',1)
 req.onupgradeneeded=()=>req.result.createObjectStore('draft')
 req.onsuccess=()=>resolve(req.result)
 req.onerror=()=>reject(req.error)
 req.onblocked=()=>reject(new Error('Kho lưu ảnh đang bị khóa bởi cửa sổ khác.'))
})}
export async function readEvidence():Promise<SavedEvidence|undefined>{
 const db=await open()
 try{return await new Promise((resolve,reject)=>{const tx=db.transaction('draft','readonly'),req=tx.objectStore('draft').get('current');req.onsuccess=()=>resolve(req.result);req.onerror=()=>reject(req.error)})}finally{db.close()}
}
export async function writeEvidence(value:SavedEvidence|null){
 const db=await open()
 try{await new Promise<void>((resolve,reject)=>{const tx=db.transaction('draft','readwrite');if(value)tx.objectStore('draft').put(value,'current');else tx.objectStore('draft').delete('current');tx.oncomplete=()=>resolve();tx.onerror=()=>reject(tx.error);tx.onabort=()=>reject(tx.error||new Error('Không lưu được ảnh.'))})}finally{db.close()}
}
