import { useState } from "react";
import { router } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { HomeScreenContent } from "@/components/home";
import { HOME_EXERCISES } from "@/lib/placeholder-exercises";

export default function Index() {
  const [isLoading] = useState(false);

  return (
    <>
      <HomeScreenContent
        homeExercises={HOME_EXERCISES}
        isLoading={isLoading}
        onExercisePress={(exerciseId) => router.push(`/exercises/player/${exerciseId}`)}
        onLibraryPress={() => router.push("/exercises")}
        onNewChatPress={() => router.push({ pathname: "/chat", params: { requestNewThread: "true" } })}
      />
      <StatusBar style="light" />
    </>
  );
}
