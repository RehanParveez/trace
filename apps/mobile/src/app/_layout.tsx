import { useEffect, useState } from "react";
import {ActivityIndicator, Text, View,
} from "react-native";
import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { i18nReady } from "../i18n";

export default function RootLayout() {
  const [languageReady, setLanguageReady] = useState(false);

  useEffect(() => {
    let mounted = true;

    void i18nReady.finally(() => {
      if (mounted) setLanguageReady(true);
    });

    return () => {
      mounted = false;
    };
  }, []);

  if (!languageReady) {
    return (
      <View
        style={{
          flex: 1,
          alignItems: "center",
          justifyContent: "center",
          backgroundColor: "#F3EEE4",
          gap: 10,
        }}
      >
        <ActivityIndicator size="large" color="#080D18" />
        <Text style={{ color: "#5C5347" }}>Loading…</Text>
      </View>
    );
  }

  return (
    <>
      <StatusBar style="dark" />
      <Stack screenOptions={{ headerShown: false }}>
        <Stack.Screen name="index" />
        <Stack.Screen name="register" />
        <Stack.Screen name="verify-email" />
        <Stack.Screen name="forgot-password" />
        <Stack.Screen name="reset-password" />
        <Stack.Screen name="(app)" />
      </Stack>
    </>
  );
}