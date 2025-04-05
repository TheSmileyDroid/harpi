import { useStore } from '@tanstack/react-store';
import clsx from 'clsx';
import { store } from '@/store';
import MusicList from './MusicList';
import VoiceChannels from './VoiceChannels';

function GuildControl({ className }: { className?: string }) {
  const activeGuild = useStore(store, (state) => state.guild);

  return (
    <div className={clsx('w-full', className)}>
      <div className="mx-auto w-full p-0">
        <div className="victorian-border m-3 flex flex-wrap content-center justify-center gap-3 border p-3 text-sm shadow-md">
          <span className="my-auto font-bold">Controle de guilda</span>
          {activeGuild?.name ? (
            <div className="border border-dashed p-3">
              <span className="italic">Guilda ativa:</span> {activeGuild?.name}
            </div>
          ) : (
            <div className="border border-dashed border-error p-3">
              <span className="font-bold italic text-error">Nenhuma guilda ativa</span>
            </div>
          )}
        </div>
      </div>
      {activeGuild?.id && (
        <div className="mx-auto flex w-full flex-wrap">
          <MusicList className="flex-grow" />
          <VoiceChannels className="flex-shrink" />
        </div>
      )}
    </div>
  );
}

export default GuildControl;
