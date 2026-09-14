// ABOUTME: Static safety-support copy shown inside CrisisDrawer — intro, situational
// ABOUTME: guidance, action links, and disclaimer. Extracted so the drawer shell stays small.

import { Pressable, View } from 'react-native';
import en from '@/dictionaries/en.json';
import { Text } from '@/components/shared';

interface ActionLinkProps {
  label: string;
  onPress?: () => void;
}

function ActionLink({ label, onPress }: ActionLinkProps) {
  return (
    <Pressable className="py-2 active:opacity-70" onPress={onPress}>
      <Text className="font-sans-medium text-base text-secondary-500 underline">{label}</Text>
    </Pressable>
  );
}

export function CrisisGuidance() {
  return (
    <>
      <Text className="mb-6 font-sans-semibold text-2xl text-secondary-500">{en.crisis.title}</Text>

      <View className="mb-8 gap-4">
        {en.crisis.intro.map((line) => (
          <Text key={line} className="text-base leading-[26px] text-secondary-500">
            {line}
          </Text>
        ))}
      </View>

      <View className="mb-8 gap-6">
        {en.crisis.guidance.map((item) => (
          <View key={item.label} className="gap-2">
            <Text className="font-sans-medium text-base text-secondary-500">{item.label}</Text>
            <Text className="text-base leading-[26px] text-secondary-500">{item.body}</Text>
          </View>
        ))}
      </View>

      <View className="mb-10 gap-4">
        {en.crisis.actions.map((label) => (
          <ActionLink key={label} label={label} />
        ))}
      </View>

      <Text className="text-sm leading-[22px] text-secondary-500">{en.crisis.disclaimer}</Text>
    </>
  );
}
