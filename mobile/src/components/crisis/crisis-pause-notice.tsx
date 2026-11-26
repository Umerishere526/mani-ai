// ABOUTME: The secondary lines under the crisis screen while chat is paused: that chat is unavailable, how long the
// ABOUTME: pause runs and the time chat opens again. A fixed time, never a ticking countdown.

import { View } from 'react-native';
import en from '@/dictionaries/en.json';
import { pauseLength, type ChatPause } from '@/lib/chat';
import { fillTemplate } from '@/lib/utils';
import { Text } from '@/components/shared';

export interface CrisisPauseNoticeProps {
  pause: ChatPause;
}

export function CrisisPauseNotice({ pause }: CrisisPauseNoticeProps) {
  const { pause: copy } = en.crisis;
  const { count, unit } = pauseLength(pause);
  const length = fillTemplate(copy.units[unit][count === 1 ? 'one' : 'other'], { count: String(count) });
  const time = new Date(pause.until).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });

  return (
    <View className="gap-1">
      <Text className="text-center text-sm text-secondary-500/80">{copy.title}</Text>
      <Text className="text-center text-sm text-secondary-500/80">{fillTemplate(copy.pausedFor, { length })}</Text>
      <Text className="text-center text-sm text-secondary-500/80">{fillTemplate(copy.opensAt, { time })}</Text>
    </View>
  );
}
