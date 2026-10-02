// One director clip: footage under the camera pulse, at most one card or cutaway at a time, an optional
// depth beat, word-timed captions in screen space, and the audio mix. Rendered once per clip.
import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import {ILLUSTRATIONS} from './illustrations';
import {AudioMix, DH, DW, DepthSandwich, Footage, WordCaptions, cameraStyle} from './primitives';
import type {ReelClipProps} from './types';

const FULL_FRAME = new Set(['cutaway', 'broll']);

export const ReelClip: React.FC<ReelClipProps> = (p) => {
  const frame = useCurrentFrame();
  const {fps, width} = useVideoConfig();
  const t = frame / fps;
  const k = width / DW;
  const cam = cameraStyle(t, p.camera.keys, p.camera.shakes, p.camera.origin);
  const live = p.layers.filter((l) => t >= l.s && t < l.e);
  const full = live.find((l) => FULL_FRAME.has(l.type));
  const fullyCovered = full ? t - full.s > 0.16 && full.e - t > 0.14 : false;   // skip decoding hidden footage
  const depth = live.find((l) => l.type === 'depth' && l.matte);
  return (
    <AbsoluteFill style={{backgroundColor: '#000'}}>
      <AbsoluteFill style={{width: DW, height: DH, transform: `scale(${k})`, transformOrigin: '0 0', overflow: 'hidden'}}>
        {!fullyCovered ? <Footage src={p.src} style={cam} /> : null}
        {depth ? (
          <DepthSandwich matte={depth.matte!} graphicStyle={cameraStyle(t, p.camera.keys, p.camera.shakes, p.camera.origin, 0.6)} personStyle={cam}>
            {render(depth, t, p)}
          </DepthSandwich>
        ) : null}
        {live.filter((l) => l.type !== 'depth').map((l) => <React.Fragment key={l.id}>{render(l, t, p)}</React.Fragment>)}
        <WordCaptions t={t} words={p.words} chunks={p.chunks} theme={p.theme} overrideY={full ? p.cutawayCaptionY : undefined} />
      </AbsoluteFill>
      <AudioMix src={p.src} cues={p.cues} fps={fps} bed={p.bed} />
    </AbsoluteFill>
  );
};

function render(layer: ReelClipProps['layers'][number], t: number, p: ReelClipProps) {
  const Illustration = layer.kind ? ILLUSTRATIONS[layer.kind] : undefined;
  if (!Illustration) return null;
  return <Illustration layer={layer} lt={t - layer.s} dur={layer.e - layer.s} theme={p.theme} src={p.src} geom={p.geom} />;
}
