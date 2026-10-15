import React from 'react';
import {AbsoluteFill, Composition} from 'remotion';
import {z} from 'zod';
import {Generated} from './Generated';
import meta from './meta.json';

const schema = z.object({background: z.string()});
const Film: React.FC<z.infer<typeof schema>> = ({background}) => (
  <AbsoluteFill style={{backgroundColor: background, fontFamily: 'Microsoft YaHei, PingFang SC, sans-serif'}}>
    <Generated />
  </AbsoluteFill>
);

export const Root: React.FC = () => <Composition
  id="OralVideo" component={Film} schema={schema}
  width={meta.width} height={meta.height} fps={meta.fps}
  durationInFrames={meta.durationInFrames}
  defaultProps={{background: meta.background}}
/>;
