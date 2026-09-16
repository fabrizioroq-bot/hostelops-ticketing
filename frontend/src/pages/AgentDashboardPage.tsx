import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Title, SimpleGrid, Group, Button, Stack, Text, Center, Loader } from "@mantine/core";
import { IconPlus, IconTicket, IconClock, IconCircleCheck, IconHourglass } from "@tabler/icons-react";
import { api } from "../lib/apiClient";
import { StatCard } from "../components/StatCard";
import { useAuth } from "../hooks/useAuth";

interface AgentPerformance {
  open: number;
  in_progress: number;
  resolved: number;
  resolved_this_week: number;
  avg_resolution_hours: number | null;
}

export function AgentDashboardPage() {
  const { profile } = useAuth();
  const [perf, setPerf] = useState<AgentPerformance | null>(null);

  useEffect(() => {
    api.get<AgentPerformance>("/dashboards/agent").then(setPerf);
  }, []);

  if (!perf) return <Center h={300}><Loader /></Center>;

  return (
    <Stack gap="lg">
      <Group justify="space-between">
        <div>
          <Title order={2}>Welcome back, {profile?.full_name.split(" ")[0]}</Title>
          <Text c="dimmed" size="sm">Here's your current workload.</Text>
        </div>
        <Button component={Link} to="/tickets/new" leftSection={<IconPlus size={16} />}>New Ticket</Button>
      </Group>

      <SimpleGrid cols={{ base: 1, sm: 2, lg: 4 }}>
        <StatCard label="Open" value={perf.open} icon={IconTicket} color="blue" />
        <StatCard label="In Progress" value={perf.in_progress} icon={IconHourglass} color="yellow" />
        <StatCard label="Resolved (all time)" value={perf.resolved} icon={IconCircleCheck} color="green" />
        <StatCard label="Resolved This Week" value={perf.resolved_this_week} icon={IconCircleCheck} color="teal" />
      </SimpleGrid>

      <SimpleGrid cols={{ base: 1, sm: 2 }}>
        <StatCard
          label="Avg. Resolution Time"
          value={perf.avg_resolution_hours != null ? `${perf.avg_resolution_hours}h` : "—"}
          icon={IconClock}
        />
      </SimpleGrid>

      <Group>
        <Button component={Link} to="/tickets" variant="light">View My Pending Tickets</Button>
      </Group>
    </Stack>
  );
}
