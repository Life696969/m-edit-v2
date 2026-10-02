import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import type {CaptionSegment, CaptionStyle} from './types';

const defaults: Required<CaptionStyle> = {
  enabled: true,
  position: 'bottom',
  fontFamily: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
  fontSize: 58,
  fontWeight: 700,
  textColor: '#FFFFFF',
  accentColor: '#FFFFFF',
  backgroundColor: 'rgba(0, 0, 0, 0.58)',
  maxWidthPercent: 88,
  bottomOffset: 160,
};

export const CaptionTrack: React.FC<{segments: CaptionSegment[]; style?: CaptionStyle}> = ({segments, style}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const timeMs = (frame / fps) * 1000;
  const active = segments.find((segment) => timeMs >= segment.start_ms && timeMs < segment.end_ms);
  const resolved = {...defaults, ...style};
  if (!resolved.enabled || !active) return null;

  const startFrame = (active.start_ms / 1000) * fps;
  const opacity = interpolate(frame, [startFrame, startFrame + Math.max(2, fps * 0.08)], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const alignment: React.CSSProperties = resolved.position === 'top'
    ? {justifyContent: 'flex-start', paddingTop: resolved.bottomOffset}
    : resolved.position === 'center'
      ? {justifyContent: 'center'}
      : {justifyContent: 'flex-end', paddingBottom: resolved.bottomOffset};

  return (
    <AbsoluteFill style={{...alignment, alignItems: 'center', pointerEvents: 'none'}}>
      <div style={{
        opacity,
        maxWidth: `${resolved.maxWidthPercent}%`,
        color: resolved.textColor,
        backgroundColor: resolved.backgroundColor,
        fontFamily: resolved.fontFamily,
        fontSize: resolved.fontSize,
        fontWeight: resolved.fontWeight,
        lineHeight: 1.12,
        textAlign: 'center',
        borderRadius: 16,
        padding: '12px 22px 14px',
        boxDecorationBreak: 'clone',
        WebkitBoxDecorationBreak: 'clone',
        textShadow: '0 2px 8px rgba(0,0,0,0.45)',
      }}>
        {active.text}
      </div>
    </AbsoluteFill>
  );
};
