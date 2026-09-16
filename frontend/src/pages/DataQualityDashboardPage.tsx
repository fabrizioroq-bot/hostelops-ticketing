import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Title, SimpleGrid, Paper, Text, Stack, Table, Badge, Center, Loader } from "@mantine/core";
import { IconCopy, IconChecklist, IconAlertTriangle, IconGauge } from "@tabler/icons-react";
import { api } from "../lib/apiClient";
import { StatCard } from "../components/StatCard";

interface DataQualitySummary {
  duplicate_candidates_pending: number;
  merged_this_month: number;
  total_tickets: number;
  incomplete_tickets: number;
  completeness_pct: number;
  avg_guest_data_quality_score: number | null;
}

interface IncompleteTicket {
  id: string;
  guest_name: string;
  hostel_id: string;
  reason: string;
  status: string;
  missing_fields: string[];
  created_at: string;
}

export function DataQualityDashboardPage() {
  const [summary, setSummary] = useState<DataQualitySummary | null>(null);
  const [incomplete, setIncomplete] = useState<IncompleteTicket[]>([]);

  useEffect(() => {
    api.get<{ summary: DataQualitySummary; incomplete_tickets: IncompleteTicket[] }>("/dashboards/data-quality")
      .then((res) => { setSummary(res.summary); setIncomplete(res.incomplete_tickets); });
  }, []);

  if (!summary) return <Center h={300}><Loader /></Center>;

  return (
    <Stack gap="lg">
      <Title order={2}>Data Quality Dashboard</Title>

      <SimpleGrid cols={{ base: 1, sm: 2, lg: 4 }}>
        <StatCard label="Pending Duplicate Candidates" value={summary.duplicate_candidates_pending} icon={IconCopy} color="yellow" />
        <StatCard label="Merged This Month" value={summary.merged_this_month} icon={IconChecklist} color="green" />
        <StatCard label="Completeness Score" value={`${summary.completeness_pct}%`} icon={IconGauge} />
        <StatCard label="Incomplete Tickets" value={summary.incomplete_tickets} icon={IconAlertTriangle} color="red" />
      </SimpleGrid>

      <Paper withBorder p="md" radius="md">
        <Text fw={600} mb="sm">Export Readiness</Text>
        <Text size="sm" c="dimmed">
          Average guest golden-record data quality score:{" "}
          <b>{summary.avg_guest_data_quality_score ?? "—"}%</b>. Higher is better for downstream
          CRM/BI exports — see the Deduplication Review page to raise this further.
        </Text>
      </Paper>

      <Paper withBorder radius="md">
        <Text fw={600} p="md" pb={0}>Incomplete Records</Text>
        <Table verticalSpacing="sm">
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Guest</Table.Th>
              <Table.Th>Reason</Table.Th>
              <Table.Th>Status</Table.Th>
              <Table.Th>Missing</Table.Th>
              <Table.Th>Created</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {incomplete.map((t) => (
              <Table.Tr key={t.id}>
                <Table.Td><Link to={`/tickets/${t.id}`}>{t.guest_name}</Link></Table.Td>
                <Table.Td>{t.reason}</Table.Td>
                <Table.Td>{t.status}</Table.Td>
                <Table.Td>
                  {t.missing_fields.map((f) => <Badge key={f} color="red" variant="light" mr={4}>{f}</Badge>)}
                </Table.Td>
                <Table.Td>{new Date(t.created_at).toLocaleDateString()}</Table.Td>
              </Table.Tr>
            ))}
            {incomplete.length === 0 && (
              <Table.Tr><Table.Td colSpan={5}><Text c="dimmed" ta="center" py="md">No incomplete records. Great job!</Text></Table.Td></Table.Tr>
            )}
          </Table.Tbody>
        </Table>
      </Paper>
    </Stack>
  );
}
