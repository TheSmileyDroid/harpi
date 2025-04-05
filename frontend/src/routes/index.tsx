import { createFileRoute } from '@tanstack/react-router';
import GuildControl from '@/components/GuildControl';

export const Route = createFileRoute('/')({
  component: Index,
});

function Index() {
  return <GuildControl />;
}
