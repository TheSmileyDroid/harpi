import { useQuery, useQueryClient } from "@tanstack/react-query";
import { RefreshCcw } from "lucide-react";
import apiClient from "../api/ApiClient";
import { Button } from "./ui/button";

function Status() {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: ["status"],
    queryFn: async () => (await apiClient.api.botStatusApiStatusGet()).data,
  });

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
