import { useCallback, useEffect, useState } from "react";
import {ActivityIndicator, FlatList, Image, Modal, Pressable, RefreshControl, StyleSheet, Text, TextInput, View,
} from "react-native";
import { useLocalSearchParams, Stack } from "expo-router";
import { useFocusEffect } from "expo-router";
import {listSitePhotos, getSitePhoto, updateSitePhoto, addPhotoTag, removePhotoTag,
} from "../../../../api/sitePhotos";
import type { AuthUser, SitePhoto, PhotoTag } from "../../../../api/types";
import { restoreSession } from "../../../../api/client";

function hasPermission(
  user: AuthUser | null,
  key: string
): boolean {
  const perms = user?.role?.permissions ?? [];
  return perms.some((p) => p.key === key);
}

export default function ProjectSitePhotosScreen() {
  const { projectId } = useLocalSearchParams<{ projectId: string }>();

  const [user, setUser] = useState<AuthUser | null>(null);
  const [authLoading, setAuthLoading] = useState(true);

  const [photos, setPhotos] = useState<SitePhoto[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<SitePhoto | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const canManage = hasPermission(user, "site_photo.manage");
  const canRead = hasPermission(user, "site_photo.read");

  useFocusEffect(
    useCallback(() => {
      let cancelled = false;

      const restore = async () => {
        try {
          const restoredUser = await restoreSession();

          if (!cancelled) {
            setUser(restoredUser);
            setAuthLoading(false);
          }
        } catch {
          if (!cancelled) {
            setUser(null);
            setAuthLoading(false);
          }
        }
      };

      restore();

      return () => {
        cancelled = true;
      };
    }, [])
  );

  const load = useCallback(
    async (isRefresh = false) => {
      if (!projectId || !canRead) return;

      if (isRefresh) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }

      setError(null);

      try {
        const data = await listSitePhotos({
          project_id: projectId,
          skip: 0,
          limit: 100,
        });

        setPhotos(data);
      } catch (e: any) {
        setError(e?.message ?? "Failed to load site photos");
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [projectId, canRead]
  );

  useFocusEffect(
    useCallback(() => {
      if (!authLoading && canRead) {
        load();
      }
    }, [authLoading, canRead, load])
  );

  const openDetail = async (photo: SitePhoto) => {
    setSelected(photo);
    setDetailLoading(true);

    try {
      const fresh = await getSitePhoto(photo.id);
      setSelected(fresh);
    } catch {
    } finally {
      setDetailLoading(false);
    }
  };

  const onImageError = async (photo: SitePhoto) => {
    try {
      const fresh = await getSitePhoto(photo.id);

      setPhotos((prev) =>
        prev.map((p) => (p.id === photo.id ? fresh : p))
      );

      if (selected?.id === photo.id) {
        setSelected(fresh);
      }
    } catch {
    }
  };

  if (authLoading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" />
      </View>
    );
  }

  if (!canRead) {
    return (
      <View style={styles.centered}>
        <Text>You don't have permission to view site photos.</Text>
      </View>
    );
  }

  return (
    <>
      <Stack.Screen options={{ title: "Site Photos" }} />

      {loading ? (
        <View style={styles.centered}>
          <ActivityIndicator size="large" />
        </View>
      ) : error ? (
        <View style={styles.centered}>
          <Text style={styles.error}>{error}</Text>

          <Pressable
            style={styles.button}
            onPress={() => load()}
          >
            <Text style={styles.buttonText}>Retry</Text>
          </Pressable>
        </View>
      ) : (
        <FlatList
          data={photos}
          keyExtractor={(item) => item.id}
          contentContainerStyle={
            photos.length === 0
              ? styles.centered
              : styles.list
          }
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={() => load(true)}
            />
          }
          ListEmptyComponent={
            <Text style={styles.empty}>
              No site photos for this project yet.
            </Text>
          }
          renderItem={({ item }) => (
            <Pressable
              style={styles.card}
              onPress={() => openDetail(item)}
            >
              <Image
                source={{ uri: item.photo_url }}
                style={styles.thumb}
                onError={() => onImageError(item)}
              />

              <View style={styles.cardBody}>
                <Text style={styles.meta}>
                  {item.photo_date ??
                    item.created_at.slice(0, 10)}
                </Text>

                {item.location_text ? (
                  <Text numberOfLines={1}>
                    {item.location_text}
                  </Text>
                ) : null}

                {item.caption_raw ? (
                  <Text
                    numberOfLines={2}
                    style={styles.caption}
                  >
                    {item.caption_raw}
                  </Text>
                ) : null}

                {item.sender_phone_number ? (
                  <Text style={styles.meta}>
                    From: {item.sender_phone_number}
                  </Text>
                ) : null}

                <View style={styles.tagRow}>
                  {item.tags.map((t: PhotoTag) => (
                    <View
                      key={t.id}
                      style={styles.tag}
                    >
                      <Text style={styles.tagText}>
                        {t.tag}
                      </Text>
                    </View>
                  ))}
                </View>
              </View>
            </Pressable>
          )}
        />
      )}

      <PhotoDetailModal
        photo={selected}
        loading={detailLoading}
        canManage={canManage}
        onClose={() => setSelected(null)}
        onUpdated={(updated) => {
          setSelected(updated);

          setPhotos((prev) =>
            prev.map((p) =>
              p.id === updated.id ? updated : p
            )
          );
        }}
        onImageError={() =>
          selected && onImageError(selected)
        }
      />
    </>
  );
}

