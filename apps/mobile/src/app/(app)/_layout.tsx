import { Drawer } from "expo-router/drawer";
import { Link } from "expo-router";
import {Pressable, ScrollView, StyleSheet, Text, View,
} from "react-native";

export default function AuthenticatedLayout() {
  return (
    <Drawer
      drawerContent={() => <ModuleMenu />}
      screenOptions={{
        headerShown: true,
        headerTitle: "Trace",
        headerStyle: { backgroundColor: "#FFFFFF" },
        headerTintColor: "#183153",
        headerTitleStyle: { fontWeight: "800" },
        drawerType: "front",
        drawerStyle: { backgroundColor: "#FFFFFF", width: 300 },
        sceneStyle: { backgroundColor: "#F4F6F8" },
      }}
    >
      <Drawer.Screen
        name="projects"
        options={{ title: "Projects", drawerLabel: "Projects" }}
      />
      <Drawer.Screen
        name="organization"
        options={{ title: "Organization", drawerLabel: "Organization" }}
      />
    </Drawer>
  );
}

function ModuleMenu() {
  return (
    <ScrollView contentContainerStyle={styles.menu}>
      <Text style={styles.brand}>TRACE</Text>
      <Text style={styles.caption}>WORKSPACE</Text>

      <MenuLink href="/projects" label="Projects" />

      <Text style={styles.caption}>ORGANIZATION</Text>
      <MenuLink href="/organization" label="Organization overview" />

      <View style={styles.note}>
        <Text style={styles.noteText}>
          Organization settings, members, roles, and invitations will each get
          their own screen under this section.
        </Text>
      </View>
    </ScrollView>
  );
}

function MenuLink({
  href,
  label,
}: {
  href: "/projects" | "/organization";
  label: string;
}) {
  return (
    <Link href={href} asChild>
      <Pressable style={styles.menuItem} accessibilityRole="button">
        <Text style={styles.menuItemText}>{label}</Text>
        <Text style={styles.chevron}>›</Text>
      </Pressable>
    </Link>
  );
}

const styles = StyleSheet.create({
  menu: { flexGrow: 1, paddingHorizontal: 18, paddingTop: 58, paddingBottom: 30 },
  brand: { color: "#183153", fontSize: 19, fontWeight: "900", letterSpacing: 1.3 },
  caption: { color: "#8A7B67", fontSize: 11, fontWeight: "800", letterSpacing: 1.2, marginTop: 30, marginBottom: 8 },
  menuItem: { minHeight: 48, borderRadius: 10, paddingHorizontal: 13, flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  menuItemText: { color: "#17212F", fontSize: 15, fontWeight: "600" },
  chevron: { color: "#8A7B67", fontSize: 22 },
  note: { backgroundColor: "#F4F6F8", borderRadius: 10, padding: 12, marginTop: 16 },
  noteText: { color: "#667085", fontSize: 12, lineHeight: 18 },
});