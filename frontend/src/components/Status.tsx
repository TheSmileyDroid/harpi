import { useEffect } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { RefreshCcw } from 'lucide-react';
import { AnimatePresence, motion } from 'motion/react';
import apiClient, { BASE_URL } from '../api/ApiClient';
import { Button } from './ui/button';

/**
 * Componente responsável por exibir o status do bot.
 */
function Status() {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: ['status'],
    queryFn: async () => (await apiClient.api.botStatusApiStatusGet()).data,
  });

  useEffect(() => {
    const createWebSocket = () => {
      console.log('Creating WebSocket');
      const webSocket = new WebSocket(
        'ws' + (location.protocol === 'https:' ? 's' : '') + '://' + BASE_URL + '/ws'
      );
      webSocket.onopen = () => {
        console.log('WebSocket connected');
      };
      webSocket.onmessage = (event) => {
        const data = JSON.parse(event.data);

        const queryKey = [...data.entity, data.id].filter(Boolean);

        console.log('WS: Invalidating query', queryKey);

        queryClient.invalidateQueries({ queryKey });
      };
      webSocket.onerror = (event) => {
        console.error('WebSocket error', event);
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
    <div className="m-1 flex h-fit overflow-clip bg-gradient-to-t from-neutral-100 to-neutral-300 text-black">
      <span className="hidden content-center p-1 px-2 md:block">Status</span>
      <AnimatePresence mode="wait">
        <motion.span
          key={query.isSuccess ? 'success' : query.isError ? 'error' : 'loading'}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          transition={{ duration: 0.2 }}
          className={`flex ${query.isFetching && 'bg-accent'} ${
            query.isError && 'bg-error'
          } ${query.isSuccess && 'bg-success'} content-center p-1`}
        >
          <span className="m-1 content-center">
            {query.isPending || (query.isFetching && '...')}
            {query.isSuccess && query.data?.status}
            {query.isError && query.error.message}
          </span>
          {!query.isPending && (
            <motion.div whileHover={{ scale: 1.1 }} whileTap={{ scale: 0.9 }}>
              <Button
                onClick={() => {
                  queryClient.invalidateQueries();
                }}
                variant={'ghost'}
                size={'icon'}
                className="border-black text-black hover:border-black/80 hover:text-black/80"
              >
                <RefreshCcw />
              </Button>
            </motion.div>
          )}
        </motion.span>
      </AnimatePresence>
    </div>
  );
}

export default Status;
