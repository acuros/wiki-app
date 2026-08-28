const fs = require('node:fs');

const TRANSCRIPTION_ENV_FILE = '/etc/transcription-api.env';

function readTranscriptionApiKey() {
  const explicitKey = process.env.EXPO_PUBLIC_TRANSCRIPTION_API_KEY;
  if (explicitKey) {
    return explicitKey;
  }
  if (!fs.existsSync(TRANSCRIPTION_ENV_FILE)) {
    return '';
  }

  const line = fs
    .readFileSync(TRANSCRIPTION_ENV_FILE, 'utf8')
    .split(/\r?\n/)
    .find((candidate) => candidate.trim().startsWith('TRANSCRIPTION_API_KEY='));
  if (!line) {
    return '';
  }
  return line
    .slice(line.indexOf('=') + 1)
    .trim()
    .replace(/^(['"])(.*)\1$/, '$2');
}

module.exports = ({ config }) => ({
  ...config,
  extra: {
    ...config.extra,
    transcriptionApiKey: readTranscriptionApiKey(),
  },
});
