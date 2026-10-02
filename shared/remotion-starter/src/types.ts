export type CaptionSegment = {
  start_ms: number;
  end_ms: number;
  text: string;
};

export type CaptionStyle = {
  enabled?: boolean;
  position?: 'top' | 'center' | 'bottom';
  fontFamily?: string;
  fontSize?: number;
  fontWeight?: number;
  textColor?: string;
  accentColor?: string;
  backgroundColor?: string;
  maxWidthPercent?: number;
  bottomOffset?: number;
};

export type MEditVideoProps = {
  src: string;
  durationInSeconds: number;
  width?: number;
  height?: number;
  fps?: number;
  captions?: CaptionSegment[];
  captionStyle?: CaptionStyle;
  fit?: 'cover' | 'contain';
  backgroundColor?: string;
};
