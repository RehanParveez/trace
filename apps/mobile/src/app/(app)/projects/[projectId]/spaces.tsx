import { useCallback, useState } from "react";
import { ActivityIndicator, KeyboardAvoidingView, Platform, Pressable, ScrollView, Text, View } from "react-native";
import { router, useFocusEffect, useLocalSearchParams } from "expo-router";
import { useTranslation } from "react-i18next";
import { restoreSession } from "../../../../api/client";
import { listProjectDrawings } from "../../../../api/drawingsBoq";
import { createSpace, listDrawingLevels, listSpaces } from "../../../../api/spaces";
import type { BuildingLevel, Space } from "../../../../api/types";
import LanguageSwitcher from "../../../../components/LanguageSwitcher";
import { describeError } from "../../../../features/drawingsBoq/errors";
import { PERM, hasPerm } from "../../../../features/drawingsBoq/permissions";
import { Action, Badge, COLORS, Field, formatNumber, ui } from "../../../../features/drawingsBoq/ui";

function first(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

function m2(value: number | string | null) {
  return value == null ? "-" : formatNumber(Number(value) / 1_000_000, 2);
}

function tone(status: string): "neutral" | "good" | "warn" | "bad" {
  if (status === "VALID") return "good";
  if (status === "INVALID") return "bad";
  if (status === "WARNING") return "warn";
  return "neutral";
}

const EMPTY = { number: "", name: "", category: "", area: "", perimeter: "", height: "" };

export default function SpacesScreen() {
  const { t, i18n } = useTranslation();
  const isUrdu = i18n.resolvedLanguage === "ur";
  const tx = (key: string, defaultValue: string, vars?: Record<string, unknown>) =>
    t(key, { defaultValue, ...vars }) as string;

  const params = useLocalSearchParams<{ projectId?: string }>();
  const projectId = first(params.projectId);

  const [permissions, setPermissions] = useState<string[]>([]);
  const [spaces, setSpaces] = useState<Space[]>([]);
  const [levels, setLevels] = useState<BuildingLevel[]>([]);
  const [levelId, setLevelId] = useState("");
  const [showInactive, setShowInactive] = useState(false);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [adding, setAdding] = useState(false);
  const [form, setForm] = useState(EMPTY);

  const canManage = hasPerm(permissions, PERM.SPACE_MANAGE);
  const levelName = (id: string | null) => levels.find((l) => l.id === id)?.name;

  const load = useCallback(async () => {
    if (!projectId) {
      setError(tx("spaces.projectMissing", "Project not found."));
      setLoading(false);
      return;
    }
    try {
      const user = await restoreSession();
      if (!user) {
        router.replace("/");
        return;
      }
      setPermissions(user.role.permissions.map((p) => p.key));

      const [list, drawings] = await Promise.all([
        listSpaces(projectId, { levelId: levelId || undefined, includeInactive: showInactive }),
        listProjectDrawings(projectId),
      ]);
      setSpaces(list);

      const models = drawings.filter((d) => d.format === "IFC" && d.is_current_revision);
      const lists = await Promise.all(models.map((d) => listDrawingLevels(d.id).catch(() => [])));
      setLevels(lists.flat().sort((a, b) => a.sequence - b.sequence));
      setError("");
    } catch (err) {
      setError(describeError(err, tx("spaces.loadFailure", "Could not load rooms.")));
    } finally {
      setLoading(false);
    }
  }, [projectId, levelId, showInactive]);

  useFocusEffect(
    useCallback(() => {
      void load();
    }, [load]),
  );

  function number(raw: string): number | undefined | "bad" {
    const text = raw.trim();
    if (!text) return undefined;
    const value = Number(text);
    return Number.isFinite(value) && value > 0 ? value : "bad";
  }

  async function handleCreate() {
    if (!projectId) return;
    if (!form.number.trim() && !form.name.trim()) {
      setError(tx("spaces.needsName", "Enter a room number or a name."));
      return;
    }
    const area = number(form.area);
    const perimeter = number(form.perimeter);
    const height = number(form.height);
    if (area === "bad" || perimeter === "bad" || height === "bad") {
      setError(tx("spaces.badNumber", "Area, perimeter and height must be numbers above zero."));
      return;
    }
    setBusy(true);
    setError("");
    try {
      const created = await createSpace(projectId, {
        number: form.number.trim() || undefined,
        name: form.name.trim() || undefined,
        category: form.category.trim() || undefined,
        level_id: levelId || undefined,
        floor_area_m2: area,
        perimeter_m: perimeter,
        height_m: height,
      });
      setAdding(false);
      setForm(EMPTY);
      router.push({
        pathname: "/projects/[projectId]/space-detail",
        params: { projectId, spaceId: created.id },
      });
    } catch (err) {
      setError(describeError(err, tx("spaces.createFailure", "Could not add the room.")));
    } finally {
      setBusy(false);
    }
  }

  if (loading) {
    return (
      <View style={ui.center}>
        <ActivityIndicator size="large" color={COLORS.navy} />
      </View>
    );
  }

  return (
    <KeyboardAvoidingView style={ui.flex} behavior={Platform.OS === "ios" ? "padding" : undefined}>
      <ScrollView contentContainerStyle={ui.page} keyboardShouldPersistTaps="handled">
        <View style={[ui.headerRow, isUrdu && ui.rtlRow]}>
          <View style={ui.headerCopy}>
            <Pressable onPress={() => router.back()}>
              <Text style={[ui.link, isUrdu && ui.rtlText]}>
                {tx("spaces.back", "Back to drawings & BOQ")}
              </Text>
            </Pressable>
            <Text style={[ui.title, isUrdu && ui.rtlText]}>{tx("spaces.title", "Rooms & finishes")}</Text>
          </View>
          <LanguageSwitcher />
        </View>

        {error ? <Text style={[ui.error, isUrdu && ui.rtlText]}>{error}</Text> : null}

        {levels.length > 0 ? (
          <View style={[ui.row, isUrdu && ui.rtlRow]}>
            <Action
              title={tx("spaces.allLevels", "All levels")}
              secondary={levelId !== ""}
              isUrdu={isUrdu}
              onPress={() => setLevelId("")}
            />
            {levels.map((level) => (
              <Action
                key={level.id}
                title={level.name}
                secondary={levelId !== level.id}
                isUrdu={isUrdu}
                onPress={() => setLevelId(level.id)}
              />
            ))}
          </View>
        ) : null}

        <View style={[ui.row, isUrdu && ui.rtlRow]}>
          <Action
            title={
              showInactive
                ? tx("spaces.hideInactive", "Hide inactive rooms")
                : tx("spaces.showInactive", "Show inactive rooms")
            }
            secondary
            isUrdu={isUrdu}
            onPress={() => setShowInactive((value) => !value)}
          />
          {canManage ? (
            <Action
              title={tx("spaces.add", "Add a room")}
              isUrdu={isUrdu}
              onPress={() => setAdding((value) => !value)}
            />
          ) : null}
        </View>

        {adding ? (
          <View style={ui.panel}>
            <Field label={tx("spaces.number", "Room number")} value={form.number} onChangeText={(v) => setForm((f) => ({ ...f, number: v }))} isUrdu={isUrdu} />
            <Field label={tx("spaces.name", "Name")} value={form.name} onChangeText={(v) => setForm((f) => ({ ...f, name: v }))} isUrdu={isUrdu} />
            <Field label={tx("spaces.category", "Category (for example BEDROOM)")} value={form.category} onChangeText={(v) => setForm((f) => ({ ...f, category: v }))} isUrdu={isUrdu} />
            <Field label={tx("spaces.area", "Floor area (m²)")} value={form.area} onChangeText={(v) => setForm((f) => ({ ...f, area: v }))} keyboardType="decimal-pad" isUrdu={isUrdu} />
            <Field label={tx("spaces.perimeter", "Perimeter (m)")} value={form.perimeter} onChangeText={(v) => setForm((f) => ({ ...f, perimeter: v }))} keyboardType="decimal-pad" isUrdu={isUrdu} />
            <Field label={tx("spaces.height", "Height (m)")} value={form.height} onChangeText={(v) => setForm((f) => ({ ...f, height: v }))} keyboardType="decimal-pad" isUrdu={isUrdu} />
            {levelId ? (
              <Text style={[ui.muted, isUrdu && ui.rtlText]}>
                {tx("spaces.onLevel", "It will be added to {{level}}.", { level: levelName(levelId) ?? "" })}
              </Text>
            ) : null}
            <View style={[ui.row, isUrdu && ui.rtlRow]}>
              <Action title={tx("spaces.save", "Add room")} disabled={busy} isUrdu={isUrdu} onPress={() => void handleCreate()} />
              <Action title={tx("drawingsBoq.cancel", "Cancel")} secondary isUrdu={isUrdu} onPress={() => { setAdding(false); setForm(EMPTY); }} />
            </View>
          </View>
        ) : null}

        {spaces.length === 0 ? (
          <Text style={[ui.muted, isUrdu && ui.rtlText]}>
            {tx("spaces.none", "No rooms yet. Rooms come from the IFC model, or you can add them by hand.")}
          </Text>
        ) : null}

        {spaces.map((space) => (
          <Pressable
            key={space.id}
            style={ui.card}
            accessibilityRole="button"
            onPress={() =>
              projectId &&
              router.push({
                pathname: "/projects/[projectId]/space-detail",
                params: { projectId, spaceId: space.id },
              })
            }
          >
            <View style={[ui.heading, isUrdu && ui.rtlRow]}>
              <Text style={[ui.itemTitle, isUrdu && ui.rtlText]}>
                {[space.number, space.name].filter(Boolean).join(" · ") || space.long_name || "-"}
              </Text>
              <Badge label={space.normalization_status} tone={tone(space.normalization_status)} />
            </View>
            <Text style={[ui.muted, isUrdu && ui.rtlText]}>
              {`${space.category} · ${m2(space.net_floor_area_mm2)} m²`}
              {levelName(space.level_id) ? ` · ${levelName(space.level_id)}` : ""}
              {space.is_active ? "" : ` · ${tx("spaces.inactive", "inactive")}`}
            </Text>
            <Text style={[ui.muted, isUrdu && ui.rtlText]}>
              {tx("spaces.counts", "{{finishes}} finishes · {{boundaries}} boundary elements", {
                finishes: space.finish_count,
                boundaries: space.boundary_count,
              })}
            </Text>
          </Pressable>
        ))}
      </ScrollView>
    </KeyboardAvoidingView>
  );
}