import type {Point} from './studioTypes'

// All lengths use one metres-per-pixel scale; never fit X and Y separately.
export function pixelDistance(points:Point[],width:number,height:number){
 return points.length===2?Math.hypot((points[0].x-points[1].x)*width/100,(points[0].y-points[1].y)*height/100):0
}
export function assessCalibration({pixelWidth,pixelHeight,measuredWidth,measuredHeight,referencePixels=0,referenceMetres=0}:{pixelWidth:number;pixelHeight:number;measuredWidth?:number;measuredHeight?:number;referencePixels?:number;referenceMetres?:number}){
 const reference=referencePixels>1&&Number.isFinite(referenceMetres)&&referenceMetres>0
 const scale=reference?referenceMetres/referencePixels:(measuredWidth??0)/pixelWidth
 const width=pixelWidth*scale,height=pixelHeight*scale
 const errors=[measuredWidth?Math.abs(width-measuredWidth)/measuredWidth:0,measuredHeight?Math.abs(height-measuredHeight)/measuredHeight:0]
 const mismatch=Math.max(...errors)
 const suppliedMeasurementsValid=[measuredWidth,measuredHeight].every(v=>v===undefined||(Number.isFinite(v)&&v>0))
 return {width,height,scale,reference,mismatch,valid:suppliedMeasurementsValid&&[width,height,scale].every(v=>Number.isFinite(v)&&v>0)&&mismatch<=.03}
}
