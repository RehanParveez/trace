import { Drawer } from "expo-router/drawer";
import { Link } from "expo-router";
import {
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { useState, type PropsWithChildren } from "react";
import { useTranslation } from "react-i18next";
import LanguageSwitcher from "../../components/LanguageSwitcher";

type NavigationRouteLike = {
  params?: Record<string, unknown>;
  state?: NavigationStateLike;
};

type NavigationStateLike = {
  index?: number;
  routes?: NavigationRouteLike[];
};

const projectModuleLinks = [
  ["navigation.projectOverview", "/projects/[projectId]"],
  ["navigation.manageProject", "/projects/[projectId]/manage"],
  ["navigation.projectTeam", "/projects/[projectId]/team"],
  ["navigation.milestones", "/projects/[projectId]/milestones"],
  ["navigation.drawingsBOQ", "/projects/[projectId]/drawings-boq"],
  [
    "navigation.progressVerification",
    "/projects/[projectId]/progress-verification",
  ],
  ["navigation.siteProgress", "/projects/[projectId]/site-progress"],
  ["navigation.sitePhotos", "/projects/[projectId]/site-photos"],
  ["navigation.labour", "/projects/[projectId]/labour"],
  ["navigation.subcontractors", "/projects/[projectId]/subcontractors"],
  ["navigation.bankGuarantees", "/projects/[projectId]/bank-guarantees"],
  ["navigation.changeOrders", "/projects/[projectId]/change-orders"],
  ["navigation.budget", "/projects/[projectId]/budgets"],
] as const;

function getActiveProjectId(
  state: NavigationStateLike,
): string | undefined {
  let currentState: NavigationStateLike | undefined = state;
  let projectId: string | undefined;

  while (currentState?.routes?.length) {
    const route: NavigationRouteLike | undefined =
      currentState.routes[currentState.index ?? 0];

    const candidate = route?.params?.projectId;
    const normalizedCandidate = Array.isArray(candidate)
      ? candidate.find(
          (value): value is string =>
            typeof value === "string" && value.trim().length > 0,
        )
      : typeof candidate === "string" && candidate.trim().length > 0
        ? candidate
        : undefined;

    if (normalizedCandidate) {
      projectId = normalizedCandidate.trim();
    }

    currentState = route?.state;
  }

  return projectId;
}

export default function AuthenticatedLayout() {
  const { t } = useTranslation();

  return (
    <Drawer
      drawerContent={(props) => (
        <ModuleMenu
          navigationState={props.state as NavigationStateLike}
        />
      )}
      screenOptions={{
        headerShown: true,
        headerTitle: t("navigation.brand"),
        headerStyle: { backgroundColor: "#FFFFFF" },
        headerTintColor: COLORS.navy,
        headerTitleStyle: { fontWeight: "800" },
        drawerType: "front",
        drawerStyle: { backgroundColor: COLORS.surface, width: 300 },
        sceneStyle: { backgroundColor: COLORS.background },
      }}
    >
      <Drawer.Screen
        name="projects"
        options={{
          title: t("navigation.projects"),
          drawerLabel: t("navigation.projects"),
        }}
      />

      <Drawer.Screen
        name="organization"
        options={{
          title: t("navigation.organization"),
          drawerLabel: t("navigation.organization"),
        }}
      />

      <Drawer.Screen
        name="labour"
        options={{
          title: t("navigation.labourDirectory"),
          drawerLabel: t("navigation.labourDirectory"),
        }}
      />

      <Drawer.Screen
        name="bank-guarantees"
        options={{
          title: t("navigation.bankGuarantees"),
          drawerLabel: t("navigation.bankGuarantees"),
        }}
      />

      <Drawer.Screen
        name="change-orders"
        options={{
          title: t("navigation.changeOrders"),
          drawerLabel: t("navigation.changeOrders"),
        }}
      />

      <Drawer.Screen
        name="budgets"
        options={{
          title: t("navigation.budgets"),
          drawerLabel: t("navigation.budgets"),
        }}
      />

      <Drawer.Screen
        name="expenses"
        options={{
          title: t("navigation.expenses"),
          drawerLabel: t("navigation.expenses"),
        }}
      />

      <Drawer.Screen
        name="ai_requests"
        options={{
          title: t("navigation.aiRequests"),
          drawerLabel: t("navigation.aiRequests"),
        }}
      />

      <Drawer.Screen
        name="notifications"
        options={{
          title: t("navigation.notifications"),
          drawerLabel: t("navigation.notifications"),
        }}
      />

      <Drawer.Screen
        name="audit"
        options={{
          title: t("navigation.auditLog"),
          drawerLabel: t("navigation.auditLog"),
        }}
      />
    </Drawer>
  );
}

function ModuleMenu({
  navigationState,
}: {
  navigationState: NavigationStateLike;
}) {
  const { t, i18n } = useTranslation();
  const isUrdu = i18n.resolvedLanguage === "ur";
  const projectId = getActiveProjectId(navigationState);

  type MenuGroupKey =
    | "workspace"
    | "projectModules"
    | "activity"
    | "organization";

  const [expanded, setExpanded] = useState<
    Record<MenuGroupKey, boolean>
  >({
    workspace: true,
    projectModules: true,
    activity: true,
    organization: true,
  });

  function toggleGroup(group: MenuGroupKey) {
    setExpanded((current) => ({
      ...current,
      [group]: !current[group],
    }));
  }

  return (
    <ScrollView contentContainerStyle={styles.menu}>
      <View style={[styles.menuBrandRow, isUrdu && styles.rtlRow]}>
        <Text style={[styles.brand, isUrdu && styles.rtlText]}>
          {t("navigation.brand").toUpperCase()}
        </Text>
        <LanguageSwitcher />
      </View>

      <MenuGroup
        title={t("navigation.workspace")}
        expanded={expanded.workspace}
        onPress={() => toggleGroup("workspace")}
        isUrdu={isUrdu}
      >
        <MenuLink
          href="/projects"
          label={t("navigation.projects")}
          isUrdu={isUrdu}
        />
        <MenuLink
          href="/labour"
          label={t("navigation.labourDirectory")}
          isUrdu={isUrdu}
        />
        <MenuLink
          href="/subcontractors"
          label={t("navigation.subcontractorDirectory")}
          isUrdu={isUrdu}
        />
      </MenuGroup>

      <MenuGroup
        title={t("navigation.projectModules")}
        expanded={expanded.projectModules}
        onPress={() => toggleGroup("projectModules")}
        isUrdu={isUrdu}
      >
        <MenuLink
          href="/bank-guarantees"
          label={t("navigation.bankGuaranteesAllProjects")}
          isUrdu={isUrdu}
        />
        <MenuLink
          href="/change-orders"
          label={t("navigation.changeOrdersAllProjects")}
          isUrdu={isUrdu}
        />
        <MenuLink
          href="/budgets"
          label={t("navigation.budgetsAllProjects")}
          isUrdu={isUrdu}
        />
        <MenuLink
          href="/expenses"
          label={t("navigation.expensesAllProjects")}
          isUrdu={isUrdu}
        />

        {projectId ? (
          projectModuleLinks.map(([labelKey, pathname]) => (
            <MenuLink
              key={labelKey}
              href={{ pathname, params: { projectId } } as any}
              label={t(labelKey)}
              isUrdu={isUrdu}
            />
          ))
        ) : (
          <View style={styles.note}>
            <Text style={[styles.noteText, isUrdu && styles.rtlText]}>
              {t("navigation.chooseProjectHelp")}
            </Text>
            <MenuLink
              href="/projects"
              label={t("navigation.chooseProject")}
              isUrdu={isUrdu}
            />
          </View>
        )}
      </MenuGroup>

      <MenuGroup
        title={t("navigation.activity")}
        expanded={expanded.activity}
        onPress={() => toggleGroup("activity")}
        isUrdu={isUrdu}
      >
        <MenuLink
          href="/ai_requests"
          label={t("navigation.aiRequests")}
          isUrdu={isUrdu}
        />
        <MenuLink
          href="/notifications"
          label={t("navigation.notifications")}
          isUrdu={isUrdu}
        />
        <MenuLink
          href="/audit"
          label={t("navigation.auditLog")}
          isUrdu={isUrdu}
        />
      </MenuGroup>

      <MenuGroup
        title={t("navigation.organizationGroup")}
        expanded={expanded.organization}
        onPress={() => toggleGroup("organization")}
        isUrdu={isUrdu}
      >
        <MenuLink
          href="/organization"
          label={t("navigation.overview")}
          isUrdu={isUrdu}
        />
        <MenuLink
          href="/organization/settings"
          label={t("navigation.settings")}
          isUrdu={isUrdu}
        />
        <MenuLink
          href="/organization/members"
          label={t("navigation.members")}
          isUrdu={isUrdu}
        />
        <MenuLink
          href="/organization/roles"
          label={t("navigation.rolesAccess")}
          isUrdu={isUrdu}
        />
        <MenuLink
          href="/organization/invitations"
          label={t("navigation.invitations")}
          isUrdu={isUrdu}
        />
        <MenuLink
          href="/organization/subscription"
          label={t("navigation.subscription")}
          isUrdu={isUrdu}
        />
      </MenuGroup>
    </ScrollView>
  );
}

function MenuGroup({
  title,
  expanded,
  onPress,
  isUrdu,
  children,
}: PropsWithChildren<{
  title: string;
  expanded: boolean;
  onPress: () => void;
  isUrdu: boolean;
}>) {
  return (
    <View style={styles.group}>
      <Pressable
        style={[styles.groupHeader, isUrdu && styles.rtlRow]}
        onPress={onPress}
        accessibilityRole="button"
        accessibilityState={{ expanded }}
      >
        <Text style={[styles.caption, isUrdu && styles.rtlText]}>
          {title}
        </Text>
        <Text style={styles.groupChevron}>
          {expanded ? "⌃" : "⌄"}
        </Text>
      </Pressable>

      {expanded ? <View>{children}</View> : null}
    </View>
  );
}

function MenuLink({
  href,
  label,
  isUrdu,
}: {
  href: any;
  label: string;
  isUrdu: boolean;
}) {
  return (
    <Link href={href} asChild>
      <Pressable
        style={StyleSheet.flatten([
         styles.menuItem,
         isUrdu ? styles.rtlRow : undefined,
        ])}
        accessibilityRole="button"
        accessibilityLabel={label}
      >
        <Text style={[styles.menuItemText, isUrdu && styles.rtlText]}>
          {label}
        </Text>
        <Text style={styles.chevron}>{isUrdu ? "‹" : "›"}</Text>
      </Pressable>
    </Link>
  );
}

const COLORS = {
  background: "#F3EEE4",
  surface: "#FFFFFF",
  navy: "#080D18",
  text: "#171C26",
  muted: "#81776A",
  border: "#E4D9C4",
  gold: "#C7952D",
};

const styles = StyleSheet.create({
  menu: {
    flexGrow: 1,
    paddingHorizontal: 18,
    paddingTop: 54,
    paddingBottom: 30,
    backgroundColor: COLORS.surface,
  },
  menuBrandRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 12,
  },
  rtlRow: {
    flexDirection: "row-reverse",
  },
  rtlText: {
    textAlign: "right",
    writingDirection: "rtl",
  },
  brand: {
    color: COLORS.navy,
    fontSize: 19,
    fontWeight: "900",
    letterSpacing: 1.3,
  },
  group: {
    marginTop: 22,
  },
  groupHeader: {
    minHeight: 40,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  caption: {
    flex: 1,
    color: COLORS.muted,
    fontSize: 11,
    fontWeight: "800",
    letterSpacing: 1.1,
    marginTop: 8,
    marginBottom: 8,
  },
  groupChevron: {
    color: COLORS.gold,
    fontSize: 20,
    fontWeight: "700",
  },
  menuItem: {
    minHeight: 48,
    borderRadius: 10,
    paddingHorizontal: 13,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 10,
  },
  menuItemText: {
    flex: 1,
    color: COLORS.text,
    fontSize: 14,
    fontWeight: "600",
  },
  chevron: {
    color: COLORS.gold,
    fontSize: 22,
  },
  note: {
    backgroundColor: "#F7F3EC",
    borderRadius: 10,
    padding: 12,
    marginTop: 4,
  },
  noteText: {
    color: COLORS.muted,
    fontSize: 12,
    lineHeight: 18,
  },
});