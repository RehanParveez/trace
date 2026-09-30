import { Stack, router, useLocalSearchParams } from "expo-router";
import { Text, View } from "react-native";
import { BankGuaranteesScreen } from "../../../../../components/_BankGuaranteesScreen";

export default function ProjectBankGuaranteesRoute() {
  const params = useLocalSearchParams<{ projectId?: string }>();
  const projectId = Array.isArray(params.projectId)
    ? params.projectId[0]
    : params.projectId;

  if (!projectId) {
    return (
      <View style={{ flex: 1, justifyContent: "center", padding: 24 }}>
        <Stack.Screen options={{ title: "Bank guarantees" }} />
        <Text>Project ID is missing.</Text>
        <Text onPress={() => router.back()} style={{ marginTop: 12, color: "#183153" }}>
          Go back
        </Text>
      </View>
    );
  }

  return <BankGuaranteesScreen projectId={projectId} />;
}