import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import ReactMarkdown from 'react-markdown';
import remarkBreaks from 'remark-breaks';

test('commentary treats hostile HTML as text', () => {
  const page = readFileSync(new URL('../app/page.js', import.meta.url), 'utf8');
  assert.doesNotMatch(page, /rehypeRaw|rehype-raw/);
  const hostile = '<iframe srcdoc="<script>alert(1)</script>"></iframe>\n\n<form action="/steal"><input></form>\n\n<style>body{display:none}</style>\n\n<script>alert(1)</script>';
  const html = renderToStaticMarkup(React.createElement(ReactMarkdown, {
    remarkPlugins: [remarkBreaks], children: hostile,
  }));
  assert.doesNotMatch(html, /<(iframe|form|input|style|script)\b/i);
  assert.match(html, /&lt;iframe/);
});
