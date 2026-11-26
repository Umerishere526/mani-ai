// ABOUTME: Home screen route — the exercises the portal puts on the home screen (GET /v1/exercises/home), the
// ABOUTME: library link and the new-chat action, rendered by HomeScreenContent.

import { router } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { HomeScreenContent } from "@/components/home";
import { useLoad } from "@/hooks/useLoad";
import { getHomeExercises } from "@/lib/api/exercises";

export default function Index() {
  const home = useLoad("home", getHomeExercises);

  return (
    <>
      <HomeScreenContent
        homeExercises={home.data ?? []}
        isLoading={home.data === null && !home.failed}
        onExercisePress={(exerciseId) => router.push(`/exercises/player/${exerciseId}`)}
        onLibraryPress={() => router.push("/exercises")}
        onNewChatPress={() => router.push({ pathname: "/chat", params: { requestNewThread: "true" } })}
      />
      <StatusBar style="light" />
    </>
  );
}
