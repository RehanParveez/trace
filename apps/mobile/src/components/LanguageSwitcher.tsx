import { Pressable, StyleSheet, Text, View } from "react-native";
import { useTranslation } from "react-i18next";
import { changeAppLanguage, type AppLanguage } from "../i18n";

const options: { code: AppLanguage; label: string }[] = [
  { code: "en", label: "EN" },
  { code: "ur", label: "اردو" },
];

export default function LanguageSwitcher() {
  const { i18n } = useTranslation();
  const activeLanguage = i18n.resolvedLanguage === "ur" ? "ur" : "en";

  return (
    <View
      style={styles.pill}
      accessibilityRole="radiogroup"
      accessibilityLabel="Language"
    >
      {options.map(({ code, label }) => {
        const selected = activeLanguage === code;

        return (
          <Pressable
            key={code}
            onPress={() => void changeAppLanguage(code)}
            accessibilityRole="radio"
            accessibilityLabel={code === "en" ? "English" : "اردو"}
            accessibilityState={{ selected }}
            style={[styles.option, selected && styles.selectedOption]}
          >
            <Text style={[styles.label, selected && styles.selectedLabel]}>
              {label}
            </Text>
          </Pressable>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  pill: {flexDirection: "row", alignItems: "center", padding: 3, borderRadius: 99, borderWidth: 1, borderColor: "#E4D9C4", backgroundColor: "#FFFFFF",},
  option: {minWidth: 38, minHeight: 34, alignItems: "center", justifyContent: "center", paddingHorizontal: 9, borderRadius: 99,},
  selectedOption: {backgroundColor: "#080D18",},
  label: {color: "#5C5347", fontSize: 11, fontWeight: "700",},
  selectedLabel: {color: "#FFFFFF",},
});