import { useQuery, useQueryClient } from "@tanstack/react-query";
import { RefreshCcw } from "lucide-react";
import { useEffect } from "react";
import apiClient, { BASE_URL } from "../api/ApiClient";
import { Button } from "./ui/button";

function Status() {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: ["status"],
    queryFn: async () => (await apiClient.api.botStatusApiStatusGet()).data,
  });

  useEffect(() => {
    const createWebSocket = () => {
      console.log("Creating WebSocket");
      const webSocket = new WebSocket(
        "ws" +
          (location.protocol === "https:" ? "s" : "") +
          "://" +
          BASE_URL +
          "/ws"
      );
      webSocket.onopen = () => {
        console.log("WebSocket connected");
      };
      webSocket.onmessage = (event) => {
        const data = JSON.parse(event.data);

        const queryKey = [...data.entity, data.id].filter(Boolean);

        console.log("WS: Invalidating query", queryKey);

        queryClient.invalidateQueries({ queryKey });
      };
      webSocket.onerror = (event) => {
        console.error("WebSocket error", event);
        // Tentar reconectar após um atraso
        setTimeout(() => {
          createWebSocket();
        }, 5000);
      };
      return webSocket;
    };

    const webSocket = createWebSocket();

    return () => {
      webSocket.close();
    };
  }, [queryClient]);

  return (
    <div className="flex bg-gradient-to-t from-neutral-200 to-neutral-300 rounded-2xl h-fit m-1 overflow-clip">
      <span className="p-3 content-center">Status</span>
      <span
        className={`flex ${query.isPending && "bg-accent"} ${
          query.isError && "bg-error"
        } ${query.isSuccess && "bg-success"} p-3 content-center`}
      >
        <span className="content-center m-1">
          {query.isPending || (query.isFetching && "...")}
          {query.isSuccess && query.data?.status}
          {query.isError && query.error.message}
        </span>
        {!query.isPending && (
          <Button
            onClick={() => {
              queryClient.invalidateQueries();
            }}
            variant={"ghost"}
            size={"icon"}
          >
            <RefreshCcw />
          </Button>
        )}
      </span>
    </div>
  );
}

export default Status;
