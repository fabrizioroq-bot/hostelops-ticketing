import { useState } from "react";
import { useNavigate, useLocation, Navigate } from "react-router-dom";
import { Paper, TextInput, PasswordInput, Button, Title, Alert, Center, Stack, Text } from "@mantine/core";
import { IconAlertCircle } from "@tabler/icons-react";
import { useAuth } from "../hooks/useAuth";
import { supabase } from "../lib/supabaseClient";

export function LoginPage() {
  const { session, signIn } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  if (session) {
    const from = (location.state as { from?: string })?.from || "/";
    return <Navigate to={from} replace />;
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await signIn(email, password);
      navigate("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed. Please check your credentials.");
    } finally {
      setLoading(false);
    }
  };

  const handleForgotPassword = async () => {
    setError(null);
    setInfo(null);
    if (!email) {
      setError("Enter your email above first, then click 'Forgot password?'.");
      return;
    }
    const { error: resetError } = await supabase.auth.resetPasswordForEmail(email, {
      redirectTo: `${window.location.origin}/login`,
    });
    if (resetError) {
      setError(resetError.message);
    } else {
      setInfo("If that email is registered, a password reset link has been sent.");
    }
  };

  return (
    <Center h="100vh" bg="gray.0">
      <Paper shadow="md" p="xl" radius="md" w={380}>
        <Stack gap="md">
          <div>
            <Title order={2}>HostelOps Ticketing</Title>
            <Text c="dimmed" size="sm">Sign in with your work email</Text>
          </div>
          {error && (
            <Alert color="red" icon={<IconAlertCircle size={16} />}>
              {error}
            </Alert>
          )}
          {info && <Alert color="blue">{info}</Alert>}
          <form onSubmit={handleSubmit}>
            <Stack gap="md">
              <TextInput
                label="Email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.currentTarget.value)}
                autoComplete="username"
              />
              <PasswordInput
                label="Password"
                required
                value={password}
                onChange={(e) => setPassword(e.currentTarget.value)}
                autoComplete="current-password"
              />
              <Button type="submit" loading={loading} fullWidth>
                Log in
              </Button>
              <Button variant="subtle" size="xs" onClick={handleForgotPassword} type="button">
                Forgot password?
              </Button>
            </Stack>
          </form>
        </Stack>
      </Paper>
    </Center>
  );
}
