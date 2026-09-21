import { useStore } from '@nanostores/react'
import { useEffect } from 'react'
import { $route, $bootstrap, initialize } from './store'
import Welcome from './routes/welcome'
import Progress from './routes/progress'
import Success from './routes/success'
import Failure from './routes/failure'

/*
 * App shell — Anakot Setup.
 *
 * No header chrome (the OS title bar already says "Anakot Setup"; an
 * in-window repeat of the H mark + words was redundant slop).
 *
 * Route state lives in a single $route atom — 4 screens, no react-router.
 * Screen transitions use a fade animation via the anakot-fade-in class
 * applied to each route component.
 */
export default function App() {
  const route = useStore($route)
  const bootstrap = useStore($bootstrap)

  useEffect(() => {
    void initialize()
  }, [])

  return (
    <div className="relative flex h-full flex-col overflow-hidden bg-background text-foreground">
      <main className="relative z-10 flex flex-1 flex-col overflow-hidden">
        {route === 'welcome' && <Welcome />}
        {route === 'progress' && <Progress bootstrap={bootstrap} />}
        {route === 'success' && <Success />}
        {route === 'failure' && <Failure bootstrap={bootstrap} />}
      </main>
    </div>
  )
}
