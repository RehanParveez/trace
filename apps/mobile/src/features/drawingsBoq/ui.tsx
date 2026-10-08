import { Pressable, StyleSheet, Text, TextInput, View } from "react-native";

export const COLORS = {
  background: "#F3EEE4",
  surface: "#FFFFFF",
  surfaceMuted: "#F7F3EC",
  navy: "#080D18",
  text: "#171C26",
  secondary: "#5C5347",
  muted: "#81776A",
  border: "#E4D9C4",
  gold: "#C7952D",
  red: "#A63A32",
  redBackground: "#FBEAE7",
  green: "#287456",
  greenBackground: "#E6F3EC",
  amber: "#9B641A",
  amberBackground: "#FBF1DD",
};

export function formatMoney(
  value: number | string | null | undefined,
  locale: string,
  notAvailable: string,
) {
  if (value === null || value === undefined) return notAvailable;
  const amount = Number(value);
  if (!Number.isFinite(amount)) return String(value);
  return new Intl.NumberFormat(locale, {
    style: "currency",
    currency: "PKR",
    maximumFractionDigits: 0,
  }).format(amount);
}

export function formatNumber(
  value: number | string | null | undefined,
  digits = 3,
): string {
  if (value === null || value === undefined) return "-";
  const n = Number(value);
  if (!Number.isFinite(n)) return String(value);
  return n.toLocaleString("en-US", { maximumFractionDigits: digits });
}

export function Action(props: {
  title: string;
  onPress: () => void;
  secondary?: boolean;
  disabled?: boolean;
  isUrdu: boolean;
}) {
  return (
    <Pressable
      style={[
        ui.action,
        props.secondary && ui.actionSecondary,
        props.disabled && ui.disabled,
      ]}
      onPress={props.onPress}
      disabled={props.disabled}
      accessibilityRole="button"
    >
      <Text
        style={[
          ui.actionText,
          props.secondary && ui.actionSecondaryText,
          props.isUrdu && ui.rtlText,
        ]}
      >
        {props.title}
      </Text>
    </Pressable>
  );
}

export function Field(props: {
  label: string;
  value: string;
  onChangeText: (value: string) => void;
  keyboardType?: "default" | "decimal-pad";
  editable?: boolean;
  multiline?: boolean;
  isUrdu: boolean;
}) {
  return (
    <>
      <Text style={[ui.fieldLabel, props.isUrdu && ui.rtlText]}>{props.label}</Text>
      <TextInput
        style={[ui.input, props.multiline && ui.inputMultiline, props.isUrdu && ui.rtlText]}
        value={props.value}
        onChangeText={props.onChangeText}
        keyboardType={props.keyboardType ?? "default"}
        editable={props.editable ?? true}
        multiline={props.multiline}
        textAlign={props.isUrdu ? "right" : "left"}
      />
    </>
  );
}

export function InfoRow(props: { label: string; value: string; isUrdu: boolean }) {
  return (
    <View style={[ui.infoRow, props.isUrdu && ui.rtlRow]}>
      <Text style={[ui.infoLabel, props.isUrdu && ui.rtlText]}>{props.label}</Text>
      <Text style={[ui.infoValue, props.isUrdu && ui.rtlText]}>{props.value}</Text>
    </View>
  );
}

export function Badge(props: {
  label: string;
  tone?: "neutral" | "good" | "warn" | "bad";
}) {
  const tone = props.tone ?? "neutral";
  return (
    <View
      style={[
        ui.badge,
        tone === "good" && ui.badgeGood,
        tone === "warn" && ui.badgeWarn,
        tone === "bad" && ui.badgeBad,
      ]}
    >
      <Text
        style={[
          ui.badgeText,
          tone === "good" && { color: COLORS.green },
          tone === "warn" && { color: COLORS.amber },
          tone === "bad" && { color: COLORS.red },
        ]}
      >
        {props.label}
      </Text>
    </View>
  );
}

