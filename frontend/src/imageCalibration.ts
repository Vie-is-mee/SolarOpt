import type {Point} from './studioTypes'

/** Frame check thresholds: within 3 % passes; up to 8 % (eaves, gutters, a soft traced edge)
 * may be applied with a visible warning; beyond that the trace or the measurements are wrong. */
export const FRAME_TOLERANCE=.03,FRAME_LIMIT=.08

// All lengths use one metres-per-pixel scale; never fit X and Y separately.
export function pixelDistance(points:Point[],width:number,height:number){
 return points.length===2?Math.hypot((points[0].x-points[1].x)*width/100,(points[0].y-points[1].y)*height/100):0
}
export function assessCalibration({pixelWidth,pixelHeight,measuredWidth,measuredHeight,referencePixels=0,referenceMetres=0}:{pixelWidth:number;pixelHeight:number;measuredWidth?:number;measuredHeight?:number;referencePixels?:number;referenceMetres?:number}){
 const reference=referencePixels>1&&Number.isFinite(referenceMetres)&&referenceMetres>0
 // A photo does not say which side was called width: pair the longer measured side with the longer traced side.
 const swapped=!!(measuredWidth&&measuredHeight&&pixelWidth>0&&pixelHeight>0&&measuredWidth!==measuredHeight&&pixelWidth!==pixelHeight&&(measuredWidth>measuredHeight)!==(pixelWidth>pixelHeight))
 const [frameWidth,frameHeight]=swapped?[measuredHeight,measuredWidth]:[measuredWidth,measuredHeight]
 // The longer side carries the smaller relative error, so it sets the single scale.
 const alongX=!frameHeight||!frameWidth||frameWidth>=frameHeight
 const scale=reference?referenceMetres/referencePixels:alongX?(frameWidth??0)/pixelWidth:(frameHeight??0)/pixelHeight
 const width=pixelWidth*scale,height=pixelHeight*scale
 const errors=[frameWidth?Math.abs(width-frameWidth)/frameWidth:0,frameHeight?Math.abs(height-frameHeight)/frameHeight:0]
 const mismatch=Math.max(...errors)
 const suppliedMeasurementsValid=[measuredWidth,measuredHeight].every(v=>v===undefined||(Number.isFinite(v)&&v>0))
 const sound=suppliedMeasurementsValid&&[width,height,scale].every(v=>Number.isFinite(v)&&v>0)
 return {width,height,scale,reference,mismatch,swapped,valid:sound&&mismatch<=FRAME_TOLERANCE,acceptable:sound&&mismatch<=FRAME_LIMIT}
}
