import { useState } from "react";
import {
  Title, Paper, Table, Badge, Stack, Group, Button, Modal, TextInput, Text,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconPlus, IconRefresh } from "@tabler/icons-react";
import { useDisclosure } from "@mantine/hooks";
import { api } from "../lib/apiClient";
import { useAuth } from "../hooks/useAuth";
import { useHostels } from "../hooks/useHostels";
import type { Hostel } from "../types";

const PMS_STATUS_COLOR: Record<string, string> = {
  not_integrated: "gray",
  pending: "yellow",
  synced: "green",
  error: "red",
};

export function HostelsPage() {
  const { profile } = useAuth();
  const { hostels } = useHostels();
  const [refreshKey, setRefreshKey] = useState(0);
  const [opened, { open, close }] = useDisclosure(false);
  const [name, setName] = useState("");
  const [location, setLocation] = useState("");
  const [contactEmail, setContactEmail] = useState("");
  const [saving, setSaving] = useState(false);
  const [syncingId, setSyncingId] = useState<string | null>(null);

  const isAdmin = profile?.role === "admin";

  const handleCreate = async () => {
    setSaving(true);
    try {
      await api.post<Hostel>("/hostels", { name, location: location || null, contact_email: contactEmail || null });
      notifications.show({ title: "Hostel created", message: name, color: "green" });
      close();
      setName(""); setLocation(""); setContactEmail("");
      setRefreshKey((k) => k + 1);
    } finally {
      setSaving(false);
    }
  };

  const handleSync = async (hostelId: string) => {
    setSyncingId(hostelId);
    try {
      const result = await api.post<{ reservations_processed: number; guests_enriched: number }>(`/pms/${hostelId}/sync`);
      notifications.show({
        title: "PMS sync complete",
        message: `Processed ${result.reservations_processed} reservations, enriched ${result.guests_enriched} guest records.`,
        color: "green",
      });
    } catch (err) {
      notifications.show({
        title: "PMS sync failed",
        message: err instanceof Error ? err.message : "Unknown error",
        color: "red",
      });
    } finally {
      setSyncingId(null);
    }
  };

  return (
    <Stack gap="md" key={refreshKey}>
      <Group justify="space-between">
        <Title order={2}>Hostel Directory</Title>
        {isAdmin && (
          <Button leftSection={<IconPlus size={16} />} onClick={open}>Add Hostel</Button>
        )}
      </Group>

      <Paper withBorder radius="md">
        <Table verticalSpacing="sm">
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Name</Table.Th>
              <Table.Th>Location</Table.Th>
              <Table.Th>Contact</Table.Th>
              <Table.Th>PMS Status</Table.Th>
              {isAdmin && <Table.Th />}
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {hostels.map((h) => (
              <Table.Tr key={h.id}>
                <Table.Td>{h.name}</Table.Td>
                <Table.Td>{h.location || "—"}</Table.Td>
                <Table.Td>
                  <Text size="sm">{h.contact_email || "—"}</Text>
                  <Text size="xs" c="dimmed">{h.contact_phone || ""}</Text>
                </Table.Td>
                <Table.Td>
                  <Badge color={PMS_STATUS_COLOR[h.pms_status]}>{h.pms_status.replace("_", " ")}</Badge>
                  {h.pms_provider && <Text size="xs" c="dimmed">{h.pms_provider}</Text>}
                </Table.Td>
                {isAdmin && (
                  <Table.Td>
                    {h.pms_provider && (
                      <Button
                        size="xs" variant="light" leftSection={<IconRefresh size={14} />}
                        loading={syncingId === h.id} onClick={() => handleSync(h.id)}
                      >
                        Sync now
                      </Button>
                    )}
                  </Table.Td>
                )}
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Paper>

      <Modal opened={opened} onClose={close} title="Add Hostel">
        <Stack gap="sm">
          <TextInput label="Name" required value={name} onChange={(e) => setName(e.currentTarget.value)} />
          <TextInput label="Location" value={location} onChange={(e) => setLocation(e.currentTarget.value)} />
          <TextInput label="Contact Email" value={contactEmail} onChange={(e) => setContactEmail(e.currentTarget.value)} />
          <Group justify="flex-end">
            <Button variant="default" onClick={close}>Cancel</Button>
            <Button onClick={handleCreate} loading={saving} disabled={!name}>Create</Button>
          </Group>
        </Stack>
      </Modal>
    </Stack>
  );
}
