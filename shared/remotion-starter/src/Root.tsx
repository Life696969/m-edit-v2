import React from 'react';
import {CalculateMetadataFunction, Composition} from 'remotion';
import {GenericVideo} from './GenericVideo';
import {ReelClip} from './director/ReelClip';
import type {ReelClipProps} from './director/types';
import directorDefaults from '../props.director.example.json';
import type {MEditVideoProps} from './types';

const defaultProps: MEditVideoProps = {
  src: 'm-edit-assets/source.mp4',
  durationInSeconds: 10,
  width: 1920,
  height: 1080,
  fps: 30,
  captions: [],
  captionStyle: {enabled: true, position: 'bottom'},
  fit: 'cover',
  backgroundColor: '#000000',
};

const calculateMetadata: CalculateMetadataFunction<MEditVideoProps> = ({props}) => {
  const fps = props.fps ?? 30;
  const width = props.width ?? 1920;
  const height = props.height ?? 1080;
  return {
    durationInFrames: Math.max(1, Math.ceil(props.durationInSeconds * fps)),
    fps,
    width,
    height,
  };
};

const reelMetadata: CalculateMetadataFunction<ReelClipProps> = ({props}) => ({
  durationInFrames: Math.max(1, Math.round(props.durationSec * props.fps)),
  fps: props.fps,
  width: props.width,
  height: props.height,
});

export const RemotionRoot: React.FC = () => (
  <>
    {/* simple: one neutral video with caption segments */}
    <Composition
      id="MEditVideo"
      component={GenericVideo}
      durationInFrames={300}
      fps={30}
      width={1920}
      height={1080}
      defaultProps={defaultProps}
      calculateMetadata={calculateMetadata}
    />
    {/* m-edit: one clip, props from `m-edit edit-props` (render every clip separately) */}
    <Composition
      id="ReelClip"
      component={ReelClip}
      durationInFrames={180}
      fps={30}
      width={1080}
      height={1920}
      defaultProps={directorDefaults as unknown as ReelClipProps}
      calculateMetadata={reelMetadata}
    />
  </>
);