function PhotoDetailModal({
  photo,
  loading,
  canManage,
  onClose,
  onUpdated,
  onImageError,
}: {
  photo: SitePhoto | null;
  loading: boolean;
  canManage: boolean;
  onClose: () => void;
  onUpdated: (p: SitePhoto) => void;
  onImageError: () => void;
}) {
  const [location, setLocation] = useState("");
  const [photoDate, setPhotoDate] = useState("");
  const [newTag, setNewTag] = useState("");
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (photo) {
      setLocation(photo.location_text ?? "");
      setPhotoDate(photo.photo_date ?? "");
      setNewTag("");
      setErr(null);
    }
  }, [photo?.id]);

  if (!photo) {
    return null;
  }

  const saveMeta = async () => {
    setSaving(true);
    setErr(null);

    try {
      const updated = await updateSitePhoto(photo.id, {
        location_text: location.trim() || null,
        photo_date: photoDate.trim() || null,
      });

      onUpdated(updated);
    } catch (e: any) {
      setErr(e?.message ?? "Update failed");
    } finally {
      setSaving(false);
    }
  };

  const addTag = async () => {
    const tag = newTag.trim();

    if (!tag) {
      return;
    }

    setSaving(true);
    setErr(null);

    try {
      await addPhotoTag(photo.id, tag);

      const fresh = await getSitePhoto(photo.id);

      onUpdated(fresh);
      setNewTag("");
    } catch (e: any) {
      setErr(e?.message ?? "Could not add tag");
    } finally {
      setSaving(false);
    }
  };

  const removeTag = async (tag: PhotoTag) => {
    setSaving(true);
    setErr(null);

    try {
      await removePhotoTag(photo.id, tag.id);

      const fresh = await getSitePhoto(photo.id);

      onUpdated(fresh);
    } catch (e: any) {
      setErr(e?.message ?? "Could not remove tag");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal
      visible
      animationType="slide"
      onRequestClose={onClose}
    >
      <View style={styles.modal}>
        <Pressable
          onPress={onClose}
          style={styles.closeBtn}
        >
          <Text style={styles.buttonText}>Close</Text>
        </Pressable>

        {loading ? (
          <ActivityIndicator />
        ) : (
          <>
            <Image
              source={{ uri: photo.photo_url }}
              style={styles.fullImage}
              onError={onImageError}
            />

            <Text style={styles.meta}>
              {photo.sender_phone_number
                ? `From ${photo.sender_phone_number}`
                : "No sender"}
            </Text>

            {photo.caption_raw ? (
              <Text style={styles.caption}>
                {photo.caption_raw}
              </Text>
            ) : null}

            {canManage ? (
              <View style={styles.form}>
                <Text style={styles.label}>
                  Location
                </Text>

                <TextInput
                  style={styles.input}
                  value={location}
                  onChangeText={setLocation}
                  placeholder="Location"
                />

                <Text style={styles.label}>
                  Photo date (YYYY-MM-DD)
                </Text>

                <TextInput
                  style={styles.input}
                  value={photoDate}
                  onChangeText={setPhotoDate}
                  placeholder="2025-01-15"
                />

                <Pressable
                  style={[
                    styles.button,
                    saving && styles.disabled,
                  ]}
                  onPress={saveMeta}
                  disabled={saving}
                >
                  <Text style={styles.buttonText}>
                    Save
                  </Text>
                </Pressable>

                <Text style={styles.label}>
                  Tags
                </Text>

                <View style={styles.tagRow}>
                  {photo.tags.map((t: PhotoTag) => (
                    <Pressable
                      key={t.id}
                      style={styles.tag}
                      onPress={() => removeTag(t)}
                    >
                      <Text style={styles.tagText}>
                        {t.tag} ×
                      </Text>
                    </Pressable>
                  ))}
                </View>

                <View style={styles.row}>
                  <TextInput
                    style={[
                      styles.input,
                      { flex: 1 },
                    ]}
                    value={newTag}
                    onChangeText={setNewTag}
                    placeholder="New tag"
                  />

                  <Pressable
                    style={[
                      styles.button,
                      saving && styles.disabled,
                    ]}
                    onPress={addTag}
                    disabled={saving}
                  >
                    <Text style={styles.buttonText}>
                      Add
                    </Text>
                  </Pressable>
                </View>
              </View>
            ) : (
              <View style={styles.tagRow}>
                {photo.tags.map((t: PhotoTag) => (
                  <View
                    key={t.id}
                    style={styles.tag}
                  >
                    <Text style={styles.tagText}>
                      {t.tag}
                    </Text>
                  </View>
                ))}
              </View>
            )}

            {err ? (
              <Text style={styles.error}>{err}</Text>
            ) : null}
          </>
        )}
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  centered: {flex: 1, justifyContent: "center", alignItems: "center", padding: 24,},
  list: {padding: 12,},
  card: {flexDirection: "row", backgroundColor: "#fff", borderRadius: 8, marginBottom: 12, overflow: "hidden", elevation: 1,},
  thumb: {width: 96, height: 96, backgroundColor: "#eee",},
  cardBody: {flex: 1, padding: 10,},
  meta: {fontSize: 12, color: "#666", marginBottom: 2,},
  caption: {fontSize: 13, color: "#333",},
  tagRow: {flexDirection: "row", flexWrap: "wrap", gap: 6, marginTop: 6,},
  tag: {backgroundColor: "#e8f0fe", paddingHorizontal: 8, paddingVertical: 4, borderRadius: 12,},
  tagText: {fontSize: 12, color: "#1a73e8",},
  empty: {textAlign: "center", color: "#666",},
  error: {color: "#c00", marginVertical: 8,},
  button: {backgroundColor: "#1a73e8", paddingHorizontal: 16, paddingVertical: 10, borderRadius: 8, marginTop: 8,},
  buttonText: {color: "#fff", fontWeight: "600",},
  disabled: {opacity: 0.5,},
  modal: {flex: 1, padding: 16, backgroundColor: "#fff",},
  closeBtn: {alignSelf: "flex-end", backgroundColor: "#1a73e8", padding: 10, borderRadius: 8, marginBottom: 8,},
  fullImage: {width: "100%", height: 280, backgroundColor: "#eee", borderRadius: 8,},
  form: {marginTop: 12,},
  label: {fontSize: 13, fontWeight: "600",marginTop: 8,},
  input: {borderWidth: 1, borderColor: "#ccc", borderRadius: 8, padding: 10, marginTop: 4,},
  row: {flexDirection: "row", alignItems: "center", gap: 8, marginTop: 8,},
});