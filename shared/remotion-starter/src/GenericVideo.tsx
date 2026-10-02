import React from 'react';
import {AbsoluteFill, OffthreadVideo, staticFile} from 'remotion';
import {CaptionTrack} from './CaptionTrack';
import type {MEditVideoProps} from './types';

export const GenericVideo: React.FC<MEditVideoProps> = ({
  src,
  captions = [],
  captionStyle,
  fit = 'cover',
  backgroundColor = '#000000',
}) => {
  return (
    <AbsoluteFill style={{backgroundColor}}>
      <OffthreadVideo
        src={staticFile(src)}
        style={{width: '100%', height: '100%', objectFit: fit}}
      />
      <CaptionTrack segments={captions} style={captionStyle} />
    </AbsoluteFill>
  );
};
