import React from 'react';
import {Easing, Img, Interactive, interpolate, OffthreadVideo, staticFile, useCurrentFrame} from 'remotion';

type Rect = [number, number, number, number];
const place = ([left,top,width,height]:Rect): React.CSSProperties => ({position:'absolute',left,top,width,height});

export const Enter: React.FC<{frames:number;children:React.ReactNode;direction?:number}> = ({frames,children,direction=0}) => {
  const f=useCurrentFrame();
  const ramp=Math.max(1,Math.min(8,Math.floor(frames/3)));
  const progress=interpolate(f,[0,ramp],[0,1],{extrapolateRight:'clamp',extrapolateLeft:'clamp'});
  const out=interpolate(f,[Math.max(ramp,frames-ramp),frames],[1,0],{extrapolateRight:'clamp',extrapolateLeft:'clamp'});
  return <div style={{position:'absolute',inset:0,opacity:progress*out,transform:`translate(${direction*(1-progress)*110}px,${direction?0:(1-progress)*18}px)`}}>{children}</div>;
};

export const Media: React.FC<{src:string;image:boolean;rect:Rect;initialRect:Rect;moveFrames:number;trim:number;fit:'cover'|'contain';transparent:boolean}> = ({src,image,rect,initialRect,moveFrames,trim,fit,transparent}) => {
  const frame=useCurrentFrame();
  const current=rect.map((value,i)=>interpolate(frame,[0,moveFrames],[initialRect[i],value],{extrapolateLeft:'clamp',extrapolateRight:'clamp',easing:Easing.out(Easing.cubic)})) as Rect;
  const style:React.CSSProperties={width:'100%',height:'100%',objectFit:fit};
  return <Interactive.Div style={{...place(current),overflow:'hidden',translate:'0px 0px',scale:1}}>
    {image ? <Img src={staticFile(src)} style={style}/> : <OffthreadVideo src={staticFile(src)} trimBefore={trim} muted transparent={transparent} style={style}/>}
  </Interactive.Div>;
};

export const Portrait: React.FC<{src:string;rect:Rect;side:'left'|'right';frames:number}> = ({src,rect,side,frames}) => {
  return <Enter frames={frames} direction={side==='left'?-1:1}>
    <Interactive.Div style={{...place(rect),borderRadius:'50%',overflow:'hidden',border:'6px solid #D4AA78',boxSizing:'border-box',boxShadow:'0 8px 28px #0003',translate:'0px 0px',scale:1}}>
      <Img src={staticFile(src)} style={{width:'100%',height:'100%',objectFit:'cover'}}/>
    </Interactive.Div>
  </Enter>;
};

export const StepLine: React.FC<{items:{text:string;at:number}[];rect:Rect}> = ({items,rect}) => {
  const f=useCurrentFrame();
  const gap=rect[3]/Math.max(items.length,1);
  const end=Math.max(1,...items.map(i=>i.at));
  const p=interpolate(f,[0,end],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  return <Interactive.Div style={{...place(rect),translate:'0px 0px',scale:1}}>
    <div style={{position:'absolute',left:17,top:22,width:5,height:Math.max(0,gap*(items.length-1))*p,background:'#B58450'}}/>
    {items.map((item,i)=><div key={i} style={{position:'absolute',left:0,top:i*gap,display:'flex',gap:26,alignItems:'center',opacity:interpolate(f,[item.at,item.at+6],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'})}}>
      <div style={{width:38,height:38,borderRadius:'50%',background:'#B58450',flexShrink:0}}/>
      <span style={{fontSize:58,fontWeight:800,color:'#49382B'}}>{item.text}</span>
    </div>)}
  </Interactive.Div>;
};
