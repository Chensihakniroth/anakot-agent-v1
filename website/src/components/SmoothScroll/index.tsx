import {useEffect} from 'react';
import Lenis from 'lenis';

/**
 * Smooth inertial scrolling for the landing page.
 *
 * Scoped to the marketing landing only. Docusaurus documentation pages are long
 * runs of prose with working anchor links, where hijacked scrolling makes text
 * harder to track and fights the router's scroll restoration. If it is ever
 * wanted site-wide, mount this in the Root wrapper instead and let Lenis own
 * route changes via `lenis.scrollTo`.
 *
 * Everything here is a no-op under `prefers-reduced-motion`, which is the
 * difference between a smooth-scroll choice and an accessibility regression.
 */
export default function SmoothScroll(): null {
  useEffect(() => {
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
    if (reduced.matches) return;

    const lenis = new Lenis({
      duration: 1.1,
      // Gentle exponential ease-out: settles rather than snapping.
      easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
      smoothWheel: true,
      // Native touch scrolling stays native; hijacking it breaks momentum on iOS.
      syncTouch: false,
      autoRaf: false,
    });

    let raf = requestAnimationFrame(function frame(time) {
      lenis.raf(time);
      raf = requestAnimationFrame(frame);
    });

    // Stop easing out if the user flips the OS setting while the page is open.
    const onChange = () => {
      if (reduced.matches) lenis.destroy();
    };
    reduced.addEventListener('change', onChange);

    return () => {
      cancelAnimationFrame(raf);
      reduced.removeEventListener('change', onChange);
      lenis.destroy();
    };
  }, []);

  return null;
}
