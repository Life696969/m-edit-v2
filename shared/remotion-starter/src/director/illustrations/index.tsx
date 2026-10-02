// The illustration registry: a layer's `kind` picks its component here.
// Add a new visual by writing one component and registering it below; the core composition never changes.
// Illustrations are bespoke per video: they draw exactly what the speaker says, timed to `beats`.
import React from 'react';
import {Card, Cutaway, pop, ramp} from '../primitives';
import type {DirectorTheme, Geom, Layer} from '../types';

export type IllustrationProps = {layer: Layer; lt: number; dur: number; theme: DirectorTheme; src: string; geom: Geom};

/** Example cutaway: numbered steps that tick in on their beats (a process explainer). */
const StepsCutaway: React.FC<IllustrationProps> = ({layer, lt, dur, theme, src, geom}) => {
  const steps = (layer.data?.steps as string[] | undefined) ?? [];
  const beats = layer.beats ?? {};
  return (
    <Cutaway lt={lt} dur={dur} theme={theme} src={src} geom={geom} kicker={(layer.data?.kicker as string) ?? ''} title={(layer.data?.title as string) ?? ''}>
      {steps.map((label, i) => {
        const at = beats[`step${i + 1}`] ?? 0.15 + i * 0.25;
        return (
          <div key={label} style={{position: 'absolute', left: 90, top: 620 + i * 170, display: 'flex', alignItems: 'center', gap: 26, transform: `translateX(${(1 - ramp(lt, at, at + 0.3)) * -80}px)`, opacity: ramp(lt, at, at + 0.12)}}>
            <div style={{width: 110, height: 110, borderRadius: 30, background: theme.highlightColor, display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: theme.font, fontWeight: 900, fontSize: 60, color: '#10141C', transform: `scale(${pop(lt, at, 0.26)})`}}>{i + 1}</div>
            <div style={{fontFamily: theme.font, fontWeight: 800, fontSize: 52, color: '#FFFFFF'}}>{label}</div>
          </div>
        );
      })}
    </Cutaway>
  );
};

/** Example card: a single label that lands on its beat. */
const LabelCard: React.FC<IllustrationProps> = ({layer, lt, dur, theme}) => (
  <Card lt={lt} dur={dur} box={layer.box ?? [64, 200, 1016, 370]} theme={theme}>
    <div style={{display: 'flex', alignItems: 'center', height: '100%', fontFamily: theme.font, fontWeight: 900, fontSize: 58, color: '#10141C'}}>
      {(layer.data?.label as string) ?? ''}
    </div>
  </Card>
);

export const ILLUSTRATIONS: Record<string, React.FC<IllustrationProps>> = {
  steps: StepsCutaway,
  label: LabelCard,
  // 'folder': FolderCutaway,   ← register per-video illustrations like this
};
