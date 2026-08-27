import { fireEvent, render } from '@testing-library/react-native';

import HomeScreen from '@/app/index';

describe('HomeScreen', () => {
  it('renders the ready state and responds to the primary action', async () => {
    const { getByRole, getByText } = await render(<HomeScreen />);

    expect(getByText('클라이언트 준비 완료')).toBeTruthy();
    await fireEvent.press(getByRole('button', { name: '시작하기' }));
    expect(getByText('첫 번째 기능을 추가할 준비가 되었습니다.')).toBeTruthy();
  });
});
