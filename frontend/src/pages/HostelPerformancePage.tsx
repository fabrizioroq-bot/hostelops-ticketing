import { useEffect, useState } from "react";
import { Title, Paper, Text, Stack, Table, Badge, Group, Center, Loader } from "@mantine/core";
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip } from "recharts";
import { api } from "../lib/apiClient";
import { REASON_LABEL } from "../lib/labels";
import type { TicketReason } from "../types";

interface HostelPerf {
  hostel_id: string;
  hostel_name: string;
  ticket_count: number;
  avg_resolution_hours: number | null;
}

interface AgentWorkload {
  assignee_id: string;
  agent_name: string;
  hostel_id: string;
  hostel_name: string;
  ticket_count: number;
}

interface HostelPerformanceResponse {
  performance: HostelPerf[];
  top_issues_by_hostel: Record<string, { reason: string; count: number }[]>;
  agent_workload: AgentWorkload[];
}

export function HostelPerformancePage() {
  const [data, setData] = useState<HostelPerformanceResponse | null>(null);

  useEffect(() => {
    api.get<HostelPerformanceResponse>("/dashboards/hostel-performance").then(setData);
  }, []);

  if (!data) return <Center h={300}><Loader /></Center>;

  return (
    <Stack gap="lg">
      <Title order={2}>Hostel Performance</Title>

      <Paper withBorder p="md" radius="md">
        <Text fw={600} mb="sm">Tickets per Hostel</Text>
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={data.performance}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="hostel_name" tick={{ fontSize: 11 }} />
            <YAxis allowDecimals={false} />
            <Tooltip />
            <Bar dataKey="ticket_count" name="Tickets" fill="#4f46e5" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </Paper>

      <Paper withBorder radius="md">
        <Text fw={600} p="md" pb={0}>Resolution Time &amp; Top Issues by Hostel</Text>
        <Table verticalSpacing="sm">
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Hostel</Table.Th>
              <Table.Th>Tickets</Table.Th>
              <Table.Th>Avg. Resolution (hrs)</Table.Th>
              <Table.Th>Top Issues</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {data.performance
              .slice()
              .sort((a, b) => (b.avg_resolution_hours ?? 0) - (a.avg_resolution_hours ?? 0))
              .map((h) => (
                <Table.Tr key={h.hostel_id}>
                  <Table.Td>{h.hostel_name}</Table.Td>
                  <Table.Td>{h.ticket_count}</Table.Td>
                  <Table.Td>{h.avg_resolution_hours ?? "—"}</Table.Td>
                  <Table.Td>
                    <Group gap={4}>
                      {(data.top_issues_by_hostel[h.hostel_id] || []).map((i) => (
                        <Badge key={i.reason} variant="light">
                          {REASON_LABEL[i.reason as TicketReason] ?? i.reason} ({i.count})
                        </Badge>
                      ))}
                    </Group>
                  </Table.Td>
                </Table.Tr>
              ))}
          </Table.Tbody>
        </Table>
      </Paper>

      <Paper withBorder radius="md">
        <Text fw={600} p="md" pb={0}>Agent Workload</Text>
        <Table verticalSpacing="sm">
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Agent</Table.Th>
              <Table.Th>Hostel</Table.Th>
              <Table.Th>Tickets Handled</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {data.agent_workload.map((a) => (
              <Table.Tr key={`${a.assignee_id}-${a.hostel_id}`}>
                <Table.Td>{a.agent_name}</Table.Td>
                <Table.Td>{a.hostel_name}</Table.Td>
                <Table.Td>{a.ticket_count}</Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Paper>
    </Stack>
  );
}
