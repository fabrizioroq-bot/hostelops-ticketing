import { useEffect, useState, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import {
  Paper, Title, Text, Badge, Group, Stack, Select, Textarea, Button, Checkbox,
  Divider, Timeline, Loader, Center, Grid, Modal,
} from "@mantine/core";
import { IconCheck, IconHistory } from "@tabler/icons-react";
import { api } from "../lib/apiClient";
import { useAuth } from "../hooks/useAuth";
import { useHostels } from "../hooks/useHostels";
import { STATUS_COLOR, PRIORITY_COLOR, REASON_LABEL, CHANNEL_LABEL, STATUS_LABEL, humanize } from "../lib/labels";
import type { AppUser, Ticket, TicketHistoryEntry, TicketPriority, TicketStatus } from "../types";

export function TicketDetailPage() {
  const { ticketId } = useParams<{ ticketId: string }>();
  const { profile } = useAuth();
  const { hostels } = useHostels();
  const [ticket, setTicket] = useState<Ticket | null>(null);
  const [history, setHistory] = useState<TicketHistoryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [resolveModalOpen, setResolveModalOpen] = useState(false);

  const [status, setStatus] = useState<TicketStatus>("open");
  const [priority, setPriority] = useState<TicketPriority>("medium");
  const [resolutionNotes, setResolutionNotes] = useState("");
  const [recontacted, setRecontacted] = useState(false);
  const [recontactedNotes, setRecontactedNotes] = useState("");
  const [assigneeId, setAssigneeId] = useState<string | null>(null);
  const [users, setUsers] = useState<AppUser[]>([]);

  const canReassign = profile?.role === "admin" || profile?.role === "supervisor";

  useEffect(() => {
    if (canReassign) {
      api.get<AppUser[]>("/users").then(setUsers).catch(() => setUsers([]));
    }
  }, [canReassign]);

  const load = useCallback(() => {
    if (!ticketId) return;
    setLoading(true);
    Promise.all([
      api.get<Ticket>(`/tickets/${ticketId}`),
      api.get<TicketHistoryEntry[]>(`/tickets/${ticketId}/history`),
    ]).then(([t, h]) => {
      setTicket(t);
      setHistory(h);
      setStatus(t.status);
      setPriority(t.priority);
      setResolutionNotes(t.resolution_notes ?? "");
      setRecontacted(t.recontacted);
      setRecontactedNotes(t.recontacted_notes ?? "");
      setAssigneeId(t.assignee_id);
    }).finally(() => setLoading(false));
  }, [ticketId]);

  useEffect(() => { load(); }, [load]);

  const persist = async (overrides: Partial<Record<string, unknown>> = {}) => {
    if (!ticketId) return;
    setSaving(true);
    try {
      const updated = await api.patch<Ticket>(`/tickets/${ticketId}`, {
        status, priority, resolution_notes: resolutionNotes || null,
        recontacted, recontacted_notes: recontactedNotes || null,
        ...(canReassign && assigneeId !== ticket?.assignee_id ? { assignee_id: assigneeId } : {}),
        ...overrides,
      });
      setTicket(updated);
      const h = await api.get<TicketHistoryEntry[]>(`/tickets/${ticketId}/history`);
      setHistory(h);
    } finally {
      setSaving(false);
      setResolveModalOpen(false);
    }
  };

  if (loading || !ticket) {
    return <Center h={300}><Loader /></Center>;
  }

  const hostelName = hostels.find((h) => h.id === ticket.hostel_id)?.name ?? ticket.hostel_id;

  return (
    <Stack gap="md">
      <Group justify="space-between">
        <div>
          <Title order={2}>{ticket.guest_name}</Title>
          <Text c="dimmed" size="sm">{ticket.reservation_number || "No reservation number"} · {hostelName}</Text>
        </div>
        <Group>
          <Badge color={PRIORITY_COLOR[ticket.priority]}>{humanize(ticket.priority)}</Badge>
          <Badge color={STATUS_COLOR[ticket.status]}>{STATUS_LABEL[ticket.status]}</Badge>
        </Group>
      </Group>

      <Grid>
        <Grid.Col span={{ base: 12, md: 7 }}>
          <Paper withBorder p="md" radius="md">
            <Stack gap="sm">
              <Text fw={600}>Ticket Details</Text>
              <Text size="sm"><b>Channel:</b> {CHANNEL_LABEL[ticket.channel]}</Text>
              <Text size="sm"><b>Reason:</b> {REASON_LABEL[ticket.reason]}</Text>
              <Text size="sm"><b>Description:</b> {ticket.description}</Text>
              <Text size="xs" c="dimmed">Created {new Date(ticket.created_at).toLocaleString()}</Text>
              {ticket.resolved_at && (
                <Text size="xs" c="dimmed">Resolved {new Date(ticket.resolved_at).toLocaleString()}</Text>
              )}
            </Stack>
          </Paper>

          <Paper withBorder p="md" radius="md" mt="md">
            <Stack gap="sm">
              <Text fw={600}>Update Ticket</Text>
              <Group grow>
                <Select
                  label="Status"
                  data={Object.entries(STATUS_LABEL).map(([value, label]) => ({ value, label }))}
                  value={status}
                  onChange={(v) => setStatus((v as TicketStatus) || ticket.status)}
                />
                <Select
                  label="Priority"
                  data={["low", "medium", "high", "urgent"].map((v) => ({ value: v, label: humanize(v) }))}
                  value={priority}
                  onChange={(v) => setPriority((v as TicketPriority) || ticket.priority)}
                />
              </Group>
              {canReassign && (
                <Select
                  label="Assignee"
                  description="Reassigning is restricted to admins and supervisors"
                  data={users
                    .filter((u) => u.role === "agent" || u.role === "supervisor")
                    .map((u) => ({ value: u.id, label: `${u.full_name} (${u.role})` }))}
                  value={assigneeId}
                  onChange={setAssigneeId}
                  searchable
                />
              )}
              <Textarea
                label="Resolution Applied"
                minRows={3}
                value={resolutionNotes}
                onChange={(e) => setResolutionNotes(e.currentTarget.value)}
              />
              <Checkbox
                label="Guest recontacted for the same reason?"
                checked={recontacted}
                onChange={(e) => setRecontacted(e.currentTarget.checked)}
              />
              {recontacted && (
                <Textarea
                  label="Recontact notes"
                  minRows={2}
                  value={recontactedNotes}
                  onChange={(e) => setRecontactedNotes(e.currentTarget.value)}
                />
              )}
              <Group justify="flex-end">
                {status === "resolved" && ticket.status !== "resolved" ? (
                  <Button leftSection={<IconCheck size={16} />} loading={saving} onClick={() => setResolveModalOpen(true)}>
                    Save &amp; Resolve
                  </Button>
                ) : (
                  <Button loading={saving} onClick={() => persist()}>Save Changes</Button>
                )}
              </Group>
            </Stack>
          </Paper>
        </Grid.Col>

        <Grid.Col span={{ base: 12, md: 5 }}>
          <Paper withBorder p="md" radius="md">
            <Group mb="sm"><IconHistory size={18} /><Text fw={600}>Change History</Text></Group>
            <Divider mb="sm" />
            {history.length === 0 && <Text size="sm" c="dimmed">No changes recorded yet.</Text>}
            <Timeline active={history.length} bulletSize={16} lineWidth={2}>
              {history.map((h) => (
                <Timeline.Item key={h.id} title={humanize(h.field_name)}>
                  <Text size="xs" c="dimmed">
                    {h.old_value ?? "—"} → {h.new_value ?? "—"}
                  </Text>
                  <Text size="xs" c="dimmed">{new Date(h.created_at).toLocaleString()}</Text>
                </Timeline.Item>
              ))}
            </Timeline>
          </Paper>
          {ticket.guest_id && (
            <Button component={Link} to={`/guests/${ticket.guest_id}`} variant="light" fullWidth mt="md">
              View Guest Profile
            </Button>
          )}
        </Grid.Col>
      </Grid>

      <Modal opened={resolveModalOpen} onClose={() => setResolveModalOpen(false)} title="Confirm resolution">
        <Text size="sm" mb="md">
          This will mark the ticket as resolved and record the resolution timestamp. Continue?
        </Text>
        <Group justify="flex-end">
          <Button variant="default" onClick={() => setResolveModalOpen(false)}>Cancel</Button>
          <Button color="green" loading={saving} onClick={() => persist()}>Confirm Resolve</Button>
        </Group>
      </Modal>
    </Stack>
  );
}
