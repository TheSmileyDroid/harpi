import { createFileRoute } from '@tanstack/react-router';
import ExcalidrawCanvas from '@/components/ExcalidrawCanvas';

export const Route = createFileRoute('/canvas')({
  component: CanvasPage,
});

function CanvasPage() {
  return (
    <div className="container mx-auto flex h-[calc(100vh-120px)] flex-col">
      <h1 className="mb-4 text-2xl font-bold">Quadro Colaborativo</h1>

      <p className="text-muted-foreground mb-6 text-sm">
        Desenhe e colabore em tempo real com outros usuários da mesma guilda.
      </p>
      <div className="h-full w-full">
        <ExcalidrawCanvas />
      </div>
    </div>
  );
}
