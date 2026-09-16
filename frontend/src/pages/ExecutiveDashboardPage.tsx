import { useEffect, useState } from "react";
import { Title, SimpleGrid, Paper, Text, Stack, Group, Select, Center, Loader } from "@mantine/core";
import { DatePickerInput } from "@mantine/dates";
import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  BarChart, Bar, PieChart, Pie, Cell, Legend,
} from "recharts";
import { IconTicket, IconHourglass, IconCircleCheck, IconRepeat } from "@tabler/icons-react";
import { api } from "../lib/apiClient";
import { StatCard } from "../components/StatCard";
import { useHostels } from "../hooks/useHostels";
import { REASON_LABEL, CHANNEL_LABEL } from "../lib/labels";
import type { DashboardOverview } from "../types";

const PIE_COLORS = ["#4f46e5", "#22c55e", "#f59e0b", "#ef4444", "#06b6d4"];

interface ExecutiveData {
  overview: DashboardOverview;
  trend: { day: string; created_count: number; resolved_count: number }[];
  by_reason: { reason: string; count: number }[];
  by_channel: { channel: string; count: number }[];
  by_priority_status: { priority: string; status: string; count: number }[];
  resolution_time_by_hostel: { group_label: string; avg_hours: number }[];
  resolution_time_by_agent: { group_label: string; avg_hours: number }[];
  recontact_rate: { total_resolved: number; recontacted: number; rate_pct: number };
}

export function ExecutiveDashboardPage() {
  const { hostels } = useHostels();
  const [hostelId, setHostelId] = useState<string | null>(null);
  const [dateRange, setDateRange] = useState<[Date | null, Date | null]>([null, null]);
  const [data, setData] = useState<ExecutiveData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const params = new URLSearchParams();
    if (hostelId) params.set("hostel_id", hostelId);
    if (dateRange[0]) params.set("date_from", dateRange[0].toISOString());
    if (dateRange[1]) params.set("date_to", dateRange[1].toISOString());
    setLoading(true);
    api.get<ExecutiveData>(`/dashboards/executive?${params.toString()}`).then(setData).finally(() => setLoading(false));
  }, [hostelId, dateRange]);

  if (loading || !data) return <Center h={300}><Loader /></Center>;

  return (
    <Stack gap="lg">
      <Group justify="space-between" wrap="wrap">
        <Title order={2}>Executive Dashboard</Title>
        <Group>
          <Select
            placeholder="All hostels" clearable searchable
            data={hostels.map((h) => ({ value: h.id, label: h.name }))}
            value={hostelId} onChange={setHostelId} w={220}
          />
          <DatePickerInput
            type="range" placeholder="Date range" clearable
            value={dateRange} onChange={setDateRange} w={260}
          />
        </Group>
      </Group>

      <SimpleGrid cols={{ base: 1, sm: 2, lg: 4 }}>
        <StatCard label="Total Tickets" value={data.overview.total} icon={IconTicket} />
        <StatCard label="Open" value={data.overview.open} icon={IconHourglass} color="blue" />
        <StatCard label="In Progress" value={data.overview.in_progress} icon={IconHourglass} color="yellow" />
        <StatCard label="Resolved" value={data.overview.resolved} icon={IconCircleCheck} color="green" />
      </SimpleGrid>

      <SimpleGrid cols={{ base: 1, lg: 2 }}>
        <Paper withBorder p="md" radius="md">
          <Text fw={600} mb="sm">Tickets Created vs Resolved</Text>
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={data.trend}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="day" tick={{ fontSize: 11 }} />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="created_count" name="Created" stroke="#4f46e5" strokeWidth={2} />
              <Line type="monotone" dataKey="resolved_count" name="Resolved" stroke="#22c55e" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </Paper>

        <Paper withBorder p="md" radius="md">
          <Text fw={600} mb="sm">Top Reasons</Text>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={data.by_reason.map((r) => ({ ...r, label: REASON_LABEL[r.reason as keyof typeof REASON_LABEL] ?? r.reason }))}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="label" tick={{ fontSize: 10 }} interval={0} angle={-20} textAnchor="end" height={60} />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="count" fill="#4f46e5" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Paper>
      </SimpleGrid>

      <SimpleGrid cols={{ base: 1, lg: 2 }}>
        <Paper withBorder p="md" radius="md">
          <Text fw={600} mb="sm">Channel Distribution</Text>
          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <Pie
                data={data.by_channel.map((c) => ({ name: CHANNEL_LABEL[c.channel as keyof typeof CHANNEL_LABEL] ?? c.channel, value: c.count }))}
                dataKey="value" nameKey="name" outerRadius={90} label
              >
                {data.by_channel.map((_, i) => <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />)}
              </Pie>
              <Tooltip />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </Paper>

        <Paper withBorder p="md" radius="md">
          <Text fw={600} mb="sm">Recontact Rate</Text>
          <Stack justify="center" h={260} gap="xs" align="center">
            <Text size="48px" fw={700}>{data.recontact_rate.rate_pct}%</Text>
            <Text c="dimmed" size="sm">
              {data.recontact_rate.recontacted} of {data.recontact_rate.total_resolved} resolved tickets
            </Text>
            <IconRepeat size={32} color="#f59e0b" />
          </Stack>
        </Paper>
      </SimpleGrid>

      <SimpleGrid cols={{ base: 1, lg: 2 }}>
        <Paper withBorder p="md" radius="md">
          <Text fw={600} mb="sm">Avg. Resolution Time by Hostel</Text>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={data.resolution_time_by_hostel} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" />
              <YAxis type="category" dataKey="group_label" width={140} tick={{ fontSize: 11 }} />
              <Tooltip />
              <Bar dataKey="avg_hours" name="Avg hours" fill="#22c55e" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Paper>
        <Paper withBorder p="md" radius="md">
          <Text fw={600} mb="sm">Avg. Resolution Time by Agent</Text>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={data.resolution_time_by_agent} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" />
              <YAxis type="category" dataKey="group_label" width={140} tick={{ fontSize: 11 }} />
              <Tooltip />
              <Bar dataKey="avg_hours" name="Avg hours" fill="#4f46e5" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Paper>
      </SimpleGrid>
    </Stack>
  );
}
