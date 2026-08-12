# Estilo do painel: CSS com tokens e ícones de fonte (Bootstrap Icons)

O painel usa CSS manuscrito com design tokens (custom properties em `crt-theme.css`) e classes semânticas (`components.css`), e ícones de fonte Bootstrap Icons (vendored) para todo glyph de UI — zero emoji/símbolo Unicode no painel, zero JS de ícone. Substituiu o Lucide (escolhido no SMI-39), que injeta SVG via JS: exigia re-init manual após swap HTMX (`lucide.createIcons`) e `toSvg()` para DOM criado por JS (toast) — mecanismos que uma fonte real não precisa, pois o glyph é um caractere e renderiza sozinho em qualquer HTML novo.

**Status**: accepted

**Considered Options**: Tailwind — rejeitado: exige build step (o repo não tem nenhum; JS é vendored) e colide com a regra "o nome é a documentação" (soup de utilitários não nomeia design; repetição viola "repetiu, virou factory"); efeitos CRT não são expressáveis como utilitários. Lucide mantido — rejeitado: 408KB e dois mecanismos JS para funcionar com DOM dinâmico. Bootstrap Icons — escolhido: fonte real (~134KB woff2), renderiza sem JS, compatível com swap HTMX e DOM criado por JS, vendored como o resto das libs.

**Consequences**: ícone novo entra como nome BI na config (`NAV_ITEMS`/`SETTINGS_SECTIONS`), nunca como glyph no template; classes `.icon-*` dimensionam por `font-size` (não width/height); o css vendored usa `font-display: block` (sem FOUC de ícone); emojis continuam permitidos nos cogs do Discord (chat, não UI).
