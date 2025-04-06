import { useQuery } from '@tanstack/react-query';
import { createFileRoute } from '@tanstack/react-router';
import { CircleOff, Cpu, Database, HardDrive, Server } from 'lucide-react';
import { motion } from 'motion/react';
import { Api } from '@/api/Api';

// Cria a API usando a baseURL correta
const api = new Api({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
});

export const Route = createFileRoute('/system')({
  component: SystemPage,
});

function SystemPage() {
  // Consulta para buscar o status do sistema
  const { data: systemStatus, isLoading: loadingStatus } = useQuery({
    queryKey: ['systemStatus'],
    queryFn: async () => {
      const response = await api.api.getSystemStatusApiSystemStatusGet();
      return response.data;
    },
    refetchInterval: 10000, // Atualiza a cada 10 segundos
  });

  // Consulta para buscar informações do servidor Minecraft
  const { data: minecraftStatus, isLoading: loadingMinecraft } = useQuery({
    queryKey: ['minecraftStatus'],
    queryFn: async () => {
      const response = await api.api.getMinecraftStatusApiSystemMinecraftGet();
      return response.data;
    },
    refetchInterval: 15000, // Atualiza a cada 15 segundos
  });

  // Consulta para buscar os processos mais ativos
  const { data: topProcesses, isLoading: loadingProcesses } = useQuery({
    queryKey: ['topProcesses'],
    queryFn: async () => {
      const response = await api.api.getTopProcessesApiSystemTopGet();
      return response.data;
    },
    refetchInterval: 5000, // Atualiza a cada 5 segundos
  });

  return (
    <div className="h-full space-y-6 overflow-scroll p-4">
      <motion.h1
        className="text-2xl font-bold"
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        Status do Sistema
      </motion.h1>

      {/* Status do Sistema */}
      <motion.div
        className="victorian-border space-y-4 p-4"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.2 }}
      >
        <h2 className="flex items-center gap-2 text-xl font-semibold">
          <Server className="h-5 w-5" /> Informações do Servidor
        </h2>

        {loadingStatus ? (
          <div className="p-4 text-center">Carregando informações do sistema...</div>
        ) : systemStatus ? (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div className="victorian-card p-3">
              <h3 className="flex items-center gap-2 text-lg font-medium">
                <Cpu className="h-4 w-4" /> CPU e Memória
              </h3>
              <div className="mt-2 space-y-2">
                <div>
                  <div className="text-sm text-gray-500">Uso de CPU</div>
                  <div className="flex items-center">
                    <div className="mr-2 h-2.5 w-full rounded-full bg-gray-200 dark:bg-gray-700">
                      <div
                        className="h-2.5 rounded-full bg-blue-600"
                        style={{ width: `${systemStatus.cpu_percent}%` }}
                      ></div>
                    </div>
                    <span>{systemStatus.cpu_percent.toFixed(1)}%</span>
                  </div>
                </div>

                <div>
                  <div className="text-sm text-gray-500">Uso de Memória</div>
                  <div className="flex items-center">
                    <div className="mr-2 h-2.5 w-full rounded-full bg-gray-200 dark:bg-gray-700">
                      <div
                        className="bg-purple-600 h-2.5 rounded-full"
                        style={{ width: `${systemStatus.memory_percent}%` }}
                      ></div>
                    </div>
                    <span>{systemStatus.memory_percent.toFixed(1)}%</span>
                  </div>
                </div>

                <div className="text-sm">
                  <span className="text-gray-500">Memória Total:</span>{' '}
                  {systemStatus.memory_total.toFixed(2)} GB
                </div>
                <div className="text-sm">
                  <span className="text-gray-500">Memória Usada:</span>{' '}
                  {systemStatus.memory_used.toFixed(2)} GB
                </div>
                <div className="text-sm">
                  <span className="text-gray-500">Uptime:</span> {systemStatus.uptime}
                </div>
              </div>
            </div>

            <div className="victorian-card p-3">
              <h3 className="flex items-center gap-2 text-lg font-medium">
                <HardDrive className="h-4 w-4" /> Discos
              </h3>
              <div className="mt-2 space-y-3">
                {systemStatus.disks.map((disk, index) => (
                  <div key={index}>
                    <div className="text-sm font-medium">{disk.path}</div>
                    <div className="flex items-center">
                      <div className="mr-2 h-2.5 w-full rounded-full bg-gray-200 dark:bg-gray-700">
                        <div
                          className="h-2.5 rounded-full bg-green-600"
                          style={{ width: `${disk.percent}%` }}
                        ></div>
                      </div>
                      <span>{disk.percent.toFixed(1)}%</span>
                    </div>
                    <div className="text-xs text-gray-500">
                      {disk.used.toFixed(1)} GB / {disk.total.toFixed(1)} GB
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div className="text-center text-red-500">
            Não foi possível carregar as informações do sistema
          </div>
        )}
      </motion.div>

      {/* Status do Minecraft */}
      <motion.div
        className="victorian-border space-y-4 p-4"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.3 }}
      >
        <h2 className="flex items-center gap-2 text-xl font-semibold">
          <Database className="h-5 w-5" /> Servidor Minecraft
        </h2>

        {loadingMinecraft ? (
          <div className="p-4 text-center">Carregando informações do servidor Minecraft...</div>
        ) : minecraftStatus ? (
          minecraftStatus.is_running ? (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <div className="victorian-card p-3">
                <h3 className="text-lg font-medium">Informações do Servidor</h3>
                <div className="mt-2 space-y-2">
                  <div className="text-sm">
                    <span className="text-gray-500">Status:</span>{' '}
                    <span className="font-medium text-green-500">Online</span>
                  </div>
                  {minecraftStatus.version && (
                    <div className="text-sm">
                      <span className="text-gray-500">Versão:</span> {minecraftStatus.version}
                    </div>
                  )}
                  {minecraftStatus.cpu_percent && (
                    <div>
                      <div className="text-sm text-gray-500">Uso de CPU</div>
                      <div className="flex items-center">
                        <div className="mr-2 h-2.5 w-full rounded-full bg-gray-200 dark:bg-gray-700">
                          <div
                            className="h-2.5 rounded-full bg-blue-600"
                            style={{ width: `${minecraftStatus.cpu_percent}%` }}
                          ></div>
                        </div>
                        <span>{minecraftStatus.cpu_percent.toFixed(1)}%</span>
                      </div>
                    </div>
                  )}
                  {minecraftStatus.memory_mb && (
                    <div className="text-sm">
                      <span className="text-gray-500">Memória:</span>{' '}
                      {(minecraftStatus.memory_mb / 1024).toFixed(2)} GB
                    </div>
                  )}
                </div>
              </div>

              <div className="victorian-card p-3">
                <h3 className="text-lg font-medium">Jogadores</h3>
                <div className="mt-2 space-y-2">
                  {minecraftStatus.online_players !== null &&
                    minecraftStatus.max_players !== null && (
                      <div className="text-sm">
                        <span className="text-gray-500">Jogadores:</span>{' '}
                        {minecraftStatus.online_players} / {minecraftStatus.max_players}
                      </div>
                    )}

                  {minecraftStatus.players_list && minecraftStatus.players_list.length > 0 ? (
                    <div className="mt-2">
                      <h4 className="text-sm font-medium">Jogadores Online:</h4>
                      <ul className="mt-1 space-y-1 text-sm">
                        {minecraftStatus.players_list.map((player, index) => (
                          <li key={index} className="border-l-2 border-green-400 pl-2">
                            {player.name}
                          </li>
                        ))}
                      </ul>
                    </div>
                  ) : (
                    <div className="text-sm italic text-gray-500">Nenhum jogador online</div>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div className="text-amber-500 flex items-center justify-center gap-2 p-4">
              <CircleOff className="h-5 w-5" />
              <span>Servidor Minecraft está offline</span>
            </div>
          )
        ) : (
          <div className="text-center text-red-500">
            Não foi possível carregar as informações do servidor Minecraft
          </div>
        )}
      </motion.div>

      {/* Processos do Sistema */}
      <motion.div
        className="victorian-border space-y-4 p-4"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.4 }}
      >
        <h2 className="flex items-center gap-2 text-xl font-semibold">
          <Cpu className="h-5 w-5" /> Processos Ativos
        </h2>

        {loadingProcesses ? (
          <div className="p-4 text-center">Carregando informações dos processos...</div>
        ) : topProcesses ? (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead>
                <tr>
                  <th className="px-3 py-2 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                    PID
                  </th>
                  <th className="px-3 py-2 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                    Nome
                  </th>
                  <th className="px-3 py-2 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                    CPU %
                  </th>
                  <th className="px-3 py-2 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                    Mem %
                  </th>
                  <th className="px-3 py-2 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                    Comando
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {topProcesses.processes.map((process, index) => (
                  <tr key={index}>
                    <td className="whitespace-nowrap px-3 py-2 text-xs text-gray-500">
                      {process.pid}
                    </td>
                    <td className="whitespace-nowrap px-3 py-2 text-xs">{process.name}</td>
                    <td className="whitespace-nowrap px-3 py-2 text-xs">
                      <div className="flex items-center">
                        <div className="mr-2 h-1.5 w-16 rounded-full bg-gray-200 dark:bg-gray-700">
                          <div
                            className="h-1.5 rounded-full bg-blue-600"
                            style={{ width: `${Math.min(process.cpu_percent * 5, 100)}%` }}
                          ></div>
                        </div>
                        <span>{process.cpu_percent.toFixed(1)}%</span>
                      </div>
                    </td>
                    <td className="whitespace-nowrap px-3 py-2 text-xs">
                      <div className="flex items-center">
                        <div className="mr-2 h-1.5 w-16 rounded-full bg-gray-200 dark:bg-gray-700">
                          <div
                            className="bg-purple-600 h-1.5 rounded-full"
                            style={{ width: `${Math.min(process.memory_percent * 5, 100)}%` }}
                          ></div>
                        </div>
                        <span>{process.memory_percent.toFixed(1)}%</span>
                      </div>
                    </td>
                    <td className="max-w-xs truncate whitespace-nowrap px-3 py-2 text-xs text-gray-500">
                      {process.command}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="mt-2 text-right text-xs text-gray-500">
              Atualizado em: {new Date(topProcesses.timestamp).toLocaleString()}
            </div>
          </div>
        ) : (
          <div className="text-center text-red-500">
            Não foi possível carregar as informações dos processos
          </div>
        )}
      </motion.div>

      {/* Imagem Top */}
      <motion.div
        className="victorian-border space-y-4 p-4"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.5 }}
      >
        <h2 className="text-xl font-semibold">Visualização do Top</h2>

        <div className="flex justify-center">
          <img
            src={`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/system/top/image`}
            alt="Top Output"
            className="max-w-full rounded border border-gray-300 shadow-sm"
            onError={(e) => {
              e.currentTarget.style.display = 'none';
              document.getElementById('top-image-error')!.style.display = 'block';
            }}
          />
          <div id="top-image-error" className="hidden text-red-500">
            Não foi possível carregar a imagem do top
          </div>
        </div>
      </motion.div>
    </div>
  );
}
