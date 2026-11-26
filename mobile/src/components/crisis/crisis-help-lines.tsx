// ABOUTME: The crisis lines as tappable actions: call or text 988, call 911, and findahelpline.com for outside the
// ABOUTME: US. 988 leads unless the danger's own help is emergency services; an overdose opens with Call 911 now.

import { View } from 'react-native';
import en from '@/dictionaries/en.json';
import { siteName, type HelpLead } from '@/lib/chat';
import { fillTemplate } from '@/lib/utils';
import { useCrisisResources } from '@/hooks/useCrisisResources';
import { Text } from '@/components/shared';
import { CrisisHelpLink } from './crisis-help-link';

export interface CrisisHelpLinesProps {
  lead?: HelpLead;
}

export function CrisisHelpLines({ lead = 'support' }: CrisisHelpLinesProps) {
  const { support, emergency, directory } = useCrisisResources();
  const { help } = en.crisis;
  const emergencyFirst = lead !== 'support';

  const supportBlock = support?.phone ? (
    <View key="support" className="w-full gap-3">
      <Text className="text-center text-base leading-6">{fillTemplate(help.supportLine, { number: support.phone })}</Text>
      <View className="flex-row gap-3">
        <CrisisHelpLink label={fillTemplate(help.call, { number: support.phone })} url={`tel:${support.phone}`} prominent={!emergencyFirst} />
        {support.sms ? (
          <CrisisHelpLink label={fillTemplate(help.text, { number: support.sms })} url={`sms:${support.sms}`} prominent={!emergencyFirst} />
        ) : null}
      </View>
    </View>
  ) : null;

  const emergencyBlock = emergency?.phone ? (
    <View key="emergency" className="w-full gap-3">
      <Text className="text-center text-base leading-6">{fillTemplate(lead === 'callNow' ? help.callNow : help.emergencyLine, { number: emergency.phone })}</Text>
      <CrisisHelpLink label={fillTemplate(help.call, { number: emergency.phone })} url={`tel:${emergency.phone}`} prominent={emergencyFirst} />
    </View>
  ) : null;

  return (
    <View className="w-full gap-5">
      {emergencyFirst ? [emergencyBlock, supportBlock] : [supportBlock, emergencyBlock]}
      {directory?.url ? (
        <CrisisHelpLink label={fillTemplate(help.directory, { site: siteName(directory.url) })} url={directory.url} />
      ) : null}
    </View>
  );
}