export const ui = StyleSheet.create({
  flex: { flex: 1, backgroundColor: COLORS.background },
  page: { flexGrow: 1, padding: 20, paddingTop: 24, paddingBottom: 38, gap: 10, backgroundColor: COLORS.background },
  center: { flex: 1, alignItems: "center", justifyContent: "center", gap: 12, padding: 24, backgroundColor: COLORS.background },
  headerRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", gap: 12, marginBottom: 8 },
  headerCopy: { flex: 1 },
  rtlRow: { flexDirection: "row-reverse" },
  rtlText: { textAlign: "right", writingDirection: "rtl" },
  title: { color: COLORS.text, fontSize: 26, fontWeight: "800", marginTop: 10 },
  section: { color: COLORS.text, fontSize: 18, fontWeight: "800", marginTop: 18, marginBottom: 2 },
  label: { color: COLORS.secondary, fontSize: 12, fontWeight: "700", marginTop: 10, marginBottom: 4 },
  fieldLabel: { color: COLORS.secondary, fontSize: 12, fontWeight: "700", marginTop: 10, marginBottom: 5 },
  input: { minHeight: 46, backgroundColor: COLORS.surface, borderColor: COLORS.border, borderWidth: 1, borderRadius: 10, paddingHorizontal: 12, paddingVertical: 10, fontSize: 14, color: COLORS.text },
  inputMultiline: { minHeight: 80, textAlignVertical: "top" },
  card: { backgroundColor: COLORS.surface, borderRadius: 14, borderWidth: 1, borderColor: COLORS.border, borderTopColor: COLORS.gold, borderTopWidth: 2, padding: 15, marginTop: 8 },
  itemTitle: { flex: 1, color: COLORS.text, fontSize: 14, fontWeight: "800", marginRight: 8 },
  muted: { color: COLORS.muted, fontSize: 13, marginTop: 5, lineHeight: 20 },
  error: { color: COLORS.red, backgroundColor: COLORS.redBackground, borderColor: "#EAC6C0", borderWidth: 1, borderRadius: 11, padding: 12, marginTop: 8, lineHeight: 19, fontSize: 13 },
  notice: { color: COLORS.green, backgroundColor: COLORS.greenBackground, borderColor: "#BFE0CE", borderWidth: 1, borderRadius: 11, padding: 12, marginTop: 8, lineHeight: 19, fontSize: 13 },
  link: { color: COLORS.navy, fontWeight: "800", fontSize: 13 },
  heading: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 10 },
  summaryBox: { backgroundColor: COLORS.surfaceMuted, borderWidth: 1, borderColor: COLORS.border, borderRadius: 11, paddingHorizontal: 12, paddingTop: 4, marginTop: 10 },
  boqItem: { borderTopWidth: 1, borderTopColor: COLORS.border, paddingVertical: 12 },
  panel: { backgroundColor: COLORS.surfaceMuted, borderWidth: 1, borderColor: COLORS.border, borderRadius: 11, padding: 12, marginTop: 8 },
  infoRow: { flexDirection: "row", justifyContent: "space-between", gap: 12, paddingVertical: 8, borderTopWidth: 1, borderTopColor: COLORS.border },
  infoLabel: { color: COLORS.muted, fontSize: 12, flex: 1 },
  infoValue: { color: COLORS.text, fontSize: 13, fontWeight: "700", flex: 1, textAlign: "right" },
  action: { minHeight: 44, flexGrow: 1, backgroundColor: COLORS.navy, borderWidth: 1, borderColor: COLORS.navy, borderRadius: 10, alignItems: "center", justifyContent: "center", paddingHorizontal: 13, paddingVertical: 11, marginTop: 8 },
  actionSecondary: { backgroundColor: COLORS.surface, borderColor: COLORS.border },
  actionText: { color: COLORS.surface, fontWeight: "800", fontSize: 13, textAlign: "center" },
  actionSecondaryText: { color: COLORS.navy },
  disabled: { opacity: 0.5 },
  row: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  pagination: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 8, marginTop: 8 },
  pageText: { color: COLORS.secondary, fontSize: 12, fontWeight: "700", textAlign: "center" },
  busy: { alignItems: "center", padding: 18, gap: 8 },
  badge: { alignSelf: "flex-start", backgroundColor: COLORS.surfaceMuted, borderColor: COLORS.border, borderWidth: 1, borderRadius: 999, paddingHorizontal: 9, paddingVertical: 3 },
  badgeGood: { backgroundColor: COLORS.greenBackground, borderColor: "#BFE0CE" },
  badgeWarn: { backgroundColor: COLORS.amberBackground, borderColor: "#EBD3A4" },
  badgeBad: { backgroundColor: COLORS.redBackground, borderColor: "#EAC6C0" },
  badgeText: { color: COLORS.secondary, fontSize: 11, fontWeight: "800" },
  progressTrack: { height: 10, backgroundColor: COLORS.surfaceMuted, borderRadius: 999, borderWidth: 1, borderColor: COLORS.border, overflow: "hidden", marginTop: 10 },
  progressFill: { height: "100%", backgroundColor: COLORS.navy },
});