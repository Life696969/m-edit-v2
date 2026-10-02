// Props for one director clip. Generated from `.m-edit/edit.json` (see shared/references/edit-data.md):
// one props file per clip, so every final is rendered and delivered on its own.

export type Word = {t: string; s: number; e: number};
export type Chunk = {words: number[]; hl?: number[]; big?: boolean; y?: number; size_px?: number};
export type CamKey = {t: number; s: number; x: number; y: number};
export type Shake = {t: number; dur: number; amp: number; freq?: number};
export type Geom = {cx: number; cy: number; h: number}; // face centre and height, fractions of the canvas

export type Layer = {
  id: string;
  type: 'cutaway' | 'card' | 'depth' | 'photo' | 'logo' | 'overlay' | 'broll' | 'text';
  s: number;
  e: number;
  /** Which registered illustration renders this layer (see illustrations/index.tsx). */
  kind?: string;
  /** Clip-local word times the illustration animates to, relative to the layer start. */
  beats?: Record<string, number>;
  box?: [number, number, number, number];
  matte?: string;
  data?: Record<string, unknown>;
};

export type Cue = {src: string; at: number; volume: number};

export type DirectorTheme = {
  font: string;
  textColor: string;
  highlightColor: string;
  captionSize: number;
  bigCaptionSize: number;
  stage: string;
  stageGlow: string;
  cardBackground: string;
};

export type ReelClipProps = {
  width: number;
  height: number;
  fps: number;
  durationSec: number;
  /** Footage, relative to the Remotion public dir. */
  src: string;
  words: Word[];
  chunks: Chunk[];
  camera: {origin: [number, number]; keys: CamKey[]; shakes: Shake[]};
  layers: Layer[];
  cues: Cue[];
  geom: Geom;
  bed?: {src: string; from: number; volume: number};
  theme: DirectorTheme;
  /** Caption centre while a full-frame cutaway is up (fraction of height). */
  cutawayCaptionY: number;
};
