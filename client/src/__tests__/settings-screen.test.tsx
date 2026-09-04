import { fireEvent, render } from '@testing-library/react-native';

import SettingsScreen from '@/app/settings';

jest.mock('expo-constants', () => ({
  __esModule: true,
  default: { expoConfig: { version: '1.0.0' } },
}));

jest.mock('expo-router', () => ({
  router: { back: jest.fn() },
}));

jest.mock('expo-updates', () => ({
  channel: 'preview',
  runtimeVersion: '1.0.0',
  updateId: '01a06ce3-549f-79be-956b-77998bf81c4e',
}));

const mockRouter = jest.requireMock('expo-router').router as { back: jest.Mock };

describe('SettingsScreen', () => {
  beforeEach(() => mockRouter.back.mockReset());

  it('shows the installed app and OTA update versions at the bottom', async () => {
    const screen = await render(<SettingsScreen />);

    expect(screen.getByText('설정')).toBeTruthy();
    expect(screen.getByText('버전 1.0.0')).toBeTruthy();
    expect(screen.getByText('실행 업데이트 01a06ce3-549f-79be-956b-77998bf81c4e')).toBeTruthy();
    expect(screen.getByText('preview · runtime 1.0.0')).toBeTruthy();

    await fireEvent.press(screen.getByRole('button', { name: '뒤로가기' }));
    expect(mockRouter.back).toHaveBeenCalledTimes(1);
  });
});
