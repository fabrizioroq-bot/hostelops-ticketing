import { useEffect, useState } from "react";
import { api } from "../lib/apiClient";
import type { Hostel } from "../types";

export function useHostels() {
  const [hostels, setHostels] = useState<Hostel[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get<Hostel[]>("/hostels")
      .then(setHostels)
      .finally(() => setLoading(false));
  }, []);

  return { hostels, loading };
}
