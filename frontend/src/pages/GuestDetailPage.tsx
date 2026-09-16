import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  Title, Paper, Stack, Text, Group, Badge, Table, Grid, RingProgress, Center, Loader,
  TextInput, Button,
} from "@mantine/core";
import { api } from "../lib/apiClient";
import { useAuth } from "../hooks/useAuth";
import { REASON_LABEL, STATUS_COLOR, STATUS_LABEL, humanize } from "../lib/labels";
import type { Guest, Ticket, TicketReason } from "../types";

export function GuestDetailPage() {
  const { guestId } = useParams<{ guestId: string }>();
  const { profile } = useAuth();
  const [guest, setGuest] = useState<Guest | null>(null);
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [loading, setLoading] = useState(true);
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [saving, setSaving] = useState(false);

  const canEdit = profile?.role === "admin" || profile?.role === "supervisor";

  useEffect(() => {
    if (!guestId) return;
    setLoading(true);
    Promise.all([
      api.get<Guest>(`/guests/${guestId}`),
      api.get<Ticket[]>(`/guests/${guestId}/tickets`),
    ]).then(([g, t]) => {
      setGuest(g);
      setTickets(t);
      setEmail(g.email ?? "");
      setPhone(g.phone ?? "");
    }).finally(() => setLoading(false));
  }, [guestId]);

  const handleSave = async () => {
    if (!guestId) return;
    setSaving(true);
    try {
      const updated = await api.patch<Guest>(`/guests/${guestId}`, { email: email || null, phone: phone || null });
      setGuest(updated);
    } finally {
      setSaving(false);
    }
  };

  if (loading || !guest) return <Center h={300}><Loader /></Center>;

  return (
    <Stack gap="md">
      <Group justify="space-between">
        <Title order={2}>{guest.full_name}</Title>
        <RingProgress
          size={70}
          thickness={7}
          sections={[{ value: guest.data_quality_score, color: guest.data_quality_score >= 80 ? "green" : guest.data_quality_score >= 50 ? "yellow" : "red" }]}
          label={<Text size="xs" ta="center">{guest.data_quality_score}%</Text>}
        />
      </Group>

      <Grid>
        <Grid.Col span={{ base: 12, md: 5 }}>
          <Paper withBorder p="md" radius="md">
            <Text fw={600} mb="sm">Golden Record</Text>
            <Stack gap="xs">
              <TextInput label="Email" value={email} onChange={(e) => setEmail(e.currentTarget.value)} disabled={!canEdit} />
              <TextInput label="Phone" value={phone} onChange={(e) => setPhone(e.currentTarget.value)} disabled={!canEdit} />
              {canEdit && <Button onClick={handleSave} loading={saving} size="xs">Save</Button>}
              <Text size="sm"><b>Total Tickets:</b> {guest.total_tickets}</Text>
              <Text size="sm"><b>Preferred Channel:</b> {guest.preferred_channel || "—"}</Text>
              <Text size="sm"><b>Last Contact:</b> {guest.last_contact_at ? new Date(guest.last_contact_at).toLocaleString() : "—"}</Text>
              <div>
                <Text size="sm" fw={500}>Common Reasons</Text>
                <Group gap={4} mt={4}>
                  {guest.common_reasons.map((r) => (
                    <Badge key={r} variant="light">{REASON_LABEL[r as TicketReason] ?? r}</Badge>
                  ))}
                </Group>
              </div>
              <div>
                <Text size="sm" fw={500}>Linked Reservations</Text>
                <Text size="xs" c="dimmed">{guest.linked_reservations.join(", ") || "None"}</Text>
              </div>
            </Stack>
          </Paper>
        </Grid.Col>

        <Grid.Col span={{ base: 12, md: 7 }}>
          <Paper withBorder radius="md">
            <Text fw={600} p="md" pb={0}>Linked Tickets</Text>
            <Table highlightOnHover verticalSpacing="sm">
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Reason</Table.Th>
                  <Table.Th>Status</Table.Th>
                  <Table.Th>Created</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {tickets.map((t) => (
                  <Table.Tr key={t.id}>
                    <Table.Td><Link to={`/tickets/${t.id}`}>{REASON_LABEL[t.reason]}</Link></Table.Td>
                    <Table.Td><Badge color={STATUS_COLOR[t.status]}>{STATUS_LABEL[t.status]}</Badge></Table.Td>
                    <Table.Td>{new Date(t.created_at).toLocaleDateString()}</Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Paper>
        </Grid.Col>
      </Grid>
    </Stack>
  );
}
