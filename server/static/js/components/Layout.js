import { html } from '../lib.js';
import Sidebar from './Sidebar.js';

export default function Layout({ children }) {
  return html`
    <div class="flex h-screen w-full bg-slate-900 text-slate-100 overflow-hidden">
      <${Sidebar} />
      <main class="flex-1 flex flex-col overflow-hidden relative">
        <div class="flex-1 overflow-y-auto p-6">
          <div class="max-w-5xl mx-auto animate-fade-in">
            ${children}
          </div>
        </div>
      </main>
    </div>
  `;
}
