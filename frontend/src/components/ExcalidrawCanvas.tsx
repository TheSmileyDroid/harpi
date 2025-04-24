import { BASE_URL } from '@/api/ApiClient';
import { store } from '@/store';
import { Excalidraw, exportToBlob } from '@excalidraw/excalidraw';
import type { ExcalidrawElement } from '@excalidraw/excalidraw/types/element/types';
import {
  type AppState,
  type BinaryFileData,
  type BinaryFiles,
  type Collaborator,
  type ExcalidrawImperativeAPI,
} from '@excalidraw/excalidraw/types/types';
import { useStore } from '@tanstack/react-store';
import { useCallback, useEffect, useRef, useState } from 'react';
import { Button } from './ui/button';

// URL base para o WebSocket
const WS_BASE_URL = 'ws' + (location.protocol === 'https:' ? 's' : '') + '://' + BASE_URL + '/ws';

interface CanvasData {
  collaborators?: Map<string, Collaborator>;
  elements: ExcalidrawElement[];
  appState?: AppState;
}

const random_names = [
  'Dragão',
  'Fênix',
  'Unicórnio',
  'Grifo',
  'Quimera',
  'Hidra',
  'Cérbero',
  'Minotauro',
  'Esfinge',
  'Pegasus',
  'Basilisco',
  'Kraken',
  'Ciclopes',
  'Centauro',
  'Sereia',
  'Fúria',
  'Golem',
  'Fada',
];

const random_colors: { [key: string]: string } = {
  Vermelho: '#FF0000',
  Azul: '#0000FF',
  Verde: '#008000',
  Amarelo: '#FFFF00',
  Roxo: '#800080',
  Laranja: '#FFA500',
  Rosa: '#FFC0CB',
  Cinza: '#808080',
  Marrom: '#A52A2A',
  Branco: '#FFFFFF',
};

const getRandomName = () => {
  const randomName = random_names[Math.floor(Math.random() * random_names.length)];
  const randomColor =
    Object.keys(random_colors)[Math.floor(Math.random() * Object.keys(random_colors).length)];
  return `${randomName} ${random_colors[randomColor]}`;
};

/**
 * Componente ExcalidrawCanvas que gerencia um canvas colaborativo usando Excalidraw
 */
