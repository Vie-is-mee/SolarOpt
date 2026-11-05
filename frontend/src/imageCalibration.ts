import type {Point} from './studioTypes'

/** Check thresholds for the optional second side: within 3 % agrees; up to 8 % is the usual eaves/gutter
 * difference; beyond that the outline or a measurement is likely wrong. None of them blocks the engineer. */
export const FRAME_TOLERANCE=.03,FRAME_LIMIT=.08
/** Largest roof side the studio accepts (factory roofs); larger sites are split into zones. */
export const MAX_ROOF_SIDE_M=300

// All lengths use one metres-per-pixel scale; never fit X and Y separately.
export function pixelDistance(points:Point[],width:number,height:number){
 return points.length===2?Math.hypot((points[0].x-points[1].x)*width/100,(points[0].y-points[1].y)*height/100):0
}
/** One scale for the whole photo: from a measured reference segment if there is one, otherwise from the
 * roof's longest side (the side people can measure or read off a map most reliably). The short side, when
 * given, is only compared against the photo; the outline is never stretched to match it. */
export function assessCalibration({pixelWidth,pixelHeight,measuredLong,measuredShort,referencePixels=0,referenceMetres=0}:{pixelWidth:number;pixelHeight:number;measuredLong?:number;measuredShort?:number;referencePixels?:number;referenceMetres?:number}){
 const reference=referencePixels>1&&Number.isFinite(referenceMetres)&&referenceMetres>0
 const pxLong=Math.max(pixelWidth,pixelHeight),pxShort=Math.min(pixelWidth,pixelHeight)
 const scale=reference?referenceMetres/referencePixels:(measuredLong??0)/pxLong
 const width=pixelWidth*scale,height=pixelHeight*scale,long=pxLong*scale,short=pxShort*scale
 const errors=[reference&&measuredLong?Math.abs(long-measuredLong)/measuredLong:0,measuredShort?Math.abs(short-measuredShort)/measuredShort:0]
 const mismatch=Math.max(...errors)
 const suppliedMeasurementsValid=[measuredLong,measuredShort].every(v=>v===undefined||(Number.isFinite(v)&&v>0))
 const sound=suppliedMeasurementsValid&&[width,height,scale].every(v=>Number.isFinite(v)&&v>0)
 return {width,height,long,short,scale,reference,mismatch,checked:errors.some(e=>e>0)||!!measuredShort,valid:sound&&mismatch<=FRAME_TOLERANCE,acceptable:sound&&mismatch<=FRAME_LIMIT,sound}
}
