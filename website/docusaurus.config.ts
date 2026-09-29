import {themes as prismThemes} from 'prism-react-renderer';
import type {Config} from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';
import relativeDocLinks from './src/remark/relativeDocLinks';

// Site origin and path prefix are environment-driven so one source tree can be
// built for any host: Railway sets SITE_URL, GitHub Pages and local `npm start`
// fall back to the upstream values. Anything that must resolve absolutely at
// runtime (canonical URLs, sitemap) is derived from these two.
const siteUrl = process.env.SITE_URL || 'https://hermes-agent.nousresearch.com';
const baseUrl = process.env.BASE_URL || '/docs/';

// Where "Download" and "Home" go. Anakot ships no installer of its own — the
// installers in this repo install the fork — so releases are the honest target.
const repoUrl = 'https://github.com/Chensihakniroth/anakot-agent-v1';
const releasesUrl = `${repoUrl}/releases`;
const upstreamUrl = 'https://github.com/NousResearch/hermes-agent';

const config: Config = {
  title: 'Anakot Agent',
  tagline: 'The self-improving AI agent',
  favicon: 'img/favicon.ico',

  url: siteUrl,
  baseUrl,

  organizationName: 'Chensihakniroth',
  projectName: 'anakot-agent-v1',

  onBrokenLinks: 'warn',

  markdown: {
    mermaid: true,
    hooks: {
      onBrokenMarkdownLinks: 'warn',
    },
  },

  i18n: {
    defaultLocale: 'en',
    locales: ['en', 'zh-Hans'],
    localeConfigs: {
      en: {
        label: 'English',
      },
      'zh-Hans': {
        label: '简体中文',
        htmlLang: 'zh-Hans',
      },
    },
  },

  themes: [
    '@docusaurus/theme-mermaid',
  ],

  plugins: [
    [
      '@docusaurus/plugin-client-redirects',
      {
        // Static-host redirects for renamed doc pages (GitHub Pages can't
        // do server-side redirects). Paths are relative to baseUrl (/docs/).
        redirects: [
          {
            // Renamed in #44470 (Automation Blueprints terminology rebrand)
            from: '/guides/automation-templates',
            to: '/guides/automation-blueprints',
          },
          {
            // Moved when the Plugins subcategory was created under
            // Developer Guide > Extending (docs restructure, July 2026)
            from: '/guides/build-a-anakot-plugin',
            to: '/developer-guide/plugins',
          },
          {
            // Users guess these short paths from abbreviated links and hit
            // raw 404s (consumer-onboarding audit finding #1, Aug 2026).
            from: '/quickstart',
            to: '/getting-started/quickstart',
          },
          {
            from: '/installation',
            to: '/getting-started/installation',
          },
        ],
      },
    ],
  ],

  presets: [
    [
      'classic',
      {
        docs: {
          routeBasePath: '/',  // Docs at the root of /docs/
          sidebarPath: './sidebars.ts',
          editUrl: 'https://github.com/Chensihakniroth/anakot-agent-v1/edit/main/website/',
          // Relative `.md` links (readable on GitHub, #114428) must also resolve
          // across the zh-Hans fallback boundary; see src/remark/relativeDocLinks.js.
          beforeDefaultRemarkPlugins: [[relativeDocLinks, {siteDir: __dirname}]],
        },
        blog: false,
        theme: {
          customCss: './src/css/custom.css',
        },
      } satisfies Preset.Options,
    ],
  ],

  themeConfig: {
    image: 'img/anakot-agent-banner.png',
    colorMode: {
      defaultMode: 'dark',
      respectPrefersColorScheme: true,
    },
    docs: {
      sidebar: {
        hideable: true,
        autoCollapseCategories: true,
      },
    },
    navbar: {
      title: 'Anakot Agent',
      logo: {
        alt: 'Anakot Agent',
        src: 'img/anakot-icon.png',
      },
      items: [
        {
          type: 'docSidebar',
          sidebarId: 'docs',
          position: 'left',
          label: 'Docs',
        },
        {
          to: '/skills',
          label: 'Skills',
          position: 'left',
        },
        {
          to: '/plugins',
          label: 'Plugins',
          position: 'left',
        },
        {
          href: releasesUrl,
          label: 'Download',
          position: 'left',
        },
        {
          to: '/getting-started/installation',
          label: 'Get started',
          position: 'right',
          className: 'navbar-cta',
        },
        {
          type: 'localeDropdown',
          position: 'right',
        },
        {
          href: repoUrl,
          label: 'GitHub',
          position: 'right',
        },
        {
          href: 'https://discord.gg/NousResearch',
          label: 'Discord',
          position: 'right',
        },
      ],
    },
    footer: {
      style: 'dark',
      links: [
        {
          title: 'Docs',
          items: [
            { label: 'Getting Started', to: '/getting-started/quickstart' },
            { label: 'User Guide', to: '/user-guide/cli' },
            { label: 'Developer Guide', to: '/developer-guide/architecture' },
            { label: 'Reference', to: '/reference/cli-commands' },
          ],
        },
        {
          title: 'Community',
          items: [
            { label: 'Discord', href: 'https://discord.gg/NousResearch' },
            { label: 'GitHub Issues', href: 'https://github.com/Chensihakniroth/anakot-agent-v1/issues' },
            { label: 'Skills Hub', href: 'https://agentskills.io' },
          ],
        },
        {
          title: 'More',
          items: [
            { label: 'Releases', href: releasesUrl },
            { label: 'GitHub', href: repoUrl },
            // Skills Hub is the agentskills.io open standard and is shared with
            // upstream — deliberately kept as-is.
            { label: 'Skills Hub', href: 'https://agentskills.io' },
            { label: 'Upstream — Hermes', href: upstreamUrl },
          ],
        },
      ],
      copyright: `Anakot Agent · MIT License · ${new Date().getFullYear()} · Fork of <a href="${upstreamUrl}">Hermes</a> by <a href="https://nousresearch.com">Nous Research</a>`,
    },
    prism: {
      theme: prismThemes.github,
      darkTheme: prismThemes.dracula,
      additionalLanguages: ['bash', 'yaml', 'json', 'python', 'toml'],
    },
    mermaid: {
      theme: {light: 'neutral', dark: 'dark'},
    },
  } satisfies Preset.ThemeConfig,
};

export default config;
