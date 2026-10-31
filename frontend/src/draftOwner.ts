let owner:number|null=null
export function setDraftOwner(value:number|null){owner=value}
export function accountIdentity(){return owner===null?'guest':String(owner)}
export function draftKey(){return owner===null?'solaropt-studio-v2':`solaropt-studio-v2-user-${owner}`}
export function evidenceKey(){return owner===null?'current':`user-${owner}`}
