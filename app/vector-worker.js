/* Trace the existing published categorical masks; never recompute measurements. */
'use strict';
importScripts('vendor/d3-array.min.js', 'vendor/d3-contour.min.js');

function project([longitude, latitude]) {
  const radians = Math.PI / 180;
  return [longitude * radians, Math.log(Math.tan(Math.PI / 4 + latitude * radians / 2))];
}
function inverse([x, y]) {
  return [Number((x * 180 / Math.PI).toFixed(6)), Number(((2 * Math.atan(Math.exp(y)) - Math.PI / 2) * 180 / Math.PI).toFixed(6))];
}
self.onmessage = ({data}) => {
  const {id, pixels, width, height, corners, classes} = data;
  try {
    const rgba = new Uint8ClampedArray(pixels);
    const labels = new Uint8Array(width * height);
    const lookup = new Map(classes.map((entry,index)=>[(entry.rgb[0]<<16)|(entry.rgb[1]<<8)|entry.rgb[2],index+1]));
    for(let i=0;i<labels.length;i++){
      const offset=i*4;
      if(rgba[offset+3])labels[i]=lookup.get((rgba[offset]<<16)|(rgba[offset+1]<<8)|rgba[offset+2])||0;
    }
    const projected=corners.map(project);
    const locate=([x,y])=>{
      const u=x/width,v=y/height;
      return inverse([0,1].map(axis=>(1-u)*(1-v)*projected[0][axis]+u*(1-v)*projected[1][axis]+u*v*projected[2][axis]+(1-u)*v*projected[3][axis]));
    };
    const generator=d3.contours().size([width,height]).smooth(false);
    const binary=new Uint8Array(labels.length),features=[];
    for(let index=0;index<classes.length;index++){
      let count=0;
      for(let i=0;i<labels.length;i++){const value=labels[i]===index+1?1:0;binary[i]=value;count+=value;}
      if(!count)continue;
      const geometry=generator.contour(binary,.5);
      geometry.coordinates=geometry.coordinates.map(polygon=>polygon.map(ring=>ring.map(locate)));
      delete geometry.value;
      features.push({type:'Feature',properties:{label:classes[index].label,color:classes[index].color},geometry});
    }
    self.postMessage({id,data:{type:'FeatureCollection',features}});
  } catch(error) {self.postMessage({id,error:error.message});}
};
