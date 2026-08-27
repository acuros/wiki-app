export const colors = {
  background: '#F7F8FA',
  surface: '#FFFFFF',
  border: '#E4E7EC',
  primary: '#3157D5',
  onPrimary: '#FFFFFF',
  text: '#151A23',
  textMuted: '#667085',
} as const;

export const spacing = {
  sm: 8,
  md: 16,
  lg: 24,
  xl: 32,
} as const;

export const typography = {
  title: {
    fontSize: 30,
    lineHeight: 38,
    fontWeight: '700',
  },
  body: {
    fontSize: 16,
    lineHeight: 24,
    fontWeight: '400',
  },
  button: {
    fontSize: 16,
    lineHeight: 20,
    fontWeight: '600',
  },
  caption: {
    fontSize: 12,
    lineHeight: 16,
    fontWeight: '700',
    letterSpacing: 1.2,
  },
} as const;
