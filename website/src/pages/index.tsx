import React, {useCallback, useState} from 'react';
import Layout from '@theme/Layout';
import Link from '@docusaurus/Link';
import Head from '@docusaurus/Head';
import MotionHero from '@site/src/components/MotionHero';
import SmoothScroll from '@site/src/components/SmoothScroll';
import styles from './styles.module.css';

const REPO_URL = 'https://github.com/Chensihakniroth/anakot-agent-v1';

const PLATFORMS = {
  macOS: 'curl -fsSL https://raw.githubusercontent.com/Chensihakniroth/anakot-agent-v1/main/scripts/install.sh | bash',
  Linux: 'curl -fsSL https://raw.githubusercontent.com/Chensihakniroth/anakot-agent-v1/main/scripts/install.sh | bash',
  Windows:
    'iex (irm https://raw.githubusercontent.com/Chensihakniroth/anakot-agent-v1/main/scripts/install.ps1)',
} as const;

type Platform = keyof typeof PLATFORMS;

/**
 * Six capabilities, six cells, laid out on a 12-column grid in two rows of
 * 5/4/3 then 3/4/5. Every row totals exactly 12, so the grid tiles with no holes
 * and no backtracking. Spans are explicit rather than auto-flow: mixing column
 * and row spans makes auto-placement strand cells (the previous version of this).
 * `tint` marks the two cells that carry a gradient so the section has real tonal
 * variation instead of six identical rectangles.
 */
const FEATURES = [
  {
    title: 'Connect',
    body: 'Telegram, Discord, Slack, WhatsApp, Signal, email, CLI, desktop. One agent and one memory across every surface.',
    span: 'span5',
    tint: true,
  },
  {
    title: 'Remember',
    body: 'It learns your projects and writes its own skills from experience, so the second month runs faster than the first.',
    span: 'span4',
    tint: false,
  },
  {
    title: 'Search',
    body: 'Web search, browser automation, vision, image generation, and speech, on any model from any provider.',
    span: 'span3',
    tint: false,
  },
  {
    title: 'Schedule',
    body: 'Reports, backups, and briefings on a natural-language schedule, delivered wherever you already talk.',
    span: 'span3',
    tint: false,
  },
  {
    title: 'Delegate',
    body: 'Isolated subagents with their own conversations and terminals, so a long research run never pollutes your main context.',
    span: 'span4',
    tint: true,
  },
  {
    title: 'Extend',
    body: 'Plugins and MCP servers add capability at the edges without growing the core or breaking your prompt cache.',
    span: 'span5',
    tint: false,
  },
];


const STEPS = [
  {
    title: 'Install',
    body: 'One script. No Docker, no Python environment to manage by hand.',
    command: 'curl -fsSL .../scripts/install.sh | bash',
  },
  {
    title: 'Connect',
    body: 'Point it at a model, then add the surfaces you already use.',
    command: 'anakot setup',
  },
  {
    title: 'Teach it',
    body: 'It writes a skill the first time it works something out, and reuses it after.',
    command: 'anakot skills list',
  },
];

/** Real CLI surface, not invented. Every command here is in the shipped CLI. */
const COMMANDS = [
  { cmd: 'anakot', note: 'Start the terminal agent' },
  { cmd: 'anakot --tui', note: 'Full-screen interface' },
  { cmd: 'anakot setup', note: 'Model, tools, and platform wizard' },
  { cmd: 'anakot doctor', note: 'Diagnose a broken install' },
  { cmd: 'anakot gateway run', note: 'Serve Telegram, Discord, Slack and more' },
  { cmd: 'anakot skills install <id>', note: 'Pull a skill from the hub' },
  { cmd: 'anakot cron create "every 9am"', note: 'Schedule a job' },
  { cmd: 'anakot profile create work', note: 'An isolated agent with its own config' },
];


/** The learning loop, in the order it actually happens. */
const LEARN_STEPS = [
  {
    n: '01',
    title: 'It notices',
    body: 'It keeps the steps and commands you used, not just the answer you got back.',
  },
  {
    n: '02',
    title: 'It writes it down',
    body: 'A markdown file: a title, when to use it, and the procedure. Open it, edit it, delete it — it is a file on disk.',
  },
  {
    n: '03',
    title: 'It uses it again',
    body: 'Next time the same shape of task appears, it loads the skill instead of working it out again.',
  },
];

/** A real skill file, trimmed. This is the actual on-disk format. */
const SKILL_SAMPLE = `---
name: release-notes
description: Draft release notes from merged PRs
---

1. Run \`anakot pr list --since last-tag --merged\`
2. Group by label: feat, fix, chore
3. Draft under each heading, one line per PR
4. Never invent a change that is not in the list`;

