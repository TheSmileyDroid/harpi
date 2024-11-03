import { Button } from "@headlessui/react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { getStatus } from "../api/api";

function Status() {
  const queryClient = useQueryClient();

  const query = useQuery({ queryKey: ["status"], queryFn: getStatus });

  return (
    <div className="inline-flex bg-gradient-to-b bg-slate-400 rounded-2xl h-fit m-1 overflow-clip">
      <span className="p-3">Status</span>
      <span
        className={`${query.isPending && "bg-blue-700"} ${
          query.isError && "bg-red-700"
        } ${query.isSuccess && "bg-green-700"} h-full w-full p-3`}
      >
        {query.isPending && "..."}
        {query.isSuccess && query.data?.status}
        {query.isError && query.error.message}
        {!query.isPending && (
          <Button
            className={"h-fit w-fit bg-transparent m-0 p-0 px-3"}
            onClick={() => {
              queryClient.invalidateQueries({ queryKey: ["status"] });
            }}
          >
            Recarregar
          </Button>
        )}
      </span>
    </div>
  );
}

export default Status;
