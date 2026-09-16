import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Title, Group, Button, Select, Table, Badge, Paper, Stack, Text } from "@mantine/core";
import { IconPlus } from "@tabler/icons-react";
import { api } from "../lib/apiClient";
import { useAuth } from "../hooks/useAuth";
import { useHostels } from "../hooks/useHostels";
import { MAINTENANCE_STATUS_COLOR, MAINTENANCE_STATUS_LABEL, MAINTENANCE_PRIORITY_COLOR, humanize } from "../lib/labels";
import type { MaintenanceTicket } from "../types";

export function MaintenanceListPage() {
  const navigate = useNavigate();
  const { profile } = useAuth();
  const { hostels } = useHostels();
  const [status, setStatus] = useState<string | null>(null);
  const [hostelId, setHostelId] = useState<string | null>(null);
  const [tickets, setTickets] = useState<MaintenanceTicket[]>([]);
  const [loading, setLoading] = useState(true);

  const canCreate = profile?.role === "admin" || profile?.role === "maintenance";

  useEffect(() => {
    const params = new URLSearchParams();
    if (status) params.set("status_", status);
    if (hostelId) params.set("hostel_id", hostelId);
    setLoading(true);
    api.get<MaintenanceTicket[]>(`/maintenance-tickets?${params.toString()}`).then(setTickets).finally(() => setLoading(false));
  }, [status, hostelId]);

  const hostelName = (id: string) => hostels.find((h) => h.id === id)?.name ?? id;

  return (
    <Stack gap="md">
      <Group justify="space-between">
        <div>
          <Title order={2}>Maintenance</Title>
          <Text c="dimmed" size="sm">Property repair &amp; upkeep tickets — separate from guest support tickets.</Text>
        </div>
        {canCreate && (
          <Button component={Link} to="/maintenance/new" leftSection={<IconPlus size={16} />}>
            Report Issue
          </Button>
        )}
      </Group>

      <Paper withBorder p="md" radius="md">
        <Group>
          <Select
            placeholder="Status" clearable
            data={Object.entries(MAINTENANCE_STATUS_LABEL).map(([value, label]) => ({ value, label }))}
            value={status} onChange={setStatus} w={180}
          />
          <Select
            placeholder="Hostel" clearable searchable
            data={hostels.map((h) => ({ value: h.id, label: h.name }))}
            value={hostelId} onChange={setHostelId} w={220}
          />
        </Group>
      </Paper>

      <Paper withBorder radius="md">
        <Table highlightOnHover verticalSpacing="sm">
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Title</Table.Th>
              <Table.Th>Hostel</Table.Th>
              <Table.Th>Priority</Table.Th>
              <Table.Th>Status</Table.Th>
              <Table.Th>Reported</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {tickets.map((t) => (
              <Table.Tr key={t.id} onClick={() => navigate(`/maintenance/${t.id}`)} style={{ cursor: "pointer" }}>
                <Table.Td>{t.title}</Table.Td>
                <Table.Td>{hostelName(t.hostel_id)}</Table.Td>
                <Table.Td><Badge color={MAINTENANCE_PRIORITY_COLOR[t.priority]}>{humanize(t.priority)}</Badge></Table.Td>
                <Table.Td><Badge color={MAINTENANCE_STATUS_COLOR[t.status]}>{MAINTENANCE_STATUS_LABEL[t.status]}</Badge></Table.Td>
                <Table.Td>{new Date(t.created_at).toLocaleString()}</Table.Td>
              </Table.Tr>
            ))}
            {!loading && tickets.length === 0 && (
              <Table.Tr>
                <Table.Td colSpan={5}><Text c="dimmed" ta="center" py="md">No maintenance tickets match these filters.</Text></Table.Td>
              </Table.Tr>
            )}
          </Table.Tbody>
        </Table>
      </Paper>
    </Stack>
  );
}