const SURFACE_GROUPS = [
  { title: 'Chat', items: ['Telegram', 'Discord', 'Slack', 'Mattermost', 'Matrix'] },
  { title: 'Work', items: ['Microsoft Teams', 'Google Chat', 'Email', 'SMS'] },
  { title: 'Messaging and home', items: ['WhatsApp', 'Signal', 'Home Assistant'] },
];

const FAQS = [
  {
    q: 'Does my data leave my machine?',
    a: 'Only where you send it. Credentials live in your own .env, sessions in a local SQLite store, and you choose the model provider. Nothing is phoned home by the agent itself.',
  },
  {
    q: 'Which models can it use?',
    a: 'Any provider you configure. OpenRouter, Anthropic, OpenAI, Google, DeepSeek, a local model, or your own OpenAI-compatible endpoint. Swap the model mid-session with /model.',
  },
  {
    q: 'What is a skill, exactly?',
    a: 'A markdown file with a procedure in it. The agent writes one when it works out a multi-step task, and you can edit it by hand. Skills are plain files you can read, diff, and share.',
  },
  {
    q: 'Can I run it on a server with no screen?',
    a: 'Yes. Seven terminal backends including Docker, SSH, Modal, and Daytona. The gateway runs headless as a service, and scheduled jobs keep running when you are not logged in.',
  },
];

