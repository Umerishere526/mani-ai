// ABOUTME: The Home screen's scrollable body — hero sphere/greeting, a list of featured
// ABOUTME: exercise cards, and a link into the full library. No network layer yet, so the
// ABOUTME: exercise list is a `homeExercises` prop rather than a live query.

import { ActivityIndicator, Pressable, ScrollView, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Feather } from '@react-native-vector-icons/feather/static';
import { AppHeader, GradientSphere, Text } from '@/components/shared';
import { colors } from '@/lib/tokens';
import { useResponsiveTypography } from '@/hooks/useResponsiveTypography';
import { useResponsiveLayout } from '@/hooks/useResponsiveLayout';
import en from '@/dictionaries/en.json';
import type { Exercise } from '@/types/exercise';
import { HomeExerciseCard } from './home-exercise-card';

const HEADER_HEIGHT = 56;

export interface HomeScreenContentProps {
  homeExercises: Exercise[];
  isLoading: boolean;
  onExercisePress: (exerciseId: string) => void;
  onLibraryPress: () => void;
  onNewChatPress: () => void;
}

export function HomeScreenContent({
  homeExercises,
  isLoading,
  onExercisePress,
  onLibraryPress,
  onNewChatPress,
}: HomeScreenContentProps) {
  const insets = useSafeAreaInsets();
  const typography = useResponsiveTypography();
  const layout = useResponsiveLayout();

  return (
    <View className="flex-1 bg-primary-900">
      <ScrollView
        className="flex-1"
        contentContainerClassName="px-4"
        style={{ paddingTop: insets.top + HEADER_HEIGHT }}
        contentContainerStyle={{ paddingBottom: insets.bottom + 24 }}
        showsVerticalScrollIndicator={false}
      >
        <View className="items-center" style={{ marginTop: 32, paddingTop: typography.homeCard.heroVerticalPadding }}>
          <GradientSphere size={typography.homeCard.sphereSize} />
          <Text
            className="mb-6 mt-4 self-center text-center font-sans-medium"
            style={[typography.body, { maxWidth: layout.greetingMaxWidth }]}
          >
            {en.home.greeting}
          </Text>
        </View>

        <View className="items-center" style={{ gap: typography.homeCard.gap }}>
          {isLoading ? (
            <View className="items-center py-8">
              <ActivityIndicator size="small" color={colors.secondary[500]} accessibilityLabel={en.home.loadingExercisesLabel} />
            </View>
          ) : (
            homeExercises.map((exercise) => (
              <HomeExerciseCard key={exercise.id} exercise={exercise} typography={typography} onPress={onExercisePress} />
            ))
          )}
        </View>

        <Pressable
          className="items-center"
          style={{ marginTop: typography.homeCard.libraryLinkMarginTop }}
          onPress={onLibraryPress}
          accessibilityRole="button"
          accessibilityLabel={en.home.libraryLink}
          accessibilityHint={en.home.libraryLinkHint}
        >
          <View className="flex-row items-center gap-1">
            <Text className="font-sans-medium text-base">{en.home.libraryLink}</Text>
            <Feather name="chevron-right" size={18} color={colors.secondary[500]} />
          </View>
        </Pressable>
      </ScrollView>
      <AppHeader transparent absolute onNewChatPress={onNewChatPress} />
    </View>
  );
}
