import { useCallback, useEffect, useState } from "react";
import { ActivityIndicator, Alert, KeyboardAvoidingView, Platform, Pressable, ScrollView, Text, View } from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import { useTranslation } from "react-i18next";
import { restoreSession } from "../../../../api/client";
import { listProjectDrawings } from "../../../../api/drawingsBoq";
import {deleteSpace, deleteSpaceFinish, getFinishPreview, getSpace, listDrawingElements, listWorkItems, setSpaceBoundaries, setSpaceFinish, updateSpace,
} from "../../../../api/spaces";
import type {DrawingElement, FinishPreview, SpaceDetail, Surface, WorkItem,
} from "../../../../api/types";
import LanguageSwitcher from "../../../../components/LanguageSwitcher";
import { describeError } from "../../../../features/drawingsBoq/errors";
import { PERM, hasPerm } from "../../../../features/drawingsBoq/permissions";
import { Action, Badge, COLORS, Field, InfoRow, formatNumber, ui } from "../../../../features/drawingsBoq/ui";

const SURFACES: Surface[] = ["FLOOR", "WALL", "CEILING", "SKIRTING", "DADO"];
const MAX_SHOWN = 40;

function first(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

const mm2ToM2 = (v: number | string | null) => (v == null ? "" : String(Number(v) / 1_000_000));
const mmToM = (v: number | string | null) => (v == null ? "" : String(Number(v) / 1000));

function positive(raw: string): number | undefined | "bad" {
  const text = raw.trim();
  if (!text) return undefined;
  const value = Number(text);
  return Number.isFinite(value) && value > 0 ? value : "bad";
}

type Panel = "" | "edit" | "finish" | "boundaries" | "preview";

export default function SpaceDetailScreen() {
  const { t, i18n } = useTranslation();
  const isUrdu = i18n.resolvedLanguage === "ur";
  const tx = (key: string, defaultValue: string, vars?: Record<string, unknown>) =>
    t(key, { defaultValue, ...vars }) as string;

  const params = useLocalSearchParams<{ projectId?: string; spaceId?: string }>();
  const projectId = first(params.projectId);
  const spaceId = first(params.spaceId);

  const [permissions, setPermissions] = useState<string[]>([]);
  const [space, setSpace] = useState<SpaceDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [panel, setPanel] = useState<Panel>("");

  const [edit, setEdit] = useState({ number: "", name: "", category: "", usage: "", area: "", perimeter: "", height: "" });

  const [surface, setSurface] = useState<Surface>("FLOOR");
  const [workItems, setWorkItems] = useState<WorkItem[] | null>(null);
  const [search, setSearch] = useState("");
  const [chosen, setChosen] = useState<WorkItem | null>(null);
  const [finishName, setFinishName] = useState("");
  const [finishHeight, setFinishHeight] = useState("");

  const [elements, setElements] = useState<DrawingElement[] | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [elementSearch, setElementSearch] = useState("");

  const [ruleSet, setRuleSet] = useState("");
  const [preview, setPreview] = useState<FinishPreview | null>(null);
  const [openLine, setOpenLine] = useState(-1);

  const canManage = hasPerm(permissions, PERM.SPACE_MANAGE);
  const canFinish = hasPerm(permissions, PERM.FINISH_MANAGE);
  const canCalc = hasPerm(permissions, PERM.CALC_RUN);

  const load = useCallback(
    async (silent = false) => {
      if (!spaceId) {
        setError(tx("spaceDetail.notFound", "Room not found."));
        setLoading(false);
        return;
      }
      if (!silent) setLoading(true);
      try {
        const user = await restoreSession();
        if (!user) {
          router.replace("/");
          return;
        }
        setPermissions(user.role.permissions.map((p) => p.key));
        const detail = await getSpace(spaceId);
        setSpace(detail);
        setSelected(new Set(detail.boundaries.map((b) => b.element_id)));
      } catch (err) {
        setError(describeError(err, tx("spaceDetail.loadFailure", "Could not load the room.")));
      } finally {
        setLoading(false);
      }
    },
    [spaceId],
  );

  useEffect(() => {
    void load();
  }, [load]);

  async function act(action: () => Promise<unknown>, done?: string) {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await action();
      await load(true);
      if (done) setNotice(done);
    } catch (err) {
      setError(describeError(err, tx("spaceDetail.actionFailure", "Action failed.")));
    } finally {
      setBusy(false);
    }
  }

  function openPanel(next: Panel) {
    if (panel === next) {
      setPanel("");
      return;
    }
    setPanel(next);
    if (next === "edit" && space) {
      setEdit({
        number: space.number ?? "",
        name: space.name ?? "",
        category: space.category,
        usage: space.usage_text ?? "",
        area: mm2ToM2(space.net_floor_area_mm2),
        perimeter: mmToM(space.perimeter_mm),
        height: mmToM(space.height_mm),
      });
    }
    if (next === "finish" && workItems === null) {
      listWorkItems()
        .then((items) => setWorkItems(items.filter((i) => i.is_active)))
        .catch((err) => setError(describeError(err, tx("spaceDetail.itemsFailure", "Could not load work items."))));
    }
    if (next === "boundaries" && elements === null && space) void loadElements();
  }

  async function loadElements() {
    if (!space || !projectId) return;
    try {
      let drawingId = space.drawing_id;
      if (!drawingId) {
        const drawings = await listProjectDrawings(projectId);
        drawingId = drawings.find((d) => d.format === "IFC" && d.is_current_revision)?.id ?? null;
      }
      setElements(drawingId ? await listDrawingElements(drawingId) : []);
    } catch (err) {
      setError(describeError(err, tx("spaceDetail.elementsFailure", "Could not load model elements.")));
      setElements([]);
    }
  }

  async function handleSaveEdit() {
    if (!space) return;
    const area = positive(edit.area);
    const perimeter = positive(edit.perimeter);
    const height = positive(edit.height);
    if (area === "bad" || perimeter === "bad" || height === "bad") {
      setError(tx("spaceDetail.badNumber", "Area, perimeter and height must be numbers above zero."));
      return;
    }
    await act(async () => {
      await updateSpace(space.id, {
        number: edit.number.trim() || undefined,
        name: edit.name.trim() || undefined,
        category: edit.category.trim() || undefined,
        usage_text: edit.usage.trim() || undefined,
        floor_area_m2: area,
        perimeter_m: perimeter,
        height_m: height,
      });
      setPanel("");
    }, tx("spaceDetail.saved", "Room saved."));
  }

  async function handleToggleActive() {
    if (!space) return;
    await act(() => updateSpace(space.id, { is_active: !space.is_active }));
  }

  function handleDelete() {
    if (!space) return;
    Alert.alert(tx("spaceDetail.deleteTitle", "Delete this room?"), tx("spaceDetail.deleteBody", "Its finishes and boundaries are removed too."), [
      { text: tx("drawingsBoq.cancel", "Cancel"), style: "cancel" },
      {
        text: tx("spaceDetail.delete", "Delete room"),
        style: "destructive",
        onPress: () => {
          setBusy(true);
          deleteSpace(space.id)
            .then(() => router.back())
            .catch((err) => setError(describeError(err, tx("spaceDetail.actionFailure", "Action failed."))))
            .finally(() => setBusy(false));
        },
      },
    ]);
  }

  async function handleAddFinish() {
    if (!space || !chosen) {
      setError(tx("spaceDetail.chooseItem", "Choose a work item first."));
      return;
    }
    const height = positive(finishHeight);
    if (height === "bad") {
      setError(tx("spaceDetail.badHeight", "Height must be a number above zero."));
      return;
    }
    await act(async () => {
      await setSpaceFinish(space.id, {
        surface,
        work_item_code: chosen.code,
        finish_name: finishName.trim() || undefined,
        height_mm: height,
      });
      setChosen(null);
      setFinishName("");
      setFinishHeight("");
      setSearch("");
      setPanel("");
    }, tx("spaceDetail.finishSaved", "Finish saved. Run a new calculation to include it."));
  }

  function handleDeleteFinish(finishId: string) {
    Alert.alert(tx("spaceDetail.removeFinishTitle", "Remove this finish?"), "", [
      { text: tx("drawingsBoq.cancel", "Cancel"), style: "cancel" },
      {
        text: tx("spaceDetail.removeFinish", "Remove"),
        style: "destructive",
        onPress: () => void act(() => deleteSpaceFinish(finishId)),
      },
    ]);
  }

  async function handleSaveBoundaries() {
    if (!space) return;
    await act(
      () => setSpaceBoundaries(space.id, Array.from(selected)),
      tx("spaceDetail.boundariesSaved", "Boundaries saved."),
    );
  }

  async function handlePreview() {
    if (!space) return;
    setBusy(true);
    setError("");
    try {
      setPreview(await getFinishPreview(space.id, ruleSet));
      setOpenLine(-1);
    } catch (err) {
      setPreview(null);
      setError(describeError(err, tx("spaceDetail.previewFailure", "Could not preview the finishes.")));
    } finally {
      setBusy(false);
    }
  }

  function toggleElement(id: string) {
    setSelected((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  if (loading) {
    return (
      <View style={ui.center}>
        <ActivityIndicator size="large" color={COLORS.navy} />
      </View>
    );
  }

  const candidates = (workItems ?? [])
    .filter((item) => {
      const q = search.trim().toLowerCase();
      return !q || item.code.toLowerCase().includes(q) || item.description.toLowerCase().includes(q);
    })
    .slice(0, 20);

  const shownElements = (elements ?? [])
    .filter((el) => {
      const q = elementSearch.trim().toLowerCase();
      if (!q) return true;
      return (el.name ?? "").toLowerCase().includes(q) || el.ifc_type.toLowerCase().includes(q);
    })
    .sort((a, b) => Number(selected.has(b.id)) - Number(selected.has(a.id)))
    .slice(0, MAX_SHOWN);

  const title = space ? [space.number, space.name].filter(Boolean).join(" · ") || space.long_name || "-" : "";

  return (
    <KeyboardAvoidingView style={ui.flex} behavior={Platform.OS === "ios" ? "padding" : undefined}>
      <ScrollView contentContainerStyle={ui.page} keyboardShouldPersistTaps="handled">
        <View style={[ui.headerRow, isUrdu && ui.rtlRow]}>
          <View style={ui.headerCopy}>
            <Pressable onPress={() => router.back()}>
              <Text style={[ui.link, isUrdu && ui.rtlText]}>{tx("spaceDetail.back", "Back to rooms")}</Text>
            </Pressable>
            <Text style={[ui.title, isUrdu && ui.rtlText]}>{title}</Text>
          </View>
          <LanguageSwitcher />
        </View>

        {error ? <Text style={[ui.error, isUrdu && ui.rtlText]}>{error}</Text> : null}
        {notice ? <Text style={[ui.notice, isUrdu && ui.rtlText]}>{notice}</Text> : null}

        {space ? (
          <>
            <View style={ui.summaryBox}>
              <InfoRow label={tx("spaceDetail.category", "Category")} value={space.category} isUrdu={isUrdu} />
              <InfoRow label={tx("spaceDetail.source", "Source")} value={space.source} isUrdu={isUrdu} />
              <InfoRow label={tx("spaceDetail.area", "Floor area")} value={space.net_floor_area_mm2 == null ? "-" : `${formatNumber(Number(space.net_floor_area_mm2) / 1_000_000, 2)} m²`} isUrdu={isUrdu} />
              <InfoRow label={tx("spaceDetail.perimeter", "Perimeter")} value={space.perimeter_mm == null ? "-" : `${formatNumber(Number(space.perimeter_mm) / 1000, 2)} m`} isUrdu={isUrdu} />
              <InfoRow label={tx("spaceDetail.height", "Height")} value={space.height_mm == null ? "-" : `${formatNumber(Number(space.height_mm) / 1000, 2)} m`} isUrdu={isUrdu} />
              <InfoRow label={tx("spaceDetail.state", "State")} value={space.is_active ? tx("spaceDetail.active", "Active") : tx("spaceDetail.inactive", "Inactive")} isUrdu={isUrdu} />
            </View>

            {space.normalization_issues.map((issue, index) => (
              <Text key={index} style={[ui.muted, isUrdu && ui.rtlText]}>
                {`${issue.severity ?? "warning"}: ${issue.message ?? issue.code ?? ""}`}
              </Text>
            ))}

            <View style={[ui.row, isUrdu && ui.rtlRow]}>
              {canManage ? (
                <>
                  <Action title={tx("spaceDetail.editRoom", "Edit room")} secondary={panel !== "edit"} isUrdu={isUrdu} onPress={() => openPanel("edit")} />
                  <Action title={tx("spaceDetail.boundaries", "Boundaries")} secondary={panel !== "boundaries"} isUrdu={isUrdu} onPress={() => openPanel("boundaries")} />
                </>
              ) : null}
              <Action title={tx("spaceDetail.preview", "Preview finishes")} secondary={panel !== "preview"} isUrdu={isUrdu} onPress={() => openPanel("preview")} />
              {canCalc && projectId ? (
                <Action
                  title={tx("spaceDetail.runCalculation", "Run calculation")}
                  secondary
                  isUrdu={isUrdu}
                  onPress={() => router.push({ pathname: "/projects/[projectId]/calculation", params: { projectId } })}
                />
              ) : null}
            </View>

            {panel === "edit" ? (
              <View style={ui.panel}>
                <Field label={tx("spaces.number", "Room number")} value={edit.number} onChangeText={(v) => setEdit((e) => ({ ...e, number: v }))} isUrdu={isUrdu} />
                <Field label={tx("spaces.name", "Name")} value={edit.name} onChangeText={(v) => setEdit((e) => ({ ...e, name: v }))} isUrdu={isUrdu} />
                <Field label={tx("spaces.category", "Category (for example BEDROOM)")} value={edit.category} onChangeText={(v) => setEdit((e) => ({ ...e, category: v }))} isUrdu={isUrdu} />
                <Field label={tx("spaceDetail.usage", "Usage")} value={edit.usage} onChangeText={(v) => setEdit((e) => ({ ...e, usage: v }))} isUrdu={isUrdu} />
                <Field label={tx("spaces.area", "Floor area (m²)")} value={edit.area} onChangeText={(v) => setEdit((e) => ({ ...e, area: v }))} keyboardType="decimal-pad" isUrdu={isUrdu} />
                <Field label={tx("spaces.perimeter", "Perimeter (m)")} value={edit.perimeter} onChangeText={(v) => setEdit((e) => ({ ...e, perimeter: v }))} keyboardType="decimal-pad" isUrdu={isUrdu} />
                <Field label={tx("spaces.height", "Height (m)")} value={edit.height} onChangeText={(v) => setEdit((e) => ({ ...e, height: v }))} keyboardType="decimal-pad" isUrdu={isUrdu} />
                <View style={[ui.row, isUrdu && ui.rtlRow]}>
                  <Action title={tx("spaceDetail.save", "Save")} disabled={busy} isUrdu={isUrdu} onPress={() => void handleSaveEdit()} />
                  <Action
                    title={space.is_active ? tx("spaceDetail.deactivate", "Mark inactive") : tx("spaceDetail.activate", "Mark active")}
                    secondary
                    disabled={busy}
                    isUrdu={isUrdu}
                    onPress={() => void handleToggleActive()}
                  />
                  <Action title={tx("spaceDetail.delete", "Delete room")} secondary disabled={busy} isUrdu={isUrdu} onPress={handleDelete} />
                </View>
              </View>
            ) : null}

            {panel === "boundaries" ? (
              <View style={ui.panel}>
                <Text style={[ui.muted, isUrdu && ui.rtlText]}>
                  {tx("spaceDetail.boundaryHelp", "Choose the walls and slabs that enclose this room. {{count}} selected.", { count: selected.size })}
                </Text>
                <Field label={tx("spaceDetail.searchElements", "Search model elements")} value={elementSearch} onChangeText={setElementSearch} isUrdu={isUrdu} />
                {elements === null ? <ActivityIndicator color={COLORS.navy} /> : null}
                {elements !== null && shownElements.length === 0 ? (
                  <Text style={[ui.muted, isUrdu && ui.rtlText]}>{tx("spaceDetail.noElements", "No model elements found.")}</Text>
                ) : null}
                {shownElements.map((el) => (
                  <Pressable key={el.id} style={ui.boqItem} onPress={() => toggleElement(el.id)} accessibilityRole="checkbox">
                    <View style={[ui.heading, isUrdu && ui.rtlRow]}>
                      <Text style={[ui.itemTitle, isUrdu && ui.rtlText]}>{el.name || el.ifc_type}</Text>
                      <Badge label={selected.has(el.id) ? tx("spaceDetail.selected", "Selected") : tx("spaceDetail.notSelected", "Not selected")} tone={selected.has(el.id) ? "good" : "neutral"} />
                    </View>
                    <Text style={[ui.muted, isUrdu && ui.rtlText]}>{`${el.ifc_type}${el.structural_role ? ` · ${el.structural_role}` : ""}`}</Text>
                  </Pressable>
                ))}
                {elements !== null && elements.length > MAX_SHOWN ? (
                  <Text style={[ui.muted, isUrdu && ui.rtlText]}>
                    {tx("spaceDetail.narrow", "Showing the first {{count}}. Type in the search box to narrow the list.", { count: MAX_SHOWN })}
                  </Text>
                ) : null}
                <Action title={tx("spaceDetail.saveBoundaries", "Save boundaries")} disabled={busy} isUrdu={isUrdu} onPress={() => void handleSaveBoundaries()} />
              </View>
            ) : null}

            {panel === "preview" ? (
              <View style={ui.panel}>
                <Field label={tx("spaceDetail.ruleSet", "Rule set code (optional)")} value={ruleSet} onChangeText={setRuleSet} isUrdu={isUrdu} />
                <Action title={tx("spaceDetail.runPreview", "Preview quantities")} disabled={busy} isUrdu={isUrdu} onPress={() => void handlePreview()} />
                {preview ? (
                  <>
                    <Text style={[ui.muted, isUrdu && ui.rtlText]}>
                      {tx("spaceDetail.ruleSetUsed", "Rule set {{code}}", { code: preview.rule_set_code })}
                    </Text>
                    {preview.lines.length === 0 ? (
                      <Text style={[ui.muted, isUrdu && ui.rtlText]}>
                        {tx("spaceDetail.noLines", "No finish quantities. Add a finish to a surface, or check the room's area.")}
                      </Text>
                    ) : null}
                    {preview.lines.map((line, index) => (
                      <Pressable key={index} style={ui.boqItem} onPress={() => setOpenLine(openLine === index ? -1 : index)}>
                        <View style={[ui.heading, isUrdu && ui.rtlRow]}>
                          <Text style={[ui.itemTitle, isUrdu && ui.rtlText]}>{`${line.surface} · ${line.work_item_code}`}</Text>
                          <Badge label={`${formatNumber(line.quantity, 3)} ${line.unit}`} tone="good" />
                        </View>
                        <Text style={[ui.muted, isUrdu && ui.rtlText]}>
                          {`${line.formula_code} · ${line.source_kind} · ${tx("spaceDetail.confidence", "confidence {{value}}", { value: formatNumber(line.confidence, 2) })}`}
                        </Text>
                        {line.warnings.map((warning, w) => (
                          <Text key={w} style={[ui.error, isUrdu && ui.rtlText]}>{warning}</Text>
                        ))}
                        {openLine === index
                          ? line.steps.map((step, s) => (
                              <Text key={s} style={[ui.muted, isUrdu && ui.rtlText]}>{JSON.stringify(step)}</Text>
                            ))
                          : null}
                      </Pressable>
                    ))}
                    {Object.keys(preview.skipped).length > 0 ? (
                      <Text style={[ui.muted, isUrdu && ui.rtlText]}>
                        {tx("spaceDetail.skipped", "Skipped: {{details}}", { details: JSON.stringify(preview.skipped) })}
                      </Text>
                    ) : null}
                  </>
                ) : null}
              </View>
            ) : null}

            <Text style={[ui.section, isUrdu && ui.rtlText]}>{tx("spaceDetail.finishes", "Finishes")}</Text>
            {space.finishes.length === 0 ? (
              <Text style={[ui.muted, isUrdu && ui.rtlText]}>{tx("spaceDetail.noFinishes", "No finishes set on this room.")}</Text>
            ) : null}
            {space.finishes.map((finish) => (
              <View key={finish.id} style={ui.boqItem}>
                <View style={[ui.heading, isUrdu && ui.rtlRow]}>
                  <Text style={[ui.itemTitle, isUrdu && ui.rtlText]}>{`${finish.surface} · ${finish.work_item_code}`}</Text>
                  <Badge label={finish.review_status} tone={finish.review_status === "OK" ? "good" : "warn"} />
                </View>
                <Text style={[ui.muted, isUrdu && ui.rtlText]}>
                  {[finish.finish_name, finish.height_mm != null ? `${formatNumber(finish.height_mm, 0)} mm` : null, finish.source]
                    .filter(Boolean)
                    .join(" · ")}
                </Text>
                {canFinish ? (
                  <Action title={tx("spaceDetail.removeFinish", "Remove")} secondary disabled={busy} isUrdu={isUrdu} onPress={() => handleDeleteFinish(finish.id)} />
                ) : null}
              </View>
            ))}

            {canFinish ? (
              <Action title={tx("spaceDetail.addFinish", "Add or change a finish")} secondary={panel !== "finish"} isUrdu={isUrdu} onPress={() => openPanel("finish")} />
            ) : null}

            {panel === "finish" ? (
              <View style={ui.panel}>
                <Text style={[ui.label, isUrdu && ui.rtlText]}>{tx("spaceDetail.surface", "Surface")}</Text>
                <View style={[ui.row, isUrdu && ui.rtlRow]}>
                  {SURFACES.map((value) => (
                    <Action key={value} title={tx(`spaceDetail.surface.${value.toLowerCase()}`, value)} secondary={surface !== value} isUrdu={isUrdu} onPress={() => setSurface(value)} />
                  ))}
                </View>
                {chosen ? (
                  <Text style={[ui.itemTitle, isUrdu && ui.rtlText]}>{`${chosen.code} · ${chosen.description} (${chosen.unit})`}</Text>
                ) : null}
                <Field label={tx("spaceDetail.searchItems", "Search work items")} value={search} onChangeText={setSearch} isUrdu={isUrdu} />
                {workItems === null ? <ActivityIndicator color={COLORS.navy} /> : null}
                {candidates.map((item) => (
                  <Pressable key={item.id} style={ui.boqItem} onPress={() => setChosen(item)}>
                    <Text style={[ui.itemTitle, isUrdu && ui.rtlText]}>{`${item.code} · ${item.unit}`}</Text>
                    <Text style={[ui.muted, isUrdu && ui.rtlText]}>{item.description}</Text>
                  </Pressable>
                ))}
                <Field label={tx("spaceDetail.finishName", "Finish name (optional)")} value={finishName} onChangeText={setFinishName} isUrdu={isUrdu} />
                {surface === "WALL" || surface === "SKIRTING" || surface === "DADO" ? (
                  <Field label={tx("spaceDetail.finishHeight", "Height (mm, optional)")} value={finishHeight} onChangeText={setFinishHeight} keyboardType="decimal-pad" isUrdu={isUrdu} />
                ) : null}
                <Action title={tx("spaceDetail.saveFinish", "Save finish")} disabled={busy} isUrdu={isUrdu} onPress={() => void handleAddFinish()} />
              </View>
            ) : null}
          </>
        ) : null}

        {busy ? (
          <View style={ui.busy}>
            <ActivityIndicator color={COLORS.navy} />
          </View>
        ) : null}
      </ScrollView>
    </KeyboardAvoidingView>
  );
}