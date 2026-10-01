import { Stack, useLocalSearchParams } from "expo-router";
import { Text, View } from "react-native";
import { ExpensesModuleScreen } from "../../../../../components/ExpensesModuleScreen";

export default function ProjectExpensesRoute() {
  const params = useLocalSearchParams<{ projectId?: string | string[] }>();
  const projectId = Array.isArray(params.projectId)
    ? params.projectId[0]
    : params.projectId;

  if (!projectId) {
    return (
      <View style={{ flex: 1, justifyContent: "center", padding: 24 }}>
        <Stack.Screen options={{ title: "Expenses" }} />
        <Text>Project ID is missing.</Text>
      </View>
    );
  }

  return <ExpensesModuleScreen projectId={projectId} />;
}