export default function ExcalidrawCanvas() {
  const excalidrawApiRef = useRef<ExcalidrawImperativeAPI | null>(null);

  const selectedGuild = useStore(store, (state) => state.guild);

  const [elements, setElements] = useState<ExcalidrawElement[]>([]);
  const [wsConnection, setWsConnection] = useState<WebSocket | null>(null);
  const lastUpdate = useRef<number>(Date.now());
  const [connectionError, setConnectionError] = useState<string | null>(null);

  const [userName, setUserName] = useState<string | null>(null);

  const [collaborators, setCollaborators] = useState<Map<string, Collaborator>>(
    new Map<string, Collaborator>()
  );

  const sentFiles = useRef<BinaryFiles>();

  function mergeIntoElements(receivedElements: ExcalidrawElement[]): ExcalidrawElement[] {
    const mergedElements = new Map<string, ExcalidrawElement>();

    receivedElements.forEach((element) => {
      if (mergedElements.has(element.id)) {
        mergedElements.set(element.id, { ...mergedElements.get(element.id), ...element });
      } else {
        mergedElements.set(element.id, element);
      }
    });

    const mergedElementsArray = Array.from(mergedElements.values());

    setElements(mergedElementsArray);

    return mergedElementsArray;
  }

  useEffect(() => {
    if (!selectedGuild) return;
    if (connectionError) {
      setConnectionError(null);
    }

    const ws = new WebSocket(`${WS_BASE_URL}/ws`);
    const name = getRandomName();
    setUserName(name);

    const color = {
      background: random_colors[name.split(' ')[1]] || '#FF0000',
      stroke: '#000000',
    };

    const collaborator: Collaborator = {
      id: name,
      username: name,
      color: color,
    };

    setCollaborators((prev) => {
      const newCollaborators = new Map(prev);
      newCollaborators.set(name, collaborator);
      return newCollaborators;
    });

    ws.onopen = () => {
      console.log('Conectado ao WebSocket');
      ws.send(JSON.stringify({ type: 'join-canvas', guildId: selectedGuild.id }));
      ws.send(JSON.stringify({ type: 'get-canvas', guildId: selectedGuild.id }));
    };

    ws.onerror = (error) => {
      console.error('Erro de WebSocket:', error);
      setConnectionError('Erro de conexão com o WebSocket');
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        if (!(data.type === 'canvas-update' && data.guildId === selectedGuild.id)) {
          return;
        }

        if (data.timestamp != 0 && !(data.timestamp > lastUpdate.current)) {
          return;
        }

        const canvasData: CanvasData = data.canvasData;

        const mergedCanvasElements = mergeIntoElements(canvasData.elements);

        excalidrawApiRef.current?.updateScene({
          elements: mergedCanvasElements,
          commitToHistory: false,
        });

        const files = JSON.parse(data.files) as BinaryFiles;
        const fileData: BinaryFileData[] = Object.values(files);
        if (fileData && fileData.length > 0) {
          excalidrawApiRef.current?.addFiles(fileData);
        }
        lastUpdate.current = data.timestamp;
      } catch (error) {
        console.error('Erro ao processar mensagem WebSocket:', error);
      }
    };

    ws.onclose = () => {
      console.log('Conexão WebSocket fechada');
      setConnectionError('Conexão com o WebSocket fechada');
    };

    ws.onerror = (error) => {
      console.error('Erro de WebSocket:', error);
    };

    setWsConnection(ws);

    console.log('Conexão WebSocket estabelecida:', ws);

    // Limpar conexão WebSocket ao desmontar
    return () => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.close();
        setWsConnection(null);
      }
    };
  }, [selectedGuild, connectionError]);

  const exportToImage = useCallback(async () => {
    if (!excalidrawApiRef.current) return;

    try {
      const blob = await exportToBlob({
        elements: excalidrawApiRef.current.getSceneElements(),
        mimeType: 'image/png',
        appState: {
          ...excalidrawApiRef.current.getAppState(),
          exportBackground: true,
        },
        files: excalidrawApiRef.current.getFiles(),
      });

      // Criar URL do blob e iniciar download
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `canvas-${selectedGuild?.name || 'harpi'}-${new Date().toISOString().slice(0, 10)}.png`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (error) {
      console.error('Erro ao exportar para imagem:', error);
    }
  }, [excalidrawApiRef, selectedGuild]);

  /**
   * Gerencia mudanças no canvas e sincroniza com outros usuários via WebSocket
   */
  const handleChange = useCallback(
    (newElements: readonly ExcalidrawElement[], _: AppState, files: BinaryFiles) => {
      if (!wsConnection || wsConnection.readyState !== WebSocket.OPEN || !selectedGuild) {
        return;
      }

      const now = Date.now();
      if (now - lastUpdate.current <= 200) {
        return;
      }

      lastUpdate.current = now;

      const appState = excalidrawApiRef.current?.getAppState();
      const activeCollaborators = createCollaboratorsMap();
      setCollaborators(activeCollaborators);

      const canvasData: CanvasData = {
        elements: [...newElements],
        appState,
        collaborators: activeCollaborators,
      };

      const filesToSend: BinaryFiles = {};
      Object.keys(files).forEach((key) => {
        if (sentFiles.current && sentFiles.current[key]) {
          return;
        }

        const file = files[key];
        if (file) {
          filesToSend[key] = file;
        }
      });

      sendCanvasUpdate(canvasData, filesToSend, now);

      sentFiles.current = { ...sentFiles.current, ...filesToSend };
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [wsConnection, selectedGuild, collaborators, userName]
  );

  /**
   * Cria um mapa de colaboradores ativos, incluindo o usuário atual
   */
  const createCollaboratorsMap = (): Map<string, Collaborator> => {
    const activeCollaborators = new Map<string, Collaborator>();

    // Adiciona colaboradores existentes
    collaborators.forEach((collaborator: Collaborator) => {
      const id = collaborator.id ?? 'Anônimo Vermelho';
      activeCollaborators.set(id, {
        ...collaborator,
        username: collaborator.username ?? 'Anônimo Vermelho',
        color: collaborator.color ?? {
          background: '#FF0000',
          stroke: '#000000',
        },
      });
    });

    // Adiciona usuário atual
    const userNameParts = userName?.split(' ') ?? [];
    const colorName = userNameParts[1];
    const backgroundColor = colorName ? (random_colors[colorName] ?? '#FF0000') : '#FF0000';

    const currentUser: Collaborator = {
      id: userName ?? 'Anônimo Vermelho',
      username: userName ?? 'Anônimo Vermelho',
      color: {
        background: backgroundColor,
        stroke: '#000000',
      },
    };

    activeCollaborators.set(userName ?? 'Anônimo Vermelho', currentUser);
    return activeCollaborators;
  };

  /**
   * Envia atualização do canvas para outros usuários via WebSocket
   */
  const sendCanvasUpdate = (
    canvasData: CanvasData,
    files: BinaryFiles,
    timestamp: number
  ): void => {
    if (!wsConnection || !selectedGuild) return;
    console.log('Enviando atualização do canvas:', canvasData);
    wsConnection.send(
      JSON.stringify({
        type: 'canvas-update',
        guildId: selectedGuild.id,
        canvasData,
        files: JSON.stringify(files),
        timestamp,
        user: userName,
      })
    );
  };

  if (!selectedGuild) {
    return (
      <div className="flex h-full items-center justify-center">
        <p>Selecione uma guilda para começar a desenhar</p>
      </div>
    );
  }

  return (
    <div className="flex h-full w-full flex-col">
      <div className="mb-2 flex justify-between">
        <h2 className="text-xl font-bold">
          Canvas Colaborativo - {selectedGuild.name} -{' '}
          <span style={{ color: userName?.split(' ')[1] }}>{userName?.split(' ')[0]}</span>
        </h2>
        <div className="flex gap-2">
          <Button variant="outline" onClick={exportToImage}>
            Exportar como Imagem
          </Button>
        </div>
      </div>

      <div className="min-h-[500px] w-full overflow-hidden rounded-md border border-gray-200">
        <Excalidraw
          excalidrawAPI={(api) => {
            excalidrawApiRef.current = api;
          }}
          initialData={{
            elements,
            appState: { currentItemFontFamily: 1 },
          }}
          onChange={handleChange}
          onPointerUpdate={() => {}}
          viewModeEnabled={false}
          zenModeEnabled={false}
          gridModeEnabled={true}
          isCollaborating={true}
          theme="light"
          renderTopRightUI={() => <div>{collaborators.entries.length} colaboradores</div>}
        />
      </div>
    </div>
  );
}
