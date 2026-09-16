import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  Title, Group, Button, TextInput, Select, Table, Badge, Pagination, Paper, Stack, Text,
} from "@mantine/core";
import { IconPlus, IconSearch } from "@tabler/icons-react";
import { api } from "../lib/apiClient";
import { useHostels } from "../hooks/useHostels";
import { STATUS_COLOR, PRIORITY_COLOR, REASON_LABEL, STATUS_LABEL, humanize } from "../lib/labels";
import type { PaginatedTickets, TicketPriority, TicketStatus } from "../types";

const PAGE_SIZE = 20;

export function TicketsListPage() {
  const navigate = useNavigate();
  const { hostels } = useHostels();
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState<string | null>(null);
  const [priority, setPriority] = useState<string | null>(null);
  const [hostelId, setHostelId] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [data, setData] = useState<PaginatedTickets | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const params = new URLSearchParams();
    if (search) params.set("search", search);
    if (status) params.set("status", status);
    if (priority) params.set("priority", priority);
    if (hostelId) params.set("hostel_id", hostelId);
    params.set("page", String(page));
    params.set("page_size", String(PAGE_SIZE));

    setLoading(true);
    api.get<PaginatedTickets>(`/tickets?${params.toString()}`)
      .then(setData)
      .finally(() => setLoading(false));
  }, [search, status, priority, hostelId, page]);

  const hostelName = (id: string) => hostels.find((h) => h.id === id)?.name ?? id;

  return (
    <Stack gap="md">
      <Group justify="space-between">
        <Title order={2}>Tickets</Title>
        <Button component={Link} to="/tickets/new" leftSection={<IconPlus size={16} />}>
          New Ticket
        </Button>
      </Group>

      <Paper withBorder p="md" radius="md">
        <Group>
          <TextInput
            placeholder="Search by guest name or reservation number"
            leftSection={<IconSearch size={16} />}
            value={search}
            onChange={(e) => { setSearch(e.currentTarget.value); setPage(1); }}
            w={320}
          />
          <Select
            placeholder="Status"
            clearable
            data={Object.entries(STATUS_LABEL).map(([value, label]) => ({ value, label }))}
            value={status}
            onChange={(v) => { setStatus(v); setPage(1); }}
            w={160}
          />
          <Select
            placeholder="Priority"
            clearable
            data={["low", "medium", "high", "urgent"].map((v) => ({ value: v, label: humanize(v) }))}
            value={priority}
            onChange={(v) => { setPriority(v); setPage(1); }}
            w={160}
          />
          <Select
            placeholder="Hostel"
            clearable
            searchable
            data={hostels.map((h) => ({ value: h.id, label: h.name }))}
            value={hostelId}
            onChange={(v) => { setHostelId(v); setPage(1); }}
            w={220}
          />
        </Group>
      </Paper>

      <Paper withBorder radius="md">
        <Table highlightOnHover verticalSpacing="sm">
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Guest</Table.Th>
              <Table.Th>Hostel</Table.Th>
              <Table.Th>Reason</Table.Th>
              <Table.Th>Priority</Table.Th>
              <Table.Th>Status</Table.Th>
              <Table.Th>Created</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {data?.items.map((t) => (
              <Table.Tr key={t.id} onClick={() => navigate(`/tickets/${t.id}`)} style={{ cursor: "pointer" }}>
                <Table.Td>
                  <Text fw={500}>{t.guest_name}</Text>
                  {t.reservation_number && <Text size="xs" c="dimmed">{t.reservation_number}</Text>}
                </Table.Td>
                <Table.Td>{hostelName(t.hostel_id)}</Table.Td>
                <Table.Td>{REASON_LABEL[t.reason]}</Table.Td>
                <Table.Td><Badge color={PRIORITY_COLOR[t.priority as TicketPriority]}>{humanize(t.priority)}</Badge></Table.Td>
                <Table.Td><Badge color={STATUS_COLOR[t.status as TicketStatus]}>{STATUS_LABEL[t.status]}</Badge></Table.Td>
                <Table.Td>{new Date(t.created_at).toLocaleString()}</Table.Td>
              </Table.Tr>
            ))}
            {!loading && data?.items.length === 0 && (
              <Table.Tr>
                <Table.Td colSpan={6}><Text c="dimmed" ta="center" py="md">No tickets match these filters.</Text></Table.Td>
              </Table.Tr>
            )}
          </Table.Tbody>
        </Table>
      </Paper>

      {data && data.total > PAGE_SIZE && (
        <Group justify="center">
          <Pagination
            total={Math.ceil(data.total / PAGE_SIZE)}
            value={page}
            onChange={setPage}
          />
        </Group>
      )}
    </Stack>
  );
}