export default function Home(): React.JSX.Element {
  const [platform, setPlatform] = useState<Platform>('macOS');
  const [copied, setCopied] = useState(false);

  const command = PLATFORMS[platform];
  const copy = useCallback(() => {
    navigator.clipboard?.writeText(command).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1600);
    });
  }, [command]);

  return (
    <Layout
      title="Anakot Agent"
      description="The self-improving AI agent. It writes skills from experience, remembers you across sessions, and runs on every surface you talk to."
    >
      <Head>
        <meta property="og:title" content="Anakot Agent: The Agent That Grows With You" />
      </Head>

      <SmoothScroll />

      <main className={styles.main}>
        {/* One object, the whole page. Fixed to the viewport and flown along a path
            by scroll, so it drifts past every section instead of living in the hero.
            Behind the content, inert, and decorative. */}
        <div className={styles.flyerViewport} aria-hidden="true">
          <div className={styles.flyer}>
            <MotionHero variant="backdrop" />
          </div>
        </div>
        <section className={styles.hero}>
          <div className={styles.heroStage}>
            <p className={styles.wordmark}>Anakot</p>
            <h1 className={styles.title}>
              <span>The agent that</span>
              <span className={styles.titleAccent}>grows with you</span>
            </h1>

            <div className={styles.heroCopy}>
              <p className={styles.lede}>
                Anakot writes skills from experience, improves them as it works, and
                remembers you across every session.
              </p>

              <div className={styles.actions}>
                <Link className={`${styles.button} ${styles.buttonPrimary}`} to="/getting-started/installation">
                  Get started
                </Link>
                <a className={`${styles.button} ${styles.buttonGhost}`} href={`${REPO_URL}/releases`}>
                  Download
                </a>
              </div>
            </div>
          </div>
        </section>

        {/* Install commands, their own band. A headline at this scale plus a terminal
            cannot both sit above the fold, so the commands live just below the hero. */}
        <section className={styles.installBand}>
          <div className={styles.terminal}>
            <div className={styles.terminalTabs} role="tablist" aria-label="Install command per platform">
              {(Object.keys(PLATFORMS) as Platform[]).map((name) => (
                <button
                  key={name}
                  type="button"
                  role="tab"
                  aria-selected={platform === name}
                  className={`${styles.tab} ${platform === name ? styles.tabActive : ''}`}
                  onClick={() => setPlatform(name)}
                >
                  {name}
                </button>
              ))}
            </div>
            <div className={styles.terminalBody}>
              <code className={styles.command}>{command}</code>
              <button
                type="button"
                className={styles.copy}
                onClick={copy}
                aria-label="Copy install command for the selected platform"
              >
                {copied ? 'Copied' : 'Copy'}
              </button>
            </div>
          </div>
        </section>

        {/* Three steps. Real commands, copyable. */}
        <section className={styles.section} aria-labelledby="steps-title">
          <h2 className={styles.sectionTitle} id="steps-title">
            Running in three steps
          </h2>
          <ol className={styles.steps}>
            {STEPS.map((step) => (
              <li key={step.title} className={styles.step}>
                <h3 className={styles.stepTitle}>{step.title}</h3>
                <p className={styles.stepBody}>{step.body}</p>
                <code className={styles.stepCommand}>{step.command}</code>
              </li>
            ))}
          </ol>
        </section>

        {/* Command reference. Every entry is a real shipped command. */}
        <section className={styles.section} aria-labelledby="commands-title">
          <h2 className={styles.sectionTitle} id="commands-title">
            The commands you will actually use
          </h2>
          <ul className={styles.commands}>
            {COMMANDS.map((c) => (
              <li key={c.cmd} className={styles.commandRow}>
                <code className={styles.commandName}>{c.cmd}</code>
                <span className={styles.commandNote}>{c.note}</span>
              </li>
            ))}
          </ul>
        </section>

        {/* Reuse the hero geometry as a quiet backdrop. Copy stays in normal flow:
            no photographic window, clipping, or scroll-dependent readability. */}
        <section className={styles.showcase} aria-labelledby="showcase-title">
          <div className={styles.showcaseStage}>
            <div className={styles.showcaseCopy}>
              <h2 className={styles.showcaseTitle} id="showcase-title">
                <span>It learns</span>
                <span>while you work</span>
              </h2>
              <p className={styles.showcaseLede}>
                Most tools forget everything when the session ends. This one writes
                down what worked, as a file you own, and picks it up next time.
              </p>
              <ol className={styles.learnSteps}>
                {LEARN_STEPS.map((step) => (
                  <li key={step.n} className={styles.learnStep}>
                    <span className={styles.learnNum}>{step.n}</span>
                    <h3 className={styles.learnTitle}>{step.title}</h3>
                    <p className={styles.learnBody}>{step.body}</p>
                  </li>
                ))}
              </ol>
              <figure className={styles.skillSample}>
                <figcaption className={styles.skillCaption}>
                  A skill it wrote for itself
                </figcaption>
                <pre className={styles.skillCode}>
                  <code>{SKILL_SAMPLE}</code>
                </pre>
              </figure>
            </div>
          </div>
        </section>

        {/* Bento: six capabilities, six cells, unequal spans, two tinted. */}
        <section className={styles.section} aria-labelledby="capabilities">
          <h2 className={styles.sectionTitle} id="capabilities">
            What it does
          </h2>
          <div className={styles.grid}>
            {FEATURES.map((f) => (
              <article
                key={f.title}
                className={`${styles.cell} ${styles[f.span]} ${f.tint ? styles.cellTint : ''}`}
              >
                <h3 className={styles.cellTitle}>{f.title}</h3>
                <p className={styles.cellBody}>{f.body}</p>
              </article>
            ))}
          </div>
        </section>

        <section className={styles.section} aria-labelledby="platforms-title">
          <h2 className={styles.sectionTitle} id="platforms-title">
            It talks to all of these
          </h2>
          <ul className={styles.surfaceGroups}>
            {SURFACE_GROUPS.map((group) => (
              <li key={group.title} className={styles.surfaceGroup}>
                <h3 className={styles.surfaceGroupTitle}>{group.title}</h3>
                <ul className={styles.surfaceList}>
                  {group.items.map((name) => (
                    <li key={name} className={styles.surface}>
                      {name}
                    </li>
                  ))}
                </ul>
              </li>
            ))}
          </ul>
        </section>

        <section className={styles.section} aria-labelledby="faq-title">
          <h2 className={styles.sectionTitle} id="faq-title">
            Common questions
          </h2>
          <div className={styles.faq}>
            {FAQS.map((item, i) => (
              <details
                key={item.q}
                className={styles.faqItem}
                // Open the first one so the section never reads as a wall of text.
                {...(i === 0 ? {open: true} : {})}
              >
                <summary className={styles.faqQuestion}>
                  <span>{item.q}</span>
                  <span className={styles.faqIcon} aria-hidden="true" />
                </summary>
                <div className={styles.faqAnswer}>{item.a}</div>
              </details>
            ))}
          </div>
        </section>

        <section className={styles.cta}>
          <div className={styles.ctaInner}>
            <div className={styles.ctaCopy}>
              <h2 className={styles.ctaTitle}>Start in sixty seconds.</h2>
              <p className={styles.ctaBody}>
                One command installs the agent, the desktop app, and every tool it
                needs. No card, no cloud account.
              </p>
            </div>
            <div className={styles.ctaActions}>
              <Link
                className={`${styles.button} ${styles.buttonPrimary}`}
                to="/getting-started/quickstart"
              >
                Read the quickstart
              </Link>
              <Link
                className={`${styles.button} ${styles.buttonGhost}`}
                to="/overview"
              >
                Browse all docs
              </Link>
              <p className={styles.ctaFootnote}>
                macOS, Linux, and Windows. Also available as a Python package.
              </p>
            </div>
          </div>
        </section>
      </main>
    </Layout>
  );
}
