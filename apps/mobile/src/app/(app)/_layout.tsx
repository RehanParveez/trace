import { Drawer } from "expo-router/drawer";
import { Link } from "expo-router";
import {Pressable, ScrollView, StyleSheet, Text, View, 
} from "react-native";

type NavigationRouteLike = {
  params?: Record<string, unknown>;
  state?: NavigationStateLike;
};

type NavigationStateLike = {
  index?: number;
  routes?:  NavigationRouteLike[];
};

const projectModuleLinks = [
  ["Project overview", "/projects/[projectId]"],
  ["Manage project", "/projects/[projectId]/manage"],
  ["Project team", "/projects/[projectId]/team"],
  ["Milestones", "/projects/[projectId]/milestones"],
  ["Drawings & BOQ", "/projects/[projectId]/drawings-boq"],
  ["Progress verification", "/projects/[projectId]/progress-verification"],
  ["Site progress", "/projects/[projectId]/site-progress"],
  ["Site photos", "/projects/[projectId]/site-photos"],
  ["Labour", "/projects/[projectId]/labour"],
  ["Subcontractors", "/projects/[projectId]/subcontractors"],
  ["Bank guarantees", "/projects/[projectId]/bank-guarantees"],
  ["Change Orders", "/projects/[projectId]/change-orders"],
  ["Budget", "/projects/[projectId]/budgets"],
] as const;

function getActiveProjectId(
  state: NavigationStateLike,
): string | undefined {
  let currentState: NavigationStateLike | undefined = state;
  let projectId: unknown;

  while (currentState?.routes?.length) {
    const route: NavigationRouteLike | undefined =
      currentState.routes[currentState.index ?? 0];
    const candidate = route?.params?.projectId;

    if (typeof candidate === "string") {
      projectId = candidate;
    }

    currentState = route?.state;
  }

  return typeof projectId === "string" ? projectId : undefined;
}

export default function AuthenticatedLayout() {
  return (
    <Drawer
      drawerContent={(props) => (
       <ModuleMenu navigationState={props.state as NavigationStateLike} /> 
      )}
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
      <Drawer.Screen
        name="labour"
        options={{ title: "Labour directory", drawerLabel: "Labour" }}
       />
      <Drawer.Screen
        name="bank-guarantees"
        options={{ title: "Bank guarantees", drawerLabel: "Bank guarantees" }}
      />
      <Drawer.Screen
        name="change-orders"
        options={{ title: "Change Orders", drawerLabel: "Change Orders" }}
      />
      <Drawer.Screen
        name="budgets"
        options={{ title: "Budgets", drawerLabel: "Budgets" }}
      />

      <Drawer.Screen
        name="expenses"
        options={{ title: "Expenses", drawerLabel: "Expenses" }}
      />

    </Drawer>  
  );
}

function ModuleMenu({
  navigationState,
}: {
  navigationState: NavigationStateLike;
}) {
  const projectId = getActiveProjectId(navigationState);

  return (
    <ScrollView contentContainerStyle={styles.menu}>
      <Text style={styles.brand}>TRACE</Text>

      <Text style={styles.caption}>WORKSPACE</Text>
      <MenuLink href="/projects" label="Projects" />
      <MenuLink href="/labour" label="Labour directory" />

      <Text style={styles.caption}>PROJECT MODULES</Text>

      <MenuLink href="/bank-guarantees" label="Bank guarantees · all projects" />
      <MenuLink href="/change-orders" label="Change Orders · all projects" />
      <MenuLink href="/budgets" label="Budgets · all projects" />
      <MenuLink href="/expenses" label="Expenses · all projects" />

      {projectId ? (
        projectModuleLinks.map(([label, pathname]) => (
          <MenuLink
            key={label}
            href={{
              pathname,
              params: { projectId },
            } as any}
            label={label}
          />
        ))
      ) : (
        <View style={styles.note}>
          <Text style={styles.noteText}>
            Open a project to see its team, milestones, drawings, progress,
            photos, labour, subcontractor, guarantee, change-order, and budget
            screens here.
          </Text>
          <MenuLink href="/projects" label="Choose a project" />
        </View>
      )}

      <Text style={styles.caption}>ORGANIZATION</Text>
      <MenuLink href="/organization" label="Overview" />
      <MenuLink href="/organization/settings" label="Settings" />
      <MenuLink href="/organization/members" label="Members" />
      <MenuLink href="/organization/roles" label="Roles and access" />
      <MenuLink href="/organization/invitations" label="Invitations" />
      <MenuLink href="/organization/subscription" label="Subscription" />
    </ScrollView>
  );
};

function MenuLink({
  href,
  label,
}: {
  href: any;
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