import { createFileRoute } from '@tanstack/react-router';
import { motion } from 'motion/react';

export const Route = createFileRoute('/about')({ component: About });

function About() {
  return (
    <div className="victorian-border mx-auto max-w-3xl p-4">
      <h2 className="mb-4 text-xl">Sobre o Harpi</h2>
      <p className="mb-2">
        Harpi é um bot de Discord avançado com recursos de música, inteligência artificial,
        processamento de voz e muito mais.
      </p>
      <p className="mb-2">
        O Harpi é um projeto open-source desenvolvido por{' '}
        <motion.a
          href="https://github.com/TheSmileyDroid"
          target="_blank"
          rel="noopener noreferrer"
          whileHover={{
            color: 'var(--secondary)',
            textShadow: '0 0 10px var(--secondary)',
            transition: { duration: 0.2 },
          }}
          whileTap={{ scale: 0.95 }}
        >
          <span className="text-[var(--primary)]">TheSmileyDroid</span>
        </motion.a>{' '}
        com o ideia inicial de ser um bot de música, mas com o tempo evoluiu para um bot completo
        com recursos de IA, como processamento de linguagem natural e geração de texto.
      </p>
      <p className="mb-2">
        Este painel de controle permite gerenciar as funções do bot em seus servidores Discord.
      </p>
      <div className="nier-card mt-4 p-4">
        <h3 className="mb-2 text-lg">Tecnologias utilizadas (Frontend)</h3>
        <ul className="list-inside list-disc">
          <li>React com TypeScript</li>
          <li>TanStack Router para navegação</li>
          <li>TanStack Query para gerenciamento de estado</li>
          <li>Tailwind CSS para estilização</li>
        </ul>
        <h3 className="mb-2 mt-4 text-lg">Tecnologias utilizadas (Backend)</h3>
        <ul className="list-inside list-disc">
          <li>Python para o core da aplicação</li>
          <li>Discord.py para integração com o Discord</li>
          <li>FastAPI para a API REST</li>
          <li>WebSockets para comunicação em tempo real</li>
          <li>Integração com modelos de IA para processamento de linguagem natural</li>
        </ul>
      </div>
    </div>
  );
}
