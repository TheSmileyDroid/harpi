import type { Key } from 'react';
import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { createFileRoute } from '@tanstack/react-router';
import { 
  Settings, 
  Power, 
  PowerOff,
  Info,
  Activity,
  Clock,
  User,
  Hash,
  CheckCircle,
  XCircle,
  AlertCircle
} from 'lucide-react';
import { motion } from 'motion/react';
import apiClient from '@/api/ApiClient';
import type { CogInfo, CommandUsage } from '@/api/Api';

export const Route = createFileRoute('/settings')({
  component: SettingsPage,
});

function SettingsPage() {
  const [selectedCog, setSelectedCog] = useState<string | null>(null);
  const queryClient = useQueryClient();

  // Query to fetch all cogs
  const { data: cogs, isLoading: loadingCogs } = useQuery({
    queryKey: ['cogs'],
    queryFn: async () => {
      const response = await apiClient.api.getAllCogsApiCogsGet();
      return response.data as Record<string, CogInfo>;
    },
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  // Mutation to toggle cog status
  const toggleCogMutation = useMutation({
    mutationFn: async ({ cogName, enabled }: { cogName: string; enabled: boolean }) => {
      await apiClient.api.toggleCogApiCogsCogNameTogglePost(cogName, { enabled });
    },
    onSuccess: () => {
      // Refresh the cogs data
      queryClient.invalidateQueries({ queryKey: ['cogs'] });
    },
  });

  // Query to fetch usage statistics for selected cog
  const { data: usageStats } = useQuery({
    queryKey: ['cogUsage', selectedCog],
    queryFn: async () => {
      if (!selectedCog) return [];
      const response = await apiClient.api.getCogUsageApiCogsCogNameUsageGet(selectedCog);
      return response.data as CommandUsage[];
    },
    enabled: !!selectedCog,
  });

  const handleToggleCog = (cogName: string, currentStatus: boolean) => {
    toggleCogMutation.mutate({
      cogName,
      enabled: !currentStatus,
    });
  };

  const formatLastUsed = (lastUsed: string | null) => {
    if (!lastUsed) return 'Never';
    try {
      const date = new Date(lastUsed);
      return date.toLocaleString();
    } catch {
      return 'Invalid date';
    }
  };

  const formatUsageCount = (count: number) => {
    if (count === 0) return 'No uses';
    if (count === 1) return '1 use';
    return `${count.toLocaleString()} uses`;
  };

  return (
    <div className="h-full space-y-6 overflow-scroll p-4">
      <motion.h1
        className="text-2xl font-bold flex items-center gap-2"
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <Settings className="h-6 w-6" />
        Cog Management
      </motion.h1>

      {loadingCogs ? (
        <div className="p-8 text-center">Loading cog configurations...</div>
      ) : cogs ? (
        <div className="grid gap-6 lg:grid-cols-2">
          {/* Cog List */}
          <motion.div
            className="victorian-border space-y-4 p-4"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.2 }}
          >
            <h2 className="text-xl font-semibold">Available Cogs</h2>
            
            <div className="space-y-3">
              {Object.entries(cogs).map(([cogName, cogInfo]) => (
                <motion.div
                  key={cogName}
                  className={`victorian-card p-4 cursor-pointer transition-all hover:shadow-lg ${
                    selectedCog === cogName ? 'ring-2 ring-blue-500' : ''
                  }`}
                  onClick={() => setSelectedCog(cogName)}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <h3 className="font-medium">{cogName}</h3>
                        {cogInfo.enabled ? (
                          <CheckCircle className="h-4 w-4 text-green-500" />
                        ) : (
                          <XCircle className="h-4 w-4 text-red-500" />
                        )}
                      </div>
                      <p className="text-sm text-gray-600 mt-1">
                        {cogInfo.description || 'No description available'}
                      </p>
                      <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
                        <span className="flex items-center gap-1">
                          <Hash className="h-3 w-3" />
                          {cogInfo.commands?.length || 0} commands
                        </span>
                        <span className="flex items-center gap-1">
                          <Activity className="h-3 w-3" />
                          {cogInfo.usage_stats?.reduce((sum, stat) => sum + (stat.total_uses || 0), 0) || 0} total uses
                        </span>
                      </div>
                    </div>
                    
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleToggleCog(cogName, cogInfo.enabled || false);
                      }}
                      disabled={toggleCogMutation.isPending}
                      className={`p-2 rounded-full transition-colors ${
                        cogInfo.enabled
                          ? 'bg-green-100 text-green-600 hover:bg-green-200'
                          : 'bg-red-100 text-red-600 hover:bg-red-200'
                      } ${toggleCogMutation.isPending ? 'opacity-50 cursor-not-allowed' : ''}`}
                    >
                      {cogInfo.enabled ? (
                        <Power className="h-4 w-4" />
                      ) : (
                        <PowerOff className="h-4 w-4" />
                      )}
                    </button>
                  </div>
                </motion.div>
              ))}
            </div>

            {toggleCogMutation.isError && (
              <div className="flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded text-red-700">
                <AlertCircle className="h-4 w-4" />
                <span>Failed to toggle cog. Please try again.</span>
              </div>
            )}
          </motion.div>

          {/* Cog Details */}
          <motion.div
            className="victorian-border space-y-4 p-4"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.3 }}
          >
            {selectedCog && cogs[selectedCog] ? (
              <>
                <div className="flex items-center gap-2">
                  <Info className="h-5 w-5" />
                  <h2 className="text-xl font-semibold">{selectedCog} Details</h2>
                </div>

                <div className="space-y-4">
                  {/* Status */}
                  <div className="victorian-card p-3">
                    <h3 className="font-medium mb-2">Status</h3>
                    <div className="flex items-center gap-2">
                      {cogs[selectedCog].enabled ? (
                        <>
                          <CheckCircle className="h-4 w-4 text-green-500" />
                          <span className="text-green-600">Enabled</span>
                        </>
                      ) : (
                        <>
                          <XCircle className="h-4 w-4 text-red-500" />
                          <span className="text-red-600">Disabled</span>
                        </>
                      )}
                    </div>
                  </div>

                  {/* Commands */}
                  <div className="victorian-card p-3">
                    <h3 className="font-medium mb-2">Commands ({cogs[selectedCog].commands?.length || 0})</h3>
                    {cogs[selectedCog].commands && cogs[selectedCog].commands.length > 0 ? (
                      <div className="space-y-2">
                        {cogs[selectedCog].commands.map((command, index: Key) => (
                          <div key={index} className="border-l-2 border-blue-400 pl-3">
                            <div className="font-mono text-sm">-{command.name}</div>
                            <div className="text-xs text-gray-600">{command.description}</div>
                            {command.aliases && command.aliases.length > 0 && (
                              <div className="text-xs text-gray-500">
                                Aliases: {command.aliases.join(', ')}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="text-gray-500 text-sm">No commands available</div>
                    )}
                  </div>

                  {/* Usage Statistics */}
                  <div className="victorian-card p-3">
                    <h3 className="font-medium mb-2 flex items-center gap-2">
                      <Activity className="h-4 w-4" />
                      Usage Statistics
                    </h3>
                    {usageStats && usageStats.length > 0 ? (
                      <div className="space-y-2">
                        {usageStats.map((stat, index: Key) => (
                          <div key={index} className="flex items-center justify-between py-2 border-b border-gray-100 last:border-b-0">
                            <div>
                              <div className="font-mono text-sm">{stat.command_name}</div>
                              <div className="text-xs text-gray-500 flex items-center gap-3">
                                <span className="flex items-center gap-1">
                                  <Hash className="h-3 w-3" />
                                  {formatUsageCount(stat.total_uses || 0)}
                                </span>
                                {stat.last_used && (
                                  <span className="flex items-center gap-1">
                                    <Clock className="h-3 w-3" />
                                    {formatLastUsed(stat.last_used)}
                                  </span>
                                )}
                                {stat.last_user && (
                                  <span className="flex items-center gap-1">
                                    <User className="h-3 w-3" />
                                    {stat.last_user}
                                  </span>
                                )}
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="text-gray-500 text-sm">No usage data available</div>
                    )}
                  </div>
                </div>
              </>
            ) : (
              <div className="text-center text-gray-500 py-8">
                Select a cog from the list to view details
              </div>
            )}
          </motion.div>
        </div>
      ) : (
        <div className="text-center text-red-500 p-8">
          Failed to load cog configurations
        </div>
      )}
    </div>
  );
}