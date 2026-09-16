import { useCallback, useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import {
  Paper, Title, Text, Badge, Group, Stack, Select, Button, Loader, Center, Grid,
  SimpleGrid, Image, FileButton,
} from "@mantine/core";
import { IconUpload } from "@tabler/icons-react";
import { notifications } from "@mantine/notifications";
import { api, uploadFile } from "../lib/apiClient";
import { useAuth } from "../hooks/useAuth";
import { useHostels } from "../hooks/useHostels";
import { MAINTENANCE_STATUS_COLOR, MAINTENANCE_STATUS_LABEL, MAINTENANCE_PRIORITY_COLOR, humanize } from "../lib/labels";
import type { MaintenancePhoto, MaintenancePriority, MaintenanceStatus, MaintenanceTicket } from "../types";

export function MaintenanceDetailPage() {
  const { ticketId } = useParams<{ ticketId: string }>();
  const { profile } = useAuth();
  const { hostels } = useHostels();
  const [ticket, setTicket] = useState<MaintenanceTicket | null>(null);
  const [photos, setPhotos] = useState<MaintenancePhoto[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const resetRef = useRef<() => void>(null);

  const canEdit = profile?.role === "admin" || profile?.role === "maintenance";

  const load = useCallback(() => {
    if (!ticketId) return;
    setLoading(true);
    Promise.all([
      api.get<MaintenanceTicket>(`/maintenance-tickets/${ticketId}`),
      api.get<MaintenancePhoto[]>(`/maintenance-tickets/${ticketId}/photos`),
    ]).then(([t, p]) => { setTicket(t); setPhotos(p); }).finally(() => setLoading(false));
  }, [ticketId]);

  useEffect(() => { load(); }, [load]);

  const updateField = async (field: "status" | "priority", value: string) => {
    if (!ticketId) return;
    setSaving(true);
    try {
      const updated = await api.patch<MaintenanceTicket>(`/maintenance-tickets/${ticketId}`, { [field]: value });
      setTicket(updated);
    } finally {
      setSaving(false);
    }
  };

  const handlePhotoUpload = async (files: File[]) => {
    if (!ticketId || files.length === 0) return;
    setUploading(true);
    try {
      for (const file of files) {
        await uploadFile<MaintenancePhoto>(`/maintenance-tickets/${ticketId}/photos`, file);
      }
      notifications.show({ title: "Photos uploaded", message: `${files.length} photo(s) added.`, color: "green" });
      const p = await api.get<MaintenancePhoto[]>(`/maintenance-tickets/${ticketId}/photos`);
      setPhotos(p);
    } catch (err) {
      notifications.show({
        title: "Upload failed",
        message: err instanceof Error ? err.message : "Could not upload one or more photos.",
        color: "red",
      });
    } finally {
      setUploading(false);
      resetRef.current?.();
    }
  };

  if (loading || !ticket) return <Center h={300}><Loader /></Center>;

  const hostelName = hostels.find((h) => h.id === ticket.hostel_id)?.name ?? ticket.hostel_id;

  return (
    <Stack gap="md">
      <Group justify="space-between">
        <div>
          <Title order={2}>{ticket.title}</Title>
          <Text c="dimmed" size="sm">{hostelName}</Text>
        </div>
        <Group>
          <Badge color={MAINTENANCE_PRIORITY_COLOR[ticket.priority]}>{humanize(ticket.priority)}</Badge>
          <Badge color={MAINTENANCE_STATUS_COLOR[ticket.status]}>{MAINTENANCE_STATUS_LABEL[ticket.status]}</Badge>
        </Group>
      </Group>

      <Grid>
        <Grid.Col span={{ base: 12, md: 7 }}>
          <Paper withBorder p="md" radius="md">
            <Stack gap="sm">
              <Text fw={600}>Description</Text>
              <Text size="sm">{ticket.description}</Text>
              <Text size="xs" c="dimmed">Reported {new Date(ticket.created_at).toLocaleString()}</Text>
              {ticket.resolved_at && (
                <Text size="xs" c="dimmed">Resolved {new Date(ticket.resolved_at).toLocaleString()}</Text>
              )}
            </Stack>
          </Paper>

          {canEdit && (
            <Paper withBorder p="md" radius="md" mt="md">
              <Text fw={600} mb="sm">Update</Text>
              <Group grow>
                <Select
                  label="Status"
                  data={Object.entries(MAINTENANCE_STATUS_LABEL).map(([value, label]) => ({ value, label }))}
                  value={ticket.status} disabled={saving}
                  onChange={(v) => v && updateField("status", v as MaintenanceStatus)}
                />
                <Select
                  label="Priority"
                  data={["low", "medium", "high", "urgent"].map((v) => ({ value: v, label: humanize(v) }))}
                  value={ticket.priority} disabled={saving}
                  onChange={(v) => v && updateField("priority", v as MaintenancePriority)}
                />
              </Group>
            </Paper>
          )}
        </Grid.Col>

        <Grid.Col span={{ base: 12, md: 5 }}>
          <Paper withBorder p="md" radius="md">
            <Group justify="space-between" mb="sm">
              <Text fw={600}>Photos</Text>
              {canEdit && (
                <FileButton resetRef={resetRef} onChange={handlePhotoUpload} accept="image/png,image/jpeg,image/webp,image/heic" multiple>
                  {(props) => (
                    <Button {...props} size="xs" variant="light" leftSection={<IconUpload size={14} />} loading={uploading}>
                      Upload photo(s)
                    </Button>
                  )}
                </FileButton>
              )}
            </Group>
            {photos.length === 0 && <Text size="sm" c="dimmed">No photos uploaded yet.</Text>}
            <SimpleGrid cols={2}>
              {photos.map((p) => (
                <Image key={p.id} src={p.url} radius="sm" h={120} fit="cover" alt="Maintenance issue photo" />
              ))}
            </SimpleGrid>
          </Paper>
        </Grid.Col>
      </Grid>
    </Stack>
  );
}
