// Building blocks for m-edit edits. Deterministic: everything is a function of the frame.
import React from 'react';
import {AbsoluteFill, Audio, Easing, OffthreadVideo, Sequence, interpolate, staticFile} from 'remotion';
import type {CamKey, Chunk, Cue, DirectorTheme, Geom, Shake, Word} from './types';

export const DW = 1080; // design canvas: every layout number below is in 1080-wide units
export const DH = 1920;

const EO = Easing.out(Easing.cubic);
const EIO = Easing.inOut(Easing.cubic);
export const BACK = Easing.out(Easing.back(1.7));

export const ramp = (t: number, a: number, b: number, from = 0, to = 1, easing: (n: number) => number = EO) =>
  interpolate(t, [a, b], [from, to], {easing, extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
export const pop = (t: number, at: number, dur = 0.24) => ramp(t, at, at + dur, 0, 1, BACK);
export const bump = (t: number, at: number, k = 0.14, dur = 0.28) =>
  1 + k * Math.sin(Math.PI * ramp(t, at, at + dur, 0, 1, EIO));

/* ---------------------------------------------------------------- the camera (camera-pulse.md) */

/** Sine ease between keys: each move leaves from rest and settles exactly on its key. */
export const cameraAt = (t: number, keys: CamKey[]): CamKey => {
  if (!keys.length) return {t, s: 1, x: 0, y: 0};
  if (t <= keys[0].t) return keys[0];
  for (let i = 0; i < keys.length - 1; i++) {
    const a = keys[i];
    const b = keys[i + 1];
    if (t >= a.t && t < b.t) {
      const e = 0.5 - 0.5 * Math.cos((Math.PI * (t - a.t)) / (b.t - a.t));
      return {t, s: a.s + (b.s - a.s) * e, x: a.x + (b.x - a.x) * e, y: a.y + (b.y - a.y) * e};
    }
  }
  return keys[keys.length - 1];
};

export const shakeAt = (t: number, shakes: Shake[]): [number, number] => {
  let dx = 0;
  let dy = 0;
  for (const s of shakes) {
    if (t < s.t || t > s.t + s.dur) continue;
    const u = (t - s.t) / s.dur;
    const env = Math.exp(-3.2 * u) * (1 - u * 0.4);
    const p = (t - s.t) * (s.freq ?? 12) * 2 * Math.PI;
    dx += s.amp * env * Math.sin(p) * 0.8;
    dy += s.amp * env * Math.sin(p * 0.83 + 1.7);
  }
  return [dx, dy];
};

/** k < 1 moves a layer less than the footage: parallax for a depth beat. */
export const cameraStyle = (t: number, keys: CamKey[], shakes: Shake[], origin: [number, number], k = 1): React.CSSProperties => {
  const c = cameraAt(t, keys);
  const [sx, sy] = shakeAt(t, shakes);
  return {
    transform: `translate(${(c.x * DW + sx) * k}px, ${(c.y * DH + sy) * k}px) scale(${1 + (c.s - 1) * k})`,
    transformOrigin: `${origin[0] * 100}% ${origin[1] * 100}%`,
  };
};

export const Footage: React.FC<{src: string; style: React.CSSProperties; transparent?: boolean}> = ({src, style, transparent}) => (
  <AbsoluteFill style={style}>
    <OffthreadVideo src={staticFile(src)} muted transparent={transparent} style={{width: '100%', height: '100%'}} />
  </AbsoluteFill>
);

/** A live circular crop of the speaker, so a cutaway keeps a face on the voice. */
export const FacePip: React.FC<{src: string; geom: Geom; x: number; y: number; d: number; k?: number; ring?: string}> = ({src, geom, x, y, d, k = 1, ring = '#FFFFFF'}) => {
  const b = 6;
  const inner = d - 2 * b;
  const sc = (inner * 1.05) / (geom.h * DH);
  return (
    <div style={{position: 'absolute', left: x, top: y, width: d, height: d, borderRadius: '50%', overflow: 'hidden', border: `${b}px solid ${ring}`, boxShadow: '0 10px 26px rgba(0,0,0,0.4)', transform: `scale(${k})`, background: '#222', boxSizing: 'border-box'}}>
      <div style={{position: 'absolute', left: inner / 2 - geom.cx * DW * sc, top: inner / 2 - geom.cy * DH * sc, width: DW * sc, height: DH * sc}}>
        <OffthreadVideo src={staticFile(src)} muted style={{width: '100%', height: '100%'}} />
      </div>
    </div>
  );
};

/* ---------------------------------------------------------------- cards and cutaways */

/** An opaque card in the free part of the frame (never a scrim: it holds its own content). */
export const Card: React.FC<{lt: number; dur: number; box: [number, number, number, number]; theme: DirectorTheme; children: React.ReactNode}> = ({lt, dur, box, theme, children}) => {
  const k = ramp(lt, 0, 0.22, 0, 1, BACK);
  const out = ramp(lt, dur - 0.12, dur, 0, 1, EIO);
  return (
    <div style={{position: 'absolute', left: box[0], top: box[1], width: box[2] - box[0], height: box[3] - box[1], borderRadius: 30, background: theme.cardBackground, boxShadow: '0 16px 40px rgba(0,0,0,0.38)', padding: '22px 26px', boxSizing: 'border-box', transform: `translateY(${(1 - k) * -60 - out * 40}px) scale(${0.94 + 0.06 * k})`, opacity: ramp(lt, 0, 0.1) * (1 - out)}}>
      {children}
    </div>
  );
};

/** Full-frame cutaway shell: stage, header, a live face pip; the illustration goes inside. */
export const Cutaway: React.FC<{lt: number; dur: number; theme: DirectorTheme; src: string; geom: Geom; kicker?: string; title?: React.ReactNode; holdToEnd?: boolean; children: React.ReactNode}> = ({lt, dur, theme, src, geom, kicker, title, holdToEnd, children}) => {
  const kin = ramp(lt, 0, 0.16);
  const kout = holdToEnd ? 0 : ramp(lt, dur - 0.14, dur, 0, 1, EIO);
  return (
    <AbsoluteFill style={{opacity: kin * (1 - kout), transform: `scale(${(1.1 - 0.1 * kin) * (1 - 0.04 * kout)})`}}>
      <AbsoluteFill style={{background: `radial-gradient(circle at 50% 46%, ${theme.stageGlow} 0%, ${theme.stage} 62%)`}}>
        <AbsoluteFill style={{backgroundImage: 'radial-gradient(rgba(255,255,255,0.07) 1.6px, transparent 1.7px)', backgroundSize: '36px 36px'}} />
      </AbsoluteFill>
      {title ? (
        <div style={{position: 'absolute', left: 70, top: 290, width: 720, opacity: ramp(lt, 0, 0.14)}}>
          {kicker ? <div style={{fontFamily: 'monospace', fontWeight: 700, fontSize: 27, letterSpacing: 7, color: '#9AA4B5'}}>{kicker}</div> : null}
          <div style={{fontFamily: theme.font, fontWeight: 900, fontSize: 82, lineHeight: 1.02, letterSpacing: -3, color: '#FFFFFF', marginTop: 6}}>{title}</div>
        </div>
      ) : null}
      {children}
      <FacePip src={src} geom={geom} x={DW - 44 - 190} y={120} d={190} k={pop(lt, 0.1, 0.24)} />
    </AbsoluteFill>
  );
};

/** Depth beat: footage → graphic (parallax) → person matte. The room is never replaced. */
export const DepthSandwich: React.FC<{matte: string; graphicStyle: React.CSSProperties; personStyle: React.CSSProperties; children: React.ReactNode}> = ({matte, graphicStyle, personStyle, children}) => (
  <>
    <AbsoluteFill style={graphicStyle}>{children}</AbsoluteFill>
    <Footage src={matte} style={personStyle} transparent />
  </>
);

/* ---------------------------------------------------------------- captions (captions.md) */

const armour = (stroke: number): React.CSSProperties => ({
  WebkitTextStroke: `${stroke}px #000`,
  paintOrder: 'stroke fill',
  textShadow: '0 3px 10px rgba(0,0,0,0.55)',
});

/** Exact spoken words, word-timed, glyph armour only (no box, no scrim). */
export const WordCaptions: React.FC<{t: number; words: Word[]; chunks: Chunk[]; theme: DirectorTheme; overrideY?: number}> = ({t, words, chunks, theme, overrideY}) => {
  const hold = 0.16;
  const active = chunks.find((c, i) => {
    const s = words[c.words[0]].s;
    const next = chunks[i + 1];
    const e = Math.min(words[c.words[c.words.length - 1]].e + hold, next ? words[next.words[0]].s : Infinity);
    return t >= s && t < e;
  });
  if (!active) return null;
  const s = words[active.words[0]].s;
  const k = ramp(t, s, s + 0.12);
  const size = active.size_px ?? (active.big ? theme.bigCaptionSize : theme.captionSize);
  const y = overrideY ?? active.y ?? 0.66;
  return (
    <div style={{position: 'absolute', left: 50, right: 50, top: y * DH, transform: `translateY(-50%) translateY(${(1 - k) * 20}px) scale(${0.95 + 0.05 * k})`, opacity: k, display: 'flex', flexWrap: 'wrap', gap: `0 ${size * 0.32}px`, justifyContent: 'center', alignItems: 'baseline', textAlign: 'center'}}>
      {active.words.map((i) => {
        const w = words[i];
        const popK = active.big ? 0.12 : 0.05;
        const wordPop = 1 + popK * Math.min(ramp(t, w.s, w.s + 0.05), ramp(t, w.s + 0.09, w.s + 0.22, 1, 0));
        return (
          <span key={i} style={{display: 'inline-block', fontFamily: theme.font, fontWeight: 800, fontSize: size, lineHeight: 1.14, letterSpacing: -1.4, color: active.hl?.includes(i) ? theme.highlightColor : theme.textColor, opacity: t >= w.s ? 1 : 0.82, transform: `scale(${wordPop})`, ...armour(size * 0.13)}}>
            {w.t}
          </span>
        );
      })}
    </div>
  );
};

/* ---------------------------------------------------------------- audio (sound-design.md) */

export const AudioMix: React.FC<{src: string; cues: Cue[]; fps: number; bed?: {src: string; from: number; volume: number}}> = ({src, cues, fps, bed}) => (
  <>
    <Audio src={staticFile(src)} />
    {bed && bed.volume > 0 ? <Audio src={staticFile(bed.src)} trimBefore={Math.round(bed.from * fps)} volume={bed.volume} /> : null}
    {cues.map((c, i) => (
      <Sequence key={`${c.src}-${i}`} from={Math.max(0, Math.round(c.at * fps))} layout="none">
        <Audio src={staticFile(c.src)} volume={c.volume} />
      </Sequence>
    ))}
  </>
);
