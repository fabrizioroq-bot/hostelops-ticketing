import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Title, TextInput, Table, Paper, Stack, Text, Badge, Group } from "@mantine/core";
import { IconSearch } from "@tabler/icons-react";
import { api } from "../lib/apiClient";
import type { Guest } from "../types";

function qualityColor(score: number): string {
  if (score >= 80) return "green";
  if (score >= 50) return "yellow";
  return "red";
}

export function GuestsListPage() {
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const [guests, setGuests] = useState<Guest[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const params = new URLSearchParams();
    if (search) params.set("search", search);
    setLoading(true);
    api.get<Guest[]>(`/guests?${params.toString()}`).then(setGuests).finally(() => setLoading(false));
  }, [search]);

  return (
    <Stack gap="md">
      <Title order={2}>Guests (Master Records)</Title>
      <TextInput
        placeholder="Search by guest name"
        leftSection={<IconSearch size={16} />}
        value={search}
        onChange={(e) => setSearch(e.currentTarget.value)}
        w={320}
      />
      <Paper withBorder radius="md">
        <Table highlightOnHover verticalSpacing="sm">
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Name</Table.Th>
              <Table.Th>Contact</Table.Th>
              <Table.Th>Total Tickets</Table.Th>
              <Table.Th>Preferred Channel</Table.Th>
              <Table.Th>Last Contact</Table.Th>
              <Table.Th>Data Quality</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {guests.map((g) => (
              <Table.Tr key={g.id} onClick={() => navigate(`/guests/${g.id}`)} style={{ cursor: "pointer" }}>
                <Table.Td>{g.full_name}</Table.Td>
                <Table.Td>
                  <Text size="sm">{g.email || "—"}</Text>
                  <Text size="xs" c="dimmed">{g.phone || "no phone on file"}</Text>
                </Table.Td>
                <Table.Td>{g.total_tickets}</Table.Td>
                <Table.Td>{g.preferred_channel || "—"}</Table.Td>
                <Table.Td>{g.last_contact_at ? new Date(g.last_contact_at).toLocaleDateString() : "—"}</Table.Td>
                <Table.Td>
                  <Group gap={4}>
                    <Badge color={qualityColor(g.data_quality_score)}>{g.data_quality_score}%</Badge>
                  </Group>
                </Table.Td>
              </Table.Tr>
            ))}
            {!loading && guests.length === 0 && (
              <Table.Tr><Table.Td colSpan={6}><Text c="dimmed" ta="center" py="md">No guests found.</Text></Table.Td></Table.Tr>
            )}
          </Table.Tbody>
        </Table>
      </Paper>
    </Stack>
  );
}
