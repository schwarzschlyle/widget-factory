import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

export type GeneratedWidget = {
  widget_title: string;
  widget_description: string;
  code: string;
};

type GenerateWidgetsResponse = {
  task_id: string;
  status: string;
};

type GenerateWidgetsResultResponse = {
  task_id: string;
  status: string;
  result: GeneratedWidget[] | null;
};

const startGenerateWidgets = async (): Promise<GenerateWidgetsResponse> => {
  const resp = await fetch("/api/generate-widgets", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });
  if (!resp.ok) throw new Error("Failed to start widget generation");
  return resp.json();
};

const fetchGenerateWidgetsResult = async (task_id: string): Promise<GenerateWidgetsResultResponse> => {
  const resp = await fetch(`/api/generate-widgets/result/${task_id}`);
  if (!resp.ok) throw new Error("Failed to poll widget generation result");
  return resp.json();
};

export function useGenerateWidgets() {
  const queryClient = useQueryClient();

  // Mutation to start widget generation
  const mutation = useMutation({
    mutationFn: startGenerateWidgets,
  });

  // Query to poll for result, enabled only after mutation is successful
  const resultQuery = useQuery<GenerateWidgetsResultResponse>({
    queryKey: ["generate-widgets-result", mutation.data?.task_id],
    queryFn: () => fetchGenerateWidgetsResult(mutation.data!.task_id),
    enabled: !!mutation.data?.task_id,
    refetchInterval: (query) => {
      const data = query.state.data as GenerateWidgetsResultResponse | undefined;
      // Poll as long as status is not SUCCESS or FAILURE
      if (!data || (data.status !== "SUCCESS" && data.status !== "FAILURE")) {
        return 10000; // poll every 10 seconds
      }
      return false;
    },
    refetchOnWindowFocus: false,
  });

  // Reset logic for new generation
  const reset = () => {
    mutation.reset();
    queryClient.removeQueries({ queryKey: ["generate-widgets-result"] });
  };

  return {
    start: mutation.mutate,
    isStarting: mutation.isPending,
    startError: mutation.error as Error | null,
    taskId: mutation.data?.task_id,
    result: resultQuery.data?.result ?? null,
    resultStatus: resultQuery.data?.status,
    isPolling: resultQuery.isFetching,
    pollError: resultQuery.error as Error | null,
    reset,
  };
}